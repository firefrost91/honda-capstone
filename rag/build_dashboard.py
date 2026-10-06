"""Build the stakeholder-evaluation dashboard.

Reads the artefacts written by ``rag.evaluate_stakeholders`` and renders one
self-contained HTML page (data embedded, no network needed):

    python -m rag.build_dashboard              # -> eval/reports/stakeholder/dashboard.html
    python -m rag.build_dashboard --fragment   # body-only variant for hosts that add <html>/<head>

Nothing is re-scored here: per-question numbers come straight from
``results.json``, answers and citations from ``raw.jsonl``, and verdicts and
targets from the evaluator itself so the dashboard cannot drift from the report.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from . import metrics as M
from .config import EVAL_DIR
from .evaluate_stakeholders import OUT_DIR, TARGETS, question_verdict

TEMPLATE = Path(__file__).with_name("dashboard_template.html")

#: (leg, label, key, target-key) for the bootstrapped per-question means.
SCORECARD = [
    ("Retrieval", "Source recall@k", "ret_source_recall", "source_recall"),
    ("Retrieval", "Hit rate (any expected source)", "ret_hit", "hit"),
    ("Retrieval", "MRR (first expected source)", "ret_mrr", None),
    ("Retrieval", "Source precision", "ret_precision", None),
    ("Retrieval", "Keyword context recall", "ret_probe_context_recall", None),
    ("Generation", "Groundedness", "groundedness", "groundedness"),
    ("Generation", "Faithfulness (LLM judge, second opinion)", "judge_faithfulness", None),
    ("Answer", "Probe coverage", "probe_recall", "probe_recall"),
]

ABLATION_METRICS = ["source_recall", "hit", "mrr", "precision", "probe_context_recall"]


def _short_url(line: str) -> str:
    # Pre-signed S3 links carry a long, already-expired query string; it is noise here.
    return re.sub(r"(https://[^\s?]*amazonaws\.com/[^\s?]*)\?[^\s#]*", r"\1", line)


def _missing_expected(expected: list[str], retrieved: list[str]) -> list[str]:
    return [p for p in expected if not any(s.startswith(p) for s in retrieved)]


def collect(report_dir: Path) -> dict:
    results = json.loads((report_dir / "results.json").read_text())
    raw = {}
    for line in (report_dir / "raw.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            raw[int(r["id"])] = r
    spec = json.loads((EVAL_DIR / "stakeholder_questions.json").read_text())
    expected = {int(q["id"]): q.get("expected_sources", []) for q in spec["questions"]}

    rows = results["questions"]
    summary = results["summary"]

    scorecard = []
    for leg, label, key, tkey in SCORECARD:
        vals = [float(r[key]) for r in rows if r.get(key) is not None]
        if not vals:
            continue
        m, lo, hi = M.bootstrap_ci(vals)
        scorecard.append({"leg": leg, "label": label, "key": key, "mean": round(m, 3),
                          "lo": round(lo, 3), "hi": round(hi, 3),
                          "target": TARGETS.get(tkey) if tkey else None})
    for label, key, tkey in [("Answers free of hard flags", "hard_flag_free", "hard_flag_free"),
                             ("Answers with an evidence-gap section", "gap_section", "gap_section")]:
        scorecard.append({"leg": "Generation" if key == "hard_flag_free" else "Honesty",
                          "label": label, "key": key, "mean": summary["rates"][key],
                          "lo": None, "hi": None, "target": TARGETS[tkey]})

    margin_vals = [float(r["relevancy_margin"]) for r in rows if r.get("relevancy_margin") is not None]
    m, lo, hi = M.bootstrap_ci(margin_vals)
    extra = {"relevancy_margin": {"mean": round(m, 3), "lo": round(lo, 3), "hi": round(hi, 3),
                                  "target": TARGETS["relevancy_margin"]}}

    ablation = {}
    for r in rows:
        for retr, vals in (r.get("ablation") or {}).items():
            for k in ABLATION_METRICS:
                if vals.get(k) is not None:
                    ablation.setdefault(retr, {}).setdefault(k, []).append(vals[k])
    ablation = {retr: {k: round(sum(v) / len(v), 3) for k, v in ks.items()}
                for retr, ks in ablation.items()}

    questions = []
    for r in rows:
        qid = int(r["id"])
        rr = raw.get(qid, {})
        exp = expected.get(qid, [])
        base = r.get("baseline") or {}
        questions.append({
            **{k: r.get(k) for k in (
                "id", "layer", "stakeholder", "stakeholder_label", "theme", "question",
                "ret_source_recall", "ret_hit", "ret_mrr", "ret_precision", "groundedness",
                "answer_relevancy", "relevancy_margin", "probe_recall", "locality", "words",
                "n_docs", "n_cited_docs", "n_gap_bullets", "elapsed_s", "hard_flag_free",
                "has_gap_section", "judge_faithfulness", "warnings", "local_terms",
                "retrieved_sources", "judge_unsupported_claims")},
            "problems": question_verdict(r),
            "expected_sources": exp,
            "missing_sources": _missing_expected(exp, r.get("retrieved_sources") or []),
            "answer": rr.get("answer", ""),
            "cited_sources": [_short_url(s) for s in rr.get("cited_sources") or []],
            "baseline": {k: base.get(k) for k in (
                "answer", "locality", "probe_recall", "answer_relevancy", "relevancy_margin",
                "words", "has_gap_section", "elapsed_s")} if base else None,
        })

    return {
        "summary": {k: v for k, v in summary.items() if k != "layer2"},
        "targets": TARGETS,
        "scorecard": scorecard,
        "extra": extra,
        "ablation": ablation,
        "layer2": results.get("layer2"),
        "scenario": spec.get("scenario"),
        "stakeholders": {k: v["label"] for k, v in spec["stakeholders"].items()},
        "questions": questions,
    }


def render(data: dict, fragment: bool = False) -> str:
    html = TEMPLATE.read_text()
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = html.replace("/*__DATA__*/null", payload)
    if fragment:
        html = re.sub(r"(?s)^.*?<!--BODY-->\n?", "", html)
        html = re.sub(r"(?s)\n?<!--/BODY-->.*$", "\n", html)
        # keep <title> and <style> from the head
        head = TEMPLATE.read_text().split("<!--HEAD-->")[1].split("<!--/HEAD-->")[0]
        html = head.strip() + "\n" + html
    return html


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--reports", type=Path, default=OUT_DIR)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--fragment", action="store_true",
                    help="omit <html>/<head>/<body> wrappers (for hosts that add their own)")
    args = ap.parse_args()
    out = args.out or args.reports / "dashboard.html"
    out.write_text(render(collect(args.reports), fragment=args.fragment))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
