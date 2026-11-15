"""Corpus hygiene (rag.quality) and the corpus-level invariants it must keep."""
from __future__ import annotations

from rag.config import CONFIG
from rag.corpus import EVIDENCE_KINDS, Passage, _informative, load_document_catalog, load_passages
from rag.quality import (clean_rows, find_boilerplate, noise_reason, published_year,
                         strip_lines)


def _row(sid, page, text, n=1):
    return {"chunk_id": f"{sid}__p{page:04d}__c{n:03d}", "source_id": sid,
            "page_number": page, "text": text}


STREETS = ["Alum Creek", "Hamilton", "Karl", "Livingston", "Parsons", "Sullivant", "Broad",
           "Refugee", "Cleveland", "Agler", "Kimberly", "Lockbourne", "Frebis", "Whittier"]

PROSE = ("The Morse Road corridor saw repeated pedestrian crashes near transit stops, "
         "and the plan recommends crossings, lighting and lower speeds along the segment.")


def test_running_headers_with_changing_page_numbers_are_detected():
    rows = [_row("tip", i, f"May 1, 2025 {i} MORPC SFY 2026-2029 TIP header\n{PROSE} {STREETS[i]}")
            for i in range(1, 12)]
    bp = find_boilerplate(rows)
    assert "tip" in bp
    cleaned = strip_lines(rows[3]["text"], bp["tip"])
    assert "MORPC SFY" not in cleaned and "Morse Road" in cleaned


def test_short_labels_survive_boilerplate_stripping():
    rows = [_row("tip", i, f"Description:\n{PROSE} project {i}") for i in range(1, 12)]
    bp = find_boilerplate(rows)
    assert not any("description" in line for line in bp.get("tip", set()))


def test_boilerplate_is_per_source():
    a = [_row("a", i, f"Shared running header for document A\n{PROSE} {STREETS[i]}")
         for i in range(10)]
    b = [_row("b", i, f"{PROSE} {STREETS[i]}") for i in range(10)]
    assert set(find_boilerplate(a + b)) == {"a"}


def test_table_of_contents_and_dot_leaders_are_noise():
    toc = "Table of Contents\n1. Introduction ........ 1\n2. Safety ........ 4\n3. Data ........ 9"
    assert noise_reason(toc) == "table_of_contents"
    leaders = "\n".join(f"Section {i} .................. {i}" for i in range(6))
    assert noise_reason(leaders) == "dot_leaders"
    assert noise_reason(PROSE) is None


def test_passing_reference_to_contents_is_not_noise():
    text = "\n".join([PROSE] * 5 + ["See the Table of Contents for the full list."])
    assert noise_reason(text) is None


def test_ineligible_sources_and_out_of_range_pages_are_dropped():
    catalog = {"good": {"index_eligible": True, "indexed_page_range": [1, 2]},
               "bad": {"index_eligible": False}}
    rows = [_row("good", 1, PROSE), _row("good", 5, PROSE + " other page"),
            _row("bad", 1, PROSE + " excluded")]
    kept, rep = clean_rows(rows, catalog, 20, _informative)
    assert [r["chunk_id"] for r in kept] == ["good__p0001__c001"]
    assert rep.dropped["outside_indexed_page_range"] == 1
    assert rep.dropped["source_not_index_eligible"] == 1


def test_exact_and_near_duplicates_are_dropped():
    long = " ".join(f"{PROSE} {st}." for st in STREETS)
    rows = [_row("s", 1, long), _row("s", 2, long),
            _row("s", 3, long.replace("Frebis", "Frebis Avenue"))]
    kept, rep = clean_rows(rows, {}, 20, _informative)
    assert len(kept) == 1
    assert rep.dropped["exact_duplicate"] == 1


def test_short_page_head_is_folded_into_its_page_mate():
    """A TIP project's ID/name line must stay attached to its cost and description."""
    head = "121958 LIC SR 16 Intersection Improvement (Safety) Pataskala"
    rows = [_row("tip", 7, head, 1), _row("tip", 7, PROSE, 2)]
    kept, rep = clean_rows(rows, {}, 20, lambda t, n: True)
    assert len(kept) == 1 and kept[0]["text"].startswith("121958")
    assert rep.merged == 1


def test_short_but_substantive_page_is_kept():
    rows = [_row("vz", 14, "VISION ZERO COLUMBUS 10\nIn 2019, 54 deaths occurred in 49 fatal "
                           "crashes on our city streets")] * 1
    rows += [_row("vz", i, f"VISION ZERO COLUMBUS {i}\n{PROSE} {i}") for i in range(1, 8)]
    kept, _ = clean_rows(rows, {}, 20, lambda t, n: True)
    assert any("54 deaths" in r["text"] for r in kept)


def test_published_year_from_title():
    assert published_year({"title": "Vision Zero Columbus Annual Report 2024"}) == 2024
    assert published_year({"title": "No year here"}) is None


# ---- invariants on the real corpus ---------------------------------------

def test_every_eligible_document_contributes_passages():
    passages = load_passages()
    have = {p.source_id for p in passages if p.kind in EVIDENCE_KINDS}
    eligible = {sid for sid, d in load_document_catalog().items() if d.get("index_eligible")}
    assert eligible <= have, sorted(eligible - have)


def test_cleaning_strips_tip_template_lines():
    tip = [p for p in load_passages() if p.source_id == "morpc_tip_2026_2029_full"]
    assert tip
    assert not any("PID: Project Name: Primary Work Category" in p.text for p in tip)


def test_cleaning_keeps_most_of_the_corpus():
    """A filter change that throws away a large share of text is a regression."""
    from dataclasses import replace
    raw = [p for p in load_passages(replace(CONFIG, apply_quality_filters=False))
           if p.kind == "chunk"]
    clean = [p for p in load_passages() if p.kind == "chunk"]
    assert 0.9 * len(raw) <= len(clean) <= len(raw)


def test_passage_round_trip_tolerates_old_and_new_fields():
    p = Passage("x", "chunk", "text", "t", "s", scope="region_specific", published_year=2024)
    d = p.to_dict()
    assert Passage.from_dict(d) == p
    d.pop("scope"), d.pop("published_year")
    d["unknown_future_field"] = 1
    assert Passage.from_dict(d).scope == ""
