"""End-to-end question answering: retrieve -> diagnose coverage -> generate."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Iterator

import numpy as np

from .config import CONFIG, Config
from .corpus import EVIDENCE_KINDS
from .attribute import (attribute, check_catalog_claims,
                        check_invented_figures, check_scope_claims, fix_glossary)
from .index import HybridIndex
from .llm import BaseLLM, get_llm
from .postprocess import GAP_HEADING, clean
from .prompts import (SYSTEM_PROMPT, build_context, build_gap_prompt,
                      build_user_prompt)
from .retrieve import Hit, Retriever
from .tools import TOOL_KIND, run_tools, tool_hits

_CITE = re.compile(r"\[S(\d+)\]")
#: Small models drift to [5] or [Source 5]; normalise before validating.
_BARE_CITE = re.compile(r"\[(?:source\s*|s\s*)?(\d{1,2})\]", re.I)


def _normalise_citations(text: str, n_sources: int) -> tuple[str, list[str]]:
    """Repair citation markers, then drop any that point outside the context.

    An out-of-range marker is worse than no marker: it looks like provenance
    while pointing at nothing, so it is removed rather than left to mislead.
    """
    warnings: list[str] = []
    text = _BARE_CITE.sub(lambda m: f"[S{int(m.group(1))}]", text)

    stray = {int(n) for n in _CITE.findall(text) if not 1 <= int(n) <= n_sources}
    if stray:
        text = _CITE.sub(
            lambda m: "" if int(m.group(1)) in stray else m.group(0), text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        warnings.append(
            f"removed {len(stray)} citation(s) pointing outside the retrieved context")
    return text, warnings


@dataclass
class Source:
    n: int
    title: str
    organization: str
    locator: str
    url: str
    kind: str
    source_id: str
    cited: bool = False

    def format(self) -> str:
        bits = [f"[S{self.n}] {self.title}"]
        if self.organization:
            bits.append(f"- {self.organization}")
        if self.locator:
            bits.append(f"({self.locator})")
        line = " ".join(bits)
        return f"{line}\n      {self.url}" if self.url else line


@dataclass
class Answer:
    question: str
    text: str
    sources: list[Source]
    subqueries: list[str] = field(default_factory=list)
    confidence: float = 0.0
    groundedness: float = 1.0
    unsupported_claims: list[str] = field(default_factory=list)
    coverage_note: str = ""
    n_sources: int = 0
    elapsed_s: float = 0.0
    #: text of each passage handed to the generator, aligned with ``sources``
    contexts: list[str] = field(default_factory=list)
    backend: str = ""
    warnings: list[str] = field(default_factory=list)
    #: stakeholder profile id the answer was framed for (rag.tools.STAKEHOLDERS)
    stakeholder: str | None = None
    #: metric tool calls made for this question, as ToolResult.to_dict()
    tool_calls: list[dict] = field(default_factory=list)

    def cited_sources(self) -> list[Source]:
        return [s for s in self.sources if s.cited]

    def render(self, show_all_sources: bool = False) -> str:
        out = [self.text.strip(), "", "SOURCES"]
        shown = self.sources if show_all_sources else (self.cited_sources() or self.sources)
        out += ["  " + s.format() for s in shown]
        meta = (f"\n[retrieval confidence {self.confidence:.2f} | "
                f"groundedness {self.groundedness:.0%} | "
                f"{self.n_sources} distinct documents | {self.backend} | {self.elapsed_s:.1f}s]")
        out.append(meta)
        if self.stakeholder or self.tool_calls:
            tools = ", ".join(f"{t['tool']} ({t['location']}, {t['year']})"
                              for t in self.tool_calls) or "none"
            out.append(f"[perspective: {self.stakeholder or 'none'} | metric tools: {tools}]")
        if self.warnings:
            out.append("[warnings] " + "; ".join(self.warnings))
        return "\n".join(out)


@dataclass
class Prepared:
    """Everything the generator needs, built once and shared by answer/stream."""
    prompt: str
    sources: list[Source]
    subqueries: list[str]
    confidence: float
    coverage_note: str
    warnings: list[str]
    kept: list[Hit]
    context: str
    stakeholder: str | None = None
    tool_calls: list[dict] = field(default_factory=list)


def _diagnose(question: str, hits: list[Hit], confidence: float) -> tuple[str, list[str]]:
    """Tell the generator, in advance, how thin its evidence is.

    Without this the model treats six weakly-matched passages exactly like six
    strong ones and answers with the same confidence either way.
    """
    notes, warnings = [], []
    kinds = {h.passage.kind for h in hits}
    n_docs = len({h.passage.source_id for h in hits})

    if confidence < 0.42:
        notes.append(
            "Retrieval matched this question only weakly. The knowledge base may not "
            "cover it. Say so plainly rather than stretching the passages to fit.")
        warnings.append("low retrieval confidence - answer may be under-supported")
    elif confidence < 0.55:
        notes.append("Retrieval support is moderate; hedge claims that rest on a single passage.")

    if kinds == {"data_card"} or (kinds <= {"data_card", "doc_card"}):
        notes.append(
            "Every passage is a catalogue entry, not document text. You can describe what "
            "data and documents exist, but you have no findings to report from them.")
        warnings.append("catalog-only evidence - no document text retrieved")

    if n_docs <= 2:
        notes.append(
            f"All evidence comes from only {n_docs} document(s). Do not present this as a "
            "regional or citywide picture.")

    # Questions that ask about change over time need dated evidence to answer.
    if re.search(r"\btrend|over time|past \d+|changed|历|historical\b", question.lower()):
        years = set()
        for h in hits:
            years.update(re.findall(r"\b(19|20)\d{2}\b", h.passage.text))
        if len(years) < 2:
            notes.append(
                "The retrieved passages carry few explicit years, so any statement about "
                "change over time is weakly dated. Flag that limitation.")
    return " ".join(notes), warnings


class RAGPipeline:
    def __init__(self, index: HybridIndex | None = None, llm: BaseLLM | None = None,
                 cfg: Config = CONFIG):
        self.cfg = cfg
        self.index = index or HybridIndex.load(cfg)
        self.retriever = Retriever(self.index, cfg)
        self.llm = llm if llm is not None else get_llm(cfg)

    # -- metric tools ------------------------------------------------------
    def _run_tools(self, question: str, stakeholder: str | None) -> tuple[list[Hit], list[dict], str | None]:
        """Run the stakeholder metric tools and wrap their output as hits.

        Tool passages go in front of the retrieved ones: the context budget
        truncates from the end, and a metric table the question asked for must
        not be the thing that gets cut. They carry their own vectors, so the
        attribution pass verifies sentences that quote them exactly as it does
        for document text.
        """
        if not self.cfg.tools_enabled:
            return [], [], stakeholder
        results, sid = run_tools(question, stakeholder, limit=self.cfg.max_tool_passages,
                                 auto_detect=self.cfg.tools_auto_detect)
        hits = tool_hits(results, self._encode_batch)
        return hits, [r.to_dict() for r in results], sid

    # -- shared front half ---------------------------------------------
    def _prepare(self, question: str, k: int | None = None,
                 stakeholder: str | None = None) -> Prepared | None:
        # An explicit perspective steers retrieval as well as framing. One
        # guessed from the question's vocabulary only frames the answer: a weak
        # keyword match ("neighborhood" -> residents) must not swap out passages
        # the question itself called for (it cost Q8 its expected source).
        explicit = stakeholder
        thits, tool_calls, stakeholder = self._run_tools(question, stakeholder)
        hits, subqueries = self.retriever.retrieve(question, llm=self.llm, k=k,
                                                   stakeholder=explicit)
        if not hits and not thits:
            return None

        qvec = self.index.encode_query(question, self.cfg)
        sims = [float(self.index.vectors[h.index] @ qvec) for h in hits]
        confidence = float(np.mean(sorted(sims, reverse=True)[:5])) if sims else 0.0

        context, kept = build_context(thits + hits, self.cfg.context_char_budget)
        retrieved = [h for h in kept if h.passage.kind != TOOL_KIND]
        coverage_note, warnings = _diagnose(question, retrieved, confidence)
        if not retrieved:
            coverage_note += (" No document passages were retrieved for this question; "
                              "only metric tool output is available.")
        n_synth = sum(1 for h in kept if h.passage.kind == TOOL_KIND
                      and "synthetic placeholder values" in h.passage.caveats)
        if n_synth:
            warnings = warnings + [
                f"{n_synth} metric passage(s) are synthetic placeholder tool output, not measured data"]
        prompt = build_user_prompt(question, context, coverage_note, stakeholder)

        sources = [
            Source(n=i + 1, title=h.passage.title, organization=h.passage.organization,
                   locator=h.passage.locator, url=h.passage.citation_url,
                   kind=h.passage.kind, source_id=h.passage.source_id)
            for i, h in enumerate(kept)
        ]
        return Prepared(prompt, sources, subqueries, confidence, coverage_note, warnings,
                        kept, context, stakeholder, tool_calls)

    def _passage_vectors(self, kept: list[Hit]) -> np.ndarray:
        return np.stack([h.vector if h.vector is not None else self.index.vectors[h.index]
                         for h in kept])

    def _finish(self, question, text, sources, subqueries, confidence, coverage_note,
                warnings, kept, t0, context="", stakeholder=None, tool_calls=None) -> Answer:
        text, clean_warnings = clean(text)
        warnings = warnings + clean_warnings
        if self.llm.available and GAP_HEADING not in text:
            bullets = self._generate_gaps(question, context, text)
            if bullets:
                text += f"\n\n{GAP_HEADING}\n" + bullets
                warnings = warnings + ["evidence-gap section generated in a second pass"]
            else:
                text += "\n\n" + self._fallback_gaps(kept, coverage_note)
                warnings = warnings + ["model omitted the evidence-gap section; "
                                       "substituted one derived from retrieval"]
        text, n_fixed = fix_glossary(text)
        if n_fixed:
            warnings = warnings + [f"corrected {n_fixed} misexpanded local acronym(s)"]
        text, repair_warnings = _normalise_citations(text, len(sources))
        warnings = warnings + repair_warnings

        # Verify every factual sentence against the passages it is supposed to
        # rest on, and rewrite the citation markers from that verification.
        groundedness, unsupported = 1.0, []
        if self.llm.available and sources:
            pvecs = self._passage_vectors(kept)
            text, attributions, summary = attribute(
                text, pvecs, lambda xs: self._encode_batch(xs))
            groundedness = summary["grounded_fraction"]
            unsupported = [a.text for a in attributions if not a.supported]

            # Figures credited only to a GIS catalogue entry cannot be real:
            # those records are not in the knowledge base.
            bogus = check_catalog_claims(attributions, [h.passage.kind for h in kept])
            if bogus:
                warnings = warnings + [
                    f"{len(bogus)} figure(s) attributed only to a dataset catalogue "
                    "entry, whose records are not loaded - treat as unverified"]

            texts = [h.passage.text for h in kept]
            for _num, msg in check_scope_claims(attributions, texts):
                warnings = warnings + ["geographic scope mismatch: " + msg]
                unsupported.append(msg)
            invented = check_invented_figures(attributions, texts)
            if invented:
                warnings = warnings + [
                    "figures not found in any cited passage: " + ", ".join(invented[:6])]
            if unsupported:
                warnings = warnings + [
                    f"{len(unsupported)} of {summary['total']} sentences not supported "
                    "by retrieved evidence (marked inline)"]
        cited = {int(n) for n in _CITE.findall(text)}
        for s in sources:
            s.cited = s.n in cited
        if not cited and self.llm.available:
            warnings = warnings + ["model produced no [S#] citations"]
        # The prompt asks the model to say once that tool figures are placeholders;
        # a small model does not do it reliably, so the answer says it itself.
        synthetic_cited = [f"[S{h_i + 1}]" for h_i, h in enumerate(kept)
                           if (h_i + 1) in cited and h.passage.kind == TOOL_KIND
                           and "synthetic placeholder values" in h.passage.caveats]
        if synthetic_cited:
            text = (f"Note: the figures cited to {', '.join(synthetic_cited)} are synthetic "
                    "placeholder output from stub metric tools, not measured data.\n\n" + text)
        return Answer(
            question=question, text=text, sources=sources, subqueries=subqueries,
            confidence=confidence, groundedness=groundedness,
            unsupported_claims=unsupported, coverage_note=coverage_note,
            n_sources=len({h.passage.source_id for h in kept if h.passage.kind != TOOL_KIND}),
            elapsed_s=time.time() - t0, backend=self.llm.name, warnings=warnings,
            stakeholder=stakeholder, tool_calls=list(tool_calls or []),
            contexts=[h.passage.text for h in kept],
        )

    # -- public API -----------------------------------------------------
    def answer(self, question: str, k: int | None = None,
               stakeholder: str | None = None) -> Answer:
        """Answer ``question``; ``stakeholder`` is a profile id from
        ``rag.tools.STAKEHOLDERS`` (auto-detected from the question when None)."""
        t0 = time.time()
        p = self._prepare(question, k, stakeholder)
        if p is None:
            return Answer(question=question, text="Nothing in the knowledge base matched "
                          "that question.", sources=[], backend=self.llm.name,
                          elapsed_s=time.time() - t0)

        if self.llm.available:
            text = self._generate_with_body(p.prompt)
        else:
            text = self._extractive(p.kept)
        return self._finish(question, text, p.sources, p.subqueries, p.confidence,
                            p.coverage_note, p.warnings, p.kept, t0, p.context,
                            p.stakeholder, p.tool_calls)

    def stream(self, question: str, k: int | None = None,
               stakeholder: str | None = None) -> Iterator[tuple[str, object]]:
        """Yield ('stage', dict) progress, ('token', str) chunks, then ('answer', Answer).

        A full answer takes minutes on a laptop; the stages are what tell the
        person it is still working, and on what.
        """
        t0 = time.time()
        yield "stage", {"stage": "searching"}
        p = self._prepare(question, k, stakeholder)
        if p is None:
            yield "answer", Answer(question=question, text="Nothing in the knowledge base "
                                   "matched that question.", sources=[], backend=self.llm.name)
            return
        kept, sources = p.kept, p.sources
        yield "stage", {"stage": "retrieved", "passages": len(kept),
                        "documents": len({h.passage.source_id for h in kept
                                          if h.passage.kind != TOOL_KIND}),
                        "titles": list(dict.fromkeys(s.title for s in sources)),
                        "stakeholder": p.stakeholder,
                        "tools": [t["tool"] for t in p.tool_calls]}

        parts: list[str] = []
        if self.llm.available:
            yield "stage", {"stage": "writing"}
            for tok in self.llm.stream(p.prompt, system=SYSTEM_PROMPT):
                parts.append(tok)
                yield "token", tok
            if not self._has_body("".join(parts)):
                parts = [self._generate_with_body(p.prompt)]
        else:
            text = self._extractive(kept)
            parts.append(text)
            yield "token", text
        yield "stage", {"stage": "checking"}
        yield "answer", self._finish(question, "".join(parts), sources, p.subqueries,
                                     p.confidence, p.coverage_note, p.warnings, kept, t0,
                                     p.context, p.stakeholder, p.tool_calls)

    def _generate_gaps(self, question: str, context: str, answer: str) -> str:
        """Ask for the gap section on its own.

        Asking for answer and gaps in one shot makes a small model trade them
        off - it writes a good answer and forgets the section, or leads with
        the section and never writes the answer. Splitting the request removes
        the competition and produces sharper gaps than a templated fallback.
        """
        if not context or not self.cfg.gap_second_pass:
            return ""
        try:
            raw = self.llm.generate(
                build_gap_prompt(question, context, answer),
                system=SYSTEM_PROMPT, max_tokens=320, temperature=0.3)
        except Exception:
            return ""
        from .postprocess import _is_bullet, _is_echoed_example
        bullets = [l.rstrip() for l in raw.split("\n")
                   if _is_bullet(l) and not _is_echoed_example(l)]
        return "\n".join(bullets[:4])

    @staticmethod
    def _fallback_gaps(kept: list[Hit], coverage_note: str) -> str:
        """Deterministic gap section for when the model drops its own.

        Everything here is derived from what retrieval actually did, so it
        states real limitations rather than plausible-sounding ones.
        """
        bullets = []
        catalogs = sorted({h.passage.title for h in kept
                           if h.passage.kind == "data_card"})
        if catalogs:
            bullets.append(
                "- Only catalogue entries are loaded for "
                + ", ".join(catalogs[:3])
                + ". Any count, rate or trend from them would have to be computed by "
                  "querying the service endpoint directly.")
        docs = sorted({h.passage.title for h in kept if h.passage.kind in EVIDENCE_KINDS})
        if docs:
            bullets.append(f"- This answer rests on {len(docs)} document(s); other local "
                           "plans, project records and public feedback were not retrieved "
                           "for it and may qualify these findings.")
        if coverage_note:
            bullets.append(f"- Retrieval diagnostic: {coverage_note.strip()}")
        if not bullets:
            bullets.append("- No specific evidence gaps could be derived from retrieval.")
        return GAP_HEADING + "\n" + "\n".join(bullets)

    @staticmethod
    def _has_body(text: str) -> bool:
        """True if there is an actual answer, not just the gap section."""
        body = clean(text)[0].split(GAP_HEADING)[0]
        return len(body.split()) >= 25

    def _generate_with_body(self, prompt: str) -> str:
        """Generate, and retry once if the model returned only a gap section.

        Recency bias makes small models start with whatever the prompt
        mentioned last, so they sometimes emit the closing section and stop.
        One corrective retry is far cheaper than shipping an empty answer.
        """
        text = self.llm.generate(prompt, system=SYSTEM_PROMPT)
        if self._has_body(text):
            return text
        retry = (prompt + "\n\nYour previous attempt contained only the closing "
                 "'what the local evidence does not cover' section. Write the substantive "
                 "answer this time: several paragraphs citing the passages, with that "
                 "section appearing once, at the very end.")
        second = self.llm.generate(retry, system=SYSTEM_PROMPT)
        return second if self._has_body(second) else text

    def _encode_batch(self, texts: list[str]) -> np.ndarray:
        """Embed answer sentences in the passage space (no query prefix)."""
        if self.index._encoder is None:
            from sentence_transformers import SentenceTransformer
            self.index._encoder = SentenceTransformer(self.index.embed_model)
        return np.asarray(self.index._encoder.encode(
            texts, normalize_embeddings=True, show_progress_bar=False), dtype=np.float32)

    @staticmethod
    def _extractive(kept: list[Hit]) -> str:
        lines = ["No language model is loaded, so this is the retrieved evidence rather "
                 "than a synthesis.\n"]
        for i, h in enumerate(kept, 1):
            snippet = " ".join(h.passage.text.split())[:400]
            lines.append(f"[S{i}] {h.passage.title} - {h.passage.locator}\n    {snippet}...\n")
        return "\n".join(lines)
