# Honda Safety RAG: stakeholder evaluation report

Run 2026-11-09 · commit `13d271a` · mlx-community/Qwen2.5-3B-Instruct-4bit (mlx) · embeddings BAAI/bge-small-en-v1.5 · 2,372 passages · top-14 context

**34 questions**: 24 stakeholder-specific (Layer 1), 8 shared-scenario (Layer 2), 2 add-ons. 56% of questions clear every per-question check (see *Per-question verdicts*). Mean latency 1023.332s.

## 1. Scorecard: the RAG triad

Targets were set before the run (see `TARGETS` in `rag/evaluate_stakeholders.py`). Brackets are 95% bootstrap intervals over questions; with this few questions they are wide, so differences under ~0.1 are not meaningful.

| Leg | Metric | Mean [95% CI] | Target | Status |
|---|---|---|---|---|
| Retrieval | Source recall@k | 0.20 [0.14, 0.27] | ≥ 0.50 | BELOW TARGET |
| Retrieval | Hit rate (any expected source) | 0.59 [0.41, 0.74] | ≥ 0.90 | BELOW TARGET |
| Retrieval | MRR (first expected source) | 0.10 [0.07, 0.12] | - |  |
| Retrieval | Source precision (share of passages from expected sources) | 0.11 [0.07, 0.15] | - |  |
| Retrieval | Keyword context recall | 0.80 [0.75, 0.85] | - |  |
| Generation | Groundedness (sentence-level attribution) | 1.00 [0.99, 1.00] | ≥ 0.85 | PASS |
| Generation | Answers free of detected invented / mis-scoped figures | 88% | 100% | BELOW TARGET |
| Answer | Answer relevancy, raw cosine (sanity check only; saturated) | 0.84 [0.83, 0.85] | - |  |
| Answer | Relevancy margin (own question minus other questions) | 0.10 [0.08, 0.11] | ≥ 0.02 | PASS |
| Answer | Probe coverage (expected topics mentioned) | 0.77 [0.69, 0.84] | ≥ 0.50 | PASS |
| Answer | Locality (local proper nouns per answer) | 4.09 [3.15, 5.06] | - |  |
| Honesty | Answers with an evidence-gap section | 100% | ≥ 95% | PASS |

## 2. Breakdown by layer and stakeholder

| Group | n | Src recall | Hit | Grounded | Relevancy | Probes | Locality | No hard flags | Latency s |
|---|---|---|---|---|---|---|---|---|---|
| Layer 1: stakeholder-specific | 24 | 0.255 | 0.708 | 0.996 | 0.834 | 0.683 | 5.458 | 83% | 1178.3 |
| Layer 2: shared scenario | 8 | 0.094 | 0.375 | 0.994 | 0.857 | 1.0 | 0.375 | 100% | 542.288 |
| Layer 2: add-ons | 2 | 0.0 | 0.0 | 1.0 | 0.861 | 0.857 | 2.5 | 100% | 1087.9 |

**Layer 1 by stakeholder**

| Group | n | Src recall | Hit | Grounded | Relevancy | Probes | Locality | No hard flags | Latency s |
|---|---|---|---|---|---|---|---|---|---|
| State / Regional Transportation Agencies | 3 | 0.167 | 0.667 | 1.0 | 0.808 | 0.619 | 7.333 | 100% | 144.433 |
| Local Government / Public Works | 3 | 0.278 | 0.667 | 1.0 | 0.843 | 0.524 | 4.0 | 100% | 118.867 |
| Emergency Responders / Healthcare Providers | 3 | 0.0 | 0.0 | 0.985 | 0.845 | 0.706 | 5.667 | 33% | 136.9 |
| Public Transit / Mobility Providers | 3 | 0.417 | 1.0 | 1.0 | 0.839 | 0.809 | 6.667 | 100% | 8618.9 |
| Nearby Residents / Local Communities | 3 | 0.372 | 1.0 | 1.0 | 0.84 | 0.714 | 5.333 | 100% | 107.967 |
| Drivers / Daily Commuters | 3 | 0.167 | 0.667 | 1.0 | 0.845 | 0.714 | 6.333 | 67% | 87.833 |
| Pedestrians / Cyclists / Vulnerable Road Users | 3 | 0.194 | 0.667 | 0.981 | 0.819 | 0.762 | 3.667 | 100% | 101.667 |
| Freight / Rail Operators | 3 | 0.444 | 1.0 | 1.0 | 0.829 | 0.619 | 4.667 | 67% | 109.833 |

**Layer 1 by theme** (each stakeholder's three questions probe different concerns)

| # | Stakeholder | Theme | Src recall | Grounded | Relevancy | Probes | Locality | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | State | Prioritization | 0.25 | 100% | 0.79 | 1.00 | 9 | OK |
| 2 | State | Local Context & Decision Making | 0.25 | 100% | 0.80 | 0.00 | 8 | OK |
| 3 | State | Historical Precedents, Risks & Trade-offs | 0.00 | 100% | 0.83 | 0.86 | 5 | CHECK |
| 4 | Local Government | Implementation Feasibility / Infrastructure Conditions | 0.33 | 100% | 0.83 | 0.43 | 4 | OK |
| 5 | Local Government | Maintenance / Long-term Sustainability | 0.50 | 100% | 0.83 | 0.43 | 5 | OK |
| 6 | Local Government | Future Demand / Long-term Safety Performance | 0.00 | 100% | 0.87 | 0.71 | 3 | CHECK |
| 7 | Emergency Responders | Emergency Access / Response Time | 0.00 | 100% | 0.85 | 0.57 | 4 | CHECK |
| 8 | Emergency Responders | Safety Improvements vs. Emergency Operations | 0.00 | 96% | 0.83 | 0.83 | 7 | CHECK |
| 9 | Emergency Responders | Crash Severity / Post-Crash Response | 0.00 | 100% | 0.86 | 0.71 | 6 | CHECK |
| 10 | Public Transit | First / Last-Mile Safety & Access | 0.25 | 100% | 0.83 | 0.71 | 6 | OK |
| 11 | Public Transit | Value of Supporting Safety Projects | 0.50 | 100% | 0.82 | 0.86 | 11 | OK |
| 12 | Public Transit | Network Connectivity / Future Mobility Needs | 0.50 | 100% | 0.86 | 0.86 | 3 | OK |
| 13 | Nearby Residents | Safety & Quality of Life Near Homes | 0.20 | 100% | 0.91 | 0.71 | 9 | OK |
| 14 | Nearby Residents | Cut-Through Traffic & Neighborhood Impacts | 0.67 | 100% | 0.78 | 0.86 | 2 | OK |
| 15 | Nearby Residents | Construction Impacts & Community Engagement | 0.25 | 100% | 0.84 | 0.57 | 5 | OK |
| 16 | Drivers | Crash Risk & Traffic Conflicts | 0.25 | 100% | 0.80 | 0.57 | 6 | OK |
| 17 | Drivers | Delay, Queues & Travel-Time Reliability | 0.25 | 100% | 0.87 | 0.71 | 8 | OK |
| 18 | Drivers | Roadway Design Clarity & Driver Behavior | 0.00 | 100% | 0.86 | 0.86 | 5 | CHECK |
| 19 | Pedestrians | Crossing Safety & Visibility | 0.25 | 100% | 0.85 | 0.71 | 4 | OK |
| 20 | Pedestrians | Sidewalk / Path Continuity & Accessibility | 0.00 | 94% | 0.77 | 0.86 | 2 | CHECK |
| 21 | Pedestrians | Separation from Vehicles & Comfort | 0.33 | 100% | 0.84 | 0.71 | 5 | OK |
| 22 | Freight | Truck Interactions & Freight Routes | 0.67 | 100% | 0.75 | 0.57 | 4 | OK |
| 23 | Freight | Rail Crossing Safety & Conflict Risk | 0.33 | 100% | 0.83 | 0.71 | 4 | CHECK |
| 24 | Freight | Freight Access & Operational Impact | 0.33 | 100% | 0.91 | 0.57 | 6 | OK |

## 3. Retrieval ablation

Same questions, retrieval only, top-14 passages. Shows which pipeline stage earns its place. `hybrid_rules` is the full pipeline without the LLM query planner.

| Retriever | Source recall | Hit | MRR | Source precision | Keyword ctx recall |
|---|---|---|---|---|---|
| dense_only | 0.181 | 0.559 | 0.363 | 0.179 | 0.634 |
| bm25_only | 0.27 | 0.647 | 0.486 | 0.17 | 0.715 |
| hybrid_rules | 0.222 | 0.706 | 0.156 | 0.097 | 0.679 |
| hybrid_llm_planner | 0.202 | 0.588 | 0.095 | 0.111 | 0.805 |

Caveat: dense-only and BM25-only return the raw top-k with no per-document cap or MMR, so they can be dominated by one long document. Source precision is therefore not directly comparable across rows; recall and hit are.

## 5. Layer 2: same scenario, different stakeholders

Scenario: *A safety improvement project at a Columbus intersection has reduced crashes from 8 to 2 per year. However, the two remaining crashes involved serious injuries. Traffic delay has improved, but pedestrian concerns remain.*

The test is not whether any one answer is good but whether the system reads the *same* evidence through *different* stakeholder lenses.

- **Perspective alignment: 75%** of the 8 answers use their own stakeholder's vocabulary more than any other stakeholder's (a reader could tell whose answer it is). Mean lift +4.57 own-terms over other stakeholders' terms.
- **Answer similarity: 0.91** mean pairwise embedding cosine across the eight answers. Higher means the answers are interchangeable; see the interpretation note below.
- **Shared evidence: 0.28** mean pairwise Jaccard overlap of retrieved documents. High overlap is expected and desirable here (same evidence), but it also means perspective differences come from generation, not retrieval.

| Stakeholder | Own terms | Others (mean) | Lift | Own rank first | Restates 8→2 | Own terms used |
|---|---|---|---|---|---|---|
| State / Regional Transportation Agencies | 6 | 0.43 | 5.57 | yes | yes | crash reduction, fatal, prioriti, regional, serious injur, target |
| Local Government / Public Works | 3 | 1.86 | 1.14 | no | yes | infrastructure condition, maintenance, operations |
| Nearby Residents / Local Communities | 5 | 1.43 | 3.57 | yes | yes | cut-through, detour, home, noise, resident |
| Drivers / Daily Commuters | 10 | 0.71 | 9.29 | yes | yes | commut, congestion, delay, driver, lane, queue |
| Pedestrians / Cyclists / Vulnerable Road Users | 8 | 1.43 | 6.57 | yes | yes | bicycl, comfort, crossing, cyclist, pedestrian, separation |
| Emergency Responders / Healthcare Providers | 6 | 1.29 | 4.71 | yes | yes | emergency, ems, hospital, incident, responder, response time |
| Public Transit / Mobility Providers | 4 | 1.86 | 2.14 | no | yes | bus, mobility, rider, transit |
| Freight / Rail Operators | 5 | 1.43 | 3.57 | yes | yes | continuity, freight, rail, trespass, truck |

*Interpretation:* embedding similarity between two answers to near-identical prompts is high by construction (they share the scenario text), so judge differentiation mainly by the alignment table above, not the raw similarity. Vocabulary alignment is a proxy: it shows the answer *speaks* like the stakeholder, not that its reasoning is right. The 'Others' counts use only terms unique to one stakeholder's list.

## 6. Per-question verdicts and failure analysis

| # | Layer | Stakeholder / theme | Problems |
|---|---|---|---|
| 3 | L1 | State / Historical Precedents, Risks & Trade-offs | retrieval miss (no expected source retrieved) |
| 6 | L1 | Local Government / Future Demand / Long-term Safety Performance | retrieval miss (no expected source retrieved) |
| 7 | L1 | Emergency Responders / Emergency Access / Response Time | retrieval miss (no expected source retrieved); hard flag: invented_figure |
| 8 | L1 | Emergency Responders / Safety Improvements vs. Emergency Operations | retrieval miss (no expected source retrieved) |
| 9 | L1 | Emergency Responders / Crash Severity / Post-Crash Response | retrieval miss (no expected source retrieved); hard flag: invented_figure |
| 18 | L1 | Drivers / Roadway Design Clarity & Driver Behavior | retrieval miss (no expected source retrieved); hard flag: invented_figure |
| 20 | L1 | Pedestrians / Sidewalk / Path Continuity & Accessibility | retrieval miss (no expected source retrieved) |
| 23 | L1 | Freight / Rail Crossing Safety & Conflict Risk | hard flag: invented_figure |
| 25 | L2 | State / Shared scenario | retrieval miss (no expected source retrieved) |
| 27 | L2 | Nearby Residents / Shared scenario | retrieval miss (no expected source retrieved) |
| 30 | L2 | Emergency Responders / Shared scenario | retrieval miss (no expected source retrieved) |
| 31 | L2 | Public Transit / Shared scenario | retrieval miss (no expected source retrieved) |
| 32 | L2 | Freight / Shared scenario | retrieval miss (no expected source retrieved) |
| 33 | L2-addon | All / Comparable Local Cases | retrieval miss (no expected source retrieved) |
| 34 | L2-addon | All / Local Evidence for Follow-Up Action | retrieval miss (no expected source retrieved) |

**Retrieval misses and weak retrieval** (expected sources not reached):

- Q1 (Prioritization): recall 0.25; expected-but-missing: vision_zero_hin_map, vision_zero_action_plan_2023_2028, proj_
- Q2 (Local Context & Decision Making): recall 0.25; expected-but-missing: rtmc_mobility_study, proj_, morpc_ej
- Q3 (Historical Precedents, Risks & Trade-offs): recall 0.00; expected-but-missing: proj_, rtmc_mobility_study, vision_zero_action_plan_1_0, morpc_tip
- Q4 (Implementation Feasibility / Infrastructure Conditions): recall 0.33; expected-but-missing: proj_, morpc_tip
- Q6 (Future Demand / Long-term Safety Performance): recall 0.00; expected-but-missing: morpc_mtp_2024_2050_attachment_06, morpc_mtp_2024_2050_attachment_13, morpc_mtp_2024_2050_attachment_10, rtmc_mobility_study
- Q7 (Emergency Access / Response Time): recall 0.00; expected-but-missing: morpc_mtp_2024_2050_attachment_08, rtmc_mobility_study, proj_np37, proj_
- Q8 (Safety Improvements vs. Emergency Operations): recall 0.00; expected-but-missing: proj_, morpc_mtp_2024_2050_attachment_08, rtmc_mobility_study
- Q9 (Crash Severity / Post-Crash Response): recall 0.00; expected-but-missing: vision_zero_action_plan_2023_2028, vision_zero_hin_map, morpc_mtp_2024_2050_attachment_06, proj_120250_fwsac_crash_stats
- Q10 (First / Last-Mile Safety & Access): recall 0.25; expected-but-missing: cota_park_and_ride_locations, rtmc_mobility_study, columbus_bike_plus_2025_report
- Q13 (Safety & Quality of Life Near Homes): recall 0.20; expected-but-missing: proj_119852, proj_120250, rtmc_appendix_k_engagement, morpc_ej
- Q15 (Construction Impacts & Community Engagement): recall 0.25; expected-but-missing: proj_np37_hilliard_construction_update, proj_119852_engage_columbus, proj_120346_engage_columbus
- Q16 (Crash Risk & Traffic Conflicts): recall 0.25; expected-but-missing: proj_120250_fwsac_crash_stats, proj_119852, proj_120250
- Q17 (Delay, Queues & Travel-Time Reliability): recall 0.25; expected-but-missing: proj_, morpc_mtp_2024_2050_attachment_06, morpc_mtp_2024_2050_attachment_08
- Q18 (Roadway Design Clarity & Driver Behavior): recall 0.00; expected-but-missing: proj_119852, proj_120250, rtmc_mobility_study, proj_120346
- Q19 (Crossing Safety & Visibility): recall 0.25; expected-but-missing: vision_zero_hin_map, columbus_bike_plus_2025_report, morpc_mtp_2024_2050
- Q20 (Sidewalk / Path Continuity & Accessibility): recall 0.00; expected-but-missing: columbus_bike_plus_2025_report, morpc_ej_technical_appendix, vision_zero_action_plan, rtmc_mobility_study
- Q21 (Separation from Vehicles & Comfort): recall 0.33; expected-but-missing: columbus_bike_plus_2025_report, vision_zero_hin_map
- Q23 (Rail Crossing Safety & Conflict Risk): recall 0.33; expected-but-missing: odot_tem_rail_crossings, fhwa_railway_crossing_resources
- Q24 (Freight Access & Operational Impact): recall 0.33; expected-but-missing: rtmc_mobility_study, proj_
- Q25 (Shared scenario): recall 0.00; expected-but-missing: vision_zero_action_plan_2023_2028, proj_120250_fwsac_crash_stats, proj_119852, morpc_mtp_2024_2050_attachment_13
- Q26 (Shared scenario): recall 0.25; expected-but-missing: proj_120250_fwsac_crash_stats, proj_119852, morpc_mtp_2024_2050_attachment_13
- Q27 (Shared scenario): recall 0.00; expected-but-missing: vision_zero_action_plan_2023_2028, proj_120250_fwsac_crash_stats, proj_119852, morpc_mtp_2024_2050_attachment_13
- Q28 (Shared scenario): recall 0.25; expected-but-missing: proj_120250_fwsac_crash_stats, proj_119852, morpc_mtp_2024_2050_attachment_13
- Q29 (Shared scenario): recall 0.25; expected-but-missing: proj_120250_fwsac_crash_stats, proj_119852, morpc_mtp_2024_2050_attachment_13
- Q30 (Shared scenario): recall 0.00; expected-but-missing: vision_zero_action_plan_2023_2028, proj_120250_fwsac_crash_stats, proj_119852, morpc_mtp_2024_2050_attachment_13
- Q31 (Shared scenario): recall 0.00; expected-but-missing: vision_zero_action_plan_2023_2028, proj_120250_fwsac_crash_stats, proj_119852, morpc_mtp_2024_2050_attachment_13
- Q32 (Shared scenario): recall 0.00; expected-but-missing: vision_zero_action_plan_2023_2028, proj_120250_fwsac_crash_stats, proj_119852, morpc_mtp_2024_2050_attachment_13
- Q33 (Comparable Local Cases): recall 0.00; expected-but-missing: proj_120250_fwsac_crash_stats, proj_119852, proj_120250, proj_np37_hilliard_construction_update
- Q34 (Local Evidence for Follow-Up Action): recall 0.00; expected-but-missing: vision_zero_action_plan_2023_2028, morpc_mtp_2024_2050_attachment_13, morpc_mtp_2024_2050_attachment_11, proj_120250_fwsac_crash_stats

**Hard-flagged answers** (detected by the pipeline's verification stages):

- Q7: figures not found in any cited passage: 120
- Q9: figures not found in any cited passage: 1,000
- Q18: figures not found in any cited passage: 800
- Q23: figures not found in any cited passage: 157

## 7. Metric definitions and limits

| Metric | Definition | Reference-free? |
|---|---|---|
| Source recall@k | share of expected documents (prefix match) with ≥1 passage in the top-k context | no, needs expected sources |
| Hit / MRR | any expected source retrieved / reciprocal rank of the first one | no |
| Keyword context recall | share of probe keywords present anywhere in the retrieved text | no, needs probes |
| Groundedness | share of factual answer sentences whose best-matching retrieved passage has cosine ≥ 0.50 | yes |
| Hard flags | numbers absent from cited passages, national figures re-scoped as local, figures cited only to an unloaded GIS catalogue entry | yes |
| Answer relevancy | cosine(question, answer body) in the retrieval embedding space | yes |
| Probe coverage | share of probe keywords in the answer | no |
| Locality | distinct Columbus / Central Ohio proper nouns from `eval/local_lexicon.json` | no, needs lexicon |
| Judge metrics | local LLM yes/no on passage relevance and claim support | yes |

**What this evaluation cannot tell you**

- There are no gold reference answers. Correctness of local claims (is the cited crash count the right one, is the project the right project) needs a domain reviewer. Faithfulness here means *supported by what was retrieved*, not *true*.
- `expected_sources` and `probes` are provisional silver labels written from catalogue titles. Low recall may mean the label is wrong, not the retrieval. Review them before quoting recall.
- Groundedness is an embedding-similarity check: it catches topical invention but can pass a correctly-themed sentence that reverses a document's meaning.
- Generation is sampled (temperature 0.2); a single run is one draw. Re-run before treating small differences as real.
- Several stakeholder topics (EMS response, freight, transit first/last-mile) have thin coverage in the corpus. A good answer there is an honest gap statement, which the relevancy and probe metrics will under-credit; read the gap bullets in the transcript.

## Appendix: all questions

| # | Layer | Stakeholder | Theme | Src recall | Hit | MRR | Grounded | Relevancy | Probes | Locality | Docs | Gap bullets | s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | L1 | state | Prioritization | 0.25 | 1.00 | 0.17 | 100% | 0.79 | 1.00 | 9 | 9 | 1 | 158.9 |
| 2 | L1 | state | Local Context & Decision Making | 0.25 | 1.00 | 0.20 | 100% | 0.80 | 0.00 | 8 | 8 | 1 | 134.3 |
| 3 | L1 | state | Historical Precedents, Risks & Trade-offs | 0.00 | 0.00 | 0.00 | 100% | 0.83 | 0.86 | 5 | 8 | 1 | 140.1 |
| 4 | L1 | local | Implementation Feasibility / Infrastructure Conditions | 0.33 | 1.00 | 0.17 | 100% | 0.83 | 0.43 | 4 | 9 | 1 | 105.5 |
| 5 | L1 | local | Maintenance / Long-term Sustainability | 0.50 | 1.00 | 0.14 | 100% | 0.83 | 0.43 | 5 | 7 | 1 | 140.8 |
| 6 | L1 | local | Future Demand / Long-term Safety Performance | 0.00 | 0.00 | 0.00 | 100% | 0.87 | 0.71 | 3 | 7 | 1 | 110.3 |
| 7 | L1 | ems | Emergency Access / Response Time | 0.00 | 0.00 | 0.00 | 100% | 0.85 | 0.57 | 4 | 7 | 1 | 150.3 |
| 8 | L1 | ems | Safety Improvements vs. Emergency Operations | 0.00 | 0.00 | 0.00 | 96% | 0.83 | 0.83 | 7 | 7 | 1 | 140.2 |
| 9 | L1 | ems | Crash Severity / Post-Crash Response | 0.00 | 0.00 | 0.00 | 100% | 0.86 | 0.71 | 6 | 7 | 1 | 120.2 |
| 10 | L1 | transit | First / Last-Mile Safety & Access | 0.25 | 1.00 | 0.12 | 100% | 0.83 | 0.71 | 6 | 7 | 4 | 117.5 |
| 11 | L1 | transit | Value of Supporting Safety Projects | 0.50 | 1.00 | 0.25 | 100% | 0.82 | 0.86 | 11 | 8 | 1 | 7382.1 |
| 12 | L1 | transit | Network Connectivity / Future Mobility Needs | 0.50 | 1.00 | 0.25 | 100% | 0.86 | 0.86 | 3 | 9 | 1 | 18357.1 |
| 13 | L1 | resident | Safety & Quality of Life Near Homes | 0.20 | 1.00 | 0.11 | 100% | 0.91 | 0.71 | 9 | 10 | 1 | 105.7 |
| 14 | L1 | resident | Cut-Through Traffic & Neighborhood Impacts | 0.67 | 1.00 | 0.20 | 100% | 0.78 | 0.86 | 2 | 9 | 1 | 103.9 |
| 15 | L1 | resident | Construction Impacts & Community Engagement | 0.25 | 1.00 | 0.11 | 100% | 0.84 | 0.57 | 5 | 8 | 1 | 114.3 |
| 16 | L1 | driver | Crash Risk & Traffic Conflicts | 0.25 | 1.00 | 0.14 | 100% | 0.80 | 0.57 | 6 | 8 | 3 | 50.7 |
| 17 | L1 | driver | Delay, Queues & Travel-Time Reliability | 0.25 | 1.00 | 0.12 | 100% | 0.87 | 0.71 | 8 | 10 | 1 | 94.5 |
| 18 | L1 | driver | Roadway Design Clarity & Driver Behavior | 0.00 | 0.00 | 0.00 | 100% | 0.86 | 0.86 | 5 | 8 | 1 | 118.3 |
| 19 | L1 | vru | Crossing Safety & Visibility | 0.25 | 1.00 | 0.12 | 100% | 0.85 | 0.71 | 4 | 7 | 1 | 99.5 |
| 20 | L1 | vru | Sidewalk / Path Continuity & Accessibility | 0.00 | 0.00 | 0.00 | 94% | 0.77 | 0.86 | 2 | 8 | 4 | 97.4 |
| 21 | L1 | vru | Separation from Vehicles & Comfort | 0.33 | 1.00 | 0.10 | 100% | 0.84 | 0.71 | 5 | 9 | 1 | 108.1 |
| 22 | L1 | freight | Truck Interactions & Freight Routes | 0.67 | 1.00 | 0.12 | 100% | 0.75 | 0.57 | 4 | 7 | 1 | 110.2 |
| 23 | L1 | freight | Rail Crossing Safety & Conflict Risk | 0.33 | 1.00 | 0.17 | 100% | 0.83 | 0.71 | 4 | 8 | 1 | 106.5 |
| 24 | L1 | freight | Freight Access & Operational Impact | 0.33 | 1.00 | 0.17 | 100% | 0.91 | 0.57 | 6 | 7 | 4 | 112.8 |
| 25 | L2 | state | Shared scenario | 0.00 | 0.00 | 0.00 | 100% | 0.90 | 1.00 | 1 | 9 | 2 | 74.6 |
| 26 | L2 | local | Shared scenario | 0.25 | 1.00 | 0.20 | 100% | 0.85 | 1.00 | 0 | 7 | 1 | 3654.6 |
| 27 | L2 | resident | Shared scenario | 0.00 | 0.00 | 0.00 | 96% | 0.85 | 1.00 | 0 | 7 | 1 | 116.7 |
| 28 | L2 | driver | Shared scenario | 0.25 | 1.00 | 0.20 | 100% | 0.84 | 1.00 | 1 | 8 | 4 | 111.9 |
| 29 | L2 | vru | Shared scenario | 0.25 | 1.00 | 0.17 | 100% | 0.87 | 1.00 | 1 | 8 | 2 | 100.2 |
| 30 | L2 | ems | Shared scenario | 0.00 | 0.00 | 0.00 | 100% | 0.84 | 1.00 | 0 | 8 | 1 | 85.3 |
| 31 | L2 | transit | Shared scenario | 0.00 | 0.00 | 0.00 | 100% | 0.82 | 1.00 | 0 | 9 | 2 | 98.5 |
| 32 | L2 | freight | Shared scenario | 0.00 | 0.00 | 0.00 | 100% | 0.88 | 1.00 | 0 | 9 | 1 | 96.5 |
| 33 | L2-addon | all | Comparable Local Cases | 0.00 | 0.00 | 0.00 | 100% | 0.86 | 0.86 | 3 | 7 | 3 | 46.3 |
| 34 | L2-addon | all | Local Evidence for Follow-Up Action | 0.00 | 0.00 | 0.00 | 100% | 0.87 | 0.86 | 2 | 9 | 2 | 2129.5 |
