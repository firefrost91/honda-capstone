"""Load the three input files into one uniform passage collection.

The knowledge base has three very different shapes and all three matter:

``chunk``      Text extracted from planning PDFs. Carries the substantive
               evidence (crash statistics, action items, growth forecasts).
``doc_card``   One synthetic card per catalogued document. Lets the system
               answer "what evidence exists / what is this corpus made of"
               without having to stumble onto a chunk that happens to say so.
``data_summary`` Aggregate statistics computed from a GIS layer by
               ``rag.ingest.gis_aggregates`` (e.g. crashes by year and
               severity). Unlike a data card these ARE numbers, each carrying
               the query that produced it, so they may be cited for figures.
``data_card``  One synthetic card per GIS/tabular dataset. These are catalog
               entries only - the records themselves are NOT in the knowledge
               base - so the card states that explicitly. That distinction is
               the difference between "the crash data shows X" (a fabrication)
               and "crash records exist at ODOT TIMS and would show X" (true).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

from .config import CONFIG, Config
from .quality import QualityReport, clean_rows, published_year

#: Passage kinds that carry findings (as opposed to catalogue descriptions).
EVIDENCE_KINDS = frozenset({"chunk", "data_summary"})

# Collapse the ragged line breaks left by PDF text extraction.
_WS = re.compile(r"[ \t]*\n[ \t]*")
_MULTISPACE = re.compile(r"\s{3,}")


def _clean(text: str) -> str:
    text = _WS.sub("\n", text or "")
    text = _MULTISPACE.sub("  ", text)
    return text.strip()


def _informative(text: str, min_words: int) -> bool:
    """Reject page furniture: headers, page numbers, bare figure labels."""
    words = text.split()
    if len(words) < min_words:
        return False
    letters = sum(c.isalpha() for c in text)
    return letters / max(len(text), 1) > 0.45


@dataclass
class Passage:
    passage_id: str
    kind: str              # chunk | doc_card | data_card
    text: str
    title: str
    source_id: str
    organization: str = ""
    theme: str = ""
    citation_url: str = ""
    locator: str = ""
    page_number: int | None = None
    document_type: str = ""
    topics: tuple[str, ...] = ()
    caveats: tuple[str, ...] = ()
    word_count: int = 0
    #: geographic scope from the catalogue (region_specific, general_state_policy, ...)
    scope: str = ""
    published_year: int | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["topics"] = list(self.topics)
        d["caveats"] = list(self.caveats)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Passage":
        known = {f for f in cls.__dataclass_fields__}
        d = {k: v for k, v in d.items() if k in known}
        d["topics"] = tuple(d.get("topics") or ())
        d["caveats"] = tuple(d.get("caveats") or ())
        return cls(**d)

    @property
    def citation(self) -> str:
        """Human-readable provenance string shown next to every answer."""
        bits = [self.title]
        if self.organization and self.organization not in self.title:
            bits.append(f"({self.organization})")
        if self.locator:
            bits.append(f"- {self.locator}")
        return " ".join(bits)

    @property
    def embed_text(self) -> str:
        """What actually gets embedded - title gives short chunks context."""
        return f"{self.title}\n{self.text}" if self.kind in EVIDENCE_KINDS else self.text


# --------------------------------------------------------------------------
# loaders
# --------------------------------------------------------------------------

def load_document_catalog(cfg: Config = CONFIG) -> dict[str, dict]:
    raw = json.loads(Path(cfg.documents_file).read_text())
    return {s["source_id"]: s for s in raw["sources"]}


def load_gis_catalog(cfg: Config = CONFIG) -> dict[str, dict]:
    raw = json.loads(Path(cfg.gis_file).read_text())
    return {s["source_id"]: s for s in raw["sources"]}


def read_chunk_rows(cfg: Config = CONFIG) -> list[dict]:
    with Path(cfg.chunks_file).open() as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _chunk_passages(cfg: Config, catalog: dict[str, dict],
                    report: QualityReport | None = None) -> Iterable[Passage]:
    rows = read_chunk_rows(cfg)
    for r in rows:
        r["text"] = _clean(r.get("text", ""))
    if cfg.apply_quality_filters:
        rows, rep = clean_rows(rows, catalog, cfg.min_chunk_words, _informative)
        if report is not None:
            report.__dict__.update(rep.__dict__)
    else:
        rows = [r for r in rows if _informative(r["text"], cfg.min_chunk_words)]
    for r in rows:
        text = r["text"]
        meta = catalog.get(r["source_id"], {})
        yield Passage(
            passage_id=r["chunk_id"],
            kind="chunk",
            text=text,
            title=r.get("title", meta.get("title", r["source_id"])),
            source_id=r["source_id"],
            organization=r.get("organization", "") or meta.get("organization", ""),
            theme=r.get("theme", "") or meta.get("theme", ""),
            citation_url=r.get("citation_url") or r.get("source_url", ""),
            locator=r.get("locator", ""),
            page_number=r.get("page_number"),
            document_type=meta.get("document_type", ""),
            topics=tuple(meta.get("topics") or ()),
            caveats=tuple(r.get("caveats") or ()),
            word_count=len(text.split()),
            scope=meta.get("scope", ""),
            published_year=published_year(meta),
        )


def load_summary_rows(cfg: Config = CONFIG) -> list[dict]:
    """Aggregate GIS summaries written by ``rag.ingest.gis_aggregates``."""
    d = Path(cfg.derived_dir)
    if not d.exists():
        return []
    rows = []
    for f in sorted(d.glob("*_summary_chunks.jsonl")):
        rows += [json.loads(l) for l in f.open() if l.strip()]
    return rows


def _summary_passages(cfg: Config, gis: dict[str, dict]) -> Iterable[Passage]:
    for r in load_summary_rows(cfg):
        meta = gis.get(r["source_id"], {})
        text = _clean(r["text"])
        yield Passage(
            passage_id=r["chunk_id"],
            kind="data_summary",
            text=text,
            title=r.get("title") or f"{meta.get('title', r['source_id'])} - aggregate summary",
            source_id=r["source_id"],
            organization=meta.get("organization", ""),
            theme=meta.get("theme", ""),
            citation_url=r.get("citation_url", "") or meta.get("source_url", ""),
            locator=r.get("locator", "aggregate query"),
            document_type="dataset_summary",
            caveats=tuple(r.get("caveats") or ()),
            word_count=len(text.split()),
            scope="region_specific",
            published_year=r.get("year"),
        )


def _doc_card_passages(catalog: dict[str, dict]) -> Iterable[Passage]:
    for sid, d in catalog.items():
        lines = [
            f"Source document: {d.get('title','')}",
            f"Published by: {d.get('organization','')}",
            f"Document type: {d.get('document_type','')} | Theme: {d.get('theme','')}"
            f" | Geographic scope: {d.get('scope','')}",
        ]
        if d.get("topics"):
            lines.append("Topics covered: " + ", ".join(d["topics"]))
        if d.get("description"):
            lines.append(f"What it contains: {d['description']}")
        if d.get("relevance"):
            lines.append(f"Why it is relevant to transportation safety: {d['relevance']}")
        if d.get("caveats"):
            lines.append("Known limitations: " + " ".join(d["caveats"]))
        yield Passage(
            passage_id=f"doccard::{sid}",
            kind="doc_card",
            text="\n".join(x for x in lines if x.strip()),
            title=d.get("title", sid),
            source_id=sid,
            organization=d.get("organization", ""),
            theme=d.get("theme", ""),
            citation_url=d.get("source_url", ""),
            locator="source catalog entry",
            document_type=d.get("document_type", ""),
            topics=tuple(d.get("topics") or ()),
            caveats=tuple(d.get("caveats") or ()),
            word_count=0,
            scope=d.get("scope", ""),
            published_year=published_year(d),
        )


def _data_card_passages(gis: dict[str, dict],
                        summarised: set[str] = frozenset()) -> Iterable[Passage]:
    for sid, d in gis.items():
        lines = [
            f"Dataset: {d.get('title','')}",
            f"Maintained by: {d.get('organization','')}",
            f"Data type: {d.get('data_type','')} | Theme: {d.get('theme','')}"
            f" | Geometry: {d.get('geometry') or 'n/a'} | Access: {d.get('access_type','')}",
        ]
        if d.get("description"):
            lines.append(f"What it records: {d['description']}")
        if d.get("relevance"):
            lines.append(f"What it can be used for in safety analysis: {d['relevance']}")
        if d.get("reported_key_fields"):
            lines.append("Reported fields: " + ", ".join(d["reported_key_fields"]))
        if d.get("source_url"):
            lines.append(f"Service endpoint: {d['source_url']}")
        # This line is load-bearing: it stops the generator from reporting
        # dataset contents it has never seen.
        if sid in summarised:
            lines.append(
                "AGGREGATE SUMMARY AVAILABLE: year/severity totals computed from this "
                "layer are indexed separately as 'aggregate summary' passages. Quote "
                "figures from those passages only; individual records are still NOT loaded.")
        if not d.get("records_included", False):
            lines.append(
                "IMPORTANT DATA STATUS: this knowledge base holds only the catalog "
                "entry for this dataset. The underlying records are NOT loaded, so no "
                "counts, rates, locations or trends can be computed from it here. It "
                "would have to be queried at the service endpoint above."
            )
        if d.get("caveats"):
            lines.append("Caveats: " + " ".join(d["caveats"]))
        yield Passage(
            passage_id=f"datacard::{sid}",
            kind="data_card",
            text="\n".join(x for x in lines if x.strip()),
            title=d.get("title", sid),
            source_id=sid,
            organization=d.get("organization", ""),
            theme=d.get("theme", ""),
            citation_url=d.get("source_url", "") or d.get("data_access_url", ""),
            locator="GIS data catalog entry",
            document_type="dataset",
            caveats=tuple(d.get("caveats") or ()),
            word_count=0,
        )


def load_passages(cfg: Config = CONFIG, report: QualityReport | None = None) -> list[Passage]:
    docs = load_document_catalog(cfg)
    gis = load_gis_catalog(cfg)
    passages = list(_chunk_passages(cfg, docs, report))
    summaries = list(_summary_passages(cfg, gis))
    passages += summaries
    passages += list(_doc_card_passages(docs))
    passages += list(_data_card_passages(gis, {p.source_id for p in summaries}))
    return passages


if __name__ == "__main__":  # quick sanity check
    import collections
    ps = load_passages()
    print(f"{len(ps)} passages")
    print(collections.Counter(p.kind for p in ps))
    for p in ps:
        if p.kind == "data_card":
            print("\n--- sample data card ---\n" + p.text)
            break
