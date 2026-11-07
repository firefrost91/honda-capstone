"""Embedding-collapse diagnostics on synthetic vectors with known structure."""
from __future__ import annotations

import numpy as np

from rag.embed_health import (Thresholds, analyse, compare_to_baseline, effective_rank_of,
                              hubness, knn, mean_pairwise_cosine, query_side, summary)


def _norm(x):
    return (x / np.linalg.norm(x, axis=1, keepdims=True)).astype(np.float32)


RNG = np.random.default_rng(7)
HEALTHY = _norm(RNG.normal(size=(600, 64)))


def test_healthy_isotropic_vectors_raise_no_alarms():
    rep = analyse(HEALTHY)
    assert abs(rep["mean_cosine"]) < 0.05
    assert rep["effective_rank_ratio"] > 0.8
    assert rep["alarms"] == []


def test_vectors_in_a_narrow_cone_are_flagged_as_anisotropic():
    centre = RNG.normal(size=(1, 64)) * 4
    cone = _norm(centre + RNG.normal(size=(600, 64)) * 0.3)
    rep = analyse(cone)
    assert rep["mean_cosine"] > 0.75
    assert any("anisotropy" in a for a in rep["alarms"])


def test_low_rank_collapse_is_flagged():
    basis = RNG.normal(size=(3, 64))
    flat = _norm(RNG.normal(size=(600, 3)) @ basis + RNG.normal(size=(600, 64)) * 0.01)
    rep = analyse(flat)
    assert rep["effective_rank_ratio"] < 0.15
    assert any("effective rank" in a for a in rep["alarms"])


def test_templated_near_duplicates_are_flagged_and_named():
    template = RNG.normal(size=(1, 64))
    dups = _norm(template + RNG.normal(size=(200, 64)) * 0.02)
    vecs = np.vstack([HEALTHY[:400], dups])
    ids = [f"p{i}" for i in range(400)] + [f"tip_page_{i}" for i in range(200)]
    sids = ["doc"] * 400 + ["tip"] * 200
    rep = analyse(vecs, ids, sids)
    assert rep["near_duplicate_rate"] > 0.15
    assert rep["near_duplicate_examples"][0]["a"].startswith("tip_page_")
    assert "tip" in rep["collapsed_sources"]


def test_planted_hub_is_detected():
    vecs = HEALTHY.copy()
    hub = _norm(vecs.mean(axis=0, keepdims=True) + 1e-3)
    vecs = np.vstack([vecs, hub])
    idx, _ = knn(vecs, 10)
    skew, counts = hubness(idx, len(vecs))
    assert int(np.argmax(counts)) == len(vecs) - 1 or counts[-1] >= np.percentile(counts, 99)


def test_query_side_overlap_detects_queries_retrieving_the_same_passages():
    q_distinct = HEALTHY[:5]
    q_same = _norm(np.repeat(HEALTHY[:1], 5, axis=0) + RNG.normal(size=(5, 64)) * 0.01)
    assert query_side(q_distinct, HEALTHY)["query_topk_overlap"] < 0.1
    assert query_side(q_same, HEALTHY)["query_topk_overlap"] > 0.8


def test_baseline_drift_only_fails_in_the_bad_direction():
    base = {"mean_cosine": 0.40, "effective_rank_ratio": 0.40, "near_duplicate_rate": 0.02,
            "hubness_skew": 2.0, "query_topk_overlap": 0.10}
    better = {**base, "mean_cosine": 0.30, "effective_rank_ratio": 0.50}
    worse = {**base, "mean_cosine": 0.50, "effective_rank_ratio": 0.30}
    assert compare_to_baseline(better, base) == []
    drift = compare_to_baseline(worse, base)
    assert len(drift) == 2


def test_summary_is_json_scalar_only():
    s = summary(analyse(HEALTHY))
    assert all(isinstance(v, (int, float)) for k, v in s.items() if k != "alarms")


def test_thresholds_can_be_overridden_from_env(monkeypatch):
    monkeypatch.setenv("CBRAG_HEALTH_MAX_MEAN_COSINE", "0.01")
    th = Thresholds.from_config()
    assert th.max_mean_cosine == 0.01
    cone = _norm(RNG.normal(size=(1, 64)) * 4 + RNG.normal(size=(100, 64)))
    assert any("anisotropy" in a for a in analyse(cone, th=th)["alarms"])


def test_mean_pairwise_cosine_matches_brute_force():
    v = HEALTHY[:50]
    sims = v @ v.T
    brute = (sims.sum() - np.trace(sims)) / (50 * 49)
    assert abs(mean_pairwise_cosine(v) - brute) < 1e-5
    assert effective_rank_of(np.eye(8, dtype=np.float32)) > 6
