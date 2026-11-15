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
from rag.ingest.extract import Extracted, _page_text, content_status, extract, html_text
from rag.quality import clean_rows, garble_ratio
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
        if s.get("status") == "skip":
            assert s.get("skip_reason"), s["source_id"]


def test_every_pdf_url_in_the_registry_declares_its_media_type():
    """So fetch can reject a soft-404 HTML page served in a PDF's place."""
    for s in json.loads(Path(CONFIG.registry_file).read_text())["sources"]:
        url = (s.get("download_url") or s["source_url"]).split("?")[0]
        if url.endswith(".pdf"):
            assert s.get("expected_media_type") == "pdf", s["source_id"]


# ---- garbled PDF extraction ----------------------------------------------------

#: What a per-glyph page looks like once the glyphs are sorted by coordinate.
SOUP = "o o C n c n p s a i o . t f A n o n e s u u e i o r i o f B e i f m o t m o d n n"


def test_garble_ratio_separates_character_soup_from_prose():
    assert garble_ratio(SOUP) > 0.9
    assert garble_ratio(SENT * 3) < 0.1
    # too short to judge either way
    assert garble_ratio("a b c") == 0.0


def test_a_garbled_page_is_retried_in_reading_order():
    class Page:
        def __init__(self):
            self.calls = []

        def extract_text(self, **kw):
            self.calls.append(kw)
            return SENT if kw.get("use_text_flow") else SOUP

    p = Page()
    assert _page_text(p) == SENT
    assert p.calls == [{}, {"use_text_flow": True}]


def test_a_clean_page_is_not_retried():
    class Page:
        def __init__(self):
            self.calls = 0

        def extract_text(self, **kw):
            self.calls += 1
            return SENT * 3

    p = Page()
    _page_text(p)
    assert p.calls == 1


def test_a_retry_that_is_no_better_is_discarded():
    class Page:
        def extract_text(self, **kw):
            return SOUP if kw.get("use_text_flow") else SOUP + " x"

    assert _page_text(Page()) == SOUP + " x"


def test_a_mostly_garbled_pdf_is_not_indexed():
    ex = Extracted("pdf", [(i, SOUP) for i in range(1, 11)], n_garbled_pages=8)
    status, caveats = content_status(ex)
    assert status == "extraction_unusable"
    assert "8 of 10" in caveats[0] and "not indexed" in caveats[0]


def test_a_few_garbled_pages_only_earn_a_caveat():
    ex = Extracted("pdf", [(i, SENT * 3) for i in range(1, 11)], n_garbled_pages=1)
    status, caveats = content_status(ex)
    assert status == "ready_with_caveats" and "1 of 10" in caveats[0]


def test_garbled_chunks_are_dropped_by_the_quality_pass():
    rows = ([{"source_id": "s", "text": f"Page {i}. " + SENT * 4, "page_number": i}
             for i in range(1, 4)]
            + [{"source_id": "s", "text": SOUP * 3, "page_number": 4}])
    kept, rep = clean_rows(rows, {}, 20, lambda t, n: len(t.split()) >= n)
    assert len(kept) == 3
    assert rep.dropped["garbled_text_extraction"] == 1


# ---- soft-404 guards -----------------------------------------------------------

#: What morpc.org actually served for eight different planning PDFs: HTTP 200,
#: text/html, and the same bytes every time.
SOFT_404 = b"<!doctype html><html><title>Welcome to MORPC</title><body>" + b"x" * 500


def test_html_served_for_a_pdf_url_is_rejected_not_cached(tmp_path):
    opener = FakeOpener({"https://x.org/plan.pdf": (SOFT_404, "text/html; charset=UTF-8")})
    res = fetch("plan", "https://x.org/plan.pdf", tmp_path, opener=opener)
    assert res.ok is False
    assert "expected a PDF" in res.error and "text/html" in res.error
    # nothing written, so the next run re-fetches instead of trusting a cache
    assert list(tmp_path.glob("plan.*")) == []


def test_a_real_pdf_mislabelled_by_the_server_is_still_accepted(tmp_path):
    """Content-Type is advisory; the magic number decides."""
    opener = FakeOpener({"https://x.org/a.pdf": (minimal_pdf([SENT]), "text/plain")})
    res = fetch("a", "https://x.org/a.pdf", tmp_path, opener=opener)
    assert res.ok and res.path.read_bytes().startswith(b"%PDF-")


def test_an_html_source_is_unaffected_by_the_pdf_guard(tmp_path):
    opener = FakeOpener({"https://x.org/page": (HTML_PAGE.encode(), "text/html")})
    assert fetch("p", "https://x.org/page", tmp_path, opener=opener).ok


def test_expected_media_type_overrides_a_url_without_a_suffix(tmp_path):
    opener = FakeOpener({"https://x.org/download?id=7": (SOFT_404, "text/html")})
    res = fetch("d", "https://x.org/download?id=7", tmp_path, opener=opener, expected="pdf")
    assert res.ok is False and "expected a PDF" in res.error


def test_a_stale_html_cache_file_for_a_pdf_url_is_ignored(tmp_path):
    (tmp_path / "plan.html").write_bytes(SOFT_404)      # saved before this guard existed
    opener = FakeOpener({"https://x.org/plan.pdf": (minimal_pdf([SENT]), "application/pdf")})
    res = fetch("plan", "https://x.org/plan.pdf", tmp_path, opener=opener)
    assert res.ok and res.from_cache is False and res.path.suffix == ".pdf"


def test_one_body_served_for_several_documents_fails_all_of_them():
    """The case the PDF guard cannot see: the stand-in page IS a web page."""
    shared = {"sha256": "deadbeef" * 8, "index_eligible": True, "content_status": "ready"}
    entries = [{"source_id": "cotsp", **shared}, {"source_id": "state_of_safety", **shared},
               {"source_id": "real_one", "sha256": "f" * 64, "index_eligible": True,
                "content_status": "ready"}]
    rows = [{"source_id": "cotsp"}, {"source_id": "state_of_safety"},
            {"source_id": "real_one"}]
    rejected = ingest.reject_shared_bodies(entries, rows)

    assert sorted(rejected) == ["cotsp", "state_of_safety"]
    assert [e["content_status"] for e in entries[:2]] == ["failed", "failed"]
    assert all(e["index_eligible"] is False for e in entries[:2])
    assert "state_of_safety" in " ".join(entries[0]["caveats"])
    assert entries[2]["content_status"] == "ready"          # the distinct body survives
    assert rows == [{"source_id": "real_one"}]              # bad chunks dropped


def test_a_body_matching_one_already_in_the_catalogue_is_rejected():
    entries = [{"source_id": "new_doc", "sha256": "a" * 64, "index_eligible": True,
                "content_status": "ready"}]
    known = {"old_doc": {"sha256": "a" * 64}}
    assert ingest.reject_shared_bodies(entries, [], known) == ["new_doc"]
    assert "old_doc" in " ".join(entries[0]["caveats"])


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


def test_a_fatality_only_mode_field_is_not_reported_as_involvement():
    """Columbus publishes PedFatal/BikeFatal and no involvement flag at all.

    Reported as "involving a pedestrian" those counts read like the real
    figure while understating it by an order of magnitude.
    """
    meta = {"objectIdField": "OBJECTID",
            "fields": [{"name": "OBJECTID", "type": "esriFieldTypeOID"},
                       {"name": "CRASH_YR"}, {"name": "SEVERITY_BY_TYPE_CD"},
                       {"name": "PedFatal"}, {"name": "BikeFatal"}]}
    lf = resolve_fields(meta)
    assert (lf.pedestrian, lf.bicycle) == ("PedFatal", "BikeFatal")
    assert lf.mode_kinds == {"pedestrian": "fatal", "bicycle": "fatal"}

    s = summarise_layer(LAYER, get=fake_arcgis)
    s.fields.mode_kinds = {"pedestrian": "fatal", "bicycle": "fatal"}
    s.fields.pedestrian, s.fields.bicycle = "PedFatal", "BikeFatal"
    text = render_chunks(s)[0]["text"]
    assert "700 pedestrian fatalities (field PedFatal)" in text
    assert "involving a pedestrian" not in text


def test_an_involvement_field_keeps_its_plain_wording():
    assert resolve_fields(ARCGIS_META).mode_kinds == {"pedestrian": "involved",
                                                      "bicycle": "involved"}


def test_undecoded_severity_codes_say_so_in_the_passage_itself():
    s = summarise_layer(LAYER, get=fake_arcgis)
    s.counts = {("FRANKLIN", 2023): {"1": 120, "5": 30000}}        # bare codes
    text = render_chunks(s)[0]["text"]
    assert "raw CRASH_SEVERITY_CD codes" in text and "not decoded" in text


def test_readable_severity_values_get_no_undecoded_caveat_or_note():
    s = summarise_layer(LAYER, get=fake_arcgis)                    # decoded via domain
    assert not any("raw codes" in c for c in s.caveats)
    assert "not decoded" not in render_chunks(s)[0]["text"]


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
    assert len(rows) == 1, "one passage per layer, not one per area-year"
    text = rows[0]["text"]
    assert "Franklin County: " in text and "Fatal: 120" in text
    assert "700 crashes involving a pedestrian (field PEDESTRIAN_IND)" in text
    assert LAYER["source_url"] in text
    assert "NOT a Central Ohio figure" in text
    # the statewide line must come after every county line, never among them
    lines = text.splitlines()
    state_at = next(i for i, l in enumerate(lines) if "NOT a Central Ohio" in l)
    assert all(i < state_at for i, l in enumerate(lines) if l.startswith("- ")
               and l.endswith(".") and "County" in l)


def test_trend_passage_spans_years_across_layers():
    s23 = summarise_layer(LAYER, get=fake_arcgis)
    s22 = summarise_layer(LAYER, get=fake_arcgis)
    s22.counts = {(a, 2022): {k: v // 2 for k, v in sev.items()} for (a, _), sev in s22.counts.items()}
    trend = render_trend_chunks([s22, s23])
    fra = next(r for r in trend if "Franklin" in r["text"])
    assert "2022" in fra["text"] and "2023" in fra["text"] and "120 fatal" in fra["text"]


def test_trends_group_by_scope_and_keep_statewide_apart():
    """One passage per scope, not per county - see render_chunks' docstring."""
    s23 = summarise_layer(LAYER, get=fake_arcgis)
    s22 = summarise_layer(LAYER, get=fake_arcgis)
    s22.counts = {(a, 2022): {k: v // 2 for k, v in sev.items()}
                  for (a, _), sev in s22.counts.items()}
    trend = render_trend_chunks([s22, s23])
    scopes = {r["area"] for r in trend}
    assert "Central Ohio counties (MORPC region)" in scopes
    assert any(s.startswith("Ohio statewide") for s in scopes)
    # several counties share one passage ...
    regional = next(r for r in trend if r["area"].startswith("Central Ohio"))
    assert regional["text"].count("\n- ") >= 2
    # ... and the statewide total is never one of its lines
    assert "statewide" not in regional["text"].lower()


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
