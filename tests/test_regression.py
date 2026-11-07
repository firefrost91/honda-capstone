"""The regression gate itself, plus the gate run against the real corpus.

The comparison logic is tested on hand-made snapshots. The retrieval tier is
exercised end to end on the real corpus with a deterministic hashing encoder
(no model download), which proves the plumbing; the real-model gate is the
``index``-marked test at the bottom, which runs when ``index/`` exists.
"""
from __future__ import annotations

import json

import pytest

from rag import regress
from rag.config import CONFIG
from tests.fixtures.make import toy_index

QUESTIONS = regress.load_questions()


def test_question_file_is_well_formed():
    ids = [q["id"] for q in QUESTIONS]
    assert len(ids) == len(set(ids))
    for q in QUESTIONS:
        assert q["question"].strip().endswith("?")
        assert isinstance(q.get("expected_sources", []), list)


def test_corpus_gate_passes_on_the_committed_data():
    cur = regress.corpus_snapshot()
    base = json.loads(regress.BASELINE_CORPUS.read_text()) if regress.BASELINE_CORPUS.exists() else None
    assert regress.check_corpus(cur, base, QUESTIONS) == []


def test_corpus_gate_catches_a_lost_source_and_a_shrunk_corpus():
    base = {"n_passages": 1000, "evidence_by_source": {"a": 10, "b": 5}}
    cur = {"n_passages": 900, "evidence_by_source": {"a": 10},
           "eligible_without_passages": ["c"], "known_source_ids": ["a"]}
    fails = regress.check_corpus(cur, base, [{"id": 1, "expected_sources": ["zz"]}])
    text = " | ".join(fails)
    assert "c" in text and "lost all their passages: b" in text
    assert "1000 -> 900" in text and "zz" in text


def _snap(recall, docs=6, ids=("p1", "p2", "p3")):
    return {"expected_recall": recall, "missing_expected": [] if recall == 1 else ["x"],
            "aspirational_recall": None, "n_distinct_sources": docs, "evidence_fraction": 0.6,
            "kinds": {}, "passage_ids": list(ids)}


def test_retrieval_gate_tolerates_noise_but_catches_real_drops():
    qs = [{"id": 1, "question": "q?"}, {"id": 2, "question": "q?"}]
    base = {"questions": {"1": _snap(1.0), "2": _snap(0.67)}}
    ok, _ = regress.check_retrieval({"1": _snap(1.0), "2": _snap(0.6)}, base, qs)
    assert ok == []
    bad, _ = regress.check_retrieval({"1": _snap(0.5), "2": _snap(0.67, docs=2)}, base, qs)
    assert any("Q1: expected-source recall" in f for f in bad)
    assert any("Q2: only 2 distinct sources" in f for f in bad)
    assert any("mean expected-source recall" in f for f in bad)


def test_new_questions_are_held_to_absolute_checks_only():
    qs = [{"id": 99, "question": "new?", "min_distinct_sources": 3}]
    fails, notes = regress.check_retrieval({"99": _snap(0.0, docs=5)}, {"questions": {}}, qs)
    assert fails == [] and any("new question" in n for n in notes)


def test_answer_gate_checks_forbidden_mentions_gaps_and_locality():
    q = {"id": 1, "question": "q?", "expects_gap_honesty": True,
         "forbidden": ["High Impact Neighborhood"], "must_mention_any": ["Vision Zero"]}
    good = {"locality": 8, "groundedness": 0.95, "has_gap_section": True,
            "answer_text": "Vision Zero Columbus targets the High Injury Network."}
    base = {"questions": {"1": dict(good)}}
    assert regress.check_answers({"questions": {"1": good}}, base, [q])[0] == []
    bad = {"locality": 3, "groundedness": 0.6, "has_gap_section": False,
           "answer_text": "The High Impact Neighborhood programme..."}
    fails = " | ".join(regress.check_answers({"questions": {"1": bad}}, base, [q])[0])
    for frag in ("forbidden", "mentions none", "gap section", "groundedness", "locality 8 -> 3"):
        assert frag in fails


def test_retrieval_tier_runs_end_to_end_and_is_deterministic():
    idx = toy_index()
    a = regress.retrieval_snapshot(QUESTIONS, CONFIG, index=idx)
    b = regress.retrieval_snapshot(QUESTIONS, CONFIG, index=idx)
    assert a == b
    assert set(a) == {str(q["id"]) for q in QUESTIONS}
    for snap in a.values():
        assert snap["n_distinct_sources"] >= 3
        assert snap["evidence_fraction"] >= 0.4      # the chunk floor holds
    fails, _ = regress.check_retrieval(a, {"questions": a}, QUESTIONS)
    assert fails == []                               # a snapshot never regresses vs itself


@pytest.mark.index
def test_real_index_does_not_regress_against_baseline():
    """The actual gate. Runs when an index has been built (make index)."""
    if not (CONFIG.index_dir / "manifest.json").exists():
        pytest.skip("no index built")
    if not regress.BASELINE_RETRIEVAL.exists():
        pytest.skip("no retrieval baseline yet (python -m rag.regress --update-baseline)")
    cur = regress.retrieval_snapshot(QUESTIONS, CONFIG)
    fails, notes = regress.check_retrieval(
        cur, json.loads(regress.BASELINE_RETRIEVAL.read_text()), QUESTIONS)
    assert fails == [], "\n".join(fails + notes)
