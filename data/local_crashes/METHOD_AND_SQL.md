# West Columbus crash snapshot: scope and reproduction

This is a **September 25, 2026 snapshot**, not a live feed. Annual ODOT layers cover 2021–2025. Study bounding box: longitude/latitude `[-83.205, 39.972, -83.06, 40.045]`. It contains 7,167 unique crash IDs; 1,802 are in selected 150-metre corridor buffers, excluding freeway records under the original selection rule. Forty corridor records have unknown functional class. See `analysis_summary.json`, `sources.json` and `validation.json`.

## Included files and usable queries

- `crash_records.jsonl.gz`: cleaned crash records with stable ODOT document numbers, source URLs, coordinates and corridor flags.
- `hotspot_candidates.json`: 127 candidate centres, 100-metre counts and explicit crash-ID memberships, including 75/150-metre sensitivity counts. Buffers overlap; **never sum site totals**.
- `project_focus_sites.json`: candidate project-site context; not proof of a project's effect.
- `high_injury_network.geojson`: 13 HIN features clipped/selected in this study area, not the entire city network.
- `analysis_summary.json`, `sources.json`, `validation.json`: original dated processing/provenance results. Fields referencing city downloads describe the original research package, not a separately shipped city census here.

From the repository root, use Python's standard library only:

```sh
python -m rag.tools.local_crashes
python -m rag.tools.local_crashes --year 2025
python -m rag.tools.local_crashes --all-study-records
python -m rag.tools.local_crashes --hotspot-id site_9998d539b0
```

The API recomputes counts from records/membership rather than trusting summary totals. `tests/test_data_repairs.py` reconciles all 127 sites against their constituent records. It does not re-estimate the spatial memberships. The full original raw-download/reprojection package and SQLite database are not shipped in this repository.

## Collection and interpretation

Original queries appended `/query` to each annual layer, using `where=1=1`, `geometry=-83.205,39.972,-83.06,40.045`, `geometryType=esriGeometryEnvelope`, `inSR=4326`, `spatialRel=esriSpatialRelIntersects`, and `returnIdsOnly=true`. Sorted IDs were fetched in batches of 500 with `outFields=*`, `returnGeometry=true`, `outSR=4326`. Original downloaded-ID reconciliation is reported in `validation.json`. Source URLs are retained per record. A new query today may return different records.

Output coordinates are EPSG:4326 longitude then latitude; original distance calculations used EPSG:26917 metres. `nearest_corridor` is a spatial label, not a verified collision-road name. Severity codes: 1 fatal, 2 suspected serious injury, 3 suspected minor injury, 4 possible injury, 5 property damage/no injury. Counts describe **crashes, not injured people**. Null enrichment means missing/unmatched, not zero. Pedestrian/bicycle crash-type categories do not identify every possible involved unit.

These are descriptive frequency candidates, not exposure-adjusted risk ranks, statistically significant clusters, or causal before/after project evaluations. No matched traffic/pedestrian exposure denominator is available; the API returns `rate: null`. No 2026 crash counts are supported. Record completeness is limited to the public snapshot.
