"""Fatal-crash trends for Central Ohio from NHTSA's FARS CrashAPI.

The ArcGIS layers in ``gis_sources.json`` cover only a few recent years. The
Fatality Analysis Reporting System (FARS) is the national census of fatal
crashes, available through NHTSA's CrashAPI from 2010 onward, so it is the
source that can actually answer "how have fatalities changed over the past
5-10 years" for each county.

As with the GIS layers, no records are kept: each county-year is fetched,
counted (crashes, and deaths from the ``FATALS`` field) and turned into a
short, self-describing ``data_summary`` passage plus one trend passage per
county.

The response schema is not documented in a form that could be verified while
this was written, so parsing is defensive and fails loudly: rows are looked
for under ``Results`` (flattening nested lists), the year under ``CaseYear``
/ ``CASEYEAR`` / ``YEAR``, deaths under ``FATALS`` / ``Fatals``. A response in
which no row carries a deaths field is an error, never a guess.

    python -m rag.ingest --fars                  # 2014 -> latest available
    python -m rag.ingest --fars --dry-run
"""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from ..config import CONFIG, Config
from .fetch import USER_AGENT

API = "https://crashviewer.nhtsa.dot.gov/CrashAPI/crashes/GetCrashesByLocation"
SOURCE_ID = "nhtsa_fars"
OHIO_FIPS = 39

#: MORPC-region counties -> county FIPS code (within Ohio).
COUNTIES = {
    "Franklin": 49, "Delaware": 41, "Licking": 89, "Fairfield": 45,
    "Union": 159, "Madison": 97, "Pickaway": 129,
}

FIRST_YEAR = 2014
#: FARS publishes a year's final file roughly two years later.
LAST_YEAR = datetime.now(timezone.utc).year - 2

GetJSON = Callable[[str, dict], object]


def _http_json(url: str, params: dict) -> object:
    full = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(full, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _is_row(item) -> bool:
    return isinstance(item, dict) and any(k.upper() in ("ST_CASE", "FATALS") for k in item)


def _rows(payload) -> list[dict]:
    """Crash rows from a response, whatever list/dict nesting wraps them."""
    if isinstance(payload, dict):
        if _is_row(payload):
            return [payload]
        for key in ("Results", "results", "Data", "data"):
            if key in payload:
                return _rows(payload[key])
        return []
    if isinstance(payload, list):
        out: list[dict] = []
        for item in payload:
            out += _rows(item)
        return out
    return []


def _get(row: dict, *names):
    lower = {k.lower(): v for k, v in row.items()}
    for n in names:
        if n.lower() in lower and lower[n.lower()] not in (None, ""):
            return lower[n.lower()]
    return None


@dataclass
class CountySeries:
    county: str
    #: year -> (fatal crashes, deaths)
    years: dict[int, tuple[int, int]] = field(default_factory=dict)


def count_rows(rows: list[dict], default_year: int) -> dict[int, tuple[int, int]]:
    """Return {year: (fatal crashes, deaths)} for one county's rows."""
    if rows and not any(_get(r, "FATALS") is not None for r in rows):
        keys = sorted(rows[0])[:20]
        raise KeyError(f"no FATALS field in FARS rows; keys seen: {', '.join(keys)}")
    out: dict[int, list[int]] = {}
    for r in rows:
        y = _get(r, "CaseYear", "CASEYEAR", "YEAR")
        year = int(y) if y is not None else default_year
        acc = out.setdefault(year, [0, 0])
        acc[0] += 1
        acc[1] += int(_get(r, "FATALS") or 0)
    return {y: (c, d) for y, (c, d) in out.items()}


def fetch_county(county: str, fips: int, first: int, last: int,
                 get: GetJSON = _http_json) -> CountySeries:
    series = CountySeries(county)
    for year in range(first, last + 1):
        payload = get(API, {"fromCaseYear": year, "toCaseYear": year, "state": OHIO_FIPS,
                            "county": fips, "format": "json"})
        for y, v in count_rows(_rows(payload), year).items():
            c, d = series.years.get(y, (0, 0))
            series.years[y] = (c + v[0], d + v[1])
    return series


def render(series: list[CountySeries], computed_at: str) -> list[dict]:
    rows = []
    caveat = ("Counts computed from NHTSA FARS (fatal crashes only); individual crash "
              "records are not stored. Not normalised by population or traffic volume.")
    region: dict[int, list[int]] = {}
    for s in series:
        for y, (c, d) in s.years.items():
            acc = region.setdefault(y, [0, 0])
            acc[0] += c
            acc[1] += d
    groups = [(s.county + " County", s.years) for s in series]
    if len(series) > 1:
        groups.append(("Central Ohio (" + ", ".join(s.county for s in series) + " counties)",
                       {y: tuple(v) for y, v in region.items()}))
    for area, years in groups:
        if not years:
            continue
        ys = sorted(years)
        series_txt = "; ".join(f"{y}: {years[y][1]:,} deaths in {years[y][0]:,} fatal crashes"
                               for y in ys)
        first, last = years[ys[0]][1], years[ys[-1]][1]
        change = ""
        if first:
            pct = (last - first) / first * 100
            change = (f" Deaths went from {first:,} in {ys[0]} to {last:,} in {ys[-1]} "
                      f"({pct:+.0f}%).")
        slug = area.split(" (")[0].lower().replace(" ", "_")
        rows.append({
            "chunk_id": f"{SOURCE_ID}__agg__{slug}",
            "source_id": SOURCE_ID,
            "title": f"Fatal crashes by year - {area} (NHTSA FARS)",
            "text": (f"Fatal crash trend {ys[0]}-{ys[-1]} - {area}, from NHTSA's Fatality "
                     f"Analysis Reporting System (FARS). {series_txt}.{change} Computed on "
                     f"{computed_at} by counting FARS crash records per year via the CrashAPI."),
            "citation_url": "https://crashviewer.nhtsa.dot.gov/CrashAPI",
            "locator": f"FARS CrashAPI, Ohio, {area}, {ys[0]}-{ys[-1]}",
            "year": ys[-1],
            "area": area,
            "caveats": [caveat],
        })
    return rows


def run(first: int = FIRST_YEAR, last: int = LAST_YEAR, dry_run: bool = False,
        cfg: Config = CONFIG, get: GetJSON = _http_json,
        counties: dict[str, int] | None = None) -> int:
    from .gis_aggregates import _write
    counties = counties or COUNTIES
    series, failures = [], 0
    for name, fips in counties.items():
        print(f"  FARS {name:10s} {first}-{last} ", end="", flush=True)
        try:
            s = fetch_county(name, fips, first, last, get)
        except Exception as exc:
            failures += 1
            print(f"FAILED  {type(exc).__name__}: {exc}")
            continue
        series.append(s)
        total = sum(d for _, d in s.years.values())
        print(f"{total:5d} deaths over {len(s.years)} years")
    if not series:
        return 1
    rows = render(series, datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    if dry_run:
        print(f"\ndry run: {len(rows)} passages not written")
        return 0
    raw = {s.county: {str(y): {"fatal_crashes": c, "deaths": d} for y, (c, d) in sorted(s.years.items())}
           for s in series}
    path = _write(rows, SOURCE_ID, {"source": API, "state_fips": OHIO_FIPS, "counties": raw},
                  Path(cfg.derived_dir))
    print(f"\nwrote {len(rows)} passages to {path}; rebuild the index: python -m rag.index")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run())
