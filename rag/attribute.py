"""Post-hoc citation attribution and groundedness checking.

Asking a 3B instruct model to place [S#] markers correctly after every factual
sentence does not work reliably - it drops them, renumbers them, or turns them
into paragraph labels. So citation is treated as a verification problem rather
than a generation problem:

1. split the answer into sentences;
2. embed each one and score it against every retrieved passage;
3. attach the passages that actually support it;
4. flag sentences nothing supports.

Step 4 is the valuable one. It catches claims the model invented - the
expansion of "HIN" into "High Impact Neighborhood" instead of "High Injury
Network" is exactly the kind of fluent, plausible, wrong sentence that scores
poorly against every real passage.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\[])")
_CITE = re.compile(r"\[S(\d+)\]")
_HEADING = re.compile(r"^\s*(\*\*|#|-\s*$)")

#: Below this cosine similarity to its best-matching passage, a sentence is
#: treated as unsupported by the retrieved evidence.
SUPPORT_THRESHOLD = 0.50
#: A second passage is cited alongside the best one if it comes this close.
CO_CITE_MARGIN = 0.04


#: A figure sourced ONLY to a dataset catalogue entry is unsupported by
#: construction - the records were never loaded, so no count, rate or year
#: can have come from it. This is the one hallucination the similarity check
#: cannot see: the sentence is topically perfect and still fabricated.
_FIGURE = re.compile(r"\b\d{1,3}(?:,\d{3})+\b|\b\d+(?:\.\d+)?\s?%|\b\d{2,}\b")


def check_catalog_claims(attributions: list["SentenceAttribution"],
                         kinds: list[str]) -> list[str]:
    """Return sentences that quote a figure sourced only to a catalogue entry."""
    offenders = []
    for a in attributions:
        if not a.citations or not _FIGURE.search(a.text):
            continue
        cited_kinds = {kinds[c - 1] for c in a.citations if 1 <= c <= len(kinds)}
        if cited_kinds and cited_kinds <= {"data_card"}:
            offenders.append(a.text)
    return offenders


#: Scope markers. This corpus constantly sets a national statistic beside a
#: regional one - "177,409 people across the U.S. ... Central Ohio has seen
#: similarly concerning trends" - so the likeliest serious error is not an
#: invented number but a real one re-scoped to the wrong geography. Similarity
#: attribution cannot see that: the sentence matches the passage almost
#: perfectly, because the number really is in it.
_NATIONAL = re.compile(
    r"\b(?:U\.?S\.?A?\b|United States|nationally|nationwide|national(?:ly)?|"
    r"across the country|in the country)", re.I)
_LOCAL = re.compile(
    r"\b(?:Central Ohio|Columbus|Franklin County|Delaware County|Licking County|"
    r"Fairfield County|Union County|MPO planning area|the region|regional|"
    r"MORPC(?:\'s)? (?:planning )?area|locally)\b", re.I)
#: Statistics, not dates. A bare four-digit year is not a figure that can be
#: mis-scoped, and treating it as one makes every sentence that names a study
#: period look like a scope error.
_NUMBER = re.compile(r"\b\d{1,3}(?:,\d{3})+\b|\b(?!(?:1[89]|20)\d{2}\b)\d{3,}\b")
#: The scope that governs a figure is the sentence it sits in, plus the one
#: before it (scope is routinely inherited: "...across the U.S. ... In that
#: same time frame, 32,674 pedestrians were killed"). A fixed character window
#: is too blunt - it reaches into the neighbouring contrast sentence and reads
#: as both scopes at once, so every real mismatch gets skipped as ambiguous.
#: Requires a capital after the break, so "the U.S. died in a crash" is not
#: split at the abbreviation - which would strip the very scope word the check
#: depends on.
_SENT_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")


def _scope_of(text: str) -> set[str]:
    scopes = set()
    if _NATIONAL.search(text):
        scopes.add("national")
    if _LOCAL.search(text):
        scopes.add("local")
    return scopes


def _governing_span(body: str, pos: int) -> str:
    """The sentence containing offset ``pos``, plus the preceding sentence."""
    starts = [0] + [m.end() for m in _SENT_BOUNDARY.finditer(body)]
    ends = [m.start() for m in _SENT_BOUNDARY.finditer(body)] + [len(body)]
    for i, (a, b) in enumerate(zip(starts, ends)):
        if a <= pos < b:
            return body[starts[i - 1] if i else a: b]
    return body[max(0, pos - 200): pos + 200]


def check_scope_claims(attributions: list["SentenceAttribution"],
                       passage_texts: list[str]) -> list[tuple[str, str]]:
    """Find figures the answer re-scoped between national and local.

    For each large number in a sentence, locate that same number in the cited
    passages and read the scope words around it. If the passage frames the
    figure nationally and the sentence frames it locally (or the reverse), the
    claim is wrong however well it matches on similarity.
    """
    problems: list[tuple[str, str]] = []
    for a in attributions:
        sent_scope = _scope_of(a.text)
        if not sent_scope or len(sent_scope) != 1:
            continue                      # no scope, or the sentence says both
        for raw in _NUMBER.findall(a.text):
            for c in a.citations:
                if not 1 <= c <= len(passage_texts):
                    continue
                body = passage_texts[c - 1]
                pos = body.find(raw)
                if pos < 0:
                    continue
                src_scope = _scope_of(_governing_span(body, pos))
                if len(src_scope) == 1 and src_scope != sent_scope:
                    problems.append((
                        raw,
                        f"answer frames {raw} as {next(iter(sent_scope))} but [S{c}] "
                        f"reports it as {next(iter(src_scope))}"))
                    break
    return problems


def check_invented_figures(attributions: list["SentenceAttribution"],
                           passage_texts: list[str]) -> list[str]:
    """Large numbers in the answer that appear in no cited passage."""
    missing = []
    for a in attributions:
        cited = " ".join(passage_texts[c - 1] for c in a.citations
                         if 1 <= c <= len(passage_texts))
        for raw in _NUMBER.findall(a.text):
            if raw not in cited and raw.replace(",", "") not in cited.replace(",", ""):
                missing.append(raw)
    return sorted(set(missing))


@dataclass
class SentenceAttribution:
    text: str
    citations: list[int]          # 1-based passage numbers
    support: float                # cosine similarity to best passage
    supported: bool
    model_cited: list[int]        # whatever the model itself claimed


def _split_sentences(text: str) -> list[str]:
    out: list[str] = []
    for block in text.split("\n"):
        block = block.rstrip()
        if not block.strip():
            out.append("")
            continue
        # Keep bullets and headings whole; they are not prose sentences.
        if _HEADING.match(block) or block.lstrip().startswith(("-", "*", "•")):
            out.append(block)
            continue
        out.extend(_SENT_SPLIT.split(block))
    return out


def _is_factual(sentence: str) -> bool:
    """Skip headings, bullets-without-claims, and connective filler."""
    s = sentence.strip()
    if len(s.split()) < 6:
        return False
    if s.startswith(("**", "#")):
        return False
    return True


def attribute(answer_text: str, passage_vectors: np.ndarray, encoder,
              threshold: float = SUPPORT_THRESHOLD) -> tuple[str, list[SentenceAttribution], dict]:
    """Rewrite ``answer_text`` with verified [S#] markers.

    Returns the rewritten text, per-sentence attributions, and a summary dict.
    """
    pieces = _split_sentences(answer_text)
    factual_idx = [i for i, s in enumerate(pieces) if _is_factual(s)]
    if not factual_idx or passage_vectors.size == 0:
        return answer_text, [], {"grounded": 0, "total": 0, "grounded_fraction": 1.0}

    # Strip the model's own markers before embedding - they are noise, and any
    # that were correct will be recovered by the similarity match anyway.
    clean = [_CITE.sub("", pieces[i]).strip() for i in factual_idx]
    vecs = encoder(clean)                                   # (m, d) normalised
    sims = vecs @ passage_vectors.T                         # (m, n_passages)

    attributions: list[SentenceAttribution] = []
    for row, i in enumerate(factual_idx):
        scores = sims[row]
        best = int(np.argmax(scores))
        best_score = float(scores[best])
        cites = [best + 1]
        # co-cite a close runner-up from a different passage
        for j in np.argsort(-scores)[1:3]:
            if best_score - float(scores[j]) <= CO_CITE_MARGIN:
                cites.append(int(j) + 1)
        supported = best_score >= threshold
        model_cited = [int(n) for n in _CITE.findall(pieces[i])]

        attributions.append(SentenceAttribution(
            text=clean[row], citations=cites if supported else [],
            support=best_score, supported=supported, model_cited=model_cited,
        ))

        if supported:
            marker = "".join(f"[S{c}]" for c in sorted(set(cites)))
            body = clean[row]
            # place the marker inside the terminal punctuation
            m = re.search(r"([.!?])\s*$", body)
            pieces[i] = f"{body[:m.start()]} {marker}{m.group(1)}" if m else f"{body} {marker}"
        else:
            pieces[i] = f"{clean[row]} [unsupported by retrieved evidence]"

    total = len(attributions)
    grounded = sum(a.supported for a in attributions)
    summary = {
        "grounded": grounded,
        "total": total,
        "grounded_fraction": grounded / total if total else 1.0,
        "mean_support": float(np.mean([a.support for a in attributions])) if total else 0.0,
    }
    return "\n".join(pieces), attributions, summary


#: Acronym expansions a small model reliably gets wrong. Similarity-based
#: attribution cannot catch these - "Metropolitan Regional Planning
#: Commission" sits right next to the correct name in embedding space - so
#: they are corrected by rule.
GLOSSARY_FIXES: tuple[tuple[str, str], ...] = (
    (r"Metropolitan\s+Regional\s+Planning\s+Commission", "Mid-Ohio Regional Planning Commission"),
    (r"Mid[- ]Ohio\s+Regional\s+Planning\s+Council", "Mid-Ohio Regional Planning Commission"),
    (r"High\s+Impact\s+Neighborhood", "High Injury Network"),
    (r"High\s+Injury\s+Neighborhood", "High Injury Network"),
    (r"Central\s+Ohio\s+Transit\s+Association", "Central Ohio Transit Authority"),
    (r"Ohio\s+Department\s+of\s+Transport\b", "Ohio Department of Transportation"),
    (r"Safe\s+Streets\s+for\s+All\s+\(SS4A\)", "Safe Streets and Roads for All (SS4A)"),
)


def fix_glossary(text: str) -> tuple[str, int]:
    n = 0
    for pattern, correct in GLOSSARY_FIXES:
        text, count = re.subn(pattern, correct, text, flags=re.I)
        n += count
    return text, n
