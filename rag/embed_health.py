"""Embedding-collapse diagnostics for the passage index.

"Collapse" here means the vectors stop separating the things retrieval needs
to separate. It shows up in a few distinct ways, and each metric below
targets one of them:

* **Anisotropy** - every vector points into the same narrow cone, so all
  cosines are high and similarity carries little information.
  -> ``mean_cosine`` over random pairs.
* **Low effective dimensionality** - the cloud lives on a few directions.
  -> ``effective_rank`` (exp of the entropy of the normalised singular values)
     and the variance share of the top principal components.
* **Near-duplicates** - many passages are practically identical (templated
  PDF pages), spending retrieval slots twice and flattening MMR.
  -> ``near_duplicate_rate``: share of passages whose nearest neighbour has
     cosine >= ``near_dup_cosine``.
* **Hubness** - a few passages are the nearest neighbour of a huge number of
  others and so come back for almost every query.
  -> skewness of the k-occurrence distribution and the top hubs by id.
* **Per-source collapse** - one document's passages are indistinguishable from
  each other (template pages) or from another document's.
  -> mean intra-source cosine per source vs. the corpus-wide mean.
* **Query-side collapse** - the operational symptom: different questions
  retrieve the same passages.
  -> mean pairwise Jaccard overlap of top-k dense results across the eval
     questions, and the top-1 vs top-50 similarity margin.

Everything is numpy on the stored, L2-normalised vectors; only the query-side
check needs the encoder.

    python -m rag.embed_health                       # report + thresholds
    python -m rag.embed_health --update-baseline     # snapshot current values
    python -m rag.embed_health --baseline eval/embed_health_baseline.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .config import CONFIG, EVAL_DIR, Config

BASELINE_FILE = EVAL_DIR / "embed_health_baseline.json"
REPORT_FILE = EVAL_DIR / "embed_health.json"


@dataclass(frozen=True)
class Thresholds:
    """Absolute limits. A value on the wrong side is a collapse alarm.

    Set for BGE-small on this corpus with headroom; a healthy sentence-
    embedding index of a single-domain corpus typically sits around mean
    cosine 0.3-0.5 for BGE (its vectors are known to be anisotropic) and an
    effective-rank ratio well above 0.2.
    """
    max_mean_cosine: float = 0.75
    min_effective_rank_ratio: float = 0.15
    max_top1_variance_share: float = 0.30
    max_near_duplicate_rate: float = 0.15
    max_hubness_skew: float = 6.0
    max_query_topk_overlap: float = 0.35
    min_query_margin: float = 0.05
    near_dup_cosine: float = 0.97
    knn_k: int = 10

    @classmethod
    def from_config(cls, cfg: Config = CONFIG) -> "Thresholds":
        import os
        kw = {}
        for name, default in cls.__dataclass_fields__.items():
            raw = os.environ.get(f"CBRAG_HEALTH_{name.upper()}")
            if raw is not None:
                kw[name] = type(default.default)(raw)
        return cls(**kw)


#: Allowed drift from the baseline before --baseline fails. Signed: the key
#: is the metric, the value is how much it may move in the BAD direction.
DRIFT_TOLERANCE = {
    "mean_cosine": 0.05,              # higher is worse
    "effective_rank_ratio": -0.03,    # lower is worse
    "near_duplicate_rate": 0.03,
    "hubness_skew": 1.5,
    "query_topk_overlap": 0.08,
}


# --------------------------------------------------------------------------
# metrics
# --------------------------------------------------------------------------

def _sample(n: int, m: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.choice(n, size=min(n, m), replace=False)


def mean_pairwise_cosine(vectors: np.ndarray, sample: int = 2000, seed: int = 0) -> float:
    """Mean off-diagonal cosine over a random sample of vectors."""
    if len(vectors) < 2:
        return 0.0
    v = vectors[_sample(len(vectors), sample, seed)]
    sims = v @ v.T
    n = len(v)
    return float((sims.sum() - np.trace(sims)) / (n * (n - 1)))


def spectrum(vectors: np.ndarray, sample: int = 4000, seed: int = 0) -> dict:
    """Effective rank and PC variance shares of the mean-centred vectors."""
    v = vectors[_sample(len(vectors), sample, seed)].astype(np.float64)
    v = v - v.mean(axis=0, keepdims=True)
    s = np.linalg.svd(v, compute_uv=False)
    var = s ** 2
    total = float(var.sum()) or 1.0
    p = s / (s.sum() or 1.0)
    p = p[p > 0]
    erank = float(np.exp(-(p * np.log(p)).sum()))
    return {
        "effective_rank": round(erank, 2),
        "effective_rank_ratio": round(erank / vectors.shape[1], 4),
        "top1_variance_share": round(float(var[0]) / total, 4) if len(var) else 0.0,
        "top10_variance_share": round(float(var[:10].sum()) / total, 4),
    }


def effective_rank_of(vectors: np.ndarray) -> float:
    return spectrum(vectors)["effective_rank"]


def knn(vectors: np.ndarray, k: int, block: int = 1024) -> tuple[np.ndarray, np.ndarray]:
    """Exact k nearest neighbours (excluding self). Returns (idx, sims)."""
    n = len(vectors)
    k = min(k, n - 1)
    idx = np.empty((n, k), dtype=np.int64)
    sim = np.empty((n, k), dtype=np.float32)
    for start in range(0, n, block):
        s = vectors[start:start + block] @ vectors.T
        rows = np.arange(s.shape[0])
        s[rows, rows + start] = -np.inf
        part = np.argpartition(-s, k - 1, axis=1)[:, :k]
        ps = np.take_along_axis(s, part, axis=1)
        order = np.argsort(-ps, axis=1)
        idx[start:start + block] = np.take_along_axis(part, order, axis=1)
        sim[start:start + block] = np.take_along_axis(ps, order, axis=1)
    return idx, sim


def hubness(nn_idx: np.ndarray, n: int) -> tuple[float, np.ndarray]:
    """Skewness of the k-occurrence distribution, and the counts themselves."""
    counts = np.bincount(nn_idx.ravel(), minlength=n).astype(np.float64)
    mu, sd = counts.mean(), counts.std()
    skew = float(((counts - mu) ** 3).mean() / sd ** 3) if sd > 0 else 0.0
    return skew, counts


def per_source_cohesion(vectors: np.ndarray, source_ids: list[str],
                        min_size: int = 5, sample: int = 300) -> dict[str, float]:
    """Mean intra-source cosine for every source with at least ``min_size`` passages."""
    groups: dict[str, list[int]] = defaultdict(list)
    for i, s in enumerate(source_ids):
        groups[s].append(i)
    out = {}
    for sid, ids in groups.items():
        if len(ids) < min_size:
            continue
        v = vectors[np.asarray(ids)[_sample(len(ids), sample)]]
        out[sid] = round(mean_pairwise_cosine(v, sample=sample), 4)
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def query_side(query_vecs: np.ndarray, vectors: np.ndarray, k: int = 10) -> dict:
    """How distinct are the top-k result sets of different questions?"""
    sims = query_vecs @ vectors.T
    tops = [set(np.argsort(-row)[:k].tolist()) for row in sims]
    overlaps = [len(a & b) / len(a | b) for i, a in enumerate(tops) for b in tops[i + 1:]]
    sorted_sims = -np.sort(-sims, axis=1)
    margin = sorted_sims[:, 0] - sorted_sims[:, min(49, sims.shape[1] - 1)]
    return {
        "query_topk_overlap": round(float(np.mean(overlaps)) if overlaps else 0.0, 4),
        "query_max_pair_overlap": round(float(np.max(overlaps)) if overlaps else 0.0, 4),
        "query_margin_top1_top50": round(float(np.mean(margin)), 4),
        "query_min_margin": round(float(np.min(margin)), 4),
    }


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------

def analyse(vectors: np.ndarray, passage_ids: list[str] | None = None,
            source_ids: list[str] | None = None, query_vecs: np.ndarray | None = None,
            th: Thresholds | None = None) -> dict:
    th = th or Thresholds()
    vectors = np.asarray(vectors, dtype=np.float32)
    n, d = vectors.shape
    passage_ids = passage_ids or [str(i) for i in range(n)]

    nn_idx, nn_sim = knn(vectors, th.knn_k)
    skew, counts = hubness(nn_idx, n)
    top_hubs = np.argsort(-counts)[:20]
    near_dup = nn_sim[:, 0] >= th.near_dup_cosine

    rep = {
        "n_vectors": int(n), "dim": int(d),
        "mean_cosine": round(mean_pairwise_cosine(vectors), 4),
        **spectrum(vectors),
        "near_duplicate_rate": round(float(near_dup.mean()), 4),
        "hubness_skew": round(skew, 3),
        "max_k_occurrence": int(counts.max()),
        "top_hubs": [{"passage_id": passage_ids[i], "k_occurrence": int(counts[i])}
                     for i in top_hubs],
        "near_duplicate_examples": [
            {"a": passage_ids[i], "b": passage_ids[int(nn_idx[i, 0])],
             "cosine": round(float(nn_sim[i, 0]), 4)}
            for i in np.flatnonzero(near_dup)[:15]],
    }
    if source_ids is not None:
        coh = per_source_cohesion(vectors, source_ids)
        rep["per_source_cohesion"] = coh
        rep["collapsed_sources"] = [s for s, c in coh.items() if c >= 0.9]
    if query_vecs is not None and len(query_vecs) > 1:
        rep.update(query_side(np.asarray(query_vecs, dtype=np.float32), vectors, th.knn_k))
    rep["alarms"] = check_thresholds(rep, th)
    return rep


def check_thresholds(rep: dict, th: Thresholds) -> list[str]:
    alarms = []

    def bad(cond, msg):
        if cond:
            alarms.append(msg)

    bad(rep["mean_cosine"] > th.max_mean_cosine,
        f"anisotropy: mean cosine {rep['mean_cosine']:.3f} > {th.max_mean_cosine}")
    bad(rep["effective_rank_ratio"] < th.min_effective_rank_ratio,
        f"low effective rank: {rep['effective_rank_ratio']:.3f} of dim < {th.min_effective_rank_ratio}")
    bad(rep["top1_variance_share"] > th.max_top1_variance_share,
        f"one direction holds {rep['top1_variance_share']:.0%} of variance")
    bad(rep["near_duplicate_rate"] > th.max_near_duplicate_rate,
        f"near-duplicates: {rep['near_duplicate_rate']:.1%} of passages")
    bad(rep["hubness_skew"] > th.max_hubness_skew,
        f"hubness: k-occurrence skew {rep['hubness_skew']:.2f} > {th.max_hubness_skew}")
    if rep.get("collapsed_sources"):
        alarms.append("sources with near-identical passages: " + ", ".join(rep["collapsed_sources"]))
    if "query_topk_overlap" in rep:
        bad(rep["query_topk_overlap"] > th.max_query_topk_overlap,
            f"different questions share {rep['query_topk_overlap']:.0%} of top-{th.knn_k} results")
        bad(rep["query_min_margin"] < th.min_query_margin,
            f"a question's top-1 vs top-50 margin is only {rep['query_min_margin']:.3f}")
    return alarms


def compare_to_baseline(rep: dict, base: dict) -> list[str]:
    """Drift alarms: metrics that moved more than DRIFT_TOLERANCE the wrong way."""
    out = []
    for key, tol in DRIFT_TOLERANCE.items():
        if key not in rep or key not in base:
            continue
        delta = rep[key] - base[key]
        worse = delta > tol if tol >= 0 else delta < tol
        if worse:
            out.append(f"{key} drifted {base[key]} -> {rep[key]} (tolerance {tol:+})")
    return out


def summary(rep: dict) -> dict:
    """The scalar part of a report, for manifests and baselines."""
    return {k: v for k, v in rep.items() if isinstance(v, (int, float)) or k == "alarms"}


def _print(rep: dict) -> None:
    keys = ["n_vectors", "dim", "mean_cosine", "effective_rank", "effective_rank_ratio",
            "top1_variance_share", "top10_variance_share", "near_duplicate_rate",
            "hubness_skew", "max_k_occurrence", "query_topk_overlap",
            "query_max_pair_overlap", "query_margin_top1_top50", "query_min_margin"]
    for k in keys:
        if k in rep:
            print(f"  {k:26s} {rep[k]}")
    print("\n  top hubs (nearest neighbour of the most other passages):")
    for h in rep["top_hubs"][:8]:
        print(f"    {h['k_occurrence']:4d}  {h['passage_id']}")
    if rep.get("per_source_cohesion"):
        print("\n  most internally similar sources (mean intra-source cosine):")
        for sid, c in list(rep["per_source_cohesion"].items())[:6]:
            print(f"    {c:.3f}  {sid}")
    print()
    if rep["alarms"]:
        for a in rep["alarms"]:
            print(f"  ALARM  {a}")
    else:
        print("  no collapse alarms")


def run(cfg: Config = CONFIG, baseline: Path | None = None, update_baseline: bool = False,
        with_queries: bool = True) -> int:
    from .index import HybridIndex
    index = HybridIndex.load(cfg)
    qv = None
    if with_queries:
        try:
            qs = json.loads((EVAL_DIR / "questions.json").read_text())["questions"]
            qv = np.stack([index.encode_query(q["question"], cfg) for q in qs])
        except Exception as exc:  # encoder unavailable offline
            print(f"[health] skipping query-side checks: {exc}")
    rep = analyse(index.vectors, [p.passage_id for p in index.passages],
                  [p.source_id for p in index.passages], qv, Thresholds.from_config(cfg))
    rep["embed_model"] = index.embed_model
    REPORT_FILE.write_text(json.dumps(rep, indent=2))
    print(f"embedding health for {index.embed_model}")
    _print(rep)

    failed = bool(rep["alarms"])
    if update_baseline:
        BASELINE_FILE.write_text(json.dumps(summary(rep), indent=2))
        print(f"\n  baseline written to {BASELINE_FILE}")
    elif baseline and Path(baseline).exists():
        drift = compare_to_baseline(rep, json.loads(Path(baseline).read_text()))
        for d in drift:
            print(f"  DRIFT  {d}")
        failed = failed or bool(drift)
    print(f"\n  wrote {REPORT_FILE}")
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Check the index for embedding collapse.")
    ap.add_argument("--baseline", type=Path, default=None,
                    help=f"compare against a baseline (e.g. {BASELINE_FILE.relative_to(EVAL_DIR.parent)})")
    ap.add_argument("--update-baseline", action="store_true")
    ap.add_argument("--no-queries", action="store_true", help="skip query-side checks")
    a = ap.parse_args()
    sys.exit(run(baseline=a.baseline, update_baseline=a.update_baseline,
                 with_queries=not a.no_queries))
