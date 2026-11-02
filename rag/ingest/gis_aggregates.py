"""Aggregate crash statistics from the ArcGIS layers in ``gis_sources.json``.

The knowledge base deliberately holds no GIS *records*, which means trend
questions ("how have crashes changed over five years") can only be answered
with whatever a planning PDF happened to print. This module closes that gap
without loading records: it asks each ArcGIS crash layer for **server-side
group-by counts** (``outStatistics``) and turns the result into short,
citable ``data_summary`` passages, each stating exactly which layer, which
grouping and which date produced it.

Field names in the catalogue are unverified (``field_schema_verified:
false``), so nothing is assumed:

1. the layer's metadata (``<layer>?f=json``) is read and fields are matched
   against the patterns in ``FIELD_PATTERNS`` - or taken from
   ``data/gis_field_map.json`` if a human has pinned them;
2. coded values (severity codes) are decoded only from the layer's own
   coded-value domains; undecoded codes are reported as codes, with a caveat;
3. a layer missing a severity field is skipped loudly, never guessed at.

    python -m rag.ingest --gis              # all crash layers
    python -m rag.ingest --gis --only odot_crash_2023
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from ..config import CONFIG, DATA_DIR, Config
from .fetch import USER_AGENT

#: Counties in the MORPC planning / Central Ohio area, as names and as ODOT's
#: three-letter county codes.
REGION_COUNTIES = {
    "FRANKLIN": "FRA", "DELAWARE": "DEL", "LICKING": "LIC", "FAIRFIELD": "FAI",
    "UNION": "UNI", "MADISON": "MAD", "PICKAWAY": "PIC", "KNOX": "KNO", "MARION": "MRN",
    "MORROW": "MRW",
}
_CODE_TO_NAME = {v: k for k, v in REGION_COUNTIES.items()}
STATEWIDE = "OHIO (statewide)"

#: Regexes over field *names* (case-insensitive), first match wins.
FIELD_PATTERNS = {
    "year": [r"^crash_?yr$", r"^crash_?year$", r"^year$", r"_yr$"],
    "severity": [r"severity", r"^crash_?sev", r"injury_?sev", r"^sev"],
    "county": [r"^county_?(name|nme|nm)?$", r"^cnty", r"county_?cd$", r"^county"],
    "pedestrian": [r"ped(estrian)?_?(ind|flag|invl|involved)?$", r"^ped"],
    "bicycle": [r"bi(cycle|ke)_?(ind|flag|invl|involved)?$", r"^bicy", r"^bike"],
}

FIELD_MAP_FILE = DATA_DIR / "gis_field_map.json"

GetJSON = Callable[[str, dict], dict]


def _http_json(url: str, params: dict) -> dict:
    full = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(full, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if isinstance(data, dict) and "error" in data:
        raise RuntimeError(f"ArcGIS error: {data['error']}")
    return data


@dataclass
class LayerFields:
    oid: str
    severity: str
    year: str | None = None
    county: str | None = None
    pedestrian: str | None = None
    bicycle: str | None = None
    domains: dict[str, dict] = field(default_factory=dict)   # field -> {code: label}


def resolve_fields(meta: dict, pinned: dict | None = None) -> LayerFields:
    """Map the layer's real field names onto the roles we group by."""
    fields = meta.get("fields") or []
    names = [f["name"] for f in fields]
    pinned = pinned or {}

    def find(role: str) -> str | None:
        if pinned.get(role):
            if pinned[role] not in names:
                raise KeyError(f"pinned field {pinned[role]!r} for {role} not in layer")
            return pinned[role]
        for pat in FIELD_PATTERNS[role]:
            for n in names:
                if re.search(pat, n, re.I):
                    return n
        return None

    oid = meta.get("objectIdField") or next(
        (f["name"] for f in fields if f.get("type") == "esriFieldTypeOID"), None)
    severity = find("severity")
    if not oid or not severity:
        raise KeyError(f"layer has no {'object-id' if not oid else 'severity'} field; "
                       f"fields are: {', '.join(names[:40])}. Pin one in {FIELD_MAP_FILE.name}.")
    domains = {}
    for f in fields:
        cv = (f.get("domain") or {}).get("codedValues")
        if cv:
            domains[f["name"]] = {str(c["code"]): c["name"] for c in cv}
    return LayerFields(oid=oid, severity=severity, year=find("year"), county=find("county"),
                       pedestrian=find("pedestrian"), bicycle=find("bicycle"), domains=domains)


def _stats_query(get: GetJSON, query_url: str, lf: LayerFields, group: list[str],
                 where: str = "1=1") -> list[dict]:
    params = {
        "where": where,
        "outStatistics": json.dumps([{"statisticType": "count", "onStatisticField": lf.oid,
                                      "outStatisticFieldName": "n"}]),
        "groupByFieldsForStatistics": ",".join(group),
        "f": "json",
    }
    data = get(query_url, params)
    return [feat.get("attributes", {}) for feat in data.get("features", [])]


def _truthy(v) -> bool:
    return str(v).strip().upper() in {"Y", "YES", "1", "TRUE", "T"}


def _county_key(v) -> str | None:
    s = str(v or "").strip().upper()
    s = re.sub(r"\s+COUNTY$", "", s)
    if s in REGION_COUNTIES:
        return s
    if s in _CODE_TO_NAME:
        return _CODE_TO_NAME[s]
    return None


def _label(lf: LayerFields, fname: str, code) -> str:
    return lf.domains.get(fname, {}).get(str(code), str(code))


def _layer_year(source: dict) -> int | None:
    m = re.search(r"(?<!\d)(20\d{2})(?!\d)", source.get("title", "") + source.get("source_url", ""))
    return int(m.group(1)) if m else None


@dataclass
class LayerSummary:
    source_id: str
    title: str
    source_url: str
    scope_label: str
    #: (area, year) -> severity label -> count
    counts: dict[tuple[str, int | None], dict[str, int]]
    #: (area, year) -> {"pedestrian": n, "bicycle": n}
    modes: dict[tuple[str, int | None], dict[str, int]]
    fields: LayerFields
    computed_at: str
    caveats: list[str]


def summarise_layer(source: dict, get: GetJSON = _http_json,
                    pinned: dict | None = None) -> LayerSummary:
    layer_url = source["source_url"]
    query_url = source.get("query_url") or layer_url.rstrip("/") + "/query"
    meta = get(layer_url, {"f": "json"})
    lf = resolve_fields(meta, pinned)
    fixed_year = _layer_year(source)
    caveats = [
        "Aggregate counts only, computed server-side; individual crash records are not "
        "loaded in this knowledge base.",
    ]
    if lf.severity not in lf.domains:
        caveats.append(f"Severity values are the layer's raw codes ({lf.severity}); no "
                       "coded-value domain was published to decode them.")

    group = [g for g in (lf.county, lf.year, lf.severity) if g]
    rows = _stats_query(get, query_url, lf, group)

    counts: dict[tuple[str, int | None], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for a in rows:
        n = int(a.get("n") or a.get("N") or 0)
        year = int(a[lf.year]) if lf.year and a.get(lf.year) not in (None, "") else fixed_year
        sev = _label(lf, lf.severity, a.get(lf.severity))
        if lf.county:
            counts[(STATEWIDE, year)][sev] += n
            area = _county_key(a.get(lf.county))
            if area is not None:
                counts[(area, year)][sev] += n
        else:
            counts[("ALL", year)][sev] += n

    modes: dict[tuple[str, int | None], dict[str, int]] = defaultdict(dict)
    for mode in ("pedestrian", "bicycle"):
        fname = getattr(lf, mode)
        if not fname:
            continue
        g = [x for x in (lf.county, lf.year, fname) if x]
        try:
            mrows = _stats_query(get, query_url, lf, g)
        except Exception as exc:
            caveats.append(f"{mode} breakdown unavailable: {exc}")
            continue
        for a in mrows:
            if not _truthy(a.get(fname)):
                continue
            area = _county_key(a.get(lf.county)) if lf.county else "ALL"
            if area is None:
                continue
            year = int(a[lf.year]) if lf.year and a.get(lf.year) not in (None, "") else fixed_year
            modes[(area, year)][mode] = modes[(area, year)].get(mode, 0) + int(a.get("n") or 0)

    scope = ("Central Ohio counties (MORPC region) with an Ohio statewide total for context"
             if lf.county else source.get("organization", "") + " service area")
    return LayerSummary(source["source_id"], source.get("title", source["source_id"]),
                        layer_url, scope, {k: dict(v) for k, v in counts.items()},
                        {k: v for k, v in modes.items()}, lf,
                        datetime.now(timezone.utc).strftime("%Y-%m-%d"), caveats)


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def _area_name(area: str, s: LayerSummary) -> str:
    if area == "ALL":
        return "City of Columbus crash layer (all records)" if "columbus" in s.source_id \
            else "all records in the layer"
    if area.startswith("OHIO"):
        return "Ohio statewide (all counties; NOT a Central Ohio figure)"
    return f"{area.title()} County"


def _severity_text(sev: dict[str, int]) -> str:
    total = sum(sev.values())
    parts = ", ".join(f"{label}: {n:,}" for label, n in
                      sorted(sev.items(), key=lambda kv: -kv[1]))
    return f"{total:,} crashes ({parts})"


def render_chunks(s: LayerSummary) -> list[dict]:
    """One passage per (area, year), each self-describing its provenance."""
    rows = []
    for (area, year), sev in sorted(s.counts.items(), key=lambda kv: (kv[0][1] or 0, kv[0][0])):
        mode = s.modes.get((area, year), {})
        mode_txt = ""
        if mode:
            mode_txt = " Involving a pedestrian: " + f"{mode.get('pedestrian', 0):,}" \
                       + "; involving a bicyclist: " + f"{mode.get('bicycle', 0):,}" + "."
        yr = f"in {year}" if year else "(all years in the layer)"
        text = (f"Aggregate crash summary - {_area_name(area, s)} {yr}: "
                f"{_severity_text(sev)}.{mode_txt} "
                f"Computed on {s.computed_at} by counting records in the ArcGIS layer "
                f"'{s.title}' grouped by "
                f"{', '.join(x for x in (s.fields.county, s.fields.year, s.fields.severity) if x)}. "
                f"Source: {s.source_url}")
        slug = re.sub(r"[^a-z0-9]+", "_", area.lower()).strip("_")[:24]
        rows.append({
            "chunk_id": f"{s.source_id}__agg__{slug}__{year or 'all'}",
            "source_id": s.source_id,
            "title": f"{s.title} - aggregate summary",
            "text": text,
            "citation_url": s.source_url,
            "locator": f"aggregate query: {_area_name(area, s)}, {year or 'all years'}",
            "year": year,
            "area": area,
            "caveats": s.caveats,
        })
    return rows


def render_trend_chunks(summaries: list[LayerSummary]) -> list[dict]:
    """Cross-layer year-over-year series per area - the passage trend questions need."""
    series: dict[str, dict[int, dict[str, int]]] = defaultdict(dict)
    origin: dict[str, set[str]] = defaultdict(set)
    for s in summaries:
        for (area, year), sev in s.counts.items():
            if year is None:
                continue
            key = _area_name(area, s)
            if year in series[key]:      # same area-year from two layers: keep the first
                continue
            series[key][year] = sev
            origin[key].add(s.title)
    rows = []
    for area, by_year in sorted(series.items()):
        if len(by_year) < 2:
            continue
        lines = []
        for y in sorted(by_year):
            sev = by_year[y]
            fatal = sum(n for k, n in sev.items() if re.search(r"fatal|killed|\bk\b", k, re.I))
            serious = sum(n for k, n in sev.items()
                          if re.search(r"serious|incapacitat|suspected serious|\ba\b", k, re.I))
            extra = []
            if fatal:
                extra.append(f"{fatal:,} fatal")
            if serious:
                extra.append(f"{serious:,} serious injury")
            lines.append(f"{y}: {sum(sev.values()):,} crashes"
                         + (f" ({', '.join(extra)})" if extra else ""))
        years = sorted(by_year)
        text = (f"Crash trend {years[0]}-{years[-1]} - {area}, from aggregate counts of "
                f"{'; '.join(sorted(origin[area]))}. " + ". ".join(lines) + ". "
                "Year-to-year differences may partly reflect changes in reporting; the "
                "layers do not normalise by traffic volume (VMT) or population.")
        slug = re.sub(r"[^a-z0-9]+", "_", area.lower()).strip("_")[:32]
        rows.append({
            "chunk_id": f"crash_trends__agg__{slug}",
            "source_id": "crash_trends_aggregate",
            "title": f"Crash trend by year - {area} (aggregate)",
            "text": text,
            "citation_url": "",
            "locator": f"aggregate across {len(origin[area])} crash layer(s)",
            "year": years[-1],
            "area": area,
            "caveats": ["Derived from aggregate counts; not normalised by exposure."],
        })
    return rows


def _write(rows: list[dict], name: str, raw: dict | None, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}_summary_chunks.jsonl"
    with path.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    if raw is not None:
        (out_dir / f"{name}_summary.json").write_text(json.dumps(raw, indent=2))
    return path


def _raw(s: LayerSummary) -> dict:
    return {
        "source_id": s.source_id, "title": s.title, "source_url": s.source_url,
        "computed_at": s.computed_at, "scope": s.scope_label, "caveats": s.caveats,
        "fields": {k: v for k, v in s.fields.__dict__.items() if k != "domains"},
        "counts": [{"area": a, "year": y, "by_severity": sev} for (a, y), sev in s.counts.items()],
        "modes": [{"area": a, "year": y, **m} for (a, y), m in s.modes.items()],
    }


def crash_layers(cfg: Config = CONFIG) -> list[dict]:
    gis = json.loads(Path(cfg.gis_file).read_text())["sources"]
    return [s for s in gis if s.get("access_type") == "arcgis_layer"
            and (s.get("theme") == "crashes" or s.get("data_type") == "crash_records"
                 or "crash" in s.get("title", "").lower())]


def run(only: list[str] | None = None, dry_run: bool = False, cfg: Config = CONFIG,
        get: GetJSON = _http_json) -> int:
    pinned_all = json.loads(FIELD_MAP_FILE.read_text()) if FIELD_MAP_FILE.exists() else {}
    layers = [s for s in crash_layers(cfg) if not only or s["source_id"] in only]
    if not layers:
        print("no crash layers selected")
        return 1
    out_dir = Path(cfg.derived_dir)
    summaries, failures = [], 0
    for src in layers:
        print(f"  {src['source_id']:32s} ", end="", flush=True)
        try:
            s = summarise_layer(src, get, pinned_all.get(src["source_id"]))
        except Exception as exc:
            failures += 1
            print(f"FAILED  {type(exc).__name__}: {exc}")
            continue
        rows = render_chunks(s)
        summaries.append(s)
        print(f"{len(rows):3d} summary passages  (severity={s.fields.severity}, "
              f"year={s.fields.year}, county={s.fields.county})")
        if not dry_run:
            _write(rows, s.source_id, _raw(s), out_dir)
    trend = render_trend_chunks(summaries)
    if trend and not dry_run:
        _write(trend, "crash_trends", None, out_dir)
        print(f"  {'crash_trends':32s} {len(trend):3d} trend passages")
    if not dry_run and summaries:
        print(f"\nwrote {out_dir}; rebuild the index: python -m rag.index")
    return 1 if failures and not summaries else 0


if __name__ == "__main__":
    sys.exit(run())
