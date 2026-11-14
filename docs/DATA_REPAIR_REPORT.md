# Data repairs and handoff — 2026-11-14

Branch: `fix/remaining-data-issues`, based on `main` at `ceef885`. This work builds on the team's merged ingestion, historical sources and GIS aggregates. It does not claim those existing additions as new work, and it does not mark all six original gaps fully resolved.

## What changed and what remains

| Original issue | Changes in this branch | Remaining limits |
|---|---|---|
| 1. Unusable sources | Enforce source eligibility for chunks, document cards, GIS cards and summaries, even with quality filtering disabled. Re-ingestion removes stale chunks when a source becomes reference-only; failed retries preserve previously usable evidence. | COTA park-and-ride was already recovered on main. The original FHWA rail resource still fails; the demographics PDF and HIN interactive map remain reference-only; the unrelated NP-37 article remains excluded. No fabricated OCR or replacement article. |
| 2. Incorrect evaluation labels | Remove the quarantined HIN catalogue expectation; recognize the available local crash snapshot. Correct Q2's stale claim that Long Street history is absent. Separate ingested supplemental sources from aspirational sources. Mark the stakeholder before/after scenario as hypothetical. Corpus regression now checks retrievable sources, not mere catalogue membership. | Retrieval and model-answer scores must be rerun against the rebuilt index. Previous saved scores do not describe this branch. |
| 3. GIS records not loaded | Import the existing dated West Columbus research snapshot: **7,167 unique records**, including **1,802 corridor crashes**, plus **127 citable hotspot summaries**. Add a deterministic count API/CLI and the local HIN geometry. Preserve existing regional aggregate summaries. | This is selective loading, not ingestion of every GIS dataset. No exposure-adjusted rates, live feed, 2026 counts or statistically significant hotspot claims. New arbitrary spatial queries require further implementation/data. |
| 4. Unverified metadata | Audit all **38 original GIS entries**; repair five ODOT URLs; verify 24 layer identities/field schemas. Quarantine nine wrong Columbus layers and two unresolved HSIP endpoints. Separate two basemaps and one reference webpage from feature services. Audit **49 links across 24 documents**: retain 15 with explicit project identifiers; move 34 to `unverified_related_project_ids`. | Exact identifier occurrence verifies association, not current design, funding or schedule. Contextual links are not necessarily false; they need agency/project evidence before promotion. The added local snapshot is a 39th catalogue entry with its own dated provenance, not a newly live-verified service. |
| 5. Historical evidence | Add the local 2021–2025 record history and annual site counts. Refresh accessible registered sources; correct evaluation expectations for the existing FHWA Long Street case and existing historical safety reports. | The corpus still lacks matched project treatment/completion dates, exposure and comparison groups needed for causal before/after evaluation. Five-year counts alone do not demonstrate project effectiveness. |
| 6. Topic gaps | Add six usable chunks from COTA's reroute page with concrete construction/stop-access impacts. Verify and document already-ingested emergency guidance and first/last-mile evidence. | No local CAD/EMS response-time records, network-wide walk-access analysis, or measured construction delay/business-impact dataset. State policy and planned benefits must not be presented as observed local outcomes. |

Synthetic stakeholder metric tools are now **off by default** (`CBRAG_TOOLS_ENABLED=1` explicitly enables demo placeholders). They are not replacements for the real snapshot API. The API is callable separately; automatic free-form chatbot tool routing has not been added. The RAG retrieves the 127 prepared summaries after rebuilding its index.

## Specific evidence available to the chatbot

| Topic | Source and locator | What it supports |
|---|---|---|
| Local crash history | `west_columbus_crash_snapshot`; `data/local_crashes/hotspot_candidates.json`, stable site IDs | Dated counts, severity, annual frequency and radius sensitivity within the defined study area. Hilliard & Rome / Renner: 131 crashes in its 100-metre buffer, 0 fatal and 2 suspected-serious-injury crashes, 2021–2025. Overlapping buffers cannot be added. |
| Historical project case | `fhwa_columbus_community_connections_case_study`, web text segments 1–4 | Long Street Bridge/Cultural Wall and the I-71 division and reconnection of neighbourhoods. Qualitative history, not a crash-effect estimate. Already present on main. |
| Historical regional safety | `morpc_state_of_safety_2015_2019`, `morpc_state_of_safety_2017_2021`, `morpc_state_of_safety_2018_2022` | Regional historical reporting. These overlapping windows are not independent annual samples. Already present on main. |
| Emergency response | `ohio_quickclear_agreement`, web text segment 1; `ohio_trauma_report_2024`; `vision_zero_action_plan_2023_2028`, PDF page 17 | Incident-management roles, trauma reporting and emergency-preemption policy. No project-specific dispatch-time effects. Already present on main. |
| Transit first/last mile | `morpc_mtp_2024_2050_attachment_07`, PDF page 12; `linkus_overview`, web text segment 2; `morpc_tip_2026_2029_full`, PDF pages 485–497 | Named shuttle partnerships, mobility-hub plans and COTA connections. Planning descriptions are not current service guarantees or measured access scores. Already present on main. |
| Construction/access | **New** `cota_reroutes`, web text segments 1–6, retrieved November 14, 2026 | Specific notices about reroutes, stop closures and construction, including MLK Jr. Blvd./Mt. Vernon Ave. State notice dates when citing; check COTA again for current travel advice. |

The additional FHWA Long Street article, rail handbook, transit-access guide and Columbus I-70/I-71 page were attempted but did not yield usable extracted evidence. They remain explicitly marked candidates in `source_registry.json`, not answerable sources.

## Files for Ansh

- `data/document_chunks.jsonl` and `data/documents.json`: refreshed document evidence, new COTA construction material and audited project associations.
- `data/gis_sources.json` and `data/gis_schema_audit.json`: corrected endpoints, live field metadata and quarantine decisions. `schema_retrieved` alone does not certify identity; use the catalogue's `layer_identity_status` and `index_eligible`.
- `data/project_link_audit.json`: all 49 decisions, evidence excerpts, page/chunk locators and citations.
- `data/local_crashes/`: compressed records, site memberships, HIN geometry and scope/provenance notes. See `METHOD_AND_SQL.md` for included files and query commands.
- `data/derived/west_columbus_summary_chunks.jsonl`: 127 ready-to-index passages backed by the snapshot.
- `rag/tools/local_crashes.py`: standard-library count API/CLI; unsupported years/sites raise errors and rates remain null without denominators.
- `eval/questions.json`, `eval/stakeholder_questions.json`: current evaluation expectations and scenario status.
- `tests/test_data_repairs.py`: exclusion, label availability, association, snapshot, every-site count reconciliation and ingestion regression tests.

## Run after pulling

Use the project's normal environment and installed dependencies:

```sh
python -m pytest tests -m 'not index and not llm' -q
python -m rag.quality
python -m rag.regress --tier corpus
python -m rag.index
python -m rag.regress --tier retrieval
# With the configured LLM running:
python -m rag.regress --tier all
```

Restart the app after rebuilding the index. An existing index will not automatically gain the new data. Do not update evaluation baselines merely to suppress a failure; inspect changed labels, geography and retrieved evidence first.

## Validation performed

- Offline tests: **120 passed, 1 deselected** (index/model-dependent test excluded).
- Corpus regression: **passed** against the committed corpus baseline.
- Quality pass: **2,584 raw document chunks → 2,280 retained**; six new COTA chunks survive filtering.
- Snapshot: all 7,167 IDs unique; corridor counts reconcile to 1,802 total, 11 fatal and 29 suspected-serious-injury crashes. All 127 site totals/severity/annual counts reconcile with underlying record memberships.
- Live metadata: all 38 original entries checked; decisions and timestamps retained in the audit.
- BM25-only smoke checks: local crash, COTA construction and Long Street queries each retrieve their intended source in the top 10 (`eval/data_repair_sparse_smoke.json`).
- Dense retrieval/index rebuild and LLM answer evaluation were **not run** in this environment. No improved retrieval/answer score is claimed.

## Remaining collection work

1. Obtain correct Columbus infrastructure and HSIP service endpoints from their owners; compare the live layer identity and field domains before enabling them.
2. Confirm the 34 contextual associations against project-specific agency pages, maps or explicit crosswalks. Do not re-promote links based only on nearby place names.
3. Collect project completion/treatment dates, comparable pre/post crash windows, matched exposure and comparison sites. These are required for effect estimates.
4. Obtain appropriately aggregated EMS/dispatch timestamps, transit stop/path/GTFS inputs and dated construction closures/detours if those analyses are required. Published policy or notices do not substitute for measured impacts.
5. Replace/recover the failed FHWA resource and visually transcribe or OCR-check the demographics attachment before promoting them to answerable evidence.
