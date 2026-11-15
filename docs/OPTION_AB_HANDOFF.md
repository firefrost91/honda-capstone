# Current handoff: Option A reliability work and Option B local demonstration

Work date: November 14, 2026. Branch: `fix/reliability-and-local-demo`, extending `fix/remaining-data-issues`. This is the current summary; the earlier `DATA_REPAIR_REPORT.md` describes the previous stage.

## Option A delivered

- Recovered the RTMC image-only demographics appendix: 104 visually checked values, four citable data pages, and explicit limits on dates, sampling and interpretation.
- Recovered the map's exact HIN feature service: 509 features, reconciled to service and unique-ID counts, with raw geometry and metadata.
- Replaced missing rail-resource coverage with selected pages of the official FHWA/FRA handbook from the USDOT repository. The blocked original directory remains excluded; 2019 guidance is not represented as current law.
- Added the correct Hilliard capital-plan source for NP-37 and preserved the exclusion of the unrelated construction article.
- Reviewed the remaining project links. Three additional original associations are supported by an authoritative crosswalk; 31 remain context-only, not project proof. Including the new NP-37 source, the audit has 19 verified and 31 context-only associations.
- Prevented registry refreshes from reinstating rejected/contextual links and retained previously usable text when official pages returned JavaScript shells.
- Rebuilt the index and ran corpus, source-retrieval and model-answer checks. Existing baselines were not reset to hide failures. The original ten-question answer run uses the frozen Option A index and the pre-Option-B prompt renderer.

Details: [source review](OPTION_A_SOURCE_REVIEW.md), [association audit](../data/project_link_audit.json), [structured demographics](../data/curated/rtmc_demographics.json), [HIN manifest](../data/local_hin/manifest.json).

## Option B delivered

The case is **Hilliard Rome Road / Renner Road, PID 119852**. It is a planning demonstration around a proposed project, not an effectiveness study of a completed treatment.

The packet joins:

- 131 crash records from 2021–2025 within the 100-metre screening buffer; 0 fatal and 2 suspected-serious-injury crashes.
- Project scope, phase estimates and dated schedule differences from the city and MORPC TIP.
- Local subsets of traffic volumes (29 candidate features), speed zones (42), roadway inventory (178) and crosswalks (124), with schemas, query parameters and count reconciliation. The case separately computes the features actually within 100 metres.
- HIN geometry, COTA Lines 5/71 route maps and the dated Renner Park & Ride facility-improvement notice.
- A reproducible map, structured evidence, reference-answer boundaries, seven demo questions and an explicit case-scoped search mode.

The full packet is [here](../data/cases/hilliard_rome_renner/README.md). Its [map](../data/cases/hilliard_rome_renner/map.png) is descriptive; points can overlap.

## How Ansh can use it now

From a checkout of this branch, with the usual environment installed:

```sh
python -m rag.index
python -m rag.case --case hilliard_rome_renner --evidence-only \
  --question 'What are the crash counts and evidence limits at Hilliard Rome and Renner?'
# With a working configured language-model backend:
python -m rag.case --case hilliard_rome_renner \
  --question 'Can we calculate a five-year crash rate using the available AADT?'
```

For application integration, use `rag.case.case_index('hilliard_rome_renner')` with `RAGPipeline` and `rag.case.case_config()`. This mode is explicit: the general chat endpoint has not been silently switched to this case. The case manifest selects evidence by audited source and passage IDs, never by the evaluation answer or expected-source list. Reference questions/answers are not indexed.

Case passages have a larger excerpt allowance to retain phase/cost detail. Source scope and caveats now reach the prompt even when body text is shortened. GIS catalogue headers describe metadata instead of incorrectly saying every dataset lacks records. Synthetic metric tools remain off.

To rebuild the spatial case only:

```sh
python -m pip install -r requirements-demo.txt
python -m scripts.build_local_demo
```

To repeat validation:

```sh
python -m pytest tests -q
python -m scripts.evaluate_data_repair --stage rerun --answers
python -m scripts.evaluate_local_demo --answers
```

The full evaluation script returns non-zero for gate failures and writes the findings without changing baselines. Do not treat a completed run as a passing run.

## Validation and remaining failures

| Check | Result |
| --- | --- |
| Corpus checks, Options A and B | Passed |
| Full test suite | 128 passed; 1 failed (existing real-index retrieval regression gate) |
| General expected-source recall | Baseline 0.750; Option A 0.667; final Option B 0.633 |
| Option A full model evaluation | All 10 answers generated; automated answer gate fails Q5 for missing required HIN/speed coverage |
| Final prompt/data/tool targeted checks | 33 passed after removing stale gap examples |
| Explicit case evidence retrieval | Expected sources present for all 7 questions; packet-completeness check only |
| Targeted case answers | Both generated; both fail manual factual review |

Generation used Qwen2.5-3B-Instruct Q4_K_M through a CPU-only llama-cpp-python backend because Metal/MLX was unavailable. This differs from the baseline backend/quantization, so it is not a controlled model-performance comparison. Evaluation outputs are retained in `eval/option_a` and `eval/option_b`.

Manual review also found unsupported causal claims in general Q10. The targeted case rate answer correctly declines to compute a five-year rate, but falsely says post-2023 crash records are absent while citing the 2021–2025 snapshot. The targeted cost answer misattributes city figures to the TIP and invents/miscompares amounts. These are failed answers, not acceptable demonstrations. See `eval/option_b/manual_review.json`.

After reviewing these outputs, the hard-coded gap examples were removed from the prompt (retained only for filtering legacy copied text). A regression test checks they are not injected. The saved model outputs predate this last prompt correction; its effect on generated answers is not yet measured. Next engineering priorities are to improve retrieval of the expected regional sources, and validate numerical and causal claims against source-specific evidence before presenting generated answers. Until then, use the evidence-only case mode and the reviewed case README for demonstrations.

The general retrieval failure is narrower than “the data is missing”: the expected Vision Zero sources still exist, but broad multi-query retrieval prefers other planning sources on some questions. The added local data also competes with expected crash sources on the general data-combination question. Correcting this requires retrieval/rubric review, not deleting useful data or marking excluded documents as available.

The case-specific source-recall result is a **packet completeness check**, not a general retrieval benchmark: the audited packet contains only 12 passages and fits in the configured context window. It shows that the relevant local evidence stays available for this explicit case. It does not prove the model interprets all evidence correctly.

Automatic “groundedness” is a semantic-similarity score, not proof of factual correctness. Manual inspection of Option A Q4 found an unsupported assertion that planned TIP projects had actually taken longer or cost more, despite a high score. The corpus does not establish those actual outcomes. Treat that answer as a failure of evidence interpretation; do not use it as historical evidence. Full answers, citations and warnings are retained for review.

## What is still not resolved

- Thirty-one source/project associations are contextual; additional project-specific confirmation is required to promote them.
- Eleven original GIS entries remain quarantined for mismatched/unresolved endpoints. Loading focused subsets does not mean all GIS datasets are now ingested.
- The original blocked rail page and map remain excluded/reference-only, with explicit replacement sources; the 2025 NP-37 plan is historical, not a verified current schedule.
- No causal before/after project-effect estimate, matched multi-year intersection exposure, local EMS response-time series, measured transit-access outcomes or quantified construction impacts has been created.
- A null ADA field is unknown; repeated AADT segments cannot be summed; a planned construction date is not proof of completed work.
- The full ten-question answer evaluation reflects Option A's frozen index/prompt. Option B has its own retrieval checks and two targeted answer checks; the final general chatbot has not received a second full ten-question generation run.

This is a usable data handoff and a bounded local demonstration. It is not a claim that every original issue, every answer-quality problem, or every agency-data dependency has disappeared.
