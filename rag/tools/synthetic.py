"""Stub metric tools that return plausible synthetic values.

These stand in for the analytics services that will eventually be plugged in
(crash-record queries, probe-data reliability, EMS CAD exports, COTA stop
inventories, FRA crossing data). Each tool here:

* is **deterministic** - the same location and year always produce the same
  numbers, so answers are reproducible and tests can pin them;
* is **internally consistent** - severities sum to the total, KSI is fatal plus
  serious, EPDO is the weighted sum, the 85th-percentile speed sits above the
  mean, a rate is the count over the exposure it claims;
* is **scaled to Central Ohio** - citywide totals sit near the ODOT / Columbus
  crash-layer aggregates already in ``data/derived`` (about 12,000 crashes,
  50-80 deaths and 260-340 serious-injury crashes a year in the city), regional
  five-year averages near MORPC's adopted targets (844.6 serious injuries,
  155.6 non-motorised KSI), and intersection rates in the 0.4-1.6 per million
  entering vehicles band that MORPC's screening uses;
* **says it is synthetic** in every passage it emits.

Only ``countermeasure_reference`` returns published figures rather than
generated ones, and it is labelled as a reference table, not a measurement.

Shared quantities (crash counts, volumes) come from ``core`` helpers seeded by
location and year alone, so two tools answering the same question never
disagree about how many crashes there were.
"""
from __future__ import annotations

import hashlib
import math
import random
import re
from dataclasses import dataclass, field

from .metrics import METRICS, MetricSpec

#: MORPC EPDO weights: fatal + serious, visible (minor) injury, possible injury, PDO.
EPDO_WEIGHTS = {"ksi": 37.56, "minor": 6.55, "possible": 4.44, "pdo": 1.0}

#: Scope of the location a question names. Drives the scale of every count.
SCOPES = ("intersection", "corridor", "city", "citywide", "county", "region")

#: Adult Level I trauma centres serving Franklin County.
TRAUMA_CENTERS = ("OhioHealth Grant Medical Center", "The Ohio State University Wexner Medical Center")


@dataclass
class ToolContext:
    location: str
    scope: str
    year: int
    question: str = ""
    stakeholder: str | None = None
    #: numbers parsed from the question, e.g. a "from 8 to 2" scenario
    before: int | None = None
    after: int | None = None
    _cache: dict = field(default_factory=dict, repr=False)

    def rng(self, label: str) -> random.Random:
        """A generator seeded by (label, location, year) - never by the tool name
        when the label is shared, so tools agree on shared quantities."""
        key = f"{label}|{self.location.lower()}|{self.year}"
        seed = int(hashlib.sha256(key.encode()).hexdigest()[:16], 16)
        return random.Random(seed)

    def core(self, name: str, build):
        if name not in self._cache:
            self._cache[name] = build(self)
        return self._cache[name]


@dataclass
class MetricValue:
    metric_id: str
    value: object          # int | float | str | bool
    note: str = ""

    @property
    def spec(self) -> MetricSpec:
        return METRICS[self.metric_id]


# --------------------------------------------------------------------------
# shared cores
# --------------------------------------------------------------------------

def _crash_core(ctx: ToolContext) -> dict:
    """Crash counts by severity, consistent across every tool."""
    r = ctx.rng("crash_core")
    scope = ctx.scope
    if scope == "intersection":
        entering = r.randint(18_000, 60_000)
        rate = r.uniform(0.4, 1.6)
        total = max(3, int(round(rate * 365 * entering / 1e6)))
        vmt100m = None
    elif scope == "corridor":
        entering = None
        aadt = r.randint(14_000, 45_000)
        length = r.uniform(1.5, 4.5)
        vmt100m = aadt * length * 365 / 1e8
        total = max(10, int(round(r.uniform(180, 420) * vmt100m)))
    elif scope == "city":
        entering, vmt100m = None, r.uniform(4, 16)
        total = int(round(r.uniform(260, 330) * vmt100m))
    elif scope == "citywide":
        entering, vmt100m = None, r.uniform(72, 86)
        total = int(round(r.uniform(140, 165) * vmt100m))
    elif scope == "county":
        entering, vmt100m = None, r.uniform(120, 140)
        total = int(round(r.uniform(195, 225) * vmt100m))
    else:  # region
        entering, vmt100m = None, r.uniform(160, 190)
        total = int(round(r.uniform(180, 200) * vmt100m))

    # severity shares anchored to the Columbus crash layer (2021: fatal 0.7 %,
    # serious 2.8 %, minor 24 %, possible 13 %, PDO 59 %)
    if total < 60:
        # small counts: draw each severity so a quiet intersection can have zero deaths
        fatal = sum(1 for _ in range(total) if r.random() < 0.006)
        serious = sum(1 for _ in range(total) if r.random() < 0.028)
    else:
        fatal = int(round(total * r.uniform(0.004, 0.008)))
        serious = int(round(total * r.uniform(0.021, 0.034)))
    minor = int(round(total * r.uniform(0.20, 0.26)))
    possible = int(round(total * r.uniform(0.11, 0.15)))
    pdo = total - fatal - serious - minor - possible
    ped = int(round(total * r.uniform(0.012, 0.03))) if total >= 60 else sum(
        1 for _ in range(total) if r.random() < 0.03)
    bike = int(round(total * r.uniform(0.004, 0.012))) if total >= 60 else sum(
        1 for _ in range(total) if r.random() < 0.012)
    ksi = fatal + serious
    epdo = (ksi * EPDO_WEIGHTS["ksi"] + minor * EPDO_WEIGHTS["minor"]
            + possible * EPDO_WEIGHTS["possible"] + pdo * EPDO_WEIGHTS["pdo"])
    return dict(total=total, fatal=fatal, serious=serious, minor=minor, possible=possible,
                pdo=pdo, ksi=ksi, ped=ped, bike=bike, epdo=epdo,
                entering=entering, vmt100m=vmt100m,
                trend=r.uniform(-18, 22),
                shares=dict(angle=r.uniform(14, 30), rear_end=r.uniform(22, 42),
                            left_turn=r.uniform(8, 20), fixed_object=r.uniform(6, 18),
                            night=r.uniform(24, 40), speed=r.uniform(9, 24)))


def _ops_core(ctx: ToolContext) -> dict:
    r = ctx.rng("ops_core")
    freeway = bool(re.search(r"\b(I-?\d{2,3}|IR-?\d+|US-?\d+|SR-?\d+|interstate|freeway|ramp)\b",
                             ctx.location, re.I))
    if freeway:
        aadt = r.randint(60_000, 160_000)
        truck = r.uniform(12, 26)
    elif ctx.scope == "intersection":
        aadt = r.randint(12_000, 42_000)
        truck = r.uniform(3, 11)
    else:
        aadt = r.randint(9_000, 38_000)
        truck = r.uniform(3, 12)
    delay = r.uniform(18, 92)
    return dict(aadt=aadt, truck_pct=truck, peak=int(aadt * r.uniform(0.085, 0.11)),
                delay=delay, vc=r.uniform(0.62, 1.08), queue=r.randint(150, 950),
                lottr=r.uniform(1.08, 1.95), cycle=r.choice([90, 100, 110, 120, 130, 140, 150]),
                freeway=freeway)


def _speed_core(ctx: ToolContext) -> dict:
    r = ctx.rng("speed_core")
    posted = r.choice([25, 25, 30, 35, 35, 40, 45])
    if re.search(r"\b(I-?\d{2,3}|IR-?\d+|interstate|freeway)\b", ctx.location, re.I):
        posted = r.choice([55, 65])
    mean = posted + r.uniform(-1.5, 5.5)
    p85 = mean + r.uniform(4, 8)
    over = max(5.0, min(92.0, 50 + (mean - posted) * 9 + r.uniform(-6, 6)))
    over10 = max(0.5, over * r.uniform(0.08, 0.3))
    return dict(posted=posted, mean=mean, p85=p85, over=over, over10=over10)


def _asset_core(ctx: ToolContext) -> dict:
    r = ctx.rng("asset_core")
    return dict(ada=r.uniform(35, 92), months=r.randint(4, 22),
                cost=r.choice([0.35, 0.6, 0.9, 1.4, 2.2, 3.5, 5.8, 8.5]) * 1e6)


def _los(delay: float) -> str:
    for grade, limit in (("A", 10), ("B", 20), ("C", 35), ("D", 55), ("E", 80)):
        if delay <= limit:
            return grade
    return "F"


# --------------------------------------------------------------------------
# tools
# --------------------------------------------------------------------------

def crash_profile(ctx: ToolContext) -> list[MetricValue]:
    c = ctx.core("crash", _crash_core)
    out = [
        MetricValue("crashes_total", c["total"]),
        MetricValue("crashes_fatal", c["fatal"]),
        MetricValue("crashes_serious_injury", c["serious"]),
        MetricValue("crashes_minor_injury", c["minor"]),
        MetricValue("crashes_possible_injury", c["possible"]),
        MetricValue("crashes_pdo", c["pdo"]),
        MetricValue("ksi", c["ksi"]),
        MetricValue("pedestrian_crashes", c["ped"]),
        MetricValue("bicycle_crashes", c["bike"]),
    ]
    if c["entering"]:
        out += [MetricValue("entering_adt", c["entering"]),
                MetricValue("crash_rate_mev", c["total"] / (365 * c["entering"] / 1e6))]
    else:
        out += [MetricValue("annual_vmt_100m", c["vmt100m"]),
                MetricValue("crash_rate_100mvmt", c["total"] / c["vmt100m"])]
    s = c["shares"]
    out += [
        MetricValue("epdo_score", c["epdo"]),
        MetricValue("severity_index", c["epdo"] / c["total"]),
        MetricValue("crash_trend_5yr_pct", c["trend"]),
        MetricValue("share_angle", s["angle"]),
        MetricValue("share_rear_end", s["rear_end"]),
        MetricValue("share_left_turn", s["left_turn"]),
        MetricValue("share_fixed_object", s["fixed_object"]),
        MetricValue("share_nighttime", s["night"]),
        MetricValue("share_speed_related", s["speed"]),
    ]
    return out


def safety_targets(ctx: ToolContext) -> list[MetricValue]:
    """Regional PM1 five-year averages against the 2 %/yr reduction targets.

    Scaled to the MORPC planning area whatever the question's location, because
    the targets are set at that scale.
    """
    r = ctx.rng("targets")
    fat = r.uniform(178, 204)
    vmt = r.uniform(160, 190)
    si = r.uniform(810, 880)
    nm = r.uniform(146, 168)
    t_fat, t_si, t_nm = fat * r.uniform(0.95, 1.0), 844.6 * 0.98, 155.6 * 0.98
    on_track = fat <= t_fat and si <= t_si and nm <= t_nm
    return [
        MetricValue("fatalities_5yr_avg", fat, "MORPC planning area"),
        MetricValue("fatality_rate_5yr_avg", fat / vmt, "MORPC planning area"),
        MetricValue("serious_injuries_5yr_avg", si, "MORPC planning area"),
        MetricValue("serious_injury_rate_5yr_avg", si / vmt, "MORPC planning area"),
        MetricValue("nonmotorized_ksi_5yr_avg", nm, "MORPC planning area"),
        MetricValue("target_fatalities", t_fat),
        MetricValue("target_serious_injuries", t_si),
        MetricValue("target_nonmotorized_ksi", t_nm),
        MetricValue("targets_on_track", "yes" if on_track else "no - at least one measure above target"),
    ]


_COUNTERMEASURES = (
    ("roundabout", 48, "signalised intersection converted to a roundabout"),
    ("leading pedestrian interval", 13, "retiming only; lowest cost"),
    ("pedestrian hybrid beacon", 55, "mid-block or unsignalised crossing"),
    ("road diet (four to three lanes)", 30, "where volumes allow"),
    ("protected left-turn phasing", 35, "where left-turn crashes dominate"),
    ("median with pedestrian refuge", 46, "where crossing distance is the issue"),
    ("corridor access management", 28, "driveway consolidation"),
)


def network_screening(ctx: ToolContext) -> list[MetricValue]:
    c = ctx.core("crash", _crash_core)
    r = ctx.rng("screening")
    predicted = c["total"] * r.uniform(0.55, 0.95)
    w = r.uniform(0.45, 0.8)
    expected = w * predicted + (1 - w) * c["total"]
    excess = expected - predicted
    rank = r.randint(4, 180) if ctx.scope == "intersection" else r.randint(2, 40)
    hin = r.random() < 0.6
    cm, crf, when = r.choice(_COUNTERMEASURES)
    a = ctx.core("asset", _asset_core)
    annual_benefit = excess * r.uniform(90_000, 240_000)
    bc = (annual_benefit * 12) / a["cost"]
    return [
        MetricValue("expected_crashes_eb", expected),
        MetricValue("excess_expected_crashes", max(0.0, excess)),
        MetricValue("psi_rank", rank, "among Columbus intersections" if ctx.scope == "intersection"
                    else "among Central Ohio corridors"),
        MetricValue("hin_member", "yes" if hin else "no"),
        MetricValue("hsip_eligible", "yes" if c["ksi"] >= 2 or excess > 2 else "no - crash history below the threshold"),
        MetricValue("leading_countermeasure", f"{cm} ({when})"),
        MetricValue("ksi_reduction_expected", crf),
        MetricValue("benefit_cost_ratio", max(0.4, min(bc, 9.5))),
        MetricValue("project_cost_estimate_usd", a["cost"]),
    ]


def countermeasure_reference(ctx: ToolContext) -> list[MetricValue]:
    """Published FHWA Proven Safety Countermeasure reduction factors.

    These are reference values, not generated ones. They are approximate
    summaries of the FHWA fact sheets and should be checked against the current
    sheet before being used in a funding application.
    """
    return [
        MetricValue("crf_roundabout_from_two_way_stop", 78),
        MetricValue("crf_roundabout_from_signal", 48),
        MetricValue("crf_leading_pedestrian_interval", 13),
        MetricValue("crf_rrfb", 47),
        MetricValue("crf_pedestrian_hybrid_beacon", 55),
        MetricValue("crf_road_diet", "19 to 47"),
        MetricValue("crf_backplates", 15),
        MetricValue("crf_lighting", 42),
        MetricValue("crf_access_management", "25 to 31"),
        MetricValue("crf_median_refuge", 46),
    ]


def traffic_operations(ctx: ToolContext) -> list[MetricValue]:
    o = ctx.core("ops", _ops_core)
    r = ctx.rng("operations")
    tti = 1 + (o["lottr"] - 1) * r.uniform(0.45, 0.7)
    pti = o["lottr"] + r.uniform(0.15, 0.6)
    return [
        MetricValue("aadt", o["aadt"]),
        MetricValue("peak_hour_volume", o["peak"]),
        MetricValue("control_delay", o["delay"]),
        MetricValue("los", _los(o["delay"])),
        MetricValue("vc_ratio", o["vc"]),
        MetricValue("queue_95th_ft", o["queue"]),
        MetricValue("lottr", o["lottr"], "reliable below 1.50"),
        MetricValue("pti", pti),
        MetricValue("tti", tti),
        MetricValue("truck_share_pct", o["truck_pct"]),
        MetricValue("cycle_length_s", o["cycle"]),
    ]


def speed_profile(ctx: ToolContext) -> list[MetricValue]:
    s = ctx.core("speed", _speed_core)
    return [
        MetricValue("posted_speed", s["posted"]),
        MetricValue("mean_speed", s["mean"]),
        MetricValue("speed_85th", s["p85"]),
        MetricValue("pct_over_limit", s["over"]),
        MetricValue("pct_over_limit_10", s["over10"]),
    ]


def vulnerable_user_profile(ctx: ToolContext) -> list[MetricValue]:
    c = ctx.core("crash", _crash_core)
    o = ctx.core("ops", _ops_core)
    a = ctx.core("asset", _asset_core)
    r = ctx.rng("vru")
    ped3 = int(round(c["ped"] * r.uniform(2.4, 3.6)))
    bike3 = int(round(c["bike"] * r.uniform(2.4, 3.6)))
    ped_ksi = min(ped3, int(round(ped3 * r.uniform(0.12, 0.3))))
    bike_ksi = min(bike3, int(round(bike3 * r.uniform(0.08, 0.25))))
    crossing = r.randint(44, 112)
    needed = crossing / 3.5
    provided = needed + r.uniform(-4, 3)
    lts = min(4, max(1, int(round(1 + (c["shares"]["speed"] / 8) + (o["aadt"] / 15_000)))))
    return [
        MetricValue("pedestrian_crashes_3yr", ped3),
        MetricValue("pedestrian_ksi_3yr", ped_ksi),
        MetricValue("bicycle_crashes_3yr", bike3),
        MetricValue("bicycle_ksi_3yr", bike_ksi),
        MetricValue("daily_pedestrian_count", r.randint(40, 1_400)),
        MetricValue("daily_bicycle_count", r.randint(10, 260)),
        MetricValue("crossing_distance_ft", crossing),
        MetricValue("ped_clearance_time_s", needed),
        MetricValue("ped_clearance_provided_s", max(4.0, provided),
                    "short of the MUTCD need" if provided < needed else "meets the MUTCD need"),
        MetricValue("lighting_coverage_pct", r.uniform(25, 100)),
        MetricValue("sidewalk_gap_miles", r.uniform(0, 2.4)),
        MetricValue("ada_ramp_compliance_pct", a["ada"]),
        MetricValue("bike_lts", lts),
        MetricValue("pedestrian_lts", min(4, max(1, lts + r.choice([-1, 0, 0, 1])))),
        MetricValue("share_nighttime_vru", r.uniform(30, 58)),
    ]


def emergency_response_profile(ctx: ToolContext) -> list[MetricValue]:
    c = ctx.core("crash", _crash_core)
    o = ctx.core("ops", _ops_core)
    r = ctx.rng("ems")
    mean = r.uniform(5.2, 8.9)
    p90 = mean + r.uniform(2.2, 4.8)
    compliance = max(40.0, min(97.0, 100 - (p90 - 8) * 9 + r.uniform(-5, 5)))
    constraints = r.sample([
        "median barrier prevents U-turns, so units approach from one direction",
        "queue spillback onto the ramp in the PM peak",
        "no shoulder for a full lane closure",
        "single access road into the neighbourhood",
        "signal pre-emption not installed on the corridor",
        "rail crossing on the direct route from the nearest station",
    ], 2)
    return [
        MetricValue("ems_response_mean_min", mean),
        MetricValue("ems_response_90th_min", p90),
        MetricValue("nfpa_als_8min_compliance_pct", compliance, "NFPA 1710 asks for 90 %"),
        MetricValue("trauma_center_nearest", r.choice(TRAUMA_CENTERS)),
        MetricValue("trauma_center_distance_mi", r.uniform(1.8, 14.5)),
        MetricValue("crash_to_hospital_mean_min", r.randint(34, 62)),
        MetricValue("roadway_clearance_mean_min", r.randint(28, 85)),
        MetricValue("incident_clearance_mean_min", r.randint(45, 125)),
        MetricValue("secondary_crash_share_pct", r.uniform(2.5, 9.0)),
        MetricValue("mvc_ems_calls_per_year", int(round(c["total"] * r.uniform(0.32, 0.48)))),
        MetricValue("serious_injury_transports_per_year", int(round(c["ksi"] * r.uniform(1.0, 1.4)))),
        MetricValue("ems_access_constraints", "; ".join(constraints)),
        MetricValue("queue_95th_ft", o["queue"]),
    ]


def transit_access_profile(ctx: ToolContext) -> list[MetricValue]:
    c = ctx.core("crash", _crash_core)
    o = ctx.core("ops", _ops_core)
    a = ctx.core("asset", _asset_core)
    r = ctx.rng("transit")
    stops = r.randint(2, 14)
    routes = sorted(r.sample([1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 21, 22, 23, 24, 25, 31, 32,
                              33, 34, 35, 51, 52, 61, 71, 72, 73, 74, 101, 102], r.randint(1, 3)))
    return [
        MetricValue("stops_quarter_mile", stops),
        MetricValue("nearest_routes", ", ".join(f"COTA {n}" for n in routes)),
        MetricValue("daily_boardings_nearby", int(stops * r.uniform(15, 140))),
        MetricValue("stops_with_sidewalk_pct", r.uniform(45, 100)),
        MetricValue("stops_ada_accessible_pct", min(100.0, a["ada"] + r.uniform(-10, 15))),
        MetricValue("ped_crashes_near_stops_3yr", min(int(round(c["ped"] * 3)), r.randint(0, 6))),
        MetricValue("park_ride_utilization_pct", r.uniform(22, 88)),
        MetricValue("bus_delay_s_per_mile", int(o["delay"] * r.uniform(1.2, 2.4))),
        MetricValue("transit_involved_crashes_3yr", r.randint(0, 5)),
        MetricValue("control_delay", o["delay"]),
    ]


def freight_rail_profile(ctx: ToolContext) -> list[MetricValue]:
    c = ctx.core("crash", _crash_core)
    o = ctx.core("ops", _ops_core)
    r = ctx.rng("freight")
    trucks = int(o["aadt"] * o["truck_pct"] / 100)
    trains = r.randint(4, 38)
    xing_aadt = r.randint(2_500, 18_000)
    device = r.choice(["gates with flashing lights", "gates with flashing lights",
                       "flashing lights only", "crossbucks only"])
    return [
        MetricValue("truck_share_pct", o["truck_pct"]),
        MetricValue("daily_trucks", trucks),
        MetricValue("truck_involved_crashes_3yr", int(round(c["total"] * 3 * o["truck_pct"] / 100 * r.uniform(0.6, 1.3)))),
        MetricValue("tttr", r.uniform(1.25, 2.6)),
        MetricValue("design_vehicle_accommodated",
                    r.choice(["WB-67 on all movements", "WB-62 on through movements; WB-67 off-tracks onto the curb on the right turn",
                              "SU-40 only; interstate semis cannot make the right turn without encroachment"])),
        MetricValue("rail_crossing_nearest", r.choice([
            "CSX crossing on the adjacent street", "Norfolk Southern crossing a half mile south",
            "CSX crossing on the parallel local street", "no public at-grade crossing within a mile"])),
        MetricValue("trains_per_day", trains),
        MetricValue("crossing_exposure_index", xing_aadt * trains),
        MetricValue("crossing_incidents_5yr", r.choice([0, 0, 0, 1, 1, 2, 3])),
        MetricValue("blocked_crossing_reports_yr", r.randint(0, 60)),
        MetricValue("trespass_incidents_3yr", r.choice([0, 0, 1, 1, 2, 4])),
        MetricValue("crossing_warning_device", device),
    ]


def infrastructure_condition(ctx: ToolContext) -> list[MetricValue]:
    a = ctx.core("asset", _asset_core)
    r = ctx.rng("assets")
    return [
        MetricValue("pci", r.randint(38, 88)),
        MetricValue("pavement_age_yr", r.randint(2, 19)),
        MetricValue("signal_equipment_age_yr", r.randint(3, 28)),
        MetricValue("sidewalk_condition_rating", r.randint(1, 5)),
        MetricValue("marking_retroreflectivity_mcd", r.randint(35, 240), "MUTCD minimum 50"),
        MetricValue("drainage_issues", r.randint(0, 7)),
        MetricValue("utility_conflicts", r.randint(0, 9)),
        MetricValue("row_width_ft", r.choice([50, 60, 66, 80, 100, 120])),
        MetricValue("ada_ramp_compliance_pct", a["ada"]),
        MetricValue("annual_maintenance_cost_usd", r.randint(18, 160) * 1_000),
        MetricValue("project_cost_estimate_usd", a["cost"]),
        MetricValue("construction_duration_months", a["months"]),
    ]


def community_impact_profile(ctx: ToolContext) -> list[MetricValue]:
    o = ctx.core("ops", _ops_core)
    a = ctx.core("asset", _asset_core)
    r = ctx.rng("community")
    homes = r.randint(60, 320)
    expected = int(homes * 9.4)          # ITE land use 210: ~9.4 trips per home per day
    local_adt = int(expected * r.uniform(0.9, 2.6))
    cut = max(0.0, (local_adt - expected) / local_adt * 100)
    noise = 52 + 10 * math.log10(max(o["aadt"], 1_000) / 1_000) + r.uniform(-3, 3)
    return [
        MetricValue("local_street_adt", local_adt),
        MetricValue("ite_expected_adt", expected),
        MetricValue("cut_through_share_pct", cut, "0-25 % is the usual acceptable band"),
        MetricValue("noise_leq_dba", noise),
        MetricValue("noise_nac_exceeded", "yes" if noise >= 66 else "no"),
        MetricValue("complaints_311_speeding_yr", r.randint(0, 28)),
        MetricValue("complaints_311_noise_yr", r.randint(0, 12)),
        MetricValue("detour_length_mi", r.uniform(0.4, 3.2)),
        MetricValue("construction_duration_months", a["months"]),
        MetricValue("residents_within_500ft", int(homes * r.uniform(2.1, 2.8))),
        MetricValue("schools_within_half_mile", r.choice([0, 0, 1, 1, 2, 3])),
        MetricValue("zero_vehicle_households_pct", r.uniform(3, 24)),
    ]


def growth_outlook(ctx: ToolContext) -> list[MetricValue]:
    r = ctx.rng("growth")
    aadt_growth = r.uniform(8, 48)
    return [
        MetricValue("aadt_growth_2050_pct", aadt_growth),
        MetricValue("population_growth_2050_pct", r.uniform(10, 55)),
        MetricValue("employment_growth_2050_pct", r.uniform(8, 40)),
        MetricValue("forecast_crash_change_no_build_pct", aadt_growth * r.uniform(0.7, 1.1)),
        MetricValue("planned_developments_count", r.randint(0, 9)),
    ]


def _poisson_ci(k: int) -> tuple[float, float]:
    """Exact-ish 95 % interval for a Poisson count (Garwood, via chi-square approximation)."""
    if k == 0:
        return 0.0, 3.69
    lo = k * (1 - 1 / (9 * k) - 1.96 / (3 * math.sqrt(k))) ** 3
    hi = (k + 1) * (1 - 1 / (9 * (k + 1)) + 1.96 / (3 * math.sqrt(k + 1))) ** 3
    return max(0.0, lo), hi


def project_outcome_evaluation(ctx: ToolContext) -> list[MetricValue]:
    """Before / after reading of a project, for the shared cross-stakeholder scenario.

    Takes the before and after counts from the question when it states them
    ("reduced crashes from 8 to 2 per year"); otherwise generates a plausible
    pair for the location.
    """
    r = ctx.rng("outcome")
    before = ctx.before if ctx.before is not None else r.randint(6, 30)
    after = ctx.after if ctx.after is not None else max(0, int(before * r.uniform(0.3, 0.8)))
    serious_after = 2 if "serious" in ctx.question.lower() and after >= 2 else min(after, r.choice([0, 0, 1]))
    ksi_before = min(before, max(serious_after, int(round(before * r.uniform(0.12, 0.3)))))
    ksi_after = serious_after
    pdo_b, pdo_a = before - ksi_before, after - ksi_after
    epdo_b = ksi_before * EPDO_WEIGHTS["ksi"] + pdo_b * r.uniform(1.0, 3.0)
    epdo_a = ksi_after * EPDO_WEIGHTS["ksi"] + pdo_a * r.uniform(1.0, 3.0)
    lo, hi = _poisson_ci(after)
    change = (after - before) / before * 100 if before else 0.0
    distinguishable = before > hi
    note = (f"a one-year count of {after} has a 95 % interval of {lo:.1f} to {hi:.1f}; "
            + ("the drop from the before count is larger than chance" if distinguishable
               else "the before count sits inside that interval, so one year cannot confirm the drop"))
    if ksi_after:
        note += (f"; {ksi_after} serious-injury crash(es) in one year are too few to judge "
                 "whether severity changed")
    ped_share = r.uniform(0, 100) if after else 0.0
    if "pedestrian" in ctx.question.lower() and after:
        ped_share = max(ped_share, 100.0 / after)
    return [
        MetricValue("crashes_before", before),
        MetricValue("crashes_after", after),
        MetricValue("crash_change_pct", change),
        MetricValue("ksi_before", ksi_before),
        MetricValue("ksi_after", ksi_after),
        MetricValue("epdo_before", epdo_b),
        MetricValue("epdo_after", epdo_a),
        MetricValue("poisson_ci_after", f"{lo:.1f} to {hi:.1f}"),
        MetricValue("significance_note", note),
        MetricValue("delay_change_pct", -r.uniform(4, 28)),
        MetricValue("ped_crash_share_after_pct", ped_share),
        MetricValue("meets_pm1_pace", "yes" if ksi_after < ksi_before * 0.98 else "no - KSI did not fall at the target pace"),
    ]


TOOL_FUNCTIONS = {
    "crash_profile": crash_profile,
    "safety_targets": safety_targets,
    "network_screening": network_screening,
    "countermeasure_reference": countermeasure_reference,
    "traffic_operations": traffic_operations,
    "speed_profile": speed_profile,
    "vulnerable_user_profile": vulnerable_user_profile,
    "emergency_response_profile": emergency_response_profile,
    "transit_access_profile": transit_access_profile,
    "freight_rail_profile": freight_rail_profile,
    "infrastructure_condition": infrastructure_condition,
    "community_impact_profile": community_impact_profile,
    "growth_outlook": growth_outlook,
    "project_outcome_evaluation": project_outcome_evaluation,
}
