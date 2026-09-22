"""Hybrid retrieval tuned for analytical, multi-document questions.

The test questions are not lookups. "How have safety trends changed over the
past 5-10 years" has no single passage that answers it; the answer has to be
assembled from a Vision Zero plan, an MTP trends chapter and a crash-data
catalog entry. Plain top-k cosine search fails that in two specific ways, and
each stage below exists to fix one of them:

1. ``plan_subqueries``  - one embedding of a broad question sits in the middle
   of several topic clusters and retrieves the centroid of nothing. Splitting
   into facets and fusing the results reaches all of them.
2. ``rrf_fuse``         - dense and sparse retrievers fail differently. Dense
   misses exact identifiers (SR-161, PID numbers); sparse misses paraphrase.
   Reciprocal rank fusion needs no score calibration between them.
3. ``_cap_per_source``  - the MORPC TIP is 47% of the corpus. Uncapped, it
   wins most queries on sheer surface area and the answer cites one document.
4. ``_mmr``             - adjacent PDF pages are near-duplicates. Without a
   diversity penalty, 14 slots get spent on 3 distinct facts.
5. ``_balance_kinds``   - catalog cards are short and keyword-dense, so on any
   question phrased around "data" or "sources" they sweep every slot and the
   answer becomes an inventory with no evidence in it. A floor on document
   text keeps both in the context.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

from .config import CONFIG, Config
from .corpus import Passage
from .index import HybridIndex


@dataclass
class Hit:
    passage: Passage
    index: int
    score: float
    dense_rank: int | None = None
    sparse_rank: int | None = None
    matched_subqueries: tuple[str, ...] = ()


# --------------------------------------------------------------------------
# 1. query planning
# --------------------------------------------------------------------------

#: Rule-based facet expansion. Used as the fallback when no LLM is available,
#: and merged with LLM-planned sub-queries when one is. Keys are regexes over
#: the question; values are extra retrieval probes.
_FACET_RULES: list[tuple[str, tuple[str, ...]]] = [
    (r"\btrend|over time|past \d+|changed|emerging\b",
     ("historical crash trends fatalities by year",
      "regional demographic and travel behaviour trends",
      "emerging transportation safety concerns")),
    (r"\bgrowth|population|employment|development|future\b",
     ("projected population and employment growth forecast 2050",
      "land use and development pattern changes",
      "travel demand and vehicle miles travelled growth")),
    (r"\bpost-?crash|emergency|response|ems|responder\b",
     ("incident management and emergency response time",
      "traffic incident management program",
      "emergency responder access and coordination")),
    (r"\bdata|dataset|information|evidence|combine\b",
     ("crash records dataset fields and coverage",
      "traffic volume count and speed data",
      "roadway inventory and infrastructure asset data",
      "public engagement and community feedback input")),
    (r"\bprioriti|improvement|invest|countermeasure|reduce\b",
     ("safety countermeasures and action strategies",
      "high injury network corridors and intersections",
      "project evaluation and prioritisation criteria")),
    (r"\bcost|budget|delay|schedule|longer|expected|overrun\b",
     ("project cost estimate and funding programme",
      "project schedule phasing and construction timeline",
      "fiscal constraint and cost inflation")),
    (r"\bcommunity|neighborhood|historical|equity|impact|displac\b",
     ("environmental justice and disadvantaged communities analysis",
      "highway construction neighborhood impacts and connectivity",
      "public involvement and community concerns")),
    (r"\bmissing|gap|unknown|still need|before recommending\b",
     ("data limitations and analysis caveats",
      "what data is required for safety study",
      "study methodology and evidence needs")),
    (r"\btrade-?off|competing|one type|another|conflict\b",
     ("balancing needs of pedestrians bicyclists transit and vehicles",
      "freight and truck route considerations",
      "public comments objections to design changes")),
]

_PLANNER_PROMPT = """You are planning retrieval for a transportation-safety knowledge base covering Columbus and Central Ohio (MORPC plans, Vision Zero Columbus, ODOT documents, project records, and GIS dataset catalogues).

Break the user's question into {n} short, distinct search queries. Each should target a DIFFERENT facet or a different document that would need to be consulted. Use the vocabulary a transportation planner would use in a document, not conversational phrasing.

Return one query per line, no numbering, no commentary.

Question: {question}"""


def plan_subqueries(question: str, llm=None, cfg: Config = CONFIG) -> list[str]:
    """Return the original question plus distinct retrieval probes."""
    queries: list[str] = [question]

    lowered = question.lower()
    for pattern, facets in _FACET_RULES:
        if re.search(pattern, lowered):
            queries.extend(facets)

    if llm is not None and cfg.use_query_planner and llm.available:
        try:
            raw = llm.generate(
                _PLANNER_PROMPT.format(n=cfg.n_subqueries, question=question),
                max_tokens=180,
                temperature=0.3,
            )
            for line in raw.splitlines():
                line = re.sub(r"^\s*[-*\d.)\]]+\s*", "", line).strip()
                if 3 <= len(line.split()) <= 25:
                    queries.append(line)
        except Exception:
            pass  # rule-based facets already give usable coverage

    # de-duplicate, preserving order
    seen, out = set(), []
    for q in queries:
        key = q.lower().strip()
        if key and key not in seen:
            seen.add(key)
            out.append(q)
    return out[: 1 + 3 * cfg.n_subqueries]


# --------------------------------------------------------------------------
# 2-4. fusion, capping, diversification
# --------------------------------------------------------------------------

def rrf_fuse(rankings: list[list[tuple[int, float]]], k: int) -> dict[int, float]:
    fused: dict[int, float] = {}
    for ranking in rankings:
        for rank, (doc_id, _score) in enumerate(ranking):
            fused[doc_id] = fused.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return fused


def _cap_per_source(ordered: list[int], passages: list[Passage], cap: int) -> list[int]:
    kept, counts = [], {}
    for i in ordered:
        sid = passages[i].source_id
        if counts.get(sid, 0) >= cap:
            continue
        counts[sid] = counts.get(sid, 0) + 1
        kept.append(i)
    return kept


def _mmr(candidates: list[int], relevance: dict[int, float], vectors: np.ndarray,
         k: int, lam: float) -> list[int]:
    if not candidates:
        return []
    # Normalise relevance ONCE over the full candidate set. Re-normalising
    # inside the loop rescales whatever is left each iteration, so a pool of
    # two always stretches to {0, 1} however close the two actually are - and
    # the diversity term never gets to matter.
    raw = np.array([relevance[i] for i in candidates], dtype=np.float32)
    span = float(raw.max() - raw.min())
    norm = (raw - raw.min()) / span if span > 1e-9 else np.ones_like(raw)
    rel = {i: float(v) for i, v in zip(candidates, norm)}

    selected: list[int] = []
    pool = list(candidates)
    while pool and len(selected) < k:
        if not selected:
            best = max(pool, key=lambda i: rel[i])
        else:
            redundancy = (vectors[pool] @ vectors[selected].T).max(axis=1)
            r = np.array([rel[i] for i in pool], dtype=np.float32)
            best = pool[int(np.argmax(lam * r - (1 - lam) * redundancy))]
        selected.append(best)
        pool.remove(best)
    return selected


class Retriever:
    def __init__(self, index: HybridIndex, cfg: Config = CONFIG):
        self.index = index
        self.cfg = cfg

    def retrieve(self, question: str, llm=None, k: int | None = None) -> tuple[list[Hit], list[str]]:
        cfg = self.cfg
        k = k or cfg.final_k
        subqueries = plan_subqueries(question, llm=llm, cfg=cfg)

        rankings: list[list[tuple[int, float]]] = []
        dense_rank: dict[int, int] = {}
        sparse_rank: dict[int, int] = {}
        matched: dict[int, set[str]] = {}

        for sq in subqueries:
            qvec = self.index.encode_query(sq, cfg)
            dense = self.index.dense_search(qvec, cfg.dense_k)
            sparse = self.index.sparse_search(sq, cfg.sparse_k)
            rankings.append(dense)
            rankings.append(sparse)
            for r, (i, _) in enumerate(dense):
                dense_rank[i] = min(dense_rank.get(i, 10**9), r)
                matched.setdefault(i, set()).add(sq)
            for r, (i, _) in enumerate(sparse):
                sparse_rank[i] = min(sparse_rank.get(i, 10**9), r)
                matched.setdefault(i, set()).add(sq)

        fused = rrf_fuse(rankings, cfg.rrf_k)
        if not fused:
            return [], subqueries

        # Passages found by several independent sub-queries are more likely to
        # be genuinely on-topic than ones that spiked for a single probe.
        for i in fused:
            fused[i] *= 1.0 + 0.12 * (len(matched.get(i, ())) - 1)

        ordered = sorted(fused, key=lambda i: fused[i], reverse=True)
        pool = _cap_per_source(ordered[: 25 * k], self.index.passages, cfg.max_per_source)
        pool = pool[: 8 * k]
        chosen = self._select(pool, fused, k)

        hits = [
            Hit(
                passage=self.index.passages[i],
                index=i,
                score=fused[i],
                dense_rank=dense_rank.get(i),
                sparse_rank=sparse_rank.get(i),
                matched_subqueries=tuple(sorted(matched.get(i, ()))),
            )
            for i in chosen
        ]
        return hits, subqueries

    def _select(self, pool: list[int], fused: dict[int, float], k: int) -> list[int]:
        """MMR selection with a floor on how many slots hold real document text."""
        cfg = self.cfg
        passages = self.index.passages
        chunk_pool = [i for i in pool if passages[i].kind == "chunk"]
        floor = min(len(chunk_pool), int(round(k * cfg.min_chunk_fraction)))

        chosen: list[int] = []
        if floor:
            chosen = _mmr(chunk_pool, fused, self.index.vectors, floor, cfg.mmr_lambda)
        rest = [i for i in pool if i not in set(chosen)]
        chosen += _mmr(rest, fused, self.index.vectors, k - len(chosen), cfg.mmr_lambda)
        return sorted(chosen, key=lambda i: fused[i], reverse=True)
