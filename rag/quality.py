"""Corpus hygiene, applied when chunks are loaded.

The chunk file came out of a PDF-extraction handoff and carries the usual
debris. None of it is harmless in a vector index:

* **Repeated page furniture.** ~300 MORPC TIP project pages share the same
  five template lines (``PID: Project Name: ...``, ``Phase STIP Fund Type
  ...``) and every MTP chapter page opens with ``2024-2050 COLUMBUS AREA``.
  Embedded as-is, those pages sit almost on top of each other: the template
  dominates the vector and the project-specific text barely moves it. That is
  a direct route to embedding collapse and to "hub" passages that come back
  for every query.
* **Tables of contents and dot leaders.** Keyword-dense, content-free, and
  they win BM25 on almost any query that names a chapter topic.
* **Duplicates.** Exact and near-exact copies spend retrieval slots twice.
* **Ineligible pages.** ``documents.json`` already records which sources are
  index-eligible and which page ranges are in scope; the loader ignored it.

Everything here works on the raw chunk dicts and never rewrites
``data/document_chunks.jsonl``, so the cleaning is reversible and its effect
is measurable: ``python -m rag.quality`` prints what was dropped and why.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# ---- boilerplate ---------------------------------------------------------

#: A line is page furniture for a source if it recurs in at least this share
#: of that source's chunks AND at least ``BOILERPLATE_MIN_COUNT`` times.
BOILERPLATE_MIN_SHARE = 0.25
BOILERPLATE_MIN_COUNT = 5
#: Short labels ("Description:", "Termini:") recur too, but they carry the
#: structure a reader needs to parse a project record. Only longer lines are
#: candidates for stripping.
BOILERPLATE_MIN_CHARS = 18

#: After boilerplate is stripped, a chunk that passed the prose test on its
#: original text is kept unless fewer than this many words remain.
STRIPPED_MIN_WORDS = 10

_ROMAN = re.compile(r"\b[ivxlc]{1,6}\b")
_DIGITS = re.compile(r"\d+")
_SPACES = re.compile(r"\s+")

#: Above this share of single-character "words", a page was extracted per
#: glyph rather than per word and is not text at all - see ``garble_ratio``.
#: Real prose in this corpus sits at 3-8%; map legends and tables reach ~25%.
GARBLED_WORD_RATIO = 0.35


def garble_ratio(text: str) -> float:
    """Share of whitespace-separated tokens that are a single character.

    Some PDFs position every glyph independently. Sorting those glyphs by
    coordinate - what a PDF text extractor does by default - interleaves
    columns, map labels and overlays into character soup:
    ``'o o C n c n p s a i o . t f A n o n e s u u'``. It is not garbage in an
    obvious way: it has the right length, the right character distribution and
    passes a letters-ratio test, so it indexes cleanly and embeds to roughly
    the same point as every other scrambled page - which is why it shows up as
    near-duplicates and per-source collapse rather than as an extraction
    error. The single-character token share separates it from real prose by an
    order of magnitude.

    Short passages are exempt: a handful of tokens says nothing either way.
    """
    words = text.split()
    if len(words) < 20:
        return 0.0
    return sum(1 for w in words if len(w) == 1) / len(words)


def _norm_line(line: str) -> str:
    """Normalise a line so running headers with changing page numbers match."""
    s = line.strip().lower()
    s = _DIGITS.sub("#", s)
    s = _ROMAN.sub("@", s)
    return _SPACES.sub(" ", s)


def find_boilerplate(rows: list[dict], min_share: float = BOILERPLATE_MIN_SHARE,
                     min_count: int = BOILERPLATE_MIN_COUNT,
                     min_chars: int = BOILERPLATE_MIN_CHARS) -> dict[str, set[str]]:
    """Return {source_id: {normalised boilerplate line, ...}}."""
    per_source_lines: dict[str, Counter] = defaultdict(Counter)
    per_source_n: Counter = Counter()
    for r in rows:
        sid = r["source_id"]
        per_source_n[sid] += 1
        seen = {_norm_line(l) for l in (r.get("text") or "").split("\n")
                if len(l.strip()) >= min_chars}
        per_source_lines[sid].update(seen)
    out: dict[str, set[str]] = {}
    for sid, counts in per_source_lines.items():
        n = per_source_n[sid]
        bad = {l for l, c in counts.items() if c >= min_count and c / n >= min_share}
        if bad:
            out[sid] = bad
    return out


def strip_lines(text: str, boilerplate: set[str]) -> str:
    if not boilerplate:
        return text
    kept = [l for l in text.split("\n") if _norm_line(l) not in boilerplate]
    return "\n".join(kept).strip()


# ---- noise ---------------------------------------------------------------

_DOT_LEADER = re.compile(r"(?:\.\s?){6,}|(?:…){3,}|(?:_\s?){8,}")
_TOC = re.compile(r"\b(table of contents|table of tables|table of figures|list of (?:figures|tables|maps))\b",
                  re.I)


def noise_reason(text: str) -> str | None:
    """Why a chunk is navigation/table debris rather than prose, or None."""
    lines = [l for l in text.split("\n") if l.strip()]
    # A contents heading near the top of the chunk, not a passing reference
    # ("see the Table of Contents") further down a page of prose.
    if any(_TOC.search(l) for l in lines[:4]):
        return "table_of_contents"
    if lines:
        leaders = sum(1 for l in lines if _DOT_LEADER.search(l))
        if leaders >= 3 and leaders / len(lines) >= 0.3:
            return "dot_leaders"
    stripped = re.sub(r"\s", "", text)
    if stripped:
        alpha = sum(c.isalpha() for c in stripped) / len(stripped)
        if alpha < 0.40:
            return "numeric_table"
    return None


# ---- duplicates ----------------------------------------------------------

NEAR_DUP_JACCARD = 0.9
_SHINGLE = 5


def _shingles(text: str, n: int = _SHINGLE) -> set[int]:
    words = re.findall(r"\w+", text.lower())
    if len(words) < n:
        return {hash(" ".join(words))}
    return {hash(" ".join(words[i:i + n])) for i in range(len(words) - n + 1)}


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / max(len(a | b), 1)


def content_hash(text: str) -> str:
    return hashlib.sha256(_SPACES.sub(" ", text.strip().lower()).encode()).hexdigest()


# ---- eligibility ---------------------------------------------------------

def eligibility_reason(row: dict, meta: dict) -> str | None:
    """Respect the catalogue's own index_eligible flag and page range."""
    if meta and meta.get("index_eligible") is False:
        return "source_not_index_eligible"
    rng = (meta or {}).get("indexed_page_range")
    page = row.get("page_number")
    if rng and page is not None and not (rng[0] <= page <= rng[1]):
        return "outside_indexed_page_range"
    return None


# ---- the pass ------------------------------------------------------------

@dataclass
class QualityReport:
    n_raw: int = 0
    n_kept: int = 0
    dropped: Counter = field(default_factory=Counter)
    dropped_by_source: dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))
    raw_by_source: Counter = field(default_factory=Counter)
    kept_by_source: Counter = field(default_factory=Counter)
    boilerplate: dict[str, list[str]] = field(default_factory=dict)
    chars_stripped: int = 0
    merged: int = 0

    def drop(self, sid: str, reason: str) -> None:
        self.dropped[reason] += 1
        self.dropped_by_source[sid][reason] += 1

    def to_dict(self) -> dict:
        total = max(self.n_kept, 1)
        share = {s: round(n / total, 3) for s, n in self.kept_by_source.most_common()}
        return {
            "n_raw_chunks": self.n_raw,
            "n_kept_chunks": self.n_kept,
            "dropped": dict(self.dropped),
            "chars_of_boilerplate_stripped": self.chars_stripped,
            "short_fragments_merged_into_next_chunk": self.merged,
            "per_source": {
                s: {"raw": self.raw_by_source[s], "kept": self.kept_by_source.get(s, 0),
                    "share_of_corpus": share.get(s, 0.0),
                    "dropped": dict(self.dropped_by_source.get(s, {}))}
                for s in sorted(self.raw_by_source, key=lambda s: -self.raw_by_source[s])
            },
            "boilerplate_lines": self.boilerplate,
        }


def clean_rows(rows: list[dict], catalog: dict[str, dict], min_words: int,
               informative=None) -> tuple[list[dict], QualityReport]:
    """Filter and clean raw chunk dicts. Returns (kept rows, report).

    ``informative`` is the corpus-level prose test (``corpus._informative``),
    passed in to avoid a circular import. It is applied to the original text;
    after stripping only the word count is re-checked, because a page that was
    nothing but template is empty once the template goes.
    """
    rep = QualityReport(n_raw=len(rows))
    for r in rows:
        rep.raw_by_source[r["source_id"]] += 1

    eligible = []
    for r in rows:
        why = eligibility_reason(r, catalog.get(r["source_id"], {}))
        if why:
            rep.drop(r["source_id"], why)
        else:
            eligible.append(r)

    boiler = find_boilerplate(eligible)
    rep.boilerplate = {s: sorted(v) for s, v in boiler.items()}

    seen_exact: set[str] = set()
    shingles_by_source: dict[str, list[set[int]]] = defaultdict(list)
    kept = []
    carry = ""   # a fragment too short to stand alone, waiting for its page-mate
    for pos, r in enumerate(eligible):
        sid = r["source_id"]
        original = r.get("text") or ""
        text = strip_lines(original, boiler.get(sid, set()))
        rep.chars_stripped += len(original) - len(text)
        if carry:
            text = (carry + "\n" + text).strip()
            carry = ""

        # Noise and prose tests look at the ORIGINAL text: stripping the
        # letter-heavy template lines from a TIP page leaves mostly dollar
        # figures, which would then fail a letters-ratio test it passed before.
        why = noise_reason(original)
        if why:
            rep.drop(sid, why)
            continue
        # Defence in depth: rag.ingest now retries a garbled page with a
        # different reading order, but a chunk file produced before that - or
        # by another hand-off - can still carry character soup.
        if garble_ratio(original) >= GARBLED_WORD_RATIO:
            rep.drop(sid, "garbled_text_extraction")
            continue
        if informative is not None and not informative(original, min_words):
            rep.drop(sid, "too_short_or_non_prose")
            continue
        if len(text.split()) < min_words:
            # Pages split across chunks often leave a short head (a TIP
            # project's ID, name and work category) whose substance is in the
            # next chunk. Dropping the head loses the link between project and
            # cost, so fold it forward instead.
            nxt = eligible[pos + 1] if pos + 1 < len(eligible) else None
            if (nxt is not None and nxt["source_id"] == sid
                    and nxt.get("page_number") == r.get("page_number")):
                carry = text
                rep.merged += 1
                continue
            # Otherwise keep it unless stripping left almost nothing: a short
            # page can still be the one that says "In 2019, 54 deaths occurred
            # in 49 fatal crashes".
            if len(text.split()) < STRIPPED_MIN_WORDS:
                rep.drop(sid, "only_boilerplate")
                continue
        h = content_hash(text)
        if h in seen_exact:
            rep.drop(sid, "exact_duplicate")
            continue
        sh = _shingles(text)
        if any(jaccard(sh, other) >= NEAR_DUP_JACCARD for other in shingles_by_source[sid]):
            rep.drop(sid, "near_duplicate")
            continue
        seen_exact.add(h)
        shingles_by_source[sid].append(sh)
        out = dict(r)
        out["text"] = text
        kept.append(out)
        rep.kept_by_source[sid] += 1
    rep.n_kept = len(kept)
    return kept, rep


def published_year(meta: dict) -> int | None:
    """Best-effort publication year from catalogue metadata (title, then URL)."""
    if isinstance(meta.get("published_year"), int):
        return meta["published_year"]
    for text in (meta.get("title", ""), meta.get("source_url", "")):
        m = re.search(r"(?<!\d)(20[0-3]\d|19[89]\d)(?!\d)", text or "")
        if m:
            return int(m.group(1))
    return None


# ---- CLI -----------------------------------------------------------------

def report(write: bool = True) -> dict:
    from .config import CONFIG, EVAL_DIR
    from .corpus import _clean, _informative, load_document_catalog, read_chunk_rows

    catalog = load_document_catalog(CONFIG)
    rows = read_chunk_rows(CONFIG)
    for r in rows:
        r["text"] = _clean(r.get("text", ""))
    _, rep = clean_rows(rows, catalog, CONFIG.min_chunk_words, _informative)
    d = rep.to_dict()

    # catalogue coverage: documents that contribute nothing to the index
    d["sources_without_chunks"] = sorted(
        sid for sid, m in catalog.items() if rep.kept_by_source.get(sid, 0) == 0)
    d["dominant_sources"] = [s for s, v in d["per_source"].items()
                             if v["share_of_corpus"] > 0.35]

    print(f"raw chunks {d['n_raw_chunks']}  ->  kept {d['n_kept_chunks']}  "
          f"({d['chars_of_boilerplate_stripped']:,} chars of boilerplate stripped, "
          f"{d['short_fragments_merged_into_next_chunk']} short fragments merged forward)")
    for reason, n in sorted(d["dropped"].items(), key=lambda kv: -kv[1]):
        print(f"  dropped {n:4d}  {reason}")
    print(f"\n{'source':48s} {'raw':>5s} {'kept':>5s} {'share':>6s}")
    for sid, v in d["per_source"].items():
        flag = "  <- dominant" if sid in d["dominant_sources"] else ""
        print(f"{sid[:48]:48s} {v['raw']:5d} {v['kept']:5d} {v['share_of_corpus']:6.1%}{flag}")
    if d["sources_without_chunks"]:
        print("\ncatalogued but contributing no chunks: " + ", ".join(d["sources_without_chunks"]))
    if write:
        out = EVAL_DIR / "data_quality.json"
        out.write_text(json.dumps(d, indent=2))
        print(f"\nwrote {out}")
    return d


if __name__ == "__main__":
    report()
