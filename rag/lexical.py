"""Self-contained BM25 with domain-aware tokenisation.

Written out rather than pulled from a library because the tokeniser needs to
understand this domain: ``I-70``/``IR-70``, ``SR-161``, ``VRU``, ``HIN`` and
``AADT`` all have to survive tokenisation and match their expansions, or the
sparse half of the hybrid retriever misses the most specific queries.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict

# Keep route designators (i-70, sr161, us-33) and acronyms intact.
_TOKEN = re.compile(r"[a-z0-9]+(?:[-/][a-z0-9]+)*")

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "can", "could",
    "did", "do", "does", "for", "from", "had", "has", "have", "how", "i", "if", "in",
    "into", "is", "it", "its", "may", "might", "must", "of", "on", "or", "should",
    "so", "some", "such", "than", "that", "the", "their", "them", "then", "there",
    "these", "they", "this", "those", "to", "was", "we", "were", "what", "when",
    "where", "which", "while", "who", "why", "will", "with", "would", "you", "your",
}

#: Query-side expansion only. Lets a plain-English question reach documents
#: that use planner shorthand, without polluting document term statistics.
SYNONYMS: dict[str, tuple[str, ...]] = {
    "crash": ("crashes", "collision", "collisions", "accident"),
    "crashes": ("crash", "collision", "collisions"),
    "fatal": ("fatality", "fatalities", "death", "deaths", "killed"),
    "serious": ("severe", "incapacitating", "injury"),
    "pedestrian": ("pedestrians", "walking", "walk", "ped"),
    "bicycle": ("bicyclist", "bicyclists", "bike", "biking", "cyclist", "cycling"),
    "speed": ("speeding", "speeds", "speed-limit", "posted"),
    "speeding": ("speed", "speeds", "speed-limit"),
    "safety": ("safe", "hsip", "vision-zero"),
    "equity": ("environmental-justice", "disadvantaged", "underserved", "title-vi"),
    "community": ("neighborhood", "neighborhoods", "residents", "public"),
    "growth": ("forecast", "projected", "projection", "projections", "2050"),
    "population": ("households", "residents", "demographic", "demographics"),
    "employment": ("jobs", "job", "employers", "workforce"),
    "transit": ("cota", "bus", "linkus", "brt"),
    "cost": ("costs", "budget", "funding", "estimate", "estimates", "expenditure"),
    "delay": ("delayed", "schedule", "timeline", "postponed", "phasing"),
    "intersection": ("intersections", "roundabout", "signalized", "junction"),
    "corridor": ("corridors", "segment", "segments", "route"),
    "emergency": ("ems", "responder", "responders", "response", "incident"),
    "post-crash": ("ems", "emergency", "incident", "response", "trauma"),
    "freight": ("truck", "trucks", "trucking", "goods"),
    "data": ("dataset", "datasets", "database", "records", "gis"),
    "trend": ("trends", "change", "changed", "over-time", "historical"),
    "vru": ("vulnerable", "pedestrian", "bicyclist"),
    "hin": ("high-injury", "high", "injury", "network"),
    "i-70": ("ir-70", "i70", "interstate-70"),
    "i-71": ("ir-71", "i71", "interstate-71"),
    "sr-161": ("sr161", "161"),
}


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall((text or "").lower()) if t not in STOPWORDS and len(t) > 1]


def expand_query(tokens: list[str]) -> list[str]:
    out = list(tokens)
    for t in tokens:
        out.extend(SYNONYMS.get(t, ()))
    return out


class BM25:
    """Okapi BM25. k1/b at the usual defaults; corpus is small so this is fast."""

    def __init__(self, corpus_tokens: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.n_docs = len(corpus_tokens)
        self.doc_len = [len(d) for d in corpus_tokens]
        self.avgdl = sum(self.doc_len) / max(self.n_docs, 1)
        self.tf: list[Counter] = [Counter(d) for d in corpus_tokens]
        df: Counter = Counter()
        for counts in self.tf:
            df.update(counts.keys())
        self.idf = {
            term: math.log(1 + (self.n_docs - n + 0.5) / (n + 0.5))
            for term, n in df.items()
        }
        # term -> doc ids, so scoring only touches documents that can score.
        self.postings: dict[str, list[int]] = defaultdict(list)
        for i, counts in enumerate(self.tf):
            for term in counts:
                self.postings[term].append(i)

    def search(self, query_tokens: list[str], top_k: int = 60) -> list[tuple[int, float]]:
        scores: dict[int, float] = defaultdict(float)
        for term in set(query_tokens):
            idf = self.idf.get(term)
            if idf is None:
                continue
            for doc_id in self.postings[term]:
                freq = self.tf[doc_id][term]
                denom = freq + self.k1 * (
                    1 - self.b + self.b * self.doc_len[doc_id] / max(self.avgdl, 1e-9)
                )
                scores[doc_id] += idf * freq * (self.k1 + 1) / denom
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        return ranked[:top_k]
