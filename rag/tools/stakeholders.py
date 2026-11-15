"""The eight stakeholder groups the tool serves, and how to tell which one is asking.

Each profile carries the concerns the group brings to a safety question (from
the stakeholder evaluation set), the metric tools that produce the numbers it
reasons with, and the vocabulary that signals the group when no perspective is
chosen explicitly. The same evidence reads differently to each group - a
project that cut crashes from eight to two is a success to a regional agency
meeting its targets and an open question to a trauma surgeon who treated the
two - so the profile is also handed to the generator as a framing instruction.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .metrics import (AGENCY, ALL, DRIVERS, EMERGENCY, FREIGHT, LOCAL_GOV,
                      RESIDENTS, TRANSIT, VRU)


@dataclass(frozen=True)
class Stakeholder:
    id: str
    name: str
    description: str
    concerns: tuple[str, ...]
    #: tool names in priority order (see rag.tools.registry)
    tools: tuple[str, ...]
    #: regexes over the question that signal this stakeholder
    signals: tuple[str, ...]
    #: what "good" looks like, for the framing instruction
    lens: str


STAKEHOLDERS: dict[str, Stakeholder] = {s.id: s for s in [
    Stakeholder(
        AGENCY, "State / regional transportation agencies",
        "ODOT and MORPC staff who look across the region and decide which roads, "
        "intersections and corridors to improve and which projects to prioritise.",
        ("crash reduction", "serious injuries and fatalities", "network-wide safety",
         "current and future demand", "project prioritisation", "comparing alternatives",
         "evidence that supports and explains decisions"),
        ("crash_profile", "safety_targets", "network_screening", "growth_outlook",
         "countermeasure_reference"),
        (r"\bprioriti[sz]", r"\bregion", r"\bMORPC\b", r"\bODOT\b", r"\btargets?\b",
         r"\btrade-?offs?\b", r"\balternatives?\b", r"\bnetwork\b", r"\bstatewide\b",
         r"\bagenc"),
        "Judge outcomes against the adopted five-year safety targets and network "
        "screening: does the location still rank, and is the investment justified "
        "relative to alternatives?"),
    Stakeholder(
        LOCAL_GOV, "Local government / public works",
        "City and township teams who plan, build, operate and maintain streets and "
        "signals.",
        ("implementation feasibility", "operations", "maintenance", "infrastructure condition",
         "capacity for future demand", "long-term safety performance"),
        ("infrastructure_condition", "crash_profile", "network_screening", "growth_outlook"),
        (r"\bmaintenan", r"\bimplement", r"\bpublic works\b", r"\blocal government",
         r"\bpavement\b",
         r"\binfrastructure condition", r"\bfeasib", r"\bright[- ]of[- ]way\b",
         r"\butilit", r"\bsustain", r"\bgeometry\b"),
        "Judge outcomes by whether the design can be built, maintained and kept "
        "effective as volumes grow, and what each remaining crash says about a "
        "fixable infrastructure or maintenance cause."),
    Stakeholder(
        RESIDENTS, "Nearby residents / local communities",
        "People who live near the road and use it daily for commuting, shopping, "
        "school and local trips.",
        ("safety near homes", "perceived safety", "noise", "cut-through traffic",
         "travel time", "access and detours during construction", "daily life impacts"),
        ("community_impact_profile", "speed_profile", "crash_profile", "vulnerable_user_profile"),
        (r"\bresident", r"\bneighbou?rhood", r"\bcut-?through\b", r"\bnoise\b", r"\bhomes?\b",
         r"\bcommunit", r"\bquality of life\b", r"\bdetour", r"\bcomplaint"),
        "Judge outcomes by what they mean on the block: two serious crashes near "
        "homes are not an acceptable residual, and perceived safety, speed, noise and "
        "diverted traffic count as much as the crash count."),
    Stakeholder(
        DRIVERS, "Drivers / daily commuters",
        "People who drive the road, intersection or corridor every day.",
        ("crash risk", "traffic conflicts", "speed", "delay", "queue length",
         "travel-time reliability", "turning and lane-changing behaviour",
         "clarity and predictability of the roadway design"),
        ("traffic_operations", "crash_profile", "speed_profile"),
        (r"\bcommut", r"\bdrivers?\b", r"\bqueue", r"\bdelay", r"\btravel[- ]time\b",
         r"\breliab", r"\blane", r"\bsignag", r"\bsignal timing\b", r"\binterchange\b",
         r"\brear-?end\b", r"\bcongestion\b"),
        "Judge outcomes by whether the trip is safer and more predictable: delay, "
        "queues, reliability and whether the design makes the expected manoeuvre "
        "obvious."),
    Stakeholder(
        VRU, "Pedestrians / cyclists / vulnerable road users",
        "People who walk, cycle or use micromobility, including older adults and "
        "people with disabilities.",
        ("crossing safety", "conflicts with vehicles", "sidewalk and path continuity",
         "accessibility", "crossing time", "visibility", "separation from vehicles",
         "comfort and confidence"),
        ("vulnerable_user_profile", "speed_profile", "crash_profile", "countermeasure_reference"),
        (r"\bpedestrian", r"\bcyclist", r"\bbicycl", r"\bbik(e|ing)\b", r"\bcrossing",
         r"\bsidewalk", r"\bvulnerable\b", r"\bVRU\b", r"\bwalk", r"\baccessib",
         r"\bolder adults\b", r"\bdisabilit", r"\bmicromobility\b"),
        "Judge outcomes by exposure and comfort for people outside a vehicle: "
        "remaining pedestrian concerns are the headline, not a footnote, and crossing "
        "distance, speed and separation decide whether the place feels safe."),
    Stakeholder(
        EMERGENCY, "Emergency responders / healthcare providers",
        "Fire, EMS, police and trauma staff who reach crash scenes, transport the "
        "injured and treat them.",
        ("emergency response time", "reliable access to incident locations",
         "frequency and severity of incidents",
         "effects of congestion and roadway design on response"),
        ("emergency_response_profile", "crash_profile", "traffic_operations"),
        (r"\bemergen", r"\bEMS\b", r"\bresponder", r"\bambulance", r"\btrauma\b",
         r"\bhospital", r"\bpost-?crash\b", r"\bresponse time", r"\bhealthcare\b",
         r"\binjur(y|ies) severity\b"),
        "Judge outcomes by severity and by what happens after the crash: two serious "
        "injuries with difficult access or long transport times are a significant "
        "concern regardless of the total count."),
    Stakeholder(
        TRANSIT, "Public transit / mobility providers",
        "COTA and other operators running buses, Park & Ride lots and mobility "
        "services.",
        ("first/last-mile safety", "Park & Ride access", "walking and cycling connections",
         "accessibility", "interactions between transit and other modes"),
        ("transit_access_profile", "vulnerable_user_profile", "traffic_operations"),
        (r"\btransit\b", r"\bCOTA\b", r"\bbus(es)?\b", r"\bpark\s*(&|and)\s*ride\b",
         r"\bfirst[/ -]?(and )?last[- ]mile\b", r"\bmobility\b", r"\bLinkUS\b",
         r"\bboarding", r"\bstops?\b"),
        "Judge outcomes by whether riders can reach the stop safely and the bus can "
        "move: sidewalk and crossing access to stops, stop accessibility and bus delay."),
    Stakeholder(
        FREIGHT, "Freight / rail operators",
        "Trucking firms and railroads that need safe, reliable freight movement.",
        ("truck and rail interactions with other road users", "crossing safety",
         "trespass and conflict risk", "freight access",
         "operational continuity during construction"),
        ("freight_rail_profile", "traffic_operations", "crash_profile"),
        (r"\bfreight\b", r"\btrucks?\b", r"\brail", r"\bat-?grade\b", r"\bcrossings?\b.*\brail",
         r"\bCSX\b", r"\bNorfolk Southern\b", r"\btrespass", r"\bdistribution cent",
         r"\bindustrial\b", r"\bdesign vehicle\b", r"\bturning radi"),
        "Judge outcomes by whether trucks and trains can still operate: turning "
        "paths, access, reliability and crossing conflicts, and whether the design "
        "shifts truck conflicts somewhere else."),
]}

assert tuple(STAKEHOLDERS) == ALL


def detect_stakeholder(question: str) -> str | None:
    """Best-guess stakeholder from the question's vocabulary, or None.

    An explicit choice from the caller always wins over this; it exists so a
    bare question like "where do trucks conflict with cyclists" still gets the
    freight tools without the user having to pick a perspective.
    """
    scores: dict[str, int] = {}
    for sid, s in STAKEHOLDERS.items():
        n = sum(1 for pat in s.signals if re.search(pat, question, re.I))
        if n:
            scores[sid] = n
    if not scores:
        return None
    best = max(scores.values())
    tied = [sid for sid, n in scores.items() if n == best]
    if len(tied) > 1 and best < 2:
        return None          # one weak hit each: no real signal
    # ties at >=2 hits: keep declaration order, which puts the broad groups first
    return tied[0]


def framing(stakeholder_id: str) -> str:
    """The perspective block handed to the generator."""
    s = STAKEHOLDERS[stakeholder_id]
    return (f"STAKEHOLDER PERSPECTIVE: answer for {s.name}. {s.description} "
            f"They care about: {', '.join(s.concerns)}. {s.lens} Lead with the "
            f"figures and findings that matter to this group, say explicitly what "
            f"would and would not satisfy them, and name the evidence they would "
            f"want next.")
