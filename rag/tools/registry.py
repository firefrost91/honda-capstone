"""Tool registry: which tools answer which question, and how their output
becomes a citable passage.

A tool call is treated exactly like a retrieved passage once it has run. Its
output is rendered as a ``tool_metric`` passage, embedded with the same model
as the corpus so post-hoc attribution can verify the sentences that quote it,
and numbered ``[S#]`` alongside the documents. Two things distinguish it from a
document passage:

* the label tells the generator it may quote the figures (unlike a catalogue
  card) and that they are placeholders (unlike a GIS aggregate);
* the ``source_id`` is ``tool:<name>``, so the "distinct documents" count and
  the per-source cap never see it.

Replacing a stub with a live service means registering a function with the
same name that returns ``MetricValue`` rows with catalogue ids - nothing
downstream changes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from ..corpus import Passage
from .metrics import METRICS, format_value
from .stakeholders import STAKEHOLDERS, detect_stakeholder
from .synthetic import TOOL_FUNCTIONS, MetricValue, ToolContext

TOOL_KIND = "tool_metric"
DEFAULT_YEAR = 2024


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    fn: Callable[[ToolContext], list[MetricValue]]
    synthetic: bool = True
    #: regexes over the question that call the tool regardless of stakeholder
    triggers: tuple[str, ...] = ()


TOOLS: dict[str, Tool] = {t.name: t for t in [
    Tool("crash_profile", "Crash counts by severity, KSI, pedestrian and bicycle "
         "involvement, crash rate, EPDO score and collision-type shares for the location "
         "and year.", TOOL_FUNCTIONS["crash_profile"],
         triggers=(r"\bcrash", r"\bfatal", r"\binjur", r"\bhotspot", r"\bcollision")),
    Tool("safety_targets", "The five federal safety performance measures as five-year "
         "rolling averages for the MORPC planning area, against the adopted 2 %/yr "
         "reduction targets.", TOOL_FUNCTIONS["safety_targets"],
         triggers=(r"\btargets?\b", r"\bperformance measure", r"\brolling average")),
    Tool("network_screening", "Empirical-Bayes expected and excess crashes, PSI rank, "
         "High Injury Network membership, HSIP eligibility, the leading countermeasure "
         "and its benefit-cost ratio.", TOOL_FUNCTIONS["network_screening"],
         triggers=(r"\bprioriti", r"\bscreen", r"\bbenefit[- ]cost\b", r"\bHSIP\b",
                   r"\bHigh Injury Network\b")),
    Tool("countermeasure_reference", "Published FHWA Proven Safety Countermeasure crash "
         "reduction factors (reference values, not measurements).",
         TOOL_FUNCTIONS["countermeasure_reference"], synthetic=False,
         triggers=(r"\bcountermeasure", r"\broundabout", r"\broad diet\b",
                   r"\bbeacon", r"\bleading pedestrian\b")),
    Tool("traffic_operations", "AADT, peak-hour volume, control delay and level of "
         "service, volume-to-capacity ratio, 95th-percentile queue, LOTTR, planning and "
         "travel time indices, truck share.", TOOL_FUNCTIONS["traffic_operations"],
         triggers=(r"\bdelay", r"\bqueue", r"\bcongest", r"\breliab", r"\blevel of service\b",
                   r"\bLOS\b", r"\bvolume")),
    Tool("speed_profile", "Posted limit, mean and 85th-percentile speed, share of drivers "
         "over the limit.", TOOL_FUNCTIONS["speed_profile"],
         triggers=(r"\bspeed", r"\b85th\b")),
    Tool("vulnerable_user_profile", "Pedestrian and bicycle crashes and KSI over three "
         "years, counts, crossing distance and clearance time, lighting, sidewalk gaps, "
         "ADA ramp compliance, bicycle and pedestrian level of traffic stress.",
         TOOL_FUNCTIONS["vulnerable_user_profile"],
         triggers=(r"\bpedestrian", r"\bcyclist", r"\bbicycl", r"\bcrossing", r"\bsidewalk",
                   r"\bwalk", r"\bvulnerable\b")),
    Tool("emergency_response_profile", "EMS response times against NFPA 1710, nearest "
         "Level I trauma centre, crash-to-hospital time, roadway and incident clearance "
         "times, secondary-crash share, EMS access constraints.",
         TOOL_FUNCTIONS["emergency_response_profile"],
         triggers=(r"\bemergen", r"\bEMS\b", r"\bresponder", r"\btrauma\b", r"\bpost-?crash\b",
                   r"\bresponse time")),
    Tool("transit_access_profile", "COTA stops and routes nearby, boardings, sidewalk and "
         "ADA access to stops, pedestrian crashes near stops, Park & Ride utilisation, "
         "bus delay.", TOOL_FUNCTIONS["transit_access_profile"],
         triggers=(r"\btransit\b", r"\bCOTA\b", r"\bbus\b", r"\bpark\s*(&|and)\s*ride\b",
                   r"\blast[- ]mile\b")),
    Tool("freight_rail_profile", "Truck share and volume, truck-involved crashes, TTTR, "
         "design-vehicle accommodation, nearest at-grade rail crossing with trains per "
         "day, exposure, incidents, blocked-crossing and trespass reports.",
         TOOL_FUNCTIONS["freight_rail_profile"],
         triggers=(r"\bfreight\b", r"\btrucks?\b", r"\brail", r"\bat-?grade\b", r"\btrespass")),
    Tool("infrastructure_condition", "Pavement condition, signal and pavement age, "
         "sidewalk condition, marking retroreflectivity, drainage and utility conflicts, "
         "right-of-way, maintenance and project cost, construction duration.",
         TOOL_FUNCTIONS["infrastructure_condition"],
         triggers=(r"\bmaintenan", r"\bpavement\b", r"\bcondition", r"\bright[- ]of[- ]way\b",
                   r"\bimplement", r"\bconstruction\b")),
    Tool("community_impact_profile", "Local-street volume against the land-use "
         "expectation (cut-through share), noise against the FHWA criterion, 311 "
         "complaints, detour length, residents and schools nearby, zero-vehicle "
         "households.", TOOL_FUNCTIONS["community_impact_profile"],
         triggers=(r"\bcut-?through\b", r"\bnoise\b", r"\bresident", r"\bneighbou?rhood",
                   r"\bdetour", r"\bcomplaint")),
    Tool("growth_outlook", "MTP-style 2050 growth in traffic, population and employment, "
         "and the no-build crash forecast.", TOOL_FUNCTIONS["growth_outlook"],
         triggers=(r"\bgrowth\b", r"\b2050\b", r"\bfuture demand\b", r"\bdevelopment\b",
                   r"\bover time\b")),
    Tool("project_outcome_evaluation", "Before/after reading of a project: crash and KSI "
         "change, EPDO, Poisson interval on the after count, delay change, pedestrian "
         "share of remaining crashes.", TOOL_FUNCTIONS["project_outcome_evaluation"],
         triggers=(r"\bfrom \d+ to \d+\b", r"\bbefore[- ]and[- ]after\b", r"\boutcome\b",
                   r"\bremaining crashes\b", r"\breduced crashes\b")),
]}

assert all(t.name in TOOL_FUNCTIONS for t in TOOLS.values())
for _s in STAKEHOLDERS.values():
    assert all(t in TOOLS for t in _s.tools), _s.id


# --------------------------------------------------------------------------
# reading the question
# --------------------------------------------------------------------------

_ROAD = (r"(?:[A-Z][A-Za-z.'-]+ ){0,2}[A-Z][A-Za-z.'-]+ "
         r"(?:Road|Rd\.?|Avenue|Ave\.?|Street|St\.?|Boulevard|Blvd\.?|Pike|Drive|Dr\.?|"
         r"Parkway|Pkwy\.?|Highway|Hwy\.?|Lane|Way|Place)")
_ROUTE = r"(?:I|IR|US|SR|OH)[- ]?\d{1,3}"
_INTERSECTION = re.compile(rf"({_ROAD}|{_ROUTE})\s+(?:and|&|at|/)\s+({_ROAD}|{_ROUTE})")
_CORRIDOR = re.compile(rf"\b({_ROAD}|{_ROUTE})\b")
_COUNTY = re.compile(r"\b(Franklin|Delaware|Licking|Fairfield|Union|Madison|Pickaway) County\b")
_CITIES = ("Hilliard", "Dublin", "Westerville", "Grove City", "Sunbury", "Powell", "Whitehall",
           "Bexley", "Upper Arlington", "Gahanna", "Reynoldsburg", "New Albany", "Worthington",
           "Grandview Heights", "Pickerington", "Delaware", "Marysville", "Lancaster", "Newark")
_REGION = re.compile(r"\b(Central Ohio|MORPC|the region|regional|Columbus metro)\b", re.I)
_YEAR = re.compile(r"\b(20[12]\d)\b")
_BEFORE_AFTER = re.compile(r"\bfrom\s+(\d{1,4})\s+to\s+(\d{1,4})\b")


def infer_location(question: str) -> tuple[str, str]:
    """(location label, scope) from the question's own words.

    Defaults to the whole city, because that is the scale most of the
    evaluation questions are asked at.
    """
    m = _INTERSECTION.search(question)
    if m:
        return f"{m.group(1).strip()} and {m.group(2).strip()}", "intersection"
    m = _CORRIDOR.search(question)
    if m:
        return f"{m.group(1).strip()} corridor", "corridor"
    m = _COUNTY.search(question)
    if m:
        return m.group(0), "county"
    for city in _CITIES:
        if re.search(rf"\b{re.escape(city)}\b", question):
            return city, "city"
    if re.search(r"\bintersection\b", question, re.I) and not re.search(r"\bintersections\b", question, re.I):
        return "the Columbus intersection in the scenario", "intersection"
    if _REGION.search(question) and not re.search(r"\bColumbus\b", question):
        return "MORPC planning area (Central Ohio)", "region"
    return "Columbus (citywide)", "citywide"


def build_context_for(question: str, stakeholder: str | None, year: int | None = None) -> ToolContext:
    location, scope = infer_location(question)
    ym = _YEAR.search(question)
    yr = year or (int(ym.group(1)) if ym else DEFAULT_YEAR)
    before = after = None
    bm = _BEFORE_AFTER.search(question)
    if bm:
        before, after = int(bm.group(1)), int(bm.group(2))
    return ToolContext(location=location, scope=scope, year=yr, question=question,
                       stakeholder=stakeholder, before=before, after=after)


def select_tools(question: str, stakeholder: str | None, limit: int) -> list[str]:
    """Tools for this question: the stakeholder's, led by any the question itself triggers."""
    triggered = [name for name, t in TOOLS.items()
                 if any(re.search(p, question, re.I) for p in t.triggers)]
    ordered: list[str] = []
    # the scenario tool is decisive when the question states a before/after pair
    if _BEFORE_AFTER.search(question) and "project_outcome_evaluation" in triggered:
        ordered.append("project_outcome_evaluation")
    if stakeholder:
        for name in STAKEHOLDERS[stakeholder].tools:
            if name in triggered and name not in ordered:
                ordered.append(name)
        for name in STAKEHOLDERS[stakeholder].tools:
            if name not in ordered:
                ordered.append(name)
    for name in triggered:
        if name not in ordered:
            ordered.append(name)
    if not ordered:
        ordered = ["crash_profile"]
    return ordered[:limit]


# --------------------------------------------------------------------------
# running and rendering
# --------------------------------------------------------------------------

@dataclass
class ToolResult:
    tool: str
    location: str
    scope: str
    year: int
    synthetic: bool
    values: list[MetricValue] = field(default_factory=list)

    @property
    def title(self) -> str:
        label = "Synthetic metric tool" if self.synthetic else "Reference table"
        return f"{label}: {self.tool.replace('_', ' ')}"   # the locator carries place and year

    def to_dict(self) -> dict:
        return {
            "tool": self.tool, "location": self.location, "scope": self.scope,
            "year": self.year, "synthetic": self.synthetic,
            "metrics": [{"id": v.metric_id, "name": v.spec.name,
                         "value": v.value, "unit": v.spec.unit, "note": v.note}
                        for v in self.values],
        }

    def to_passage(self) -> Passage:
        t = TOOLS[self.tool]
        if self.synthetic:
            head = (f"SYNTHETIC PLACEHOLDER OUTPUT from the stub tool '{self.tool}'. These "
                    f"values were generated to be plausible for {self.location} in {self.year}; "
                    f"they are NOT measured data and will be replaced by a live analytics "
                    f"service. Scope: {self.scope}.")
        else:
            head = (f"REFERENCE VALUES from '{self.tool}': published figures, approximate; "
                    f"not specific to {self.location}.")
        lines = [head, ""]
        for v in self.values:
            s = v.spec
            unit = f" {s.unit}" if s.unit and not isinstance(v.value, str) else ""
            note = f" [{v.note}]" if v.note else ""
            lines.append(f"- {s.name}: {format_value(s, v.value)}{unit}{note}. {s.definition}")
        bases = sorted({v.spec.basis for v in self.values})
        lines += ["", "Basis: " + "; ".join(bases) + "."]
        text = "\n".join(lines)
        return Passage(
            passage_id=f"tool:{self.tool}:{self.location}:{self.year}",
            kind=TOOL_KIND, text=text, title=self.title,
            source_id=f"tool:{self.tool}",
            organization="stub analytics tool (synthetic)" if self.synthetic else "FHWA (reference)",
            theme="metrics", citation_url="", locator=f"{self.location}, {self.year}",
            document_type="tool_output", topics=tuple(v.metric_id for v in self.values),
            caveats=("synthetic placeholder values",) if self.synthetic else ("approximate reference values",),
            word_count=len(text.split()), scope="region_specific", published_year=self.year,
        )


def run_tool(name: str, ctx: ToolContext) -> ToolResult:
    t = TOOLS[name]
    values = t.fn(ctx)
    unknown = [v.metric_id for v in values if v.metric_id not in METRICS]
    if unknown:
        raise KeyError(f"tool {name} emitted metrics not in the catalogue: {unknown}")
    return ToolResult(tool=name, location=ctx.location, scope=ctx.scope, year=ctx.year,
                      synthetic=t.synthetic, values=values)


def run_tools(question: str, stakeholder: str | None = None, limit: int = 4,
              auto_detect: bool = True) -> tuple[list[ToolResult], str | None]:
    """Resolve the perspective, pick the tools, run them. Returns (results, stakeholder)."""
    sid = stakeholder or (detect_stakeholder(question) if auto_detect else None)
    if sid is not None and sid not in STAKEHOLDERS:
        raise KeyError(f"unknown stakeholder {sid!r}; choose from {sorted(STAKEHOLDERS)}")
    ctx = build_context_for(question, sid)
    return [run_tool(name, ctx) for name in select_tools(question, sid, limit)], sid


def tool_hits(results: list[ToolResult], encode: Callable[[list[str]], np.ndarray]):
    """Wrap tool passages as retrieval hits carrying their own vectors.

    ``index`` is -1 because the passage is not in the index; the pipeline reads
    the vector from the hit instead.
    """
    from ..retrieve import Hit
    passages = [r.to_passage() for r in results]
    if not passages:
        return []
    vecs = encode([p.embed_text for p in passages])
    return [Hit(passage=p, index=-1, score=1.0, vector=np.asarray(vecs[i], dtype=np.float32))
            for i, p in enumerate(passages)]


def catalog() -> dict:
    """What the API advertises: stakeholders, tools and the metric catalogue."""
    return {
        "stakeholders": [
            {"id": s.id, "name": s.name, "description": s.description,
             "concerns": list(s.concerns), "tools": list(s.tools)}
            for s in STAKEHOLDERS.values()],
        "tools": [
            {"name": t.name, "description": t.description, "synthetic": t.synthetic}
            for t in TOOLS.values()],
        "metrics": [
            {"id": m.id, "name": m.name, "unit": m.unit, "definition": m.definition,
             "basis": m.basis, "stakeholders": list(m.stakeholders), "direction": m.direction}
            for m in METRICS.values()],
    }
