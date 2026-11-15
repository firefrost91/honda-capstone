"""Stakeholder metric tools: catalogue integrity, determinism, plausibility,
and how tool output enters the answer pipeline.

Run:  ./.venv/bin/python -m pytest tests/test_tools.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.attribute import SentenceAttribution, check_catalog_claims
from rag.config import CONFIG
from rag.prompts import SYSTEM_PROMPT, build_context, build_user_prompt, render_passage
from rag.tools import (METRICS, STAKEHOLDERS, TOOL_KIND, TOOLS, build_context_for,
                       detect_stakeholder, infer_location, run_tool, run_tools,
                       select_tools, tool_hits)
from rag.tools.metrics import ALL, metrics_for
from rag.tools.synthetic import EPDO_WEIGHTS, ToolContext

SCENARIO = ("A safety improvement project at a Columbus intersection has reduced crashes "
            "from 8 to 2 per year. However, the two remaining crashes involved serious "
            "injuries. Traffic delay has improved, but pedestrian concerns remain. How would "
            "you evaluate the outcome from the perspective of [stakeholder]?")

EVAL_SET = json.loads((Path(__file__).resolve().parent.parent / "eval"
                       / "stakeholder_questions.json").read_text())


def _ctx(scope="intersection", location="Morse Road and Cleveland Avenue", year=2024, q=""):
    return ToolContext(location=location, scope=scope, year=year, question=q)


def _values(tool, ctx):
    return {v.metric_id: v.value for v in run_tool(tool, ctx).values}


# ---- catalogue --------------------------------------------------------------

def test_every_stakeholder_has_tools_and_every_tool_emits_catalogue_metrics():
    for s in STAKEHOLDERS.values():
        assert 3 <= len(s.tools) <= 5, s.id
        assert all(t in TOOLS for t in s.tools)
    for scope in ("intersection", "corridor", "citywide", "region"):
        ctx = _ctx(scope=scope, location=f"somewhere {scope}")
        for name in TOOLS:
            vals = run_tool(name, ctx).values        # raises on an unknown metric id
            assert vals, name
            assert len({v.metric_id for v in vals}) == len(vals), f"{name} repeats a metric"


def test_every_metric_is_reachable_by_at_least_one_tool_and_stakeholder():
    emitted = set()
    for scope in ("intersection", "corridor", "citywide"):
        ctx = _ctx(scope=scope, location=f"place {scope}")
        for name in TOOLS:
            emitted |= {v.metric_id for v in run_tool(name, ctx).values}
    assert emitted == set(METRICS), set(METRICS) ^ emitted
    for sid in ALL:
        assert metrics_for(sid), sid


def test_the_eval_set_covers_all_eight_stakeholders_three_each():
    counts = {}
    for q in EVAL_SET["layer_1"]:
        assert q["stakeholder"] in STAKEHOLDERS
        counts[q["stakeholder"]] = counts.get(q["stakeholder"], 0) + 1
    assert counts == {sid: 3 for sid in STAKEHOLDERS}
    assert "[stakeholder]" in EVAL_SET["layer_2"]["question"]


# ---- determinism --------------------------------------------------------------

def test_same_location_and_year_give_the_same_numbers_and_tools_agree():
    a = _values("crash_profile", _ctx())
    b = _values("crash_profile", _ctx())
    assert a == b
    other = _values("crash_profile", _ctx(location="Hilliard-Rome Road and Roberts Road"))
    assert other["crashes_total"] != a["crashes_total"] or other["epdo_score"] != a["epdo_score"]
    # a second tool drawing on the shared crash core sees the same KSI
    ems = _values("emergency_response_profile", _ctx())
    assert ems["serious_injury_transports_per_year"] >= a["ksi"]


# ---- plausibility ---------------------------------------------------------------

def test_crash_profile_is_internally_consistent():
    for scope, loc in (("intersection", "Morse Road and Cleveland Avenue"),
                       ("citywide", "Columbus (citywide)"),
                       ("region", "MORPC planning area (Central Ohio)")):
        v = _values("crash_profile", _ctx(scope=scope, location=loc))
        sev = ("crashes_fatal", "crashes_serious_injury", "crashes_minor_injury",
               "crashes_possible_injury", "crashes_pdo")
        assert sum(v[k] for k in sev) == v["crashes_total"]
        assert v["ksi"] == v["crashes_fatal"] + v["crashes_serious_injury"]
        epdo = (v["ksi"] * EPDO_WEIGHTS["ksi"] + v["crashes_minor_injury"] * EPDO_WEIGHTS["minor"]
                + v["crashes_possible_injury"] * EPDO_WEIGHTS["possible"] + v["crashes_pdo"])
        assert abs(v["epdo_score"] - epdo) < 1e-6
        assert abs(v["severity_index"] - epdo / v["crashes_total"]) < 1e-6
        assert v["pedestrian_crashes"] <= v["crashes_total"]
        if scope == "intersection":
            assert abs(v["crash_rate_mev"] - v["crashes_total"] / (365 * v["entering_adt"] / 1e6)) < 1e-9
            assert 0.2 <= v["crash_rate_mev"] <= 2.5
        else:
            assert abs(v["crash_rate_100mvmt"] - v["crashes_total"] / v["annual_vmt_100m"]) < 1e-9


def test_citywide_and_regional_scale_match_the_published_aggregates():
    """Columbus crash layer: ~12k crashes, 50-80 deaths, 260-340 serious-injury
    crashes a year; MORPC five-year averages near 845 serious injuries."""
    c = _values("crash_profile", _ctx(scope="citywide", location="Columbus (citywide)"))
    assert 10_000 <= c["crashes_total"] <= 14_500
    assert 40 <= c["crashes_fatal"] <= 120
    assert 200 <= c["crashes_serious_injury"] <= 500
    t = _values("safety_targets", _ctx(scope="region", location="MORPC planning area"))
    assert 780 <= t["serious_injuries_5yr_avg"] <= 900
    assert 0.9 <= t["fatality_rate_5yr_avg"] <= 1.3
    assert abs(t["target_serious_injuries"] - 844.6 * 0.98) < 1e-6


def test_speed_operations_and_response_values_keep_their_orderings():
    s = _values("speed_profile", _ctx())
    assert s["speed_85th"] > s["mean_speed"]
    assert 0 < s["pct_over_limit_10"] < s["pct_over_limit"] <= 100
    o = _values("traffic_operations", _ctx())
    assert o["lottr"] >= 1.0 and o["pti"] > o["lottr"] and o["tti"] >= 1.0
    assert o["los"] in "ABCDEF"
    assert (o["los"] == "F") == (o["control_delay"] > 80)
    e = _values("emergency_response_profile", _ctx())
    assert e["ems_response_90th_min"] > e["ems_response_mean_min"]
    assert 0 < e["nfpa_als_8min_compliance_pct"] <= 100
    v = _values("vulnerable_user_profile", _ctx())
    assert abs(v["ped_clearance_time_s"] - v["crossing_distance_ft"] / 3.5) < 1e-9
    assert 1 <= v["bike_lts"] <= 4 and 1 <= v["pedestrian_lts"] <= 4
    f = _values("freight_rail_profile", _ctx())
    assert f["crossing_exposure_index"] > f["trains_per_day"]
    c = _values("community_impact_profile", _ctx())
    assert c["cut_through_share_pct"] >= 0
    assert (c["noise_nac_exceeded"] == "yes") == (c["noise_leq_dba"] >= 66)


def test_scenario_tool_reads_the_before_and_after_counts_from_the_question():
    ctx = build_context_for(SCENARIO, None)
    assert (ctx.before, ctx.after) == (8, 2)
    assert ctx.scope == "intersection"
    v = _values("project_outcome_evaluation", ctx)
    assert v["crashes_before"] == 8 and v["crashes_after"] == 2
    assert abs(v["crash_change_pct"] + 75) < 1e-9
    assert v["ksi_after"] == 2                      # "two remaining crashes involved serious injuries"
    assert v["ksi_before"] >= v["ksi_after"]
    assert "interval" in v["significance_note"] and "serious" in v["significance_note"]
    assert v["ped_crash_share_after_pct"] >= 50     # at least one of two was a pedestrian crash
    # without KSI after, the note still explains the interval
    v0 = _values("project_outcome_evaluation", _ctx(q="crashes fell from 12 to 3"))
    assert v0["significance_note"].startswith("a one-year count")


# ---- reading the question -------------------------------------------------------

def test_location_inference():
    assert infer_location("crashes at Morse Road and Cleveland Avenue") == (
        "Morse Road and Cleveland Avenue", "intersection")
    assert infer_location("queues on I-270 near Dublin")[1] == "corridor"
    assert infer_location("speeding in Hilliard neighbourhoods") == ("Hilliard", "city")
    assert infer_location("Franklin County EMS response")[1] == "county"
    assert infer_location("What should Central Ohio prioritise?")[1] == "region"
    assert infer_location("What are the worst crossings in Columbus / Central Ohio?") == (
        "Columbus (citywide)", "citywide")
    assert build_context_for("crash trend in 2022 on Cleveland Avenue", None).year == 2022


def test_stakeholder_detection_on_the_evaluation_questions():
    expected = {q["id"]: q["stakeholder"] for q in EVAL_SET["layer_1"]}
    detected = {q["id"]: detect_stakeholder(q["question"]) for q in EVAL_SET["layer_1"]}
    hits = sum(1 for i, s in expected.items() if detected[i] == s)
    # the questions are deliberately phrased in each group's vocabulary; most
    # should route without an explicit choice, and none to an unknown id
    assert hits >= 15, detected
    assert all(d is None or d in STAKEHOLDERS for d in detected.values())
    # an explicit choice always wins
    _, sid = run_tools(EVAL_SET["layer_1"][0]["question"], stakeholder="residents")
    assert sid == "residents"


def test_tool_selection_prefers_what_the_question_asks_for_and_respects_the_cap():
    chosen = select_tools(SCENARIO, "emergency", limit=4)
    assert chosen[0] == "project_outcome_evaluation"
    assert "emergency_response_profile" in chosen and len(chosen) <= 4
    assert select_tools("What is the crash history on Parsons Avenue?", None, limit=2) == [
        "crash_profile"]
    assert len(select_tools(SCENARIO, "agency", limit=3)) == 3
    results, _ = run_tools(SCENARIO, "vru", limit=CONFIG.max_tool_passages)
    assert len(results) <= CONFIG.max_tool_passages


# ---- entering the pipeline ------------------------------------------------------

def test_tool_passages_declare_themselves_synthetic_and_render_untruncated():
    results, _ = run_tools(SCENARIO, "residents", limit=3)
    for r in results:
        p = r.to_passage()
        assert p.kind == TOOL_KIND and p.source_id == f"tool:{r.tool}"
        assert "SYNTHETIC PLACEHOLDER" in p.text and r.location in p.text and str(r.year) in p.text
        assert "synthetic placeholder values" in p.caveats
        rendered = render_passage(1, p)
        assert "METRIC TOOL OUTPUT" in rendered
        assert not rendered.endswith("...")         # the metric list must not be cut
    ref = run_tool("countermeasure_reference", _ctx()).to_passage()
    assert "REFERENCE VALUES" in ref.text and "approximate reference values" in ref.caveats


def test_tool_hits_carry_their_own_vectors():
    results, _ = run_tools("crash history at Morse Road and Cleveland Avenue", None, limit=2)
    hits = tool_hits(results, lambda xs: np.ones((len(xs), 4), dtype=np.float32))
    assert hits and all(h.index == -1 and h.vector.shape == (4,) for h in hits)
    context, kept = build_context(hits, CONFIG.context_char_budget)
    assert len(kept) == len(hits) and "[S1] METRIC TOOL OUTPUT" in context


def test_figures_from_tool_output_are_not_flagged_as_catalogue_claims():
    a = SentenceAttribution(text="The tool reports 1,234 crashes in 2024.", citations=[1],
                            support=0.9, supported=True, model_cited=[])
    assert check_catalog_claims([a], [TOOL_KIND]) == []
    assert check_catalog_claims([a], ["data_card"]) == [a.text]


def test_prompt_carries_the_perspective_and_fills_the_placeholder():
    prompt = build_user_prompt(SCENARIO, "ctx", "", stakeholder="emergency")
    assert "STAKEHOLDER PERSPECTIVE" in prompt
    assert "Emergency responders / healthcare providers" in prompt
    assert "[stakeholder]" not in prompt
    assert "STAKEHOLDER PERSPECTIVE" not in build_user_prompt(SCENARIO, "ctx", "")
    assert "METRIC TOOL OUTPUT MAY BE QUOTED" in SYSTEM_PROMPT


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
