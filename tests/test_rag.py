"""Unit tests for the parts that must not silently regress.

Run:  ./.venv/bin/python -m pytest tests -q
(or)  ./.venv/bin/python tests/test_rag.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.attribute import (attribute, check_catalog_claims, fix_glossary,
                           _split_sentences, SentenceAttribution)
from rag.corpus import load_passages, _informative, _clean
from rag.lexical import BM25, tokenize, expand_query
from rag.postprocess import clean
from rag.retrieve import _cap_per_source, _mmr, plan_subqueries, rrf_fuse


# ---- corpus ---------------------------------------------------------------

def test_page_furniture_is_filtered():
    assert not _informative("14", 20)
    assert not _informative("VISION ZERO COLUMBUS  •  27", 20)
    assert _informative(" ".join(["pedestrian safety corridor analysis"] * 8), 20)


def test_clean_collapses_pdf_linebreaks():
    assert _clean("speed  \n  limits\n\napply") == "speed\nlimits\n\napply"


def test_corpus_has_all_three_passage_kinds():
    kinds = {p.kind for p in load_passages()}
    assert kinds == {"chunk", "doc_card", "data_card"}


def test_data_cards_declare_records_are_absent():
    """The guard against quoting figures from datasets that were never loaded."""
    cards = [p for p in load_passages() if p.kind == "data_card"]
    assert cards
    assert all("records are NOT loaded" in c.text or "records_included" in c.text
               for c in cards[:5])


# ---- lexical --------------------------------------------------------------

def test_tokenizer_preserves_route_designators():
    assert "i-70" in tokenize("Crashes along I-70 downtown")
    assert "sr-161" in tokenize("The SR-161 safety project")


def test_query_expansion_reaches_planner_vocabulary():
    expanded = expand_query(tokenize("pedestrian crash data"))
    assert "ped" in expanded and "collision" in expanded


def test_bm25_ranks_the_matching_document_first():
    docs = [tokenize(t) for t in [
        "pedestrian crossing improvements on Morse Road",
        "bridge deck replacement over the Scioto river",
        "transit signal priority for COTA buses",
    ]]
    top = BM25(docs).search(tokenize("pedestrian crossing Morse"), top_k=1)
    assert top[0][0] == 0


# ---- retrieval ------------------------------------------------------------

def test_rrf_rewards_agreement_between_retrievers():
    fused = rrf_fuse([[(1, 0.9), (2, 0.8)], [(2, 5.0), (3, 4.0)]], k=60)
    assert fused[2] > fused[1] and fused[2] > fused[3]


def test_source_cap_prevents_one_document_dominating():
    class P:
        def __init__(self, sid): self.source_id = sid
    passages = [P("tip")] * 10 + [P("vz")] * 5
    kept = _cap_per_source(list(range(15)), passages, cap=3)
    assert sum(1 for i in kept if passages[i].source_id == "tip") == 3


def test_mmr_prefers_a_novel_passage_over_a_near_duplicate():
    vecs = np.array([[1, 0], [0.999, 0.045], [0, 1]], dtype=np.float32)
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    chosen = _mmr([0, 1, 2], {0: 1.0, 1: 0.99, 2: 0.7}, vecs, k=2, lam=0.5)
    assert chosen == [0, 2]


def test_planner_expands_analytical_questions():
    qs = plan_subqueries("How have safety trends changed over the past 10 years?")
    assert len(qs) > 1 and qs[0].startswith("How have")


# ---- answer hygiene -------------------------------------------------------

def test_glossary_fixes_local_acronyms():
    fixed, n = fix_glossary("The Metropolitan Regional Planning Commission and the "
                            "High Impact Neighborhood")
    assert "Mid-Ohio Regional Planning Commission" in fixed
    assert "High Injury Network" in fixed and n == 2


def test_postprocess_removes_template_echo_and_duplicate_gap_section():
    raw = ("**What the local evidence does not cover**\n"
           "- 2-4 bullets naming concretely what is missing, stale, or would have to be.\n\n"
           "Real answer about Columbus speeds.\n\n"
           "**What the local evidence does not cover**\n"
           "- No pedestrian counts exist for the corridor.\n"
           "- Crash records after 2023 are not loaded.\n")
    cleaned, warnings = clean(raw)
    assert cleaned.count("What the local evidence does not cover") == 1
    assert "2-4 bullets" not in cleaned
    assert "No pedestrian counts" in cleaned
    assert warnings


def test_postprocess_marks_truncated_generation():
    cleaned, warnings = clean("Columbus is studying speed limits [S")
    assert "truncated" in cleaned.lower() and warnings


def test_attribution_cites_the_supporting_passage_and_flags_invention():
    # passage 0 is about speed, passage 1 about bridges
    vecs = np.array([[1, 0, 0], [0, 1, 0]], dtype=np.float32)

    def fake_encoder(sentences):
        out = []
        for s in sentences:
            if "speed" in s.lower():
                out.append([1, 0, 0])
            elif "bridge" in s.lower():
                out.append([0, 1, 0])
            else:
                out.append([0, 0, 1])      # matches nothing
        return np.array(out, dtype=np.float32)

    text = ("Lowering speed reduces the severity of crashes in the city.\n"
            "The bridge deck was replaced during the project last year.\n"
            "Columbus purchased four hundred autonomous shuttles in 2019.")
    out, attrs, summary = attribute(text, vecs, fake_encoder)
    assert "[S1]" in out and "[S2]" in out
    assert "[unsupported by retrieved evidence]" in out
    assert summary["grounded"] == 2 and summary["total"] == 3


def test_sentence_splitter_keeps_bullets_intact():
    pieces = _split_sentences("- One bullet. Still the bullet.\nPlain text. More text.")
    assert pieces[0] == "- One bullet. Still the bullet."


def test_gap_dedupe_preserves_the_answer_when_the_heading_comes_first():
    """Regression: a leading gap heading used to swallow the whole answer."""
    raw = ("**What the local evidence does not cover**\n"
           "- An early bullet.\n\n"
           "Columbus has documented speed management work on Morse Road.\n"
           "The Vision Zero plan sets a 2035 target.\n\n"
           "**What the local evidence does not cover**\n"
           "- No pedestrian counts exist.\n"
           "- Crash records after 2023 are absent.\n")
    cleaned, _ = clean(raw)
    assert "Morse Road" in cleaned
    assert "2035 target" in cleaned
    assert cleaned.count("What the local evidence does not cover") == 1
    assert "No pedestrian counts" in cleaned
    assert cleaned.index("Morse Road") < cleaned.index("What the local evidence")



def test_bold_heading_is_not_mistaken_for_a_bullet():
    """Regression: '**heading**' starts with '*', which merged the gap sections."""
    from rag.postprocess import _is_bullet
    assert _is_bullet("- a real bullet")
    assert _is_bullet("* a real bullet")
    assert _is_bullet("  • a real bullet")
    assert not _is_bullet("**What the local evidence does not cover**")
    assert not _is_bullet("**Bold lead-in** followed by prose")


def test_two_gap_sections_collapse_to_one_heading():
    raw = ("**What the local evidence does not cover**\n\n"
           "- Bullet one.\n- Bullet two.\n\n"
           "**What the local evidence does not cover**\n"
           "- Bullet three.\n")
    cleaned, _ = clean(raw)
    assert cleaned.count("What the local evidence does not cover") == 1
    assert "Bullet one." in cleaned and "Bullet two." in cleaned



def test_figures_sourced_only_to_a_catalogue_entry_are_flagged():
    """The records behind a data card are not loaded, so a figure citing only
    one cannot have come from the knowledge base."""
    kinds = ["data_card", "chunk"]
    only_catalog = SentenceAttribution(
        text="The network recorded 162,384 crashes last period.",
        citations=[1], support=0.8, supported=True, model_cited=[])
    with_document = SentenceAttribution(
        text="The plan reports 102 pedestrian deaths from 2017 to 2021.",
        citations=[1, 2], support=0.8, supported=True, model_cited=[])
    no_figure = SentenceAttribution(
        text="The dataset records roadway segment geometry.",
        citations=[1], support=0.8, supported=True, model_cited=[])

    assert check_catalog_claims([only_catalog], kinds) == [only_catalog.text]
    assert check_catalog_claims([with_document], kinds) == []
    assert check_catalog_claims([no_figure], kinds) == []


if __name__ == "__main__":
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); passed += 1; print(f"  PASS  {name}")
            except Exception as exc:
                failed += 1; print(f"  FAIL  {name}: {type(exc).__name__}: {exc}")
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)
