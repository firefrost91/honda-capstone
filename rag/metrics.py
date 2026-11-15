"""Metric primitives for RAG evaluation.

The standard framing (RAGAS, TruLens, ARES) is the "RAG triad", plus system
metrics. Each leg answers a different question about where a bad answer came
from, which is the point of scoring them separately:

    retrieval    did the right evidence reach the generator?
                 -> source recall / hit / MRR against expected documents,
                    context precision (judge), keyword context recall
    generation   is the answer supported by that evidence?
                 -> faithfulness (embedding attribution + hard-error flags,
                    optionally an LLM claim judge)
    answer       does it address the question that was asked?
                 -> answer relevancy (embedding), probe coverage, locality
    system       latency, abstention / gap honesty

Everything here is deterministic and runs offline. The two LLM-judge helpers
are opt-in because a 3B judge is noisy and shares blind spots with the 3B
generator; treat their output as a second opinion, not ground truth.
"""
from __future__ import annotations

import random
import re
from itertools import combinations
from statistics import mean

import numpy as np

_CITE = re.compile(r"\[S(\d+)\]")
GAP_HEADING = re.compile(r"\*\*\s*what the local evidence does not cover\s*\*\*", re.I)

#: Warning prefixes emitted by the pipeline that mean a *specific* error was
#: detected, as opposed to a general caveat. These are counted separately from
#: the groundedness fraction because a fluent answer can score 100% grounded
#: and still carry one.
HARD_FLAGS = {
    "invented_figure": "figures not found in any cited passage",
    "scope_mismatch": "geographic scope mismatch",
    "catalog_figure": "attributed only to a dataset catalogue",
}


# --------------------------------------------------------------------------
# text helpers
# --------------------------------------------------------------------------

def split_body_and_gaps(text: str) -> tuple[str, str]:
    m = GAP_HEADING.search(text)
    return (text[:m.start()], text[m.end():]) if m else (text, "")


def count_gap_bullets(gap_text: str) -> int:
    return len([l for l in gap_text.split("\n")
                if re.match(r"\s*(?:[-•]|\*(?!\*))\s+\S", l)])


def hard_flags(warnings: list[str]) -> dict[str, int]:
    return {k: sum(1 for w in warnings if marker in w) for k, marker in HARD_FLAGS.items()}


def term_hits(text: str, terms: list[str]) -> list[str]:
    low = text.lower()
    return sorted({t for t in terms if re.search(rf"(?<![a-z0-9]){re.escape(t.lower())}", low)})


# --------------------------------------------------------------------------
# retrieval metrics (document level, against expected-source prefixes)
# --------------------------------------------------------------------------

def _matches(source_id: str, prefixes: list[str]) -> list[str]:
    return [p for p in prefixes if source_id.startswith(p)]


def retrieval_metrics(retrieved_ids: list[str], expected: list[str]) -> dict:
    """``retrieved_ids`` is ordered best-first, one source_id per passage.

    * ``source_recall``  - share of expected sources/families with >=1 passage
    * ``hit``            - any expected source retrieved at all
    * ``mrr``            - 1/rank of the first passage from an expected source
    * ``precision``      - share of passages that come from an expected source
    Expected entries are prefixes, so ``morpc_mtp_2024_2050`` covers every
    chapter of the MTP.
    """
    if not expected:
        return {"source_recall": None, "hit": None, "mrr": None, "precision": None}
    covered, first, relevant = set(), None, 0
    for rank, sid in enumerate(retrieved_ids, 1):
        m = _matches(sid, expected)
        if m:
            covered.update(m)
            relevant += 1
            first = first or rank
    return {
        "source_recall": len(covered) / len(expected),
        "hit": 1.0 if covered else 0.0,
        "mrr": 1.0 / first if first else 0.0,
        "precision": relevant / len(retrieved_ids) if retrieved_ids else 0.0,
    }


def probe_recall(text: str, probes: list[str]) -> float | None:
    if not probes:
        return None
    low = text.lower()
    return sum(p.lower() in low for p in probes) / len(probes)


def average_precision(relevance: list[bool]) -> float:
    """Rank-aware context precision (mean precision@i over relevant positions)."""
    hits, total = 0, 0.0
    for i, rel in enumerate(relevance, 1):
        if rel:
            hits += 1
            total += hits / i
    return total / hits if hits else 0.0


# --------------------------------------------------------------------------
# answer-level metrics
# --------------------------------------------------------------------------

def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def pairwise_mean(vectors: np.ndarray) -> float:
    """Mean off-diagonal cosine similarity of row vectors."""
    if len(vectors) < 2:
        return float("nan")
    return mean(cosine(vectors[i], vectors[j]) for i, j in combinations(range(len(vectors)), 2))


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a | b) else 1.0


def mean_pairwise_jaccard(sets: list[set]) -> float:
    if len(sets) < 2:
        return float("nan")
    return mean(jaccard(a, b) for a, b in combinations(sets, 2))


def discriminating_terms(term_sets: dict[str, list[str]]) -> dict[str, list[str]]:
    """Drop any term that appears in more than one stakeholder's list.

    Otherwise "crossing" (pedestrians *and* rail) or "signal" (drivers *and*
    freight) would let an answer score on someone else's perspective.
    """
    counts: dict[str, int] = {}
    for terms in term_sets.values():
        for t in set(terms):
            counts[t] = counts.get(t, 0) + 1
    return {k: [t for t in v if counts[t] == 1] for k, v in term_sets.items()}


def perspective_alignment(answers: dict[str, str], term_sets: dict[str, list[str]]) -> dict:
    """Does each stakeholder's answer sound like *that* stakeholder?

    For every answer, count distinct own-perspective terms and distinct terms
    from each other stakeholder. ``own_rank_first`` is True when its own list
    scores strictly highest - i.e. a reader could tell whose answer it is from
    vocabulary alone. ``lift`` is own hits minus the mean of the others.
    """
    terms = discriminating_terms(term_sets)
    out = {}
    for who, text in answers.items():
        counts = {k: len(term_hits(text, v)) for k, v in terms.items()}
        others = [c for k, c in counts.items() if k != who]
        own = counts.get(who, 0)
        out[who] = {
            "own": own,
            "others_mean": round(mean(others), 2) if others else 0.0,
            "lift": round(own - (mean(others) if others else 0.0), 2),
            "own_rank_first": own > max(others) if others else False,
            "own_terms": term_hits(text, terms.get(who, [])),
        }
    return out


# --------------------------------------------------------------------------
# uncertainty
# --------------------------------------------------------------------------

def bootstrap_ci(values: list[float], n: int = 2000, seed: int = 7,
                 alpha: float = 0.05) -> tuple[float, float, float]:
    """(mean, lo, hi). With ~24-34 questions an interval is the honest report."""
    vals = [v for v in values if v is not None and not (isinstance(v, float) and np.isnan(v))]
    if not vals:
        return float("nan"), float("nan"), float("nan")
    if len(vals) == 1:
        return vals[0], vals[0], vals[0]
    rng = random.Random(seed)
    means = sorted(mean(rng.choices(vals, k=len(vals))) for _ in range(n))
    return mean(vals), means[int(n * alpha / 2)], means[int(n * (1 - alpha / 2)) - 1]


# --------------------------------------------------------------------------
# optional LLM-judge metrics
# --------------------------------------------------------------------------

_CTX_JUDGE = """Question: {question}

Passage:
\"\"\"{passage}\"\"\"

Does the passage contain information that helps answer the question? Reply with exactly one word: Relevant or Irrelevant."""

_CLAIM_JUDGE = """Source passages:
\"\"\"{passages}\"\"\"

Claim: {claim}

Is the claim stated in or directly supported by the source passages above? Reply with exactly one word: Supported or Unsupported."""

#: Same width the generator saw (``prompts.render_passage``). Judging against a
#: shorter slice makes true claims look unsupported - an early version truncated
#: to 900 chars and rejected claims copied verbatim from the passage.
JUDGE_PASSAGE_CHARS = 1150


def _yes(raw: str) -> bool:
    return raw.strip().lower().startswith(("supported", "relevant", "yes"))


def judge_context_relevance(llm, question: str, passage: str) -> bool:
    prompt = _CTX_JUDGE.format(question=question[:700], passage=passage[:JUDGE_PASSAGE_CHARS])
    return _yes(llm.generate(prompt, max_tokens=5, temperature=0.0))


def judge_claim_support(llm, claim: str, passages: list[str]) -> bool:
    block = "\n\n".join(p[:JUDGE_PASSAGE_CHARS] for p in passages)
    prompt = _CLAIM_JUDGE.format(passages=block, claim=claim)
    return _yes(llm.generate(prompt, max_tokens=5, temperature=0.0))


def cited_claims(text: str, max_claims: int = 12) -> list[tuple[str, list[int]]]:
    """Cited sentences from the answer body, evenly sampled if there are many."""
    body, _ = split_body_and_gaps(text)
    out = []
    for line in body.split("\n"):
        for sent in re.split(r"(?<=[.!?])\s+(?=[A-Z(\[])", line):
            cites = sorted({int(n) for n in _CITE.findall(sent)})
            clean = _CITE.sub("", sent).strip()
            if cites and len(clean.split()) >= 6:
                out.append((clean, cites))
    if len(out) > max_claims:
        step = len(out) / max_claims
        out = [out[int(i * step)] for i in range(max_claims)]
    return out
