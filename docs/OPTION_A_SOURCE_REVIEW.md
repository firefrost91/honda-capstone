# Option A: source recovery and association review

Reviewed November 14, 2026. This extends `fix/remaining-data-issues`; it does not retroactively change the previous audit report.

## Original five unusable sources

| Original source | Disposition |
|---|---|
| COTA park-and-ride PDF | Already recovered on the team's main branch; retained as a dated 2024 source. |
| RTMC Appendix B demographics | Visually reviewed all five PDF pages. Transcribed all 104 percentages on the four data pages into `data/curated/rtmc_demographics.json` and generated citable page-level prose. No unsupported sample dates, sizes or citywide population interpretations. |
| HIN interactive map | Recovered the exact FeatureServer URL referenced by the map definition. Loaded 509 line features; service count and unique OBJECTID totals reconcile. Stored geometry, metadata and query manifest in `data/local_hin/`. Original map remains a reference; its replacement carries the data. Crash-attribute periods/weighting remain unknown. |
| FHWA rail resource page | Direct FHWA/FRA fetches still returned HTTP 403. Recovered the official 2019 handbook from USDOT's National Transportation Library. Indexed selected background and assessment-input pages under a new source ID. This replaces topic coverage, not the original resource page, and is not current regulatory advice. |
| Unrelated NP-37 construction article | Remains excluded. Added the correct City of Hilliard 2025 capital-plan project description and budget (T-156), cross-checked against MORPC TIP NP-37, PDF page 293. The newer 2026 city plan downloaded but is image-based and has not been transcribed; do not present the 2025 schedule as current status. |

## Association decisions

The original audit covered 49 associations across 24 documents, not 24 individual associations.

- Fifteen original associations remain verified by explicit identifiers.
- Three additional associations are supported by an authoritative crosswalk: the Hilliard Rome/Renner project page matches the PID 119852 fact sheet; the two Trabue bridge sources connect to PID 120346 through the TIP's explicit statement that preliminary engineering is included with PID 105498. The two PIDs are related, not interchangeable.
- Thirty-one original associations remain **context only, not project proof**. They are retained separately in `context_project_ids`, not silently promoted. A corridor study or statewide policy can be useful without establishing a specific project's funding, design or status. Agency confirmation would be needed to promote these.
- The new Hilliard capital-plan source adds one verified NP-37 association. Current audit total: 50 associations, 19 verified and 31 context-only.

Each decision preserves source/page excerpts in `data/project_link_audit.json`. Chunk-level IDs now match audited catalogue IDs. Registry refreshes cannot silently restore contextual associations as verified ones.

## Evaluation procedure

The existing ten questions retain their expected-source gates. Added `answerability_limit` documents where a bounded answer or missing-evidence finding is appropriate before running the evaluation. Baselines are compared, not reset to make new results pass.

```sh
python -m rag.index
python -m scripts.evaluate_data_repair --stage option_a --answers
```

Results are written incrementally to `eval/option_a/`, including full answers, source citations, warnings, retrieval results, model/configuration and the index fingerprint. Gate failures remain visible. The later demonstration has a separate evaluation snapshot so its additions cannot be confused with Option A's results.

Two official Engage Columbus pages returned JavaScript shells during the refresh attempt. Validation caught that they supplied no usable text. Their previously successful dated text snapshots were retained, with the failed refresh recorded; their content is not represented as newly verified current schedules.
