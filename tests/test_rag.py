"""Unit tests for the parts that must not silently regress.

Run:  ./.venv/bin/python -m pytest tests -q
(or)  ./.venv/bin/python tests/test_rag.py
"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.attribute import (attribute, check_catalog_claims,
                           check_invented_figures, check_scope_claims,
                           fix_glossary, _split_sentences, SentenceAttribution)
from rag.config import CONFIG
from rag.corpus import load_passages, _informative, _clean
from rag.lexical import BM25, tokenize, expand_query
from rag.postprocess import clean
from rag.retrieve import Retriever, _cap_per_source, _clean_planned_query, _mmr, plan_subqueries, rrf_fuse


# ---- corpus ---------------------------------------------------------------

def test_page_furniture_is_filtered():
    assert not _informative("14", 20)
    assert not _informative("VISION ZERO COLUMBUS  •  27", 20)
    assert _informative(" ".join(["pedestrian safety corridor analysis"] * 8), 20)


def test_clean_collapses_pdf_linebreaks():
    assert _clean("speed  \n  limits\n\napply") == "speed\nlimits\n\napply"


def test_corpus_has_all_the_catalogue_passage_kinds():
    # data_summary appears only once `make ingest-gis` has written data/derived,
    # so it is expected-if-present rather than required.
    kinds = {p.kind for p in load_passages()}
    assert {"chunk", "doc_card", "data_card"} <= kinds
    assert kinds <= {"chunk", "doc_card", "data_card", "data_summary"}


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


class _FakeLLM:
    available = True

    def __init__(self, text):
        self.text = text

    def generate(self, *a, **k):
        return self.text


def test_planner_output_is_cleaned_of_preamble_labels_and_region_boilerplate():
    clean = _clean_planned_query
    assert clean("Here are 4 search queries:") is None
    assert clean("Query 1: pedestrian fatality counts by road class Columbus / Central Ohio") \
        == "pedestrian fatality counts by road class"
    assert clean('2. "high injury network corridors in Central Ohio"') == "high injury network corridors"
    assert clean("- **speed management** program evaluation") == "speed management program evaluation"
    assert clean("Columbus / Central Ohio") is None          # nothing left once stripped
    assert clean("crash data") is None                       # too short to be a probe
    assert clean('{"queries": ["a", "b"]}') is None          # JSON debris
    assert clean("Columbus area high severity crash hotspots") == "high severity crash hotspots"
    assert clean("lessons from delayed Columbus transportation projects") == "lessons from delayed transportation projects"
    # proper names that START with the region are not boilerplate
    assert clean("Central Ohio Transit Authority bus service frequency") == "Central Ohio Transit Authority bus service frequency"
    assert clean("Central Ohio Transportation Safety Plan action strategies").startswith("Central Ohio Transportation")
    assert clean("City of Columbus speed management policy") == "City of Columbus speed management policy"
    # a document name that contains the city is kept
    assert "Vision Zero Columbus" in clean("Vision Zero Columbus action plan strategies")


def test_planner_drops_probes_that_restate_the_question_or_each_other():
    q = "What data would we need to prioritize pedestrian safety improvements?"
    llm = _FakeLLM("Here are the queries:\n"
                   "1. pedestrian safety improvements data prioritize\n"
                   "2. sidewalk gap inventory near transit stops\n"
                   "3. sidewalk gap inventory by transit stop\n")
    out = plan_subqueries(q, llm=llm, cfg=replace(CONFIG, max_subqueries=20))
    planned = [x for x in out if "sidewalk" in x]
    assert len(planned) == 1
    assert not any("Here are" in x or "prioritize pedestrian safety improvements data" in x for x in out)


def test_llm_probes_get_slots_even_when_rule_facets_match_first():
    q = "How have crash trends changed, and what data and cost evidence do we need?"
    assert len(plan_subqueries(q)) == CONFIG.max_subqueries      # rules alone fill it
    llm = _FakeLLM("sidewalk gap inventory near transit stops\n"
                   "pedestrian crash severity by functional class\n")
    out = plan_subqueries(q, llm=llm)
    assert out[0] == q and len(out) == CONFIG.max_subqueries
    assert sum("sidewalk" in x or "functional class" in x for x in out) == 2


class _StubIndex:
    def __init__(self, kinds):
        from types import SimpleNamespace
        self.passages = [SimpleNamespace(kind=k) for k in kinds]


def test_catalogue_cards_need_a_reason_to_take_a_slot():
    kinds = ["chunk", "data_card", "data_card", "data_card", "doc_card", "chunk"]
    pool = list(range(6))
    fused = {i: 1.0 - i * 0.1 for i in pool}
    r = Retriever(_StubIndex(kinds), replace(CONFIG, max_catalog_cards=2,
                                             max_catalog_cards_data_question=4))
    q = "Which safety countermeasures should we prioritise?"
    # only cards the question itself ranked highly are admitted, then capped at 2
    qrank = {1: 0, 2: 5, 3: 7, 4: 50}          # 4 is deep in the list (or probe-only)
    out = r._admit_catalog_cards(pool, fused, qrank, q)
    assert [i for i in out if kinds[i] != "chunk"] == [1, 2]      # 3 over the cap, 4 too deep
    assert 0 in out and 5 in out                                  # text is never dropped
    # a question about data admits cards found only through probes, up to 4
    dq = "What types of local data can be combined?"
    out = r._admit_catalog_cards(pool, fused, {}, dq)
    assert [i for i in out if kinds[i] != "chunk"] == [1, 2, 3, 4]


def test_stakeholder_probes_take_slots_right_after_the_question():
    from rag.tools.stakeholders import STAKEHOLDERS
    q = "How would you evaluate the outcome of this safety project?"
    for s in STAKEHOLDERS.values():
        assert len(s.focus) >= 2, s.id            # every group has retrieval probes
    probes = STAKEHOLDERS["emergency"].focus
    out = plan_subqueries(q, stakeholder_probes=probes)
    assert out[0] == q and out[1:3] == list(probes)
    assert len(out) <= CONFIG.max_subqueries
    # different groups asking the same question get different probe sets
    assert plan_subqueries(q, stakeholder_probes=STAKEHOLDERS["freight"].focus) != out
    # and the cap on stakeholder slots is honoured
    capped = plan_subqueries(q, cfg=replace(CONFIG, max_stakeholder_probes=1), stakeholder_probes=probes)
    assert capped[1] == probes[0] and probes[1] not in capped


def test_role_block_reaches_the_planner_prompt_only_when_given():
    from rag.retrieve import _role_block
    assert _role_block("") == ""
    assert "Emergency responders" in _role_block("Emergency responders. They care about: response time.")


def test_only_an_explicit_perspective_steers_retrieval():
    from types import SimpleNamespace
    from rag.llm import NullLLM
    from rag.pipeline import RAGPipeline
    seen = []
    pipe = RAGPipeline(index=SimpleNamespace(passages=[]), llm=NullLLM())
    pipe.retriever = SimpleNamespace(retrieve=lambda q, llm=None, k=None, stakeholder=None:
                                     (seen.append(stakeholder), ([], []))[1])
    pipe._run_tools = lambda q, st: ([], [], st or "residents")    # auto-detect finds residents
    pipe._prepare("Why are neighborhood streets unsafe?")
    pipe._prepare("Why are neighborhood streets unsafe?", stakeholder="freight")
    assert seen == [None, "freight"]


def test_planner_obeys_the_subquery_ceiling_and_keeps_the_question():
    """Past the ceiling, fusion prefers passages that place on every facet."""
    # a question that trips several facet rules at once
    q = ("Based on local evidence and data, what improvements should Columbus "
         "prioritize to reduce crashes, and what information is still missing?")
    assert len(plan_subqueries(q)) == CONFIG.max_subqueries
    assert plan_subqueries(q)[0] == q
    assert plan_subqueries(q, cfg=replace(CONFIG, max_subqueries=1)) == [q]


def test_the_chunk_floor_reserves_most_slots_for_document_text():
    assert CONFIG.min_chunk_fraction >= 0.6, (
        "below this, catalogue cards take the majority of the context: "
        "measured 6 chunks + 8 cards out of 14 at 0.4")
    assert round(CONFIG.final_k * CONFIG.min_chunk_fraction) >= 9


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


def test_sentence_splitter_does_not_cut_at_abbreviations():
    pieces = _split_sentences("Crashes cluster at Trabue Road & N. Wilson Road. "
                              "The U.S. Census counts residents. Speeds are high.")
    assert pieces == ["Crashes cluster at Trabue Road & N. Wilson Road.",
                      "The U.S. Census counts residents.", "Speeds are high."]


def test_attribution_keeps_paragraphs_on_one_line():
    vecs = np.array([[1, 0]], dtype=np.float32)
    text = ("Lowering speed reduces crash severity in the city centre. "
            "Lower speed also shortens stopping distances for drivers.\n\nNext paragraph.")
    out, _, _ = attribute(text, vecs, lambda xs: np.array([[1, 0]] * len(xs), dtype=np.float32))
    assert out.split("\n") == [
        "Lowering speed reduces crash severity in the city centre [S1]. "
        "Lower speed also shortens stopping distances for drivers [S1].",
        "", "Next paragraph."]


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



# The real passage that produced the bug this guards against: a national
# figure sitting one sentence away from a regional one.
_MIXED_SCOPE_PASSAGE = (
    "During the five-year period between 2017 and 2021, 177,409 people across the "
    "U.S. died in a motor vehicle crash. In that same time frame, 32,674 pedestrians "
    "were killed while walking in their communities. Central Ohio has seen similarly "
    "concerning trends. The MPO planning area had 162,384 crashes."
)


def _attr(text, citations=(1,)):
    return SentenceAttribution(text=text, citations=list(citations), support=0.9,
                               supported=True, model_cited=[])


def test_national_figure_rescoped_to_central_ohio_is_flagged():
    problems = check_scope_claims(
        [_attr("In Central Ohio alone, 32,674 pedestrians were killed while walking.")],
        [_MIXED_SCOPE_PASSAGE])
    assert problems and problems[0][0] == "32,674"
    assert "national" in problems[0][1] and "local" in problems[0][1]


def test_correctly_scoped_figures_are_not_flagged():
    passages = [_MIXED_SCOPE_PASSAGE]
    assert check_scope_claims(
        [_attr("Across the U.S., 177,409 people died in motor vehicle crashes.")],
        passages) == []
    assert check_scope_claims(
        [_attr("The Central Ohio MPO planning area had 162,384 crashes.")],
        passages) == []


def test_abbreviation_periods_do_not_split_the_governing_sentence():
    """'U.S. died' must not be read as a sentence break - that strips the scope."""
    from rag.attribute import _governing_span
    span = _governing_span(_MIXED_SCOPE_PASSAGE, _MIXED_SCOPE_PASSAGE.index("32,674"))
    assert "U.S." in span


def test_figures_absent_from_every_cited_passage_are_reported():
    missing = check_invented_figures(
        [_attr("The corridor saw 4,912 crashes and 162,384 elsewhere.")],
        [_MIXED_SCOPE_PASSAGE])
    assert missing == ["4,912"]



def test_bare_years_are_not_treated_as_statistics():
    """Years made every sentence naming a study period look like a scope error."""
    from rag.attribute import _NUMBER
    assert _NUMBER.findall("between 2017 and 2021 the count rose") == []
    assert "162,384" in _NUMBER.findall("there were 162,384 crashes in 2022")
    assert "691" in _NUMBER.findall("691 people died")


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
