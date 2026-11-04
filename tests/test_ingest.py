"""Ingestion pipeline: fetch -> extract -> chunk -> merge, and GIS aggregates. Offline."""
from __future__ import annotations

import io
import json
import urllib.error
from dataclasses import replace
from pathlib import Path

import pytest

from rag.config import CONFIG
from rag.corpus import load_passages
from rag.ingest import __main__ as ingest
from rag.ingest.chunk import MAX_WORDS, chunk_source, split_page
from rag.ingest.extract import content_status, extract, html_text
from rag.ingest.fetch import fetch
from rag.ingest.gis_aggregates import (render_chunks, render_trend_chunks, resolve_fields,
                                       summarise_layer)
from tests.fixtures.make import ARCGIS_META, HTML_PAGE, fake_arcgis, minimal_pdf

SENT = "Pedestrian crashes on Morse Road increased near COTA stops, according to the 2024 report."
CHUNK_KEYS = {"chunk_id", "source_id", "title", "text", "source_url", "citation_url",
              "page_number", "locator", "organization", "theme", "related_project_ids",
              "parent_source_id", "retrieved_at", "original_path", "caveats", "word_count",
              "char_start", "char_end", "content_sha256"}


class _Resp(io.BytesIO):
    def __init__(self, data, ct, url):
        super().__init__(data)
        self.headers = {"Content-Type": ct}
        self._url = url

    def geturl(self):
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeOpener:
    """Serves registry URLs from memory; anything else is a 404."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = 0

    def open(self, req, timeout=None):
        self.calls += 1
        url = req.full_url
        if url not in self.routes:
            raise urllib.error.HTTPError(url, 404, "nf", {}, None)
        data, ct = self.routes[url]
        return _Resp(data, ct, url)


# ---- extract / chunk --------------------------------------------------------

def test_html_extraction_drops_navigation_and_scripts():
    title, text = html_text(HTML_PAGE)
    assert title == "Vision Zero Progress"
    assert "Morse Road" in text and "Leading pedestrian intervals" in text
    assert "tracking" not in text and "Navigation item" not in text and "footer" not in text


def test_pdf_extraction_is_per_page_and_counts_blank_pages(tmp_path):
    f = tmp_path / "doc.pdf"
    f.write_bytes(minimal_pdf([SENT * 2, "", SENT * 2]))
    ex = extract(f)
    assert ex.kind == "pdf" and [p for p, _ in ex.pages] == [1, 2, 3]
    assert ex.n_empty_pages == 1
    status, caveats = content_status(ex)
    assert status == "ready_with_caveats" and "1 of 3" in caveats[0]


def test_chunker_respects_word_limit_and_overlaps():
    text = " ".join([SENT] * 120)
    spans = split_page(text)
    assert len(spans) > 1
    assert all(len(text[a:b].split()) <= MAX_WORDS for a, b in spans)
    assert all(spans[i + 1][0] < spans[i][1] for i in range(len(spans) - 1)), "no overlap"
    assert spans[-1][1] == len(text.rstrip())


def test_chunks_match_the_existing_schema():
    src = {"source_id": "vz_report", "title": "VZ", "source_url": "https://x.org/r.pdf",
           "organization": "City of Columbus", "theme": "vision_zero"}
    rows = chunk_source(src, [(3, " ".join([SENT] * 40)), (None, SENT * 3)])
    assert rows and all(set(r) == CHUNK_KEYS for r in rows)
    assert rows[0]["chunk_id"] == "vz_report__p0003__c001"
    assert rows[0]["citation_url"].endswith("#page=3") and rows[0]["locator"] == "PDF page 3"
    assert rows[-1]["chunk_id"].startswith("vz_report__p0000__")
    existing = json.loads(Path(CONFIG.chunks_file).open().readline())
    assert set(existing) == CHUNK_KEYS


# ---- fetch ------------------------------------------------------------------

def test_fetch_records_provenance_and_uses_cache(tmp_path):
    opener = FakeOpener({"https://x.org/a.pdf": (b"%PDF-1.4 data", "application/pdf")})
    r = fetch("a", "https://x.org/a.pdf", tmp_path, opener=opener)
    assert r.ok and r.path.suffix == ".pdf" and len(r.sha256) == 64 and r.retrieved_at
    r2 = fetch("a", "https://x.org/a.pdf", tmp_path, opener=opener)
    assert r2.from_cache and opener.calls == 1


def test_fetch_does_not_retry_a_404(tmp_path, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    opener = FakeOpener({})
    r = fetch("gone", "https://x.org/missing.pdf", tmp_path, opener=opener)
    assert not r.ok and "404" in r.error and opener.calls == 1


# ---- end to end: registry -> data files -> passages ---------------------------

@pytest.fixture
def sandbox(tmp_path):
    """A copy of the data files plus a two-source registry, all under tmp_path."""
    for name in ("documents.json", "document_chunks.jsonl", "gis_sources.json"):
        (tmp_path / name).write_text(Path(CONFIG.documents_file).with_name(name).read_text())
    registry = {"sources": [
        {"source_id": "test_vz_report", "title": "Test VZ Report 2024", "organization": "City",
         "document_type": "annual_report", "theme": "vision_zero", "scope": "region_specific",
         "source_url": "https://x.org/vz.pdf", "topics": ["vision zero"], "status": "candidate"},
        {"source_id": "test_web_page", "title": "Test Web Page", "organization": "City",
         "document_type": "web_page", "theme": "vision_zero", "scope": "region_specific",
         "source_url": "https://x.org/page", "status": "candidate"},
        {"source_id": "test_dead_link", "title": "Dead", "source_url": "https://x.org/dead",
         "status": "candidate"},
    ]}
    (tmp_path / "registry.json").write_text(json.dumps(registry))
    cfg = replace(CONFIG, documents_file=tmp_path / "documents.json",
                  chunks_file=tmp_path / "document_chunks.jsonl",
                  gis_file=tmp_path / "gis_sources.json",
                  registry_file=tmp_path / "registry.json",
                  originals_dir=tmp_path / "originals", derived_dir=tmp_path / "derived")
    opener = FakeOpener({
        "https://x.org/vz.pdf": (minimal_pdf([SENT * 3, SENT * 3]), "application/pdf"),
        "https://x.org/page": (HTML_PAGE.replace("<p>", "<p>" + SENT + " ").encode(), "text/html"),
    })
    return cfg, opener


def test_ingest_merges_new_sources_and_they_become_passages(sandbox, monkeypatch):
    cfg, opener = sandbox
    monkeypatch.setattr("time.sleep", lambda s: None)
    monkeypatch.setattr(ingest, "EVAL_DIR", cfg.documents_file.parent)
    before = len(load_passages(cfg))
    reports = ingest.run(cfg=cfg, opener=opener)
    status = {r["source_id"]: r["status"] for r in reports}
    assert status == {"test_vz_report": "ready", "test_web_page": "ready",
                      "test_dead_link": "failed"}
    catalog = {s["source_id"]: s for s in json.loads(cfg.documents_file.read_text())["sources"]}
    assert catalog["test_vz_report"]["sha256"] and catalog["test_vz_report"]["index_eligible"]
    assert catalog["test_dead_link"]["index_eligible"] is False
    passages = load_passages(cfg)
    assert len(passages) > before
    assert {"test_vz_report", "test_web_page"} <= {p.source_id for p in passages
                                                    if p.kind == "chunk"}


def test_ingest_is_idempotent(sandbox, monkeypatch):
    cfg, opener = sandbox
    monkeypatch.setattr("time.sleep", lambda s: None)
    monkeypatch.setattr(ingest, "EVAL_DIR", cfg.documents_file.parent)
    def state():
        rows = [json.loads(l) for l in cfg.chunks_file.read_text().splitlines()]
        return [(r["chunk_id"], r["content_sha256"]) for r in rows]

    ingest.run(cfg=cfg, opener=opener)
    first = state()
    ingest.run(cfg=cfg, opener=opener, refresh=True)   # re-download, re-chunk, re-merge
    assert state() == first


def test_failed_retry_never_overwrites_a_good_source(sandbox, monkeypatch):
    cfg, _ = sandbox
    monkeypatch.setattr("time.sleep", lambda s: None)
    monkeypatch.setattr(ingest, "EVAL_DIR", cfg.documents_file.parent)
    entry, rows, _ = ingest.ingest_source(
        {"source_id": "linkus_overview", "source_url": "https://x.org/dead"}, cfg,
        opener=FakeOpener({}))
    ingest.merge([entry], rows, cfg)
    cat = {s["source_id"]: s for s in json.loads(cfg.documents_file.read_text())["sources"]}
    assert cat["linkus_overview"]["content_status"] == "ready"


def test_registry_entries_are_well_formed():
    reg = json.loads(Path(CONFIG.registry_file).read_text())["sources"]
    ids = [s["source_id"] for s in reg]
    assert len(ids) == len(set(ids))
    for s in reg:
        assert s["source_url"].startswith("https://"), s["source_id"]
        assert s.get("gap_targeted"), s["source_id"]


# ---- GIS aggregates ------------------------------------------------------------

LAYER = {"source_id": "odot_crash_2023", "title": "ODOT Crash Data - 2023",
         "source_url": "https://tims.example/Safety/2023_Crash_Locations/MapServer/0",
         "query_url": "https://tims.example/Safety/2023_Crash_Locations/MapServer/0/query",
         "organization": "ODOT"}


def test_fields_are_resolved_from_layer_metadata():
    lf = resolve_fields(ARCGIS_META)
    assert (lf.oid, lf.severity, lf.year, lf.county) == (
        "OBJECTID", "CRASH_SEVERITY_CD", "CRASH_YR", "COUNTY_NME")
    assert lf.pedestrian == "PEDESTRIAN_IND" and lf.bicycle == "BICYCLE_IND"
    assert lf.domains["CRASH_SEVERITY_CD"]["1"] == "Fatal"


def test_layer_without_severity_fails_loudly():
    meta = {"objectIdField": "OBJECTID", "fields": [{"name": "OBJECTID"}, {"name": "ROUTE"}]}
    with pytest.raises(KeyError, match="severity"):
        resolve_fields(meta)


def test_aggregates_are_regional_decoded_and_self_describing():
    s = summarise_layer(LAYER, get=fake_arcgis)
    assert s.counts[("FRANKLIN", 2023)] == {"Fatal": 120, "Serious Injury": 900,
                                            "Property Damage Only": 30000}
    assert ("CUYAHOGA", 2023) not in s.counts          # outside the region
    assert sum(s.counts[("OHIO (statewide)", 2023)].values()) == 31175
    assert s.modes[("FRANKLIN", 2023)] == {"pedestrian": 700, "bicycle": 210}
    rows = render_chunks(s)
    fra = next(r for r in rows if r["area"] == "FRANKLIN")
    assert "Franklin County in 2023" in fra["text"] and "Fatal: 120" in fra["text"]
    assert "involving a pedestrian: 700".lower() in fra["text"].lower()
    assert LAYER["source_url"] in fra["text"]
    state = next(r for r in rows if r["area"].startswith("OHIO"))
    assert "NOT a Central Ohio figure" in state["text"]


def test_trend_passage_spans_years_across_layers():
    s23 = summarise_layer(LAYER, get=fake_arcgis)
    s22 = summarise_layer(LAYER, get=fake_arcgis)
    s22.counts = {(a, 2022): {k: v // 2 for k, v in sev.items()} for (a, _), sev in s22.counts.items()}
    trend = render_trend_chunks([s22, s23])
    fra = next(r for r in trend if "Franklin" in r["text"])
    assert "2022" in fra["text"] and "2023" in fra["text"] and "120 fatal" in fra["text"]


def test_summaries_load_as_citable_data_summary_passages(tmp_path):
    from rag.ingest.gis_aggregates import _write
    cfg = replace(CONFIG, derived_dir=tmp_path)
    _write(render_chunks(summarise_layer(LAYER, get=fake_arcgis)), "odot_crash_2023", None, tmp_path)
    ps = load_passages(cfg)
    summ = [p for p in ps if p.kind == "data_summary"]
    assert summ and all(p.source_id == "odot_crash_2023" for p in summ)
    card = next(p for p in ps if p.passage_id == "datacard::odot_crash_2023")
    assert "AGGREGATE SUMMARY AVAILABLE" in card.text
    other = next(p for p in ps if p.passage_id == "datacard::odot_crash_2022")
    assert "AGGREGATE SUMMARY AVAILABLE" not in other.text


def test_figures_cited_to_a_data_summary_are_not_flagged():
    from rag.attribute import SentenceAttribution, check_catalog_claims
    a = [SentenceAttribution(text="Franklin County had 120 fatal crashes in 2023.",
                             citations=[1], support=0.8, supported=True, model_cited=[])]
    assert check_catalog_claims(a, ["data_summary"]) == []
    assert check_catalog_claims(a, ["data_card"]) == [a[0].text]


# ---- NHTSA FARS ------------------------------------------------------------------

def _fars_payload(year, deaths_per_crash):
    rows = [{"ST_CASE": 390000 + i, "CaseYear": str(year), "FATALS": str(d), "COUNTYNAME": "FRANKLIN (49)"}
            for i, d in enumerate(deaths_per_crash)]
    return {"Count": len(rows), "Message": "Results returned successfully", "Results": [rows]}


def test_fars_counts_crashes_and_deaths_per_year_and_builds_trend_passages():
    from rag.ingest import fars
    data = {2019: [1, 1, 2], 2020: [1, 1, 1, 1], 2021: [3, 1, 1, 1, 1]}
    calls = []

    def get(url, params):
        calls.append(params)
        assert params["state"] == 39 and params["format"] == "json"
        return _fars_payload(params["fromCaseYear"], data[params["fromCaseYear"]])

    s = fars.fetch_county("Franklin", 49, 2019, 2021, get)
    assert s.years == {2019: (3, 4), 2020: (4, 4), 2021: (5, 7)}
    assert len(calls) == 3 and all(c["county"] == 49 for c in calls)
    rows = fars.render([s], "2026-11-04")
    assert len(rows) == 1 and rows[0]["source_id"] == "nhtsa_fars"
    text = rows[0]["text"]
    assert "2019: 4 deaths in 3 fatal crashes" in text and "(+75%)" in text


def test_fars_region_total_sums_counties():
    from rag.ingest import fars
    a, b = fars.CountySeries("Franklin", {2020: (10, 12)}), fars.CountySeries("Delaware", {2020: (2, 2)})
    rows = fars.render([a, b], "2026-11-04")
    region = next(r for r in rows if r["area"].startswith("Central Ohio"))
    assert "2020: 14 deaths in 12 fatal crashes" in region["text"]


def test_fars_without_a_deaths_field_fails_loudly():
    from rag.ingest import fars
    with pytest.raises(KeyError, match="FATALS"):
        fars.count_rows([{"ST_CASE": 1, "SOMETHING": 2}], 2020)


def test_fars_nested_and_flat_results_are_both_read():
    from rag.ingest.fars import _rows
    row = {"ST_CASE": 1, "FATALS": 1}
    assert _rows({"Results": [[row, row]]}) == [row, row]
    assert _rows({"Results": [row]}) == [row]
    assert _rows([row]) == [row]


def test_fars_summaries_load_as_data_summary_passages(tmp_path):
    from rag.ingest import fars
    cfg = replace(CONFIG, derived_dir=tmp_path)
    assert fars.run(2020, 2020, cfg=cfg, counties={"Franklin": 49},
                    get=lambda u, p: _fars_payload(2020, [1, 2])) == 0
    ps = [p for p in load_passages(cfg) if p.source_id == "nhtsa_fars"]
    assert ps and ps[0].kind == "data_summary" and "3 deaths in 2 fatal crashes" in ps[0].text
