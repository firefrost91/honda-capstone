"""Hybrid retrieval tuned for analytical, multi-document questions.

The test questions are not lookups. "How have safety trends changed over the
past 5-10 years" has no single passage that answers it; the answer has to be
assembled from a Vision Zero plan, an MTP trends chapter and a crash-data
catalog entry. Plain top-k cosine search fails that in two specific ways, and
each stage below exists to fix one of them:

1. ``plan_subqueries``  - one embedding of a broad question sits in the middle
   of several topic clusters and retrieves the centroid of nothing. Splitting
   into facets and fusing the results reaches all of them. Only up to
   ``cfg.max_subqueries`` of them: past that, fusion starts preferring
   passages that place on every facet over the one that actually answers the
   question. See the note on that setting.
2. ``rrf_fuse``         - dense and sparse retrievers fail differently. Dense
   misses exact identifiers (SR-161, PID numbers); sparse misses paraphrase.
   Reciprocal rank fusion needs no score calibration between them.
3. ``_cap_per_source``  - the MORPC TIP is the largest single source in the
   corpus. Uncapped, it wins most queries on sheer surface area and the answer
   cites one document.
4. ``_mmr``             - adjacent PDF pages are near-duplicates. Without a
   diversity penalty, 14 slots get spent on 3 distinct facts.
5. ``_select``          - catalog cards are short and keyword-dense, so on any
   question phrased around "data" or "sources" they sweep every slot and the
   answer becomes an inventory with no evidence in it. A floor on document
   text keeps both in the context. The floor only reserves slots, it does not
   cap the cards, so ``cfg.min_chunk_fraction`` alone decides the split.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

from .config import CONFIG, Config
from .corpus import EVIDENCE_KINDS, Passage
from .index import HybridIndex


@dataclass
class Hit:
    passage: Passage
    index: int
    score: float
    dense_rank: int | None = None
    sparse_rank: int | None = None
    matched_subqueries: tuple[str, ...] = ()
    #: Set for passages that are not in the index (metric tool output); the
    #: pipeline reads this instead of ``index.vectors[index]`` when ``index < 0``.
    vector: np.ndarray | None = None


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

_PLANNER_PROMPT = """You write search queries for a transportation-safety document collection (MORPC plans, Vision Zero action plans, ODOT manuals, project records, GIS dataset catalogues).

Break the user's question into {n} short, distinct search queries. Each must target a DIFFERENT facet or a different document that would need to be consulted.

{role}Rules:
- 4 to 12 words each, written in the vocabulary a planner would use in a document, not conversational phrasing.
- Do NOT mention Columbus, Central Ohio, Ohio or the region. Every document already covers it, so it adds nothing to a search.
- Use concrete topic words (program names, metrics, road types, agencies, document types) that are not already the question's own wording.
- Output only the queries, one per line. No numbering, bullets, quotes, labels or commentary.

Example question: Why are pedestrian deaths rising on arterial roads?
Example output:
pedestrian fatality counts by roadway functional class
arterial corridor speed limits and crossing spacing
high injury network pedestrian crash locations
signalized intersection countermeasures leading pedestrian interval

Question: {question}
Output:"""

#: Region boilerplate the planner tends to append. Stripped from planned
#: queries: a phrase present in every document discriminates between none.
_REGION_BOILERPLATE = re.compile(
    r"\b(?:in|for|across|within|of)?\s*"
    r"(?:columbus\s*(?:/|,|and|&)\s*(?:the\s+)?central\s+ohio|central\s+ohio(?:\s+region)?"
    r"|columbus,?\s+ohio|the\s+columbus\s+region)\b"
    # ... but not when it is the start of a name: Central Ohio Transit Authority
    # (COTA), Central Ohio Transportation Safety Plan (COTSP), Central Ohio Greenways
    r"(?!\s+(?:transit|transportation|greenways?|regional|rail|mobility|traffic\s+incident))", re.I)
#: A bare "Columbus" is just as uninformative, but it is also part of real
#: names ("Vision Zero Columbus", "City of Columbus", "Columbus Division of
#: Police"), which must survive.
_BARE_COLUMBUS = re.compile(
    r"(?<!Vision Zero )(?<!City of )(?<!vision zero )(?<!city of )"
    r"\bcolumbus(?:[- ]area)?\b(?!\s+(?:Division|Department|Metropolitan|Zero|Police|Fire))", re.I)
_PREAMBLE = re.compile(
    r"^(?:here\s+(?:are|is)|sure|certainly|okay|below|these|the following|queries?\b|search queries)", re.I)
_LABEL = re.compile(r"^\s*(?:query|q|search|probe)\s*\d*\s*[:.\-)]\s*", re.I)
_STOP = frozenset(
    "a an and are as at be by for from how in is it of on or that the this to was what "
    "when where which who why with does did do has have had can could should would will "
    "been being their there than then these those into over about across between".split())


def _content_tokens(text: str) -> frozenset[str]:
    return frozenset(w for w in re.findall(r"[a-z0-9][a-z0-9\-]*", text.lower()) if w not in _STOP)


def _clean_planned_query(line: str) -> str | None:
    """Return a usable retrieval probe from one line of planner output, or None.

    Small local models emit preambles ("Here are 4 queries:"), numbering,
    quotes, labels and region boilerplate. Anything that does not survive
    cleaning as a short phrase of real topic words is dropped rather than
    issued as a probe, because every probe adds a ranking to the fusion.
    """
    line = re.sub(r"^\s*(?:[-*\u2022#>]+|\d+[.)\]:])\s*", "", line)
    line = _LABEL.sub("", line)
    line = line.replace("**", "").replace("`", "").strip().strip("\"'\u201c\u201d\u2018\u2019").strip()
    if not line or _PREAMBLE.match(line) or line.endswith(":"):
        return None
    if re.search(r"[{}\[\]<>|=]", line):
        return None
    line = _REGION_BOILERPLATE.sub(" ", line)
    line = _BARE_COLUMBUS.sub(" ", line)
    line = re.sub(r"\s+", " ", line).strip(" ,;:-/")
    words = line.split()
    if not 3 <= len(words) <= 16:
        return None
    if sum(c.isalpha() for c in line) < 0.7 * len(line.replace(" ", "")):
        return None
    if len(_content_tokens(line)) < 2:
        return None
    return line


def _is_near_duplicate(candidate: str, accepted: list[str], threshold: float = 0.75) -> bool:
    ct = _content_tokens(candidate)
    for other in accepted:
        ot = _content_tokens(other)
        if ct and ot and len(ct & ot) / min(len(ct), len(ot)) >= threshold:
            return True
    return False


def _role_block(stakeholder_context: str) -> str:
    if not stakeholder_context:
        return ""
    return (f"The answer is for this audience: {stakeholder_context}\n"
            "Make the queries reach the evidence THIS audience would want, which may differ "
            "from what another audience asking the same question would need.\n\n")


def plan_subqueries(question: str, llm=None, cfg: Config = CONFIG,
                    stakeholder_probes: tuple[str, ...] = (),
                    stakeholder_context: str = "") -> list[str]:
    """Return the original question plus distinct retrieval probes.

    The ceiling (``cfg.max_subqueries``) is small, so the order decides which
    probes survive:

    1. the question itself, always;
    2. up to ``cfg.max_stakeholder_probes`` probes for the stakeholder's own
       concerns, so a question shared across stakeholders does not retrieve the
       same passages for each;
    3. LLM-planned probes and rule-based facets, alternating. Appending every
       rule facet first left the planner 0.7 slots on average across the eval
       questions, and none at all on six of ten.
    """
    queries: list[str] = [question]

    rule_probes: list[str] = []
    lowered = question.lower()
    for pattern, facets in _FACET_RULES:
        if re.search(pattern, lowered):
            rule_probes.extend(facets)

    llm_probes: list[str] = []
    if llm is not None and cfg.use_query_planner and llm.available:
        try:
            raw = llm.generate(
                _PLANNER_PROMPT.format(n=cfg.n_subqueries, question=question,
                                       role=_role_block(stakeholder_context)),
                max_tokens=180,
                temperature=0.2,
            )
            for line in raw.splitlines():
                cleaned = _clean_planned_query(line)
                # Skip probes that merely restate the question or a probe
                # already queued: they add a ranking, not a facet.
                if cleaned and not _is_near_duplicate(cleaned, [question, *llm_probes]):
                    llm_probes.append(cleaned)
        except Exception:
            pass  # rule-based facets already give usable coverage

    queries.extend(stakeholder_probes[: max(0, cfg.max_stakeholder_probes)])

    # LLM probe first in each pair; with no LLM this is just the rule order.
    for i in range(max(len(llm_probes), len(rule_probes))):
        if i < len(llm_probes):
            queries.append(llm_probes[i])
        if i < len(rule_probes):
            queries.append(rule_probes[i])

    # de-duplicate, preserving order
    seen, out = set(), []
    for q in queries:
        key = q.lower().strip()
        if key and key not in seen:
            seen.add(key)
            out.append(q)
    # Every extra probe dilutes the fused ranking (see cfg.max_subqueries), so
    # the ceiling is a hard total rather than a per-source allowance. The
    # question itself is out[0] and always survives.
    return out[: max(1, cfg.max_subqueries)]


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


#: Questions that are about what data exists, as opposed to questions that
#: merely touch a topic a dataset also covers.
_DATA_QUESTION = re.compile(
    r"\b(?:data|datasets?|data ?sources?|gis|layers?|records|catalogu?e?s?|databases?)\b", re.I)
CATALOG_KINDS = frozenset({"doc_card", "data_card"})


class Retriever:
    def __init__(self, index: HybridIndex, cfg: Config = CONFIG):
        self.index = index
        self.cfg = cfg

    def retrieve(self, question: str, llm=None, k: int | None = None,
                 stakeholder: str | None = None) -> tuple[list[Hit], list[str]]:
        cfg = self.cfg
        k = k or cfg.final_k
        probes: tuple[str, ...] = ()
        context = ""
        if stakeholder:
            from .tools.stakeholders import STAKEHOLDERS
            if stakeholder in STAKEHOLDERS:
                st = STAKEHOLDERS[stakeholder]
                probes = st.focus
                if cfg.stakeholder_aware_planner:
                    context = f"{st.name}. They care about: {', '.join(st.concerns)}."
        subqueries = plan_subqueries(question, llm=llm, cfg=cfg, stakeholder_probes=probes,
                                     stakeholder_context=context)
        focus = {q for q in subqueries[1:] if q in probes}
        focus_hit: set[int] = set()
        question_rank: dict[int, int] = {}      # best rank under the question itself

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
                if sq in focus and r < cfg.stakeholder_boost_rank:
                    focus_hit.add(i)
                if sq == question:
                    question_rank[i] = min(question_rank.get(i, 10**9), r)
            for r, (i, _) in enumerate(sparse):
                sparse_rank[i] = min(sparse_rank.get(i, 10**9), r)
                matched.setdefault(i, set()).add(sq)
                if sq in focus and r < cfg.stakeholder_boost_rank:
                    focus_hit.add(i)
                if sq == question:
                    question_rank[i] = min(question_rank.get(i, 10**9), r)

        fused = rrf_fuse(rankings, cfg.rrf_k)
        if not fused:
            return [], subqueries

        # Passages found by several independent sub-queries are more likely to
        # be genuinely on-topic than ones that spiked for a single probe.
        for i in fused:
            fused[i] *= 1.0 + 0.12 * (len(matched.get(i, ())) - 1)

        # Passages near the top of the role's own probes outrank the shared core
        # that every audience's question retrieves.
        for i in focus_hit:
            fused[i] *= 1.0 + cfg.stakeholder_boost

        ordered = sorted(fused, key=lambda i: fused[i], reverse=True)
        pool = _cap_per_source(ordered[: 25 * k], self.index.passages, cfg.max_per_source)
        pool = pool[: 8 * k]
        pool = self._admit_catalog_cards(pool, fused, question_rank, question)
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

    def _admit_catalog_cards(self, pool: list[int], fused: dict[int, float],
                             question_rank: dict[int, int], question: str) -> list[int]:
        """Keep catalogue cards only where they earn a slot, and no more than the cap.

        A card is admitted if the question is about data, or if the question
        itself (not just a facet probe) ranked it in its top
        ``cfg.catalog_card_rank`` (the retrievers return 60 per list, so merely
        appearing in them is too weak a signal). Probes such as "high
        injury network corridors" exist to find document text, but they match
        the cards for the same datasets just as well. Admitted cards are then
        trimmed to the best ``cap`` by fused score.
        """
        cfg = self.cfg
        passages = self.index.passages
        data_q = bool(_DATA_QUESTION.search(question))
        cap = cfg.max_catalog_cards_data_question if data_q else cfg.max_catalog_cards
        kept_cards = 0
        out: list[int] = []
        for i in sorted(pool, key=lambda j: fused[j], reverse=True):
            if passages[i].kind in CATALOG_KINDS:
                if not (data_q or question_rank.get(i, 10**9) < cfg.catalog_card_rank) or kept_cards >= cap:
                    continue
                kept_cards += 1
            out.append(i)
        # keep the original pool order for everything that survived
        keep = set(out)
        return [i for i in pool if i in keep]

    def _select(self, pool: list[int], fused: dict[int, float], k: int) -> list[int]:
        """MMR selection with a floor on how many slots hold real document text."""
        cfg = self.cfg
        passages = self.index.passages
        chunk_pool = [i for i in pool if passages[i].kind in EVIDENCE_KINDS]
        floor = min(len(chunk_pool), int(round(k * cfg.min_chunk_fraction)))

        chosen: list[int] = []
        if floor:
            chosen = _mmr(chunk_pool, fused, self.index.vectors, floor, cfg.mmr_lambda)
        rest = [i for i in pool if i not in set(chosen)]
        chosen += _mmr(rest, fused, self.index.vectors, k - len(chosen), cfg.mmr_lambda)
        return sorted(chosen, key=lambda i: fused[i], reverse=True)
