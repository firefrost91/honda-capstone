"""Regression gate for the evaluation questions.

Three tiers, cheapest first. Each compares the current state against a
committed baseline and exits non-zero on regression, so it can sit in CI or a
pre-push hook:

``corpus``     no index, no model. Every index-eligible catalogued document
               still contributes passages; the passage count has not dropped
               more than ``CORPUS_DROP_TOLERANCE``; every expected source a
               question names still exists. Catches a data change that
               silently loses a document.
``retrieval``  needs the index and the embedding model, no LLM. Deterministic
               (rule-based query planning only). Per question: recall of the
               ``expected_sources`` in the final context, number of distinct
               documents, share of real document text. Catches retrieval,
               chunking and embedding regressions in seconds.
``answers``    full pipeline with the LLM (minutes). Locality, groundedness,
               gap section, ``must_mention_any`` and ``forbidden`` strings.

    python -m rag.regress                       # corpus + retrieval, vs baseline
    python -m rag.regress --tier all            # + answers (slow)
    python -m rag.regress --update-baseline     # accept the current state
    python -m rag.regress --only 3 7

New questions (no baseline entry yet) are held to the absolute checks only and
listed as "new" until the baseline is updated.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from dataclasses import replace
from pathlib import Path

from .config import CONFIG, EVAL_DIR, Config

BASELINE_CORPUS = EVAL_DIR / "baseline_corpus.json"
BASELINE_RETRIEVAL = EVAL_DIR / "baseline_retrieval.json"
BASELINE_ANSWERS = EVAL_DIR / "baseline_answers.json"

#: Allowed movement in the bad direction before a check fails.
CORPUS_DROP_TOLERANCE = 0.05          # fraction of passages
RECALL_TOLERANCE = 0.10               # per question, absolute
MEAN_RECALL_TOLERANCE = 0.05
DISTINCT_SOURCES_TOLERANCE = 2
LOCALITY_TOLERANCE = 2                # per question, local proper nouns
MEAN_LOCALITY_TOLERANCE = 1.0
MIN_GROUNDEDNESS = 0.85               # absolute


def load_questions(only: list[int] | None = None) -> list[dict]:
    qs = json.loads((EVAL_DIR / "questions.json").read_text())["questions"]
    return [q for q in qs if not only or q["id"] in only]


def _read(path: Path) -> dict | None:
    return json.loads(path.read_text()) if path.exists() else None


def _write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------
# tier 1: corpus
# --------------------------------------------------------------------------

def corpus_snapshot(cfg: Config = CONFIG) -> dict:
    from .corpus import load_document_catalog, load_gis_catalog, load_passages
    passages = load_passages(cfg)
    by_source = Counter(p.source_id for p in passages if p.kind != "doc_card"
                        and p.kind != "data_card")
    docs = load_document_catalog(cfg)
    return {
        "n_passages": len(passages),
        "by_kind": dict(Counter(p.kind for p in passages)),
        "evidence_by_source": dict(sorted(by_source.items())),
        "eligible_without_passages": sorted(
            sid for sid, d in docs.items() if d.get("index_eligible") and not by_source.get(sid)),
        "known_source_ids": sorted(set(docs) | set(load_gis_catalog(cfg))
                                   | {p.source_id for p in passages}),
    }


def check_corpus(cur: dict, base: dict | None, questions: list[dict]) -> list[str]:
    fails = []
    if cur["eligible_without_passages"]:
        fails.append("index-eligible documents with no passages: "
                     + ", ".join(cur["eligible_without_passages"]))
    known = set(cur["known_source_ids"])
    for q in questions:
        missing = [s for s in q.get("expected_sources", []) if s not in known]
        if missing:
            fails.append(f"Q{q['id']}: expected source(s) not in the corpus: {', '.join(missing)}")
    if base:
        floor = base["n_passages"] * (1 - CORPUS_DROP_TOLERANCE)
        if cur["n_passages"] < floor:
            fails.append(f"passage count fell {base['n_passages']} -> {cur['n_passages']}")
        lost = [s for s, n in base["evidence_by_source"].items()
                if n and not cur["evidence_by_source"].get(s)]
        if lost:
            fails.append("sources that lost all their passages: " + ", ".join(lost))
    return fails


# --------------------------------------------------------------------------
# tier 2: retrieval
# --------------------------------------------------------------------------

def deterministic_config(cfg: Config = CONFIG) -> Config:
    """Rule-based planning, no LLM: the same question always retrieves the same set."""
    return replace(cfg, use_query_planner=False, llm_backend="none")


def retrieval_snapshot(questions: list[dict], cfg: Config = CONFIG, index=None) -> dict:
    from .corpus import EVIDENCE_KINDS
    from .index import HybridIndex
    from .retrieve import Retriever
    cfg = deterministic_config(cfg)
    index = index or HybridIndex.load(cfg)
    retriever = Retriever(index, cfg)
    out = {}
    for q in questions:
        hits, _ = retriever.retrieve(q["question"], llm=None)
        sids = [h.passage.source_id for h in hits]
        out[str(q["id"])] = score_retrieval(q, sids, [h.passage.kind for h in hits],
                                            [h.passage.passage_id for h in hits], EVIDENCE_KINDS)
    return out


def score_retrieval(q: dict, source_ids: list[str], kinds: list[str],
                    passage_ids: list[str], evidence_kinds=frozenset({"chunk", "data_summary"})) -> dict:
    got = set(source_ids)
    exp = q.get("expected_sources") or []
    asp = q.get("aspirational_sources") or []
    return {
        "expected_recall": round(sum(s in got for s in exp) / len(exp), 3) if exp else None,
        "missing_expected": [s for s in exp if s not in got],
        "aspirational_recall": round(sum(s in got for s in asp) / len(asp), 3) if asp else None,
        "n_distinct_sources": len(got),
        "evidence_fraction": round(sum(k in evidence_kinds for k in kinds) / max(len(kinds), 1), 3),
        "kinds": dict(Counter(kinds)),
        "passage_ids": passage_ids,
    }


def _jaccard(a, b) -> float:
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a | b else 1.0


def check_retrieval(cur: dict, base: dict | None, questions: list[dict]) -> tuple[list[str], list[str]]:
    """Returns (failures, notes)."""
    fails, notes = [], []
    base_q = (base or {}).get("questions", {})
    for q in questions:
        k = str(q["id"])
        c = cur[k]
        if c["n_distinct_sources"] < q.get("min_distinct_sources", 3):
            fails.append(f"Q{k}: only {c['n_distinct_sources']} distinct sources "
                         f"(min {q.get('min_distinct_sources', 3)})")
        b = base_q.get(k)
        if b is None:
            notes.append(f"Q{k}: new question, no baseline yet")
            continue
        if c["expected_recall"] is not None and b.get("expected_recall") is not None \
                and c["expected_recall"] < b["expected_recall"] - RECALL_TOLERANCE:
            fails.append(f"Q{k}: expected-source recall {b['expected_recall']:.2f} -> "
                         f"{c['expected_recall']:.2f} (now missing {', '.join(c['missing_expected'])})")
        if c["n_distinct_sources"] < b["n_distinct_sources"] - DISTINCT_SOURCES_TOLERANCE:
            fails.append(f"Q{k}: distinct sources {b['n_distinct_sources']} -> {c['n_distinct_sources']}")
        overlap = _jaccard(c["passage_ids"], b.get("passage_ids", []))
        if overlap < 0.5:
            notes.append(f"Q{k}: retrieved set changed substantially (Jaccard {overlap:.2f} vs baseline)")
        if (c.get("aspirational_recall") or 0) > (b.get("aspirational_recall") or 0):
            notes.append(f"Q{k}: aspirational recall improved "
                         f"{b.get('aspirational_recall') or 0:.2f} -> {c['aspirational_recall']:.2f}")
    rec = [cur[str(q["id"])]["expected_recall"] for q in questions
           if cur[str(q["id"])]["expected_recall"] is not None]
    brec = [base_q[str(q["id"])]["expected_recall"] for q in questions
            if str(q["id"]) in base_q and base_q[str(q["id"])].get("expected_recall") is not None]
    if rec and brec and len(rec) == len(brec):
        m, bm = sum(rec) / len(rec), sum(brec) / len(brec)
        if m < bm - MEAN_RECALL_TOLERANCE:
            fails.append(f"mean expected-source recall {bm:.3f} -> {m:.3f}")
    return fails, notes


# --------------------------------------------------------------------------
# tier 3: answers
# --------------------------------------------------------------------------

def answer_snapshot(questions: list[dict], cfg: Config = CONFIG) -> dict:
    from .evaluate import score_answer
    from .pipeline import RAGPipeline
    lexicon = json.loads((EVAL_DIR / "local_lexicon.json").read_text())["terms"]
    pipe = RAGPipeline(cfg=cfg)
    out = {"backend": pipe.llm.name, "llm_model": cfg.llm_model, "questions": {}}
    for q in questions:
        print(f"  answering Q{q['id']} ...", flush=True)
        a = pipe.answer(q["question"])
        s = score_answer(q, a, lexicon)
        out["questions"][str(q["id"])] = {
            "locality": s.locality, "groundedness": s.groundedness,
            "has_gap_section": s.has_gap_section, "n_distinct_sources": s.n_distinct_sources,
            "probes_hit": s.probes_hit, "words": s.words, "elapsed_s": s.elapsed_s,
            "answer_text": a.text,
        }
    return out


def check_answers(cur: dict, base: dict | None, questions: list[dict]) -> tuple[list[str], list[str]]:
    fails, notes = [], []
    base_q = (base or {}).get("questions", {})
    for q in questions:
        k = str(q["id"])
        c = cur["questions"][k]
        text = c.get("answer_text", "").lower()
        for bad in q.get("forbidden", []):
            if bad.lower() in text:
                fails.append(f"Q{k}: forbidden phrase present: {bad!r}")
        mm = q.get("must_mention_any") or []
        if mm and not any(m.lower() in text for m in mm):
            fails.append(f"Q{k}: mentions none of {mm}")
        if q.get("expects_gap_honesty") and not c["has_gap_section"]:
            fails.append(f"Q{k}: no evidence-gap section")
        if c["groundedness"] < MIN_GROUNDEDNESS:
            fails.append(f"Q{k}: groundedness {c['groundedness']:.0%} < {MIN_GROUNDEDNESS:.0%}")
        b = base_q.get(k)
        if b is None:
            notes.append(f"Q{k}: new question, no answer baseline yet")
            continue
        if c["locality"] < b["locality"] - LOCALITY_TOLERANCE:
            fails.append(f"Q{k}: locality {b['locality']} -> {c['locality']}")
    shared = [str(q["id"]) for q in questions if str(q["id"]) in base_q]
    if shared:
        m = sum(cur["questions"][k]["locality"] for k in shared) / len(shared)
        bm = sum(base_q[k]["locality"] for k in shared) / len(shared)
        if m < bm - MEAN_LOCALITY_TOLERANCE:
            fails.append(f"mean locality {bm:.2f} -> {m:.2f}")
    return fails, notes


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------

def _meta(cfg: Config) -> dict:
    meta = {"created_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "final_k": cfg.final_k,
            "max_per_source": cfg.max_per_source, "mmr_lambda": cfg.mmr_lambda}
    manifest = cfg.index_dir / "manifest.json"
    if manifest.exists():
        m = json.loads(manifest.read_text())
        meta.update(embed_model=m.get("embed_model"), corpus_fingerprint=m.get("corpus_fingerprint"))
    return meta


def _report(name: str, fails: list[str], notes: list[str]) -> None:
    status = "FAIL" if fails else "pass"
    print(f"\n[{name}] {status}")
    for f in fails:
        print(f"  x {f}")
    for n in notes:
        print(f"  - {n}")


def _merge_baseline(path: Path, new_q: dict, meta: dict) -> dict:
    """Update only the questions that were run, keep the rest."""
    old = _read(path) or {}
    qs = {**old.get("questions", {}), **new_q}
    return {**meta, "questions": dict(sorted(qs.items(), key=lambda kv: int(kv[0])))}


def run(tier: str = "retrieval", only: list[int] | None = None, update: bool = False,
        cfg: Config = CONFIG) -> int:
    questions = load_questions(only)
    failed = False

    cur_corpus = corpus_snapshot(cfg)
    if update:
        _write(BASELINE_CORPUS, {k: v for k, v in cur_corpus.items() if k != "known_source_ids"})
        print(f"wrote {BASELINE_CORPUS.name}")
    else:
        fails = check_corpus(cur_corpus, _read(BASELINE_CORPUS), questions)
        _report("corpus", fails, [])
        failed |= bool(fails)

    if tier in ("retrieval", "all"):
        try:
            cur = retrieval_snapshot(questions, cfg)
        except FileNotFoundError as exc:
            print(f"\n[retrieval] skipped: {exc}")
            return 1 if failed else 0
        if update:
            _write(BASELINE_RETRIEVAL, _merge_baseline(BASELINE_RETRIEVAL, cur, _meta(cfg)))
            print(f"wrote {BASELINE_RETRIEVAL.name}")
        else:
            fails, notes = check_retrieval(cur, _read(BASELINE_RETRIEVAL), questions)
            print(f"\n{'Q':>3s} {'recall':>7s} {'aspir.':>7s} {'docs':>5s} {'evid.':>6s}  missing")
            for q in questions:
                c = cur[str(q["id"])]
                r = "-" if c["expected_recall"] is None else f"{c['expected_recall']:.2f}"
                a = "-" if c["aspirational_recall"] is None else f"{c['aspirational_recall']:.2f}"
                print(f"{q['id']:>3d} {r:>7s} {a:>7s} {c['n_distinct_sources']:>5d} "
                      f"{c['evidence_fraction']:>6.0%}  {', '.join(c['missing_expected'])}")
            _report("retrieval", fails, notes)
            failed |= bool(fails)

    if tier == "all":
        cur = answer_snapshot(questions, cfg)
        if update:
            _write(BASELINE_ANSWERS, _merge_baseline(
                BASELINE_ANSWERS, cur["questions"],
                {**_meta(cfg), "backend": cur["backend"], "llm_model": cur["llm_model"]}))
            print(f"wrote {BASELINE_ANSWERS.name}")
        else:
            fails, notes = check_answers(cur, _read(BASELINE_ANSWERS), questions)
            _report("answers", fails, notes)
            failed |= bool(fails)

    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Regression gate for the evaluation questions.")
    ap.add_argument("--tier", choices=["corpus", "retrieval", "all"], default="retrieval")
    ap.add_argument("--only", type=int, nargs="*")
    ap.add_argument("--update-baseline", action="store_true",
                    help="accept the current state as the new baseline")
    a = ap.parse_args()
    sys.exit(run(a.tier, a.only, a.update_baseline))
