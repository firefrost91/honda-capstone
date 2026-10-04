"""Stakeholder evaluation: run the 34-question set and write the standard RAG reports.

    python -m rag.evaluate_stakeholders                  # core metrics
    python -m rag.evaluate_stakeholders --judge          # + LLM-judge precision / faithfulness
    python -m rag.evaluate_stakeholders --baseline       # + no-retrieval LLM comparison
    python -m rag.evaluate_stakeholders --only 7 8 25    # subset
    python -m rag.evaluate_stakeholders --resume         # continue an interrupted run
    python -m rag.evaluate_stakeholders --report-only    # rebuild reports from raw.jsonl

Outputs land in ``eval/reports/stakeholder/``:

    report.md          the readable report (scorecard, breakdowns, failure analysis)
    results.json       summary + per-question scores
    per_question.csv   one row per question, for spreadsheets
    transcript.md      full answers and sources
    raw.jsonl          checkpoint: one record per completed question

The set has two layers. Layer 1 asks each stakeholder's own local questions and
is scored on retrieval, faithfulness and answer quality. Layer 2 asks every
stakeholder the *same* scenario and is additionally scored on whether the
answers differ by perspective while resting on the same evidence.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import time
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import mean

import numpy as np

from . import metrics as M
from .config import CONFIG, EVAL_DIR
from .pipeline import RAGPipeline
from .retrieve import Retriever

OUT_DIR = EVAL_DIR / "reports" / "stakeholder"

#: Targets are stated up front, not tuned to the results. They are the usual
#: "acceptable for a decision-support prototype" bars.
TARGETS = {
    "source_recall": 0.50,       # half of the expected documents reached the generator
    "hit": 0.90,                 # almost never retrieve nothing relevant
    "groundedness": 0.85,
    "hard_flag_free": 1.00,      # no detected invented figure / mis-scoped number
    "relevancy_margin": 0.02,    # answer fits its own question better than other questions
    "probe_recall": 0.50,
    "gap_section": 0.95,
}

BASELINE_SYSTEM = ("You are a transportation-safety expert. Answer the question as helpfully "
                   "and specifically as you can.")


# --------------------------------------------------------------------------
# per-question scoring
# --------------------------------------------------------------------------

def _clean_for_embedding(text: str) -> str:
    import re
    body, _ = M.split_body_and_gaps(text)
    body = re.sub(r"\[S\d+\]|\[unsupported by retrieved evidence\]", "", body)
    return re.sub(r"\s+", " ", body).strip()


def _retrieval_variants(pipe: RAGPipeline, question: str, k: int) -> dict[str, list[int]]:
    """Retrieval-only ablations: which stage of the pipeline earns its place?"""
    idx, cfg = pipe.index, pipe.cfg
    qvec = idx.encode_query(question, cfg)
    return {
        "dense_only": [i for i, _ in idx.dense_search(qvec, k)],
        "bm25_only": [i for i, _ in idx.sparse_search(question, k)],
        "hybrid_rules": [h.index for h in Retriever(idx, cfg).retrieve(question, llm=None, k=k)[0]],
    }


def _retrieval_row(ids: list[str], texts: list[str], q: dict) -> dict:
    r = M.retrieval_metrics(ids, q.get("expected_sources", []))
    r["probe_context_recall"] = M.probe_recall(" ".join(texts), q.get("probes", []))
    return r


def evaluate_question(pipe: RAGPipeline, q: dict, lexicon: list[str], *, judge: bool,
                      baseline: bool, judge_validation: dict | None = None) -> dict:
    ans = pipe.answer(q["question"])
    body, gaps = M.split_body_and_gaps(ans.text)
    qvec = pipe.index.encode_query(q["question"], pipe.cfg)
    avec = pipe._encode_batch([_clean_for_embedding(ans.text) or ans.text])[0]

    ids = [s.source_id for s in ans.sources]
    kinds = [s.kind for s in ans.sources]
    ret = _retrieval_row(ids, ans.contexts, q)
    counts = defaultdict(int)
    for sid in ids:
        counts[sid] += 1
    flags = M.hard_flags(ans.warnings)

    row = {
        "id": q["id"], "layer": q["layer"], "stakeholder": q["stakeholder"],
        "stakeholder_label": q["stakeholder_label"], "theme": q["theme"],
        "question": q["question"],
        # retrieval
        "n_passages": len(ids), "n_docs": len(set(ids)),
        "card_share": round(sum(k != "chunk" for k in kinds) / max(len(kinds), 1), 3),
        "max_doc_share": round(max(counts.values()) / max(len(ids), 1), 3) if counts else 0.0,
        "retrieval_confidence": round(ans.confidence, 3),
        "retrieved_sources": sorted(set(ids)),
        **{f"ret_{k}": (None if v is None else round(v, 3)) for k, v in ret.items()},
        # generation / faithfulness
        "groundedness": round(ans.groundedness, 3),
        "n_unsupported": len(ans.unsupported_claims),
        **{f"flag_{k}": v for k, v in flags.items()},
        "hard_flag_free": not any(flags.values()),
        "warnings": ans.warnings,
        # answer
        "answer_relevancy": round(M.cosine(qvec, avec), 3),
        "probe_recall": None if not q.get("probes") else round(M.probe_recall(ans.text, q["probes"]), 3),
        "locality": len(M.term_hits(ans.text, lexicon)),
        "local_terms": M.term_hits(ans.text, lexicon),
        "words": len(body.split()),
        "has_gap_section": bool(gaps.strip()),
        "n_gap_bullets": M.count_gap_bullets(gaps),
        "n_cited_docs": len({s.source_id for s in ans.cited_sources()}),
        "elapsed_s": round(ans.elapsed_s, 1),
        # raw material for the reports
        "answer": ans.text,
        "cited_sources": [s.format() for s in (ans.cited_sources() or ans.sources)],
        "subqueries": ans.subqueries,
    }

    # ablations over retrieval alone (no generation, so effectively free)
    row["ablation"] = {"hybrid_llm_planner": {k: v for k, v in ret.items()}}
    for name, passage_idx in _retrieval_variants(pipe, q["question"], pipe.cfg.final_k).items():
        row["ablation"][name] = _retrieval_row(
            [pipe.index.passages[i].source_id for i in passage_idx],
            [pipe.index.passages[i].text for i in passage_idx], q)

    if judge and pipe.llm.available:
        row.update(_judge(pipe, q, ans, judge_validation))
    if baseline and pipe.llm.available:
        row["baseline"] = _baseline(pipe, q, lexicon, qvec)
    return row


def validate_judge(pipe: RAGPipeline, questions: list[dict], n: int = 10, seed: int = 3) -> dict:
    """Control test for the LLM judge, run before it is trusted.

    A judge that answers NO to everything produces a plausible-looking
    "context precision 0.04" that is entirely a property of the judge. So:
      * claim support: a sentence from a passage must be Supported by that
        passage and Unsupported by an unrelated one;
      * context relevance: the passage nearest a question must be Relevant,
        the farthest chunk Irrelevant.
    """
    import random, re
    rng = random.Random(seed)
    idx = pipe.index
    chunks = [i for i, p in enumerate(idx.passages) if p.kind == "chunk" and 600 < len(p.text) < 1150]
    pos = neg = tot = 0
    for i in rng.sample(chunks, min(n, len(chunks))):
        sents = [x.strip() for x in re.split(r"(?<=[.!?])\s+", idx.passages[i].text.replace("\n", " "))
                 if 8 <= len(x.split()) <= 30]
        if not sents:
            continue
        claim, other = sents[len(sents) // 2], rng.choice([j for j in chunks if j != i])
        pos += M.judge_claim_support(pipe.llm, claim, [idx.passages[i].text])
        neg += not M.judge_claim_support(pipe.llm, claim, [idx.passages[other].text])
        tot += 1
    rpos = rneg = rtot = 0
    chunk_vecs = idx.vectors[chunks]
    for q in rng.sample(questions, min(8, len(questions))):
        sims = chunk_vecs @ idx.encode_query(q["question"], pipe.cfg)
        best, worst = chunks[int(np.argmax(sims))], chunks[int(np.argmin(sims))]
        rpos += M.judge_context_relevance(pipe.llm, q["question"], idx.passages[best].text)
        rneg += not M.judge_context_relevance(pipe.llm, q["question"], idx.passages[worst].text)
        rtot += 1
    out = {"claim_pos_accept": pos / max(tot, 1), "claim_neg_reject": neg / max(tot, 1),
           "ctx_pos_accept": rpos / max(rtot, 1), "ctx_neg_reject": rneg / max(rtot, 1),
           "n_claim_controls": tot, "n_ctx_controls": rtot}
    out["claim_valid"] = min(out["claim_pos_accept"], out["claim_neg_reject"]) >= 0.75
    out["ctx_valid"] = min(out["ctx_pos_accept"], out["ctx_neg_reject"]) >= 0.75
    out["valid"] = out["claim_valid"] or out["ctx_valid"]
    return out


def _judge(pipe: RAGPipeline, q: dict, ans, jv: dict) -> dict:
    """Run only the judges that passed their control test."""
    rel = ([M.judge_context_relevance(pipe.llm, q["question"], c) for c in ans.contexts]
           if jv["ctx_valid"] else [])
    claims = M.cited_claims(ans.text) if jv["claim_valid"] else []
    ok = [M.judge_claim_support(pipe.llm, c, [ans.contexts[n - 1] for n in cites
                                               if 1 <= n <= len(ans.contexts)])
          for c, cites in claims]
    return {
        "judge_context_precision": round(sum(rel) / len(rel), 3) if rel else None,
        "judge_context_ap": round(M.average_precision(rel), 3) if rel else None,
        "judge_faithfulness": round(sum(ok) / len(ok), 3) if ok else None,
        "judge_claims_checked": len(ok),
        "judge_unsupported_claims": [c for (c, _), good in zip(claims, ok) if not good],
    }


def _baseline(pipe: RAGPipeline, q: dict, lexicon: list[str], qvec) -> dict:
    t0 = time.time()
    text = pipe.llm.generate(q["question"], system=BASELINE_SYSTEM)
    avec = pipe._encode_batch([_clean_for_embedding(text) or text])[0]
    return {
        "answer": text,
        "locality": len(M.term_hits(text, lexicon)),
        "probe_recall": None if not q.get("probes") else round(M.probe_recall(text, q["probes"]), 3),
        "answer_relevancy": round(M.cosine(qvec, avec), 3),
        "words": len(text.split()),
        "has_gap_section": bool(M.GAP_HEADING.search(text)),
        "elapsed_s": round(time.time() - t0, 1),
    }


# --------------------------------------------------------------------------
# aggregation
# --------------------------------------------------------------------------

def _avg(rows: list[dict], key: str) -> float | None:
    vals = [r[key] for r in rows if r.get(key) is not None]
    return round(mean(float(v) for v in vals), 3) if vals else None


def _ci(rows: list[dict], key: str) -> str:
    vals = [float(r[key]) for r in rows if r.get(key) is not None]
    if not vals:
        return "n/a"
    m, lo, hi = M.bootstrap_ci(vals)
    return f"{m:.2f} [{lo:.2f}, {hi:.2f}]"


def question_verdict(r: dict) -> list[str]:
    problems = []
    if r["ret_hit"] == 0.0:
        problems.append("retrieval miss (no expected source retrieved)")
    if r["groundedness"] < TARGETS["groundedness"]:
        problems.append(f"low groundedness ({r['groundedness']:.0%})")
    if not r["hard_flag_free"]:
        problems.append("hard flag: " + ", ".join(
            k.removeprefix("flag_") for k in r if k.startswith("flag_") and r[k]))
    if r.get("relevancy_margin") is not None and r["relevancy_margin"] < TARGETS["relevancy_margin"]:
        problems.append(f"answer not specific to its question (margin {r['relevancy_margin']:+.3f})")
    if not r["has_gap_section"]:
        problems.append("no evidence-gap section")
    return problems


def layer2_analysis(rows: list[dict], pipe: RAGPipeline, stakeholders: dict) -> dict | None:
    sh = [r for r in rows if r["layer"] == "L2"]
    if len(sh) < 2:
        return None
    answers = {r["stakeholder"]: r["answer"] for r in sh}
    terms = {k: v["perspective_terms"] for k, v in stakeholders.items() if k in answers}
    align = M.perspective_alignment(answers, terms)
    vecs = pipe._encode_batch([_clean_for_embedding(a) or a for a in answers.values()])
    src_sets = [set(r["retrieved_sources"]) for r in sh]
    import re
    return {
        "n_stakeholders": len(sh),
        "mean_pairwise_similarity": round(M.pairwise_mean(vecs), 3),
        "mean_source_jaccard": round(M.mean_pairwise_jaccard(src_sets), 3),
        "perspective_alignment_rate": round(mean(a["own_rank_first"] for a in align.values()), 3),
        "mean_perspective_lift": round(mean(a["lift"] for a in align.values()), 2),
        "alignment": align,
        "restates_scenario": {
            r["stakeholder"]: bool(re.search(r"\b8\b", r["answer"]) and re.search(r"\b(?:2|two)\b", r["answer"]))
            for r in sh},
    }


def _add_relevancy_margin(rows: list[dict], all_questions: list[dict], pipe: RAGPipeline) -> None:
    """Answer relevancy minus the answer's similarity to *other* questions.

    Raw question-answer cosine is saturated: any on-topic Columbus safety text
    scores 0.85+ against any Columbus safety question, and a no-retrieval LLM
    scores the same as the RAG. The margin asks the sharper question - does the
    answer fit *its own* question better than the rest of the set? Questions that
    share a scenario are excluded from "others", since their answers should be alike.
    """
    qv = {q["id"]: pipe.index.encode_query(q["question"], pipe.cfg) for q in all_questions}
    scen = {q["id"]: q.get("scenario") for q in all_questions}

    def margin(text: str, qid: int) -> float:
        a = pipe._encode_batch([_clean_for_embedding(text) or text])[0]
        others = [M.cosine(v, a) for i, v in qv.items()
                  if i != qid and not (scen[qid] and scen[i] == scen[qid])]
        return round(M.cosine(qv[qid], a) - mean(others), 3)

    for r in rows:
        r["relevancy_margin"] = margin(r["answer"], r["id"])
        if r.get("baseline"):
            r["baseline"]["relevancy_margin"] = margin(r["baseline"]["answer"], r["id"])


def summarise(rows: list[dict], l2: dict | None, pipe: RAGPipeline, args) -> dict:
    l1 = [r for r in rows if r["layer"] == "L1"]
    summary = {
        "date": date.today().isoformat(),
        "git_commit": _git_head(),
        "backend": pipe.llm.name, "llm_model": CONFIG.llm_model,
        "embed_model": pipe.index.embed_model, "n_passages": len(pipe.index.passages),
        "n_questions": len(rows), "n_layer1": len(l1),
        "n_layer2": len([r for r in rows if r["layer"] == "L2"]),
        "n_addons": len([r for r in rows if r["layer"] == "L2-addon"]),
        "judge": bool(args.judge), "judge_validation": getattr(args, "judge_validation", None),
        "baseline": bool(args.baseline),
        "final_k": CONFIG.final_k,
        "total_latency_s": round(sum(r["elapsed_s"] for r in rows), 1),
        "mean_latency_s": _avg(rows, "elapsed_s"),
    }
    keys = ["ret_source_recall", "ret_hit", "ret_mrr", "ret_precision", "ret_probe_context_recall",
            "retrieval_confidence", "n_docs", "card_share", "max_doc_share",
            "groundedness", "answer_relevancy", "relevancy_margin", "probe_recall", "locality", "words",
            "n_cited_docs", "n_gap_bullets", "judge_context_precision", "judge_context_ap",
            "judge_faithfulness"]
    summary["means"] = {k: _avg(rows, k) for k in keys}
    summary["rates"] = {
        "hard_flag_free": round(mean(r["hard_flag_free"] for r in rows), 3),
        "gap_section": round(mean(r["has_gap_section"] for r in rows), 3),
        "questions_passing": round(mean(not question_verdict(r) for r in rows), 3),
    }
    if l2:
        summary["layer2"] = {k: v for k, v in l2.items() if k not in ("alignment", "restates_scenario")}
    return summary


def _git_head() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, cwd=EVAL_DIR.parent).stdout.strip()
    except Exception:
        return ""


# --------------------------------------------------------------------------
# report rendering
# --------------------------------------------------------------------------

def _table(headers: list[str], rows: list[list]) -> list[str]:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join("" if c is None else str(c) for c in r) + " |" for r in rows]
    return out + [""]


def _fmt(v, pct: bool = False) -> str:
    if v is None:
        return "n/a"
    return f"{v:.0%}" if pct else f"{v:.2f}"


def _status(value, target) -> str:
    return "n/a" if value is None else ("PASS" if value >= target else "BELOW TARGET")


def render_report(rows: list[dict], summary: dict, l2: dict | None, stakeholders: dict) -> str:
    s = summary
    out = ["# Honda Safety RAG: stakeholder evaluation report", "",
           f"Run {s['date']} · commit `{s['git_commit']}` · {s['llm_model']} ({s['backend']}) · "
           f"embeddings {s['embed_model']} · {s['n_passages']:,} passages · top-{s['final_k']} context", "",
           f"**{s['n_questions']} questions**: {s['n_layer1']} stakeholder-specific (Layer 1), "
           f"{s['n_layer2']} shared-scenario (Layer 2), {s['n_addons']} add-ons. "
           f"{s['rates']['questions_passing']:.0%} of questions clear every per-question check "
           f"(see *Per-question verdicts*). Mean latency {s['mean_latency_s']}s.", ""]

    # ---- 1. scorecard -------------------------------------------------
    m = s["means"]
    out += ["## 1. Scorecard: the RAG triad", "",
            "Targets were set before the run (see `TARGETS` in `rag/evaluate_stakeholders.py`). "
            "Brackets are 95% bootstrap intervals over questions; with this few questions they are wide, "
            "so differences under ~0.1 are not meaningful.", ""]
    card = [
        ["Retrieval", "Source recall@k", _ci(rows, "ret_source_recall"), f"≥ {TARGETS['source_recall']:.2f}", _status(m["ret_source_recall"], TARGETS["source_recall"])],
        ["Retrieval", "Hit rate (any expected source)", _ci(rows, "ret_hit"), f"≥ {TARGETS['hit']:.2f}", _status(m["ret_hit"], TARGETS["hit"])],
        ["Retrieval", "MRR (first expected source)", _ci(rows, "ret_mrr"), "-", ""],
        ["Retrieval", "Source precision (share of passages from expected sources)", _ci(rows, "ret_precision"), "-", ""],
        ["Retrieval", "Keyword context recall", _ci(rows, "ret_probe_context_recall"), "-", ""],
        ["Generation", "Groundedness (sentence-level attribution)", _ci(rows, "groundedness"), f"≥ {TARGETS['groundedness']:.2f}", _status(m["groundedness"], TARGETS["groundedness"])],
        ["Generation", "Answers free of detected invented / mis-scoped figures", f"{s['rates']['hard_flag_free']:.0%}", "100%", _status(s["rates"]["hard_flag_free"], TARGETS["hard_flag_free"])],
        ["Answer", "Answer relevancy, raw cosine (sanity check only; saturated)", _ci(rows, "answer_relevancy"), "-", ""],
        ["Answer", "Relevancy margin (own question minus other questions)", _ci(rows, "relevancy_margin"), f"≥ {TARGETS['relevancy_margin']:.2f}", _status(m["relevancy_margin"], TARGETS["relevancy_margin"])],
        ["Answer", "Probe coverage (expected topics mentioned)", _ci(rows, "probe_recall"), f"≥ {TARGETS['probe_recall']:.2f}", _status(m["probe_recall"], TARGETS["probe_recall"])],
        ["Answer", "Locality (local proper nouns per answer)", _ci(rows, "locality"), "-", ""],
        ["Honesty", "Answers with an evidence-gap section", f"{s['rates']['gap_section']:.0%}", f"≥ {TARGETS['gap_section']:.0%}", _status(s["rates"]["gap_section"], TARGETS["gap_section"])],
    ]
    jv = s.get("judge_validation")
    if jv and not jv["ctx_valid"]:
        card += [["Retrieval (judge)", "Context precision / AP: withheld, relevance judge failed its control test", "n/a", "-", "UNRELIABLE"]]
    elif m.get("judge_context_precision") is not None:
        card += [
            ["Retrieval (judge)", "Context precision, LLM judge", _ci(rows, "judge_context_precision"), "-", ""],
            ["Retrieval (judge)", "Context AP (rank-weighted), LLM judge", _ci(rows, "judge_context_ap"), "-", ""]]
    if jv and not jv["claim_valid"]:
        card += [["Generation (judge)", "Judge faithfulness: withheld, claim judge failed its control test", "n/a", "-", "UNRELIABLE"]]
    elif m.get("judge_faithfulness") is not None:
        card += [["Generation (judge)", "Faithfulness, LLM judge over cited claims", _ci(rows, "judge_faithfulness"), "-", ""]]
    out += _table(["Leg", "Metric", "Mean [95% CI]", "Target", "Status"], card)
    if jv:
        out += [f"**LLM-judge control test** ({jv['n_claim_controls']} claim and {jv['n_ctx_controls']} relevance controls, "
                "run before scoring): a sentence copied from a passage should be *Supported* by it and *Unsupported* by an "
                "unrelated passage; the passage nearest a question should be *Relevant*, the farthest *Irrelevant*. "
                f"Accept/reject accuracy: claim-support {jv['claim_pos_accept']:.0%} / {jv['claim_neg_reject']:.0%}, "
                f"context-relevance {jv['ctx_pos_accept']:.0%} / {jv['ctx_neg_reject']:.0%}. "
                + "A judge is used only if both its accept and reject rates are ≥ 75%. "
                + f"Claim-support judge: {'passed' if jv['claim_valid'] else 'FAILED, not reported'}. "
                + f"Relevance judge: {'passed' if jv['ctx_valid'] else 'FAILED, not reported'}. "
                + "Even a passing judge is the same 3B model that wrote the answers, so treat it as a second opinion.", ""]

    # ---- 2. by layer / stakeholder -----------------------------------
    out += ["## 2. Breakdown by layer and stakeholder", ""]
    def agg(label, rs):
        return [label, len(rs), _avg(rs, "ret_source_recall"), _avg(rs, "ret_hit"), _avg(rs, "groundedness"),
                _avg(rs, "answer_relevancy"), _avg(rs, "probe_recall"), _avg(rs, "locality"),
                f"{mean(r['hard_flag_free'] for r in rs):.0%}", _avg(rs, "elapsed_s")]
    hdr = ["Group", "n", "Src recall", "Hit", "Grounded", "Relevancy", "Probes", "Locality", "No hard flags", "Latency s"]
    layers = [agg(name, [r for r in rows if r["layer"] == key])
              for name, key in [("Layer 1: stakeholder-specific", "L1"),
                                ("Layer 2: shared scenario", "L2"),
                                ("Layer 2: add-ons", "L2-addon")]
              if any(r["layer"] == key for r in rows)]
    out += _table(hdr, layers)
    out += ["**Layer 1 by stakeholder**", ""]
    out += _table(hdr, [agg(stakeholders[k]["label"], [r for r in rows if r["layer"] == "L1" and r["stakeholder"] == k])
                        for k in stakeholders if any(r["layer"] == "L1" and r["stakeholder"] == k for r in rows)])
    out += ["**Layer 1 by theme** (each stakeholder's three questions probe different concerns)", ""]
    out += _table(["#", "Stakeholder", "Theme", "Src recall", "Grounded", "Relevancy", "Probes", "Locality", "Verdict"],
                  [[r["id"], stakeholders[r["stakeholder"]]["label"].split(" / ")[0], r["theme"],
                    _fmt(r["ret_source_recall"]), _fmt(r["groundedness"], True), _fmt(r["answer_relevancy"]),
                    _fmt(r["probe_recall"]), r["locality"], "OK" if not question_verdict(r) else "CHECK"]
                   for r in rows if r["layer"] == "L1"])

    # ---- 3. retrieval ablation ---------------------------------------
    out += ["## 3. Retrieval ablation", "",
            "Same questions, retrieval only, top-"
            f"{s['final_k']} passages. Shows which pipeline stage earns its place. "
            "`hybrid_rules` is the full pipeline without the LLM query planner.", ""]
    names = ["dense_only", "bm25_only", "hybrid_rules", "hybrid_llm_planner"]
    arows = []
    for n in names:
        vs = [r["ablation"][n] for r in rows if n in r.get("ablation", {})]
        if vs:
            arows.append([n] + [_avg(vs, k) for k in ("source_recall", "hit", "mrr", "precision", "probe_context_recall")])
    out += _table(["Retriever", "Source recall", "Hit", "MRR", "Source precision", "Keyword ctx recall"], arows)
    out += ["Caveat: dense-only and BM25-only return the raw top-k with no per-document cap or MMR, "
            "so they can be dominated by one long document. Source precision is therefore "
            "not directly comparable across rows; recall and hit are.", ""]

    # ---- 4. baseline --------------------------------------------------
    base = [r for r in rows if r.get("baseline")]
    if base:
        out += ["## 4. RAG vs. the same LLM with no retrieval", "",
                "The project's thesis is that a locally-grounded RAG gives more locally relevant insight than a "
                "general LLM. The baseline is the same model, same question, no context.", ""]
        def b(key): return _avg([r["baseline"] for r in base], key)
        out += _table(["Metric", "RAG", "No-retrieval baseline"], [
            ["Locality (local proper nouns)", _avg(base, "locality"), b("locality")],
            ["Probe coverage", _avg(base, "probe_recall"), b("probe_recall")],
            ["Answer relevancy, raw cosine", _avg(base, "answer_relevancy"), b("answer_relevancy")],
            ["Relevancy margin", _avg(base, "relevancy_margin"), b("relevancy_margin")],
            ["Words", _avg(base, "words"), b("words")],
            ["Evidence-gap section", f"{mean(r['has_gap_section'] for r in base):.0%}",
             f"{mean(r['baseline']['has_gap_section'] for r in base):.0%}"],
            ["Latency s", _avg(base, "elapsed_s"), b("elapsed_s")],
        ])
        out += ["Locality is the metric that cleanly separates the two. The baseline has no citations and its "
                "specifics cannot be verified here, so this comparison says nothing about whether its "
                "unsourced claims are *correct*.", ""]

    # ---- 5. layer 2 ---------------------------------------------------
    if l2:
        out += ["## 5. Layer 2: same scenario, different stakeholders", "",
                "Scenario: *" + json.loads((EVAL_DIR / "stakeholder_questions.json").read_text())["scenario"] + "*", "",
                "The test is not whether any one answer is good but whether the system reads the *same* evidence "
                "through *different* stakeholder lenses.", "",
                f"- **Perspective alignment: {l2['perspective_alignment_rate']:.0%}** of the {l2['n_stakeholders']} answers use their own "
                "stakeholder's vocabulary more than any other stakeholder's (a reader could tell whose answer it is). "
                f"Mean lift {l2['mean_perspective_lift']:+.2f} own-terms over other stakeholders' terms.",
                f"- **Answer similarity: {l2['mean_pairwise_similarity']:.2f}** mean pairwise embedding cosine across the "
                "eight answers. Higher means the answers are interchangeable; see the interpretation note below.",
                f"- **Shared evidence: {l2['mean_source_jaccard']:.2f}** mean pairwise Jaccard overlap of retrieved documents. "
                "High overlap is expected and desirable here (same evidence), but it also means perspective differences "
                "come from generation, not retrieval.", ""]
        al = l2["alignment"]
        out += _table(["Stakeholder", "Own terms", "Others (mean)", "Lift", "Own rank first", "Restates 8→2", "Own terms used"],
                      [[stakeholders[k]["label"], v["own"], v["others_mean"], v["lift"],
                        "yes" if v["own_rank_first"] else "no",
                        "yes" if l2["restates_scenario"].get(k) else "no", ", ".join(v["own_terms"][:6])]
                       for k, v in al.items()])
        out += ["*Interpretation:* embedding similarity between two answers to near-identical prompts is high by "
                "construction (they share the scenario text), so judge differentiation mainly by the alignment "
                "table above, not the raw similarity. Vocabulary alignment is a proxy: it shows the answer *speaks* "
                "like the stakeholder, not that its reasoning is right. The 'Others' counts use only terms unique to one "
                "stakeholder's list.", ""]

    # ---- 6. failures --------------------------------------------------
    out += ["## 6. Per-question verdicts and failure analysis", ""]
    bad = [(r, question_verdict(r)) for r in rows if question_verdict(r)]
    if not bad:
        out += ["Every question clears all checks.", ""]
    else:
        out += _table(["#", "Layer", "Stakeholder / theme", "Problems"],
                      [[r["id"], r["layer"], f"{stakeholders.get(r['stakeholder'], {'label': 'All'})['label'].split(' / ')[0]} / {r['theme']}",
                        "; ".join(p)] for r, p in bad])
    out += ["**Retrieval misses and weak retrieval** (expected sources not reached):", ""]
    weak = [r for r in rows if r["ret_source_recall"] is not None and r["ret_source_recall"] < TARGETS["source_recall"]]
    if weak:
        for r in weak:
            exp = json.loads((EVAL_DIR / "stakeholder_questions.json").read_text())["questions"][r["id"] - 1]["expected_sources"]
            got = [e for e in exp if any(x.startswith(e) for x in r["retrieved_sources"])]
            out.append(f"- Q{r['id']} ({r['theme']}): recall {r['ret_source_recall']:.2f}; expected-but-missing: "
                       + (", ".join(e for e in exp if e not in got) or "none"))
        out.append("")
    else:
        out += ["- None below target.", ""]
    flagged = [r for r in rows if not r["hard_flag_free"]]
    out += ["**Hard-flagged answers** (detected by the pipeline's verification stages):", ""]
    if flagged:
        for r in flagged:
            for w in r["warnings"]:
                if any(mk in w for mk in M.HARD_FLAGS.values()):
                    out.append(f"- Q{r['id']}: {w}")
        out.append("")
    else:
        out += ["- None.", ""]
    if m.get("judge_faithfulness") is not None:
        out += ["**Claims the LLM judge could not verify** (second opinion; a 3B judge over-rejects, review by hand):", ""]
        for r in rows:
            for c in (r.get("judge_unsupported_claims") or [])[:2]:
                out.append(f"- Q{r['id']}: {c[:220]}")
        out.append("")

    # ---- 7. method ----------------------------------------------------
    out += ["## 7. Metric definitions and limits", "",
            "| Metric | Definition | Reference-free? |", "|---|---|---|",
            "| Source recall@k | share of expected documents (prefix match) with ≥1 passage in the top-k context | no, needs expected sources |",
            "| Hit / MRR | any expected source retrieved / reciprocal rank of the first one | no |",
            "| Keyword context recall | share of probe keywords present anywhere in the retrieved text | no, needs probes |",
            "| Groundedness | share of factual answer sentences whose best-matching retrieved passage has cosine ≥ 0.50 | yes |",
            "| Hard flags | numbers absent from cited passages, national figures re-scoped as local, figures cited only to an unloaded GIS catalogue entry | yes |",
            "| Answer relevancy | cosine(question, answer body) in the retrieval embedding space | yes |",
            "| Probe coverage | share of probe keywords in the answer | no |",
            "| Locality | distinct Columbus / Central Ohio proper nouns from `eval/local_lexicon.json` | no, needs lexicon |",
            "| Judge metrics | local LLM yes/no on passage relevance and claim support | yes |", "",
            "**What this evaluation cannot tell you**", "",
            "- There are no gold reference answers. Correctness of local claims (is the cited crash count the "
            "right one, is the project the right project) needs a domain reviewer. Faithfulness here means "
            "*supported by what was retrieved*, not *true*.",
            "- `expected_sources` and `probes` are provisional silver labels written from catalogue titles. "
            "Low recall may mean the label is wrong, not the retrieval. Review them before quoting recall.",
            "- Groundedness is an embedding-similarity check: it catches topical invention but can pass a "
            "correctly-themed sentence that reverses a document's meaning.",
            "- Generation is sampled (temperature 0.2); a single run is one draw. Re-run before treating small "
            "differences as real.",
            "- Several stakeholder topics (EMS response, freight, transit first/last-mile) have thin coverage in "
            "the corpus. A good answer there is an honest gap statement, which the relevancy and probe metrics "
            "will under-credit; read the gap bullets in the transcript.", ""]

    # ---- appendix -----------------------------------------------------
    out += ["## Appendix: all questions", ""]
    out += _table(["#", "Layer", "Stakeholder", "Theme", "Src recall", "Hit", "MRR", "Grounded", "Relevancy", "Probes", "Locality", "Docs", "Gap bullets", "s"],
                  [[r["id"], r["layer"], r["stakeholder"], r["theme"], _fmt(r["ret_source_recall"]), _fmt(r["ret_hit"]),
                    _fmt(r["ret_mrr"]), _fmt(r["groundedness"], True), _fmt(r["answer_relevancy"]),
                    _fmt(r["probe_recall"]), r["locality"], r["n_docs"], r["n_gap_bullets"], r["elapsed_s"]]
                   for r in rows])
    return "\n".join(out)


def render_transcript(rows: list[dict]) -> str:
    out = ["# Stakeholder evaluation: answers and sources", ""]
    for r in rows:
        out += ["---", "", f"## Q{r['id']} · {r['layer']} · {r['stakeholder_label']} · {r['theme']}", "",
                f"> {r['question']}", "", r["answer"], "", "**Sources**", ""]
        out += [f"- {s}" for s in r["cited_sources"]]
        out += ["", f"<sub>grounded {r['groundedness']:.0%} · relevancy {r['answer_relevancy']:.2f} · "
                    f"locality {r['locality']} · source recall {r['ret_source_recall']} · "
                    f"{r['elapsed_s']}s · warnings: {'; '.join(r['warnings']) or 'none'}</sub>", ""]
        if r.get("baseline"):
            out += ["<details><summary>No-retrieval baseline answer</summary>", "", r["baseline"]["answer"], "", "</details>", ""]
    return "\n".join(out)


CSV_COLS = ["id", "layer", "stakeholder", "theme", "n_passages", "n_docs", "card_share", "max_doc_share",
            "retrieval_confidence", "ret_source_recall", "ret_hit", "ret_mrr", "ret_precision",
            "ret_probe_context_recall", "groundedness", "n_unsupported", "flag_invented_figure",
            "flag_scope_mismatch", "flag_catalog_figure", "answer_relevancy", "probe_recall", "locality",
            "words", "has_gap_section", "n_gap_bullets", "n_cited_docs", "elapsed_s",
            "judge_context_precision", "judge_context_ap", "judge_faithfulness"]


def write_reports(rows: list[dict], pipe: RAGPipeline, args, out_dir: Path = OUT_DIR) -> dict:
    spec = json.loads((EVAL_DIR / "stakeholder_questions.json").read_text())
    stakeholders = spec["stakeholders"]
    rows = sorted(rows, key=lambda r: r["id"])
    _add_relevancy_margin(rows, spec["questions"], pipe)
    l2 = layer2_analysis(rows, pipe, stakeholders)
    summary = summarise(rows, l2, pipe, args)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.md").write_text(render_report(rows, summary, l2, stakeholders))
    (out_dir / "transcript.md").write_text(render_transcript(rows))
    slim = [{k: v for k, v in r.items() if k not in ("answer", "cited_sources")} for r in rows]
    (out_dir / "results.json").write_text(json.dumps(
        {"summary": summary, "layer2": l2, "questions": slim}, indent=2, default=str))
    with (out_dir / "per_question.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return summary


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------

def run(args) -> dict:
    spec = json.loads((EVAL_DIR / "stakeholder_questions.json").read_text())
    lexicon = json.loads((EVAL_DIR / "local_lexicon.json").read_text())["terms"]
    qs = spec["questions"]
    if args.only:
        qs = [q for q in qs if q["id"] in args.only]

    pipe = RAGPipeline()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw = OUT_DIR / "raw.jsonl"
    done: dict[int, dict] = {}
    if (args.resume or args.report_only) and raw.exists():
        for line in raw.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                done[rec["id"]] = rec
    elif raw.exists() and not args.only:
        raw.unlink()

    if args.judge and pipe.llm.available and not args.report_only:
        args.judge_validation = validate_judge(pipe, spec["questions"])
        print("judge control test:", {k: (round(v, 2) if isinstance(v, float) else v)
                                      for k, v in args.judge_validation.items()}, flush=True)
        if not args.judge_validation["valid"]:
            print("  both judges failed validation; judge metrics will be skipped", flush=True)
            args.judge = False
        (OUT_DIR / "judge_validation.json").write_text(json.dumps(args.judge_validation, indent=2))
    elif (OUT_DIR / "judge_validation.json").exists():
        args.judge_validation = json.loads((OUT_DIR / "judge_validation.json").read_text())

    print(f"backend={pipe.llm.name}  embed={pipe.index.embed_model}  passages={len(pipe.index.passages)}  "
          f"judge={args.judge}  baseline={args.baseline}\n")
    if not args.report_only:
        for q in qs:
            if q["id"] in done:
                continue
            print(f"[{q['id']:2d}/{len(spec['questions'])}] {q['layer']:8s} {q['stakeholder']:8s} "
                  f"{q['theme'][:40]}...", flush=True)
            row = evaluate_question(pipe, q, lexicon, judge=args.judge, baseline=args.baseline,
                                    judge_validation=getattr(args, "judge_validation", None))
            done[q["id"]] = row
            with raw.open("a") as fh:
                fh.write(json.dumps(row, default=str) + "\n")
            print(f"        recall={row['ret_source_recall']}  grounded={row['groundedness']:.0%}  "
                  f"rel={row['answer_relevancy']:.2f}  loc={row['locality']}  {row['elapsed_s']}s  "
                  f"{'OK' if not question_verdict(row) else 'CHECK: ' + '; '.join(question_verdict(row))}",
                  flush=True)

    rows = list(done.values()) if args.report_only else [done[q["id"]] for q in qs if q["id"] in done]
    summary = write_reports(rows, pipe, args)
    print(f"\nwrote reports to {OUT_DIR}")
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the stakeholder evaluation set.")
    ap.add_argument("--only", type=int, nargs="*", help="run only these question ids")
    ap.add_argument("--judge", action="store_true", help="add LLM-judge context precision and faithfulness (slow)")
    ap.add_argument("--baseline", action="store_true", help="also answer each question with no retrieval")
    ap.add_argument("--resume", action="store_true", help="skip questions already in raw.jsonl")
    ap.add_argument("--report-only", action="store_true", help="rebuild reports from raw.jsonl")
    run(ap.parse_args())


if __name__ == "__main__":
    main()
