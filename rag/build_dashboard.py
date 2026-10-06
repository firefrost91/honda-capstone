"""Build the stakeholder-evaluation dashboard.

Reads the artefacts written by ``rag.evaluate_stakeholders`` and renders one
self-contained, plain-language HTML summary (data embedded, no network needed):

    python -m rag.build_dashboard              # -> eval/reports/stakeholder/dashboard.html
    python -m rag.build_dashboard --fragment   # body-only variant for hosts that add <html>/<head>

Nothing is re-scored here: numbers come straight from ``results.json``, and
verdicts and targets from the evaluator itself so the page cannot drift from
``report.md``.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from statistics import mean

from .evaluate_stakeholders import OUT_DIR, TARGETS, question_verdict

TEMPLATE = Path(__file__).with_name("dashboard_template.html")


def _avg(vals) -> float | None:
    vals = [float(v) for v in vals if v is not None]
    return round(mean(vals), 3) if vals else None


def collect(report_dir: Path) -> dict:
    results = json.loads((report_dir / "results.json").read_text())
    rows = results["questions"]
    summary = results["summary"]

    ablation: dict[str, dict[str, float]] = {}
    for retr in {k for r in rows for k in (r.get("ablation") or {})}:
        ablation[retr] = {k: _avg((r.get("ablation") or {}).get(retr, {}).get(k) for r in rows)
                          for k in ("source_recall", "hit")}

    with_base = [r for r in rows if r.get("baseline")]
    baseline = {
        "n": len(with_base),
        "rag": {k: _avg(r[k] for r in with_base) for k in ("locality", "probe_recall", "elapsed_s")},
        "base": {k: _avg(r["baseline"][k] for r in with_base) for k in ("locality", "probe_recall", "elapsed_s")},
    }

    layer2 = results.get("layer2") or {}
    return {
        "summary": {k: summary[k] for k in (
            "date", "git_commit", "llm_model", "n_passages", "n_questions", "n_layer1",
            "n_layer2", "n_addons", "mean_latency_s", "means", "rates")},
        "targets": TARGETS,
        "ablation": ablation,
        "baseline": baseline,
        "layer2": {k: layer2.get(k) for k in ("n_stakeholders", "perspective_alignment_rate")}
                  | {"aligned": sorted(k for k, a in (layer2.get("alignment") or {}).items()
                                       if a.get("own_rank_first"))},
        "questions": [{
            "id": r["id"], "layer": r["layer"], "stakeholder": r["stakeholder"],
            "stakeholder_label": r["stakeholder_label"], "theme": r["theme"],
            "ret_source_recall": r["ret_source_recall"], "ret_hit": r["ret_hit"],
            "hard_flag_free": r["hard_flag_free"], "problems": question_verdict(r),
        } for r in rows],
    }


def render(data: dict, fragment: bool = False) -> str:
    template = TEMPLATE.read_text()
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = template.replace("/*__DATA__*/null", payload)
    if fragment:
        head = template.split("<!--HEAD-->")[1].split("<!--/HEAD-->")[0]
        body = re.search(r"(?s)<!--BODY-->\n?(.*?)\n?<!--/BODY-->", html).group(1)
        html = head.strip() + "\n" + body + "\n"
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
