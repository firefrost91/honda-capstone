"""Tests for the evaluation metrics (pure functions; no models needed).

Run:  ./.venv/bin/python tests/test_eval_metrics.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag import metrics as M

ROOT = Path(__file__).resolve().parent.parent


def test_retrieval_metrics_prefix_match_and_rank():
    ids = ["other", "morpc_mtp_2024_2050_attachment_06", "x", "vision_zero_hin_map"]
    r = M.retrieval_metrics(ids, ["morpc_mtp_2024_2050", "vision_zero_hin_map", "proj_"])
    assert abs(r["source_recall"] - 2 / 3) < 1e-9      # proj_ never retrieved
    assert r["hit"] == 1.0 and r["mrr"] == 0.5 and r["precision"] == 0.5


def test_retrieval_metrics_miss_and_no_labels():
    assert M.retrieval_metrics(["a", "b"], ["z"])["mrr"] == 0.0
    assert M.retrieval_metrics(["a"], [])["hit"] is None


def test_average_precision_rewards_early_relevance():
    assert M.average_precision([True, True, False]) > M.average_precision([False, True, True])
    assert M.average_precision([False, False]) == 0.0


def test_hard_flags_parse_pipeline_warnings():
    w = ["figures not found in any cited passage: 283",
         "geographic scope mismatch: answer frames 1,000 as local but [S2] reports it as national",
         "evidence-gap section generated in a second pass"]
    f = M.hard_flags(w)
    assert f == {"invented_figure": 1, "scope_mismatch": 1, "catalog_figure": 0}


def test_gap_split_and_bullets():
    t = "Body text here.\n\n**What the local evidence does not cover**\n- one\n* two\n**bold not bullet**"
    body, gaps = M.split_body_and_gaps(t)
    assert body.strip() == "Body text here." and M.count_gap_bullets(gaps) == 2


def test_discriminating_terms_drops_shared_words():
    d = M.discriminating_terms({"a": ["crossing", "x"], "b": ["crossing", "y"]})
    assert d == {"a": ["x"], "b": ["y"]}


def test_perspective_alignment_identifies_owner():
    terms = {"ems": ["ambulance", "response time"], "freight": ["truck", "csx"]}
    out = M.perspective_alignment({"ems": "Ambulance response time matters.",
                                   "freight": "A truck at the CSX crossing."}, terms)
    assert out["ems"]["own_rank_first"] and out["freight"]["own_rank_first"]
    swapped = M.perspective_alignment({"ems": "A truck at the CSX crossing.",
                                       "freight": "Ambulance response time."}, terms)
    assert not swapped["ems"]["own_rank_first"]


def test_cited_claims_extracts_and_samples():
    text = ("Roberts Road had seventeen crashes in three years [S2]. Short one [S1]. "
            "The roundabout adds pedestrian facilities and lighting [S3][S4].\n\n"
            "**What the local evidence does not cover**\n- A gap bullet that is long enough to count [S9].")
    claims = M.cited_claims(text)
    assert [c for _, c in claims] == [[2], [3, 4]]
    many = " ".join(f"This is claim number {i} about the corridor [S1]." for i in range(40))
    assert len(M.cited_claims(many, max_claims=12)) == 12


def test_bootstrap_ci_brackets_mean():
    m, lo, hi = M.bootstrap_ci([0.2, 0.4, 0.6, 0.8, 1.0])
    assert lo <= m <= hi and abs(m - 0.6) < 1e-9


def test_pairwise_and_jaccard():
    v = np.array([[1.0, 0], [1.0, 0], [0, 1.0]])
    assert abs(M.pairwise_mean(v) - 1 / 3) < 1e-9
    assert M.jaccard({1, 2}, {2, 3}) == 1 / 3


def test_question_file_is_well_formed():
    spec = json.loads((ROOT / "eval" / "stakeholder_questions.json").read_text())
    qs = spec["questions"]
    assert [q["id"] for q in qs] == list(range(1, len(qs) + 1))
    assert sum(q["layer"] == "L1" for q in qs) == 24 and sum(q["layer"] == "L2" for q in qs) == 8
    assert sum(q["layer"] == "L2-addon" for q in qs) == 2
    for k in spec["stakeholders"]:                       # three distinct themes each
        themes = [q["theme"] for q in qs if q["layer"] == "L1" and q["stakeholder"] == k]
        assert len(themes) == 3 and len(set(themes)) == 3, k
    for q in qs:
        assert q["probes"] and q["expected_sources"]
        if q["layer"] == "L2":
            assert spec["scenario"] in q["question"] and q["stakeholder_label"] in q["question"]


def test_expected_sources_exist_in_catalogue():
    """A typo in a prefix would silently cap recall at zero for that source."""
    ids = [s["source_id"] for s in json.loads((ROOT / "data" / "documents.json").read_text())["sources"]]
    spec = json.loads((ROOT / "eval" / "stakeholder_questions.json").read_text())
    for q in spec["questions"]:
        for p in q["expected_sources"]:
            assert any(i.startswith(p) for i in ids), f"Q{q['id']}: no source matches '{p}'"


if __name__ == "__main__":
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); passed += 1; print(f"  PASS  {name}")
            except Exception as exc:
                failed += 1; print(f"  FAIL  {name}: {type(exc).__name__}: {exc}")
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)
