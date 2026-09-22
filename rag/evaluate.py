"""Run the prototype test set and score the answers.

The scores here are diagnostics, not a benchmark. They measure the properties
the prototype is supposed to have - local specificity, grounded citations,
source diversity, and willingness to name gaps - because those are what
separate a local RAG from a general LLM answering from memory.

``locality`` is the headline number. A general-purpose model answering these
questions without the corpus scores near zero on it by construction: it has no
way to name Renner Road, the COTSP, or the SFY 2026-2029 TIP.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .config import CONFIG, EVAL_DIR
from .pipeline import Answer, RAGPipeline

_GAP_HEADING = re.compile(r"what the local evidence does not cover", re.I)
_HEDGE = re.compile(
    r"\b(not (?:available|documented|covered|in|present)|does not (?:contain|cover|say)|"
    r"no (?:data|record|evidence|information)|would (?:have to|need to) be|"
    r"cannot be (?:determined|computed)|this suggests|an inference|not documented)\b", re.I)


@dataclass
class QuestionScore:
    id: int
    question: str
    locality: int = 0                 # distinct local proper nouns used
    local_terms: list[str] = field(default_factory=list)
    probes_hit: int = 0
    probes_total: int = 0
    n_distinct_sources: int = 0
    n_cited: int = 0
    groundedness: float = 0.0
    confidence: float = 0.0
    has_gap_section: bool = False
    n_gap_bullets: int = 0
    hedges: int = 0
    words: int = 0
    elapsed_s: float = 0.0
    warnings: list[str] = field(default_factory=list)

    def verdict(self) -> str:
        """Coarse pass/attention flag over the properties that matter most."""
        problems = []
        if self.locality < 3:
            problems.append("thin local detail")
        if self.groundedness < 0.85:
            problems.append("weak grounding")
        if not self.has_gap_section:
            problems.append("no gap section")
        if self.n_distinct_sources < 3:
            problems.append("narrow sourcing")
        return "OK" if not problems else "CHECK: " + ", ".join(problems)


def score_answer(q: dict, a: Answer, lexicon: list[str]) -> QuestionScore:
    text = a.text
    lowered = text.lower()

    found = sorted({t for t in lexicon if re.search(rf"\b{re.escape(t.lower())}\b", lowered)})
    probes = q.get("probes", [])
    hit = sum(1 for p in probes if p.lower() in lowered)

    gap_match = _GAP_HEADING.search(text)
    bullets = 0
    if gap_match:
        tail = text[gap_match.end():]
        bullets = len([l for l in tail.split("\n") if l.strip().startswith(("-", "*", "•"))])

    return QuestionScore(
        id=q["id"], question=q["question"],
        locality=len(found), local_terms=found,
        probes_hit=hit, probes_total=len(probes),
        n_distinct_sources=a.n_sources, n_cited=len(a.cited_sources()),
        groundedness=round(a.groundedness, 3), confidence=round(a.confidence, 3),
        has_gap_section=bool(gap_match), n_gap_bullets=bullets,
        hedges=len(_HEDGE.findall(text)),
        words=len(text.split()), elapsed_s=round(a.elapsed_s, 1),
        warnings=a.warnings,
    )


def run(out_dir: Path = EVAL_DIR, only: list[int] | None = None) -> dict:
    qs = json.loads((EVAL_DIR / "questions.json").read_text())["questions"]
    lexicon = json.loads((EVAL_DIR / "local_lexicon.json").read_text())["terms"]
    if only:
        qs = [q for q in qs if q["id"] in only]

    pipeline = RAGPipeline()
    print(f"backend={pipeline.llm.name}  embed={pipeline.index.embed_model}  "
          f"passages={len(pipeline.index.passages)}\n")

    scores, transcript, t0 = [], [], time.time()
    for q in qs:
        print(f"[{q['id']:2d}/{len(qs)}] {q['question'][:78]}...", flush=True)
        a = pipeline.answer(q["question"])
        s = score_answer(q, a, lexicon)
        scores.append(s)
        transcript.append({
            "id": q["id"], "question": q["question"], "note": q.get("note", ""),
            "answer": a.text,
            "sources": [src.format() for src in (a.cited_sources() or a.sources)],
            "subqueries": a.subqueries, "score": asdict(s),
        })
        print(f"        locality={s.locality:2d}  sources={s.n_distinct_sources:2d}  "
              f"grounded={s.groundedness:.0%}  gaps={s.n_gap_bullets}  "
              f"{s.elapsed_s:5.1f}s  {s.verdict()}")

    summary = {
        "backend": pipeline.llm.name,
        "embed_model": pipeline.index.embed_model,
        "llm_model": CONFIG.llm_model,
        "n_questions": len(scores),
        "total_s": round(time.time() - t0, 1),
        "mean_locality": round(sum(s.locality for s in scores) / len(scores), 2),
        "mean_sources": round(sum(s.n_distinct_sources for s in scores) / len(scores), 2),
        "mean_groundedness": round(sum(s.groundedness for s in scores) / len(scores), 3),
        "gap_section_rate": round(sum(s.has_gap_section for s in scores) / len(scores), 2),
        "mean_latency_s": round(sum(s.elapsed_s for s in scores) / len(scores), 1),
        "needs_attention": [s.id for s in scores if s.verdict() != "OK"],
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps(
        {"summary": summary, "scores": [asdict(s) for s in scores]}, indent=2))
    (out_dir / "transcript.md").write_text(_render_transcript(summary, transcript))

    print("\n" + "=" * 78)
    for k, v in summary.items():
        print(f"  {k:22s} {v}")
    print(f"\n  wrote {out_dir/'results.json'} and {out_dir/'transcript.md'}")
    return summary


def _render_transcript(summary: dict, rows: list[dict]) -> str:
    out = ["# Columbus / Central Ohio RAG - prototype test transcript", "",
           "| metric | value |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in summary.items()]
    for r in rows:
        s = r["score"]
        out += ["", "---", "", f"## Q{r['id']}. {r['question']}", ""]
        if r["note"]:
            out += [f"> **Test intent:** {r['note']}", ""]
        out += [r["answer"], "", "**Sources**", ""]
        out += [f"- {src}" for src in r["sources"]]
        out += ["", f"<sub>locality {s['locality']} ({', '.join(s['local_terms'][:12])}) · "
                    f"{s['n_distinct_sources']} documents · grounded {s['groundedness']:.0%} · "
                    f"confidence {s['confidence']:.2f} · {s['elapsed_s']}s</sub>"]
    return "\n".join(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Run the Columbus RAG prototype test set.")
    ap.add_argument("--only", type=int, nargs="*", help="run only these question ids")
    args = ap.parse_args()
    run(only=args.only)
