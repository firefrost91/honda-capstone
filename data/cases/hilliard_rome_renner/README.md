# Hilliard Rome / Renner: a focused planning demonstration

**Project:** PID 119852, Hilliard Rome Road at Renner Road intersection improvements, Columbus. This is a planning case around a proposed improvement, not a completed-project effectiveness study.

The case combines verified project documents, a dated crash history, nearby infrastructure, transit connections and a separate construction notice. It demonstrates what the system can establish, where sources disagree, and which conclusions would go beyond the evidence.

## What the evidence supports

- **Crash screening:** 131 ODOT crash records within the candidate site's 100-metre buffer during 2021–2025, including zero fatal crashes and two suspected-serious-injury crashes. Annual counts: 30, 27, 24, 23, 27. These are crashes, not numbers of injured people. September 25, 2026 snapshot; 75/150-metre counts are 117/150. Counts depend on the selected boundary.
- **Crash types:** 36 rear-end, 32 angle and 26 left-turn crashes are the largest recorded categories. These descriptions do not establish the causes of crashes or prescribe a particular design.
- **Network context:** the recovered catalogued HIN layer has a Hilliard-Rome line within 10 metres of the focus point. This corroborates geographic context; it does not establish the latest HIN version or independently reproduce the city's designation methodology.
- **Road conditions:** four 2025 roadway-inventory segments intersect the 100-metre buffer. They record two lanes on Renner and three on Hilliard & Rome, with speed-limit fields of 45. These are segment attributes, not verified counts of all approach/turning lanes or a field audit of today's signs.
- **Traffic volume:** nearby 2025 AADT records show 13,851 on two adjacent Renner segments and 48,624 on a Hilliard-Rome segment. The duplicated Renner count must not be added twice. These records do not provide five years of matched intersection exposure.
- **Crossings:** six crosswalk features intersect the 100-metre buffer; all six have null `ADACOMPLY`. Null means unknown, not unsafe, noncompliant or accessible. Feature counts are not a field-verified count of distinct complete crossings.
- **Transit/access:** COTA's May 4, 2026 route documents identify Renner Road Park & Ride on Lines 5 and 71. The November 14 snapshot of COTA reroutes includes a November 9 facility-improvement notice affecting that park-and-ride, expected to last 1–2 weeks. This is a separate facility activity, not evidence that PID 119852 construction has begun.

## Preserve differences between project sources

| Source | What it says | Correct use |
|---|---|---|
| MORPC 2026–2029 TIP, PDF page 202, generated April 22, 2025 | $9,163,541 total estimate; right-of-way $1,850,000 and construction $7,313,541 | A programmed estimate with the phases shown in that source. |
| City fact sheet, page 1; both original and newer URL retrieved | Design $2m, right-of-way $1.5m, utility relocations $350k, construction $8m; design finish late 2026 | Preserve phase labels; $8m is construction, not a total-project estimate. |
| Previously captured Engage Columbus page, updated August 31, 2026 | Design listed through summer 2028; construction late 2028–spring 2031, subject to approval/weather | Retain as a dated snapshot. The current refresh returned a JavaScript shell; no newly extracted current schedule. |

These differences are not proof of actual cost overruns, delays or completed work. They require scope/version reconciliation with the project owner. Do not silently average the amounts or select one schedule as certain.

## Demo questions and expected boundaries

1. **Why consider safety improvements here?** Combine the bounded crash history with the city project description and network context; do not call this the most dangerous intersection in Columbus.
2. **What changed from 2021 to 2025?** Report the annual counts and radius sensitivity. Do not call them an intervention effect.
3. **Can we calculate the crash rate using AADT?** Explain the available 2025 segment records and the missing matched multi-year/intersection exposure; do not divide five-year crashes by one year's AADT.
4. **How could transit users be affected?** Cite the route connections and the dated facility notice; explain that measured walk access, ridership effects and accessible detour conditions are not established.
5. **What does the project cost and when will it happen?** Keep TIP and city phase estimates/date versions distinct; distinguish planned dates from actuals.
6. **Are the crossings accessible?** Explain that the six inventory features have unknown ADA status; request a condition/accessibility survey rather than infer compliance.
7. **Did the project reduce crashes?** No supported conclusion: this packet does not establish a completed treatment or a valid after period/comparison group.

Machine-readable questions and source expectations are in `questions.json`. They are reference answers and evaluation boundaries, not observed LLM output.

## Files and reproduction

- `case.json`: computed counts, selected infrastructure attributes and explicit limitations.
- `crashes.jsonl`: the 131 member records, joined by stable crash ID to the original snapshot.
- `raw/`: four local GIS envelope queries, schemas, reconciled counts and request parameters; includes document download provenance. The full external PDFs are not committed.
- `map.geojson` / `map.png`: local evidence map; coordinates and projection documented. Points may overlap.
- `evidence.json`: source IDs, locators and direct URLs for the case statements.

```sh
python -m pip install -r requirements-demo.txt
python -m scripts.build_local_demo
python -m rag.tools.local_crashes --hotspot-id site_9998d539b0
```

The rebuild reads committed snapshots and does not refresh services. Distances use EPSG:26917; GeoJSON uses EPSG:4326. Live infrastructure was collected November 14, 2026; the crash snapshot is September 25, 2026. Combining them provides planning context, not proof that infrastructure attributes were identical throughout 2021–2025.

## Run the explicit case mode

```sh
python -m rag.index
python -m rag.case --case hilliard_rome_renner --evidence-only --question 'What do the crash counts show?'
python -m rag.case --case hilliard_rome_renner --question 'What do the TIP and city estimates actually cover?'
```

The second command needs only retrieval; the third uses the configured LLM. General regional searches can miss these project documents, so this mode selects the 12 audited evidence passages named in `evidence.json`. The small packet fits in context; source recall here is a completeness check, not a broad retrieval benchmark. Case reference questions and expected answers are not added to the index.
