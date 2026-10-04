# Honda Safety RAG: stakeholder evaluation report

Run 2026-10-03 · commit `f224584` · mlx-community/Qwen2.5-3B-Instruct-4bit (mlx) · embeddings BAAI/bge-small-en-v1.5 · 1,478 passages · top-14 context

**34 questions**: 24 stakeholder-specific (Layer 1), 8 shared-scenario (Layer 2), 2 add-ons. 68% of questions clear every per-question check (see *Per-question verdicts*). Mean latency 128.985s.

## 1. Scorecard: the RAG triad

Targets were set before the run (see `TARGETS` in `rag/evaluate_stakeholders.py`). Brackets are 95% bootstrap intervals over questions; with this few questions they are wide, so differences under ~0.1 are not meaningful.

| Leg | Metric | Mean [95% CI] | Target | Status |
|---|---|---|---|---|
| Retrieval | Source recall@k | 0.30 [0.23, 0.37] | ≥ 0.50 | BELOW TARGET |
| Retrieval | Hit rate (any expected source) | 0.79 [0.68, 0.91] | ≥ 0.90 | BELOW TARGET |
| Retrieval | MRR (first expected source) | 0.28 [0.17, 0.39] | - |  |
| Retrieval | Source precision (share of passages from expected sources) | 0.19 [0.13, 0.25] | - |  |
| Retrieval | Keyword context recall | 0.69 [0.63, 0.76] | - |  |
| Generation | Groundedness (sentence-level attribution) | 1.00 [1.00, 1.00] | ≥ 0.85 | PASS |
| Generation | Answers free of detected invented / mis-scoped figures | 82% | 100% | BELOW TARGET |
| Answer | Answer relevancy, raw cosine (sanity check only; saturated) | 0.85 [0.84, 0.86] | - |  |
| Answer | Relevancy margin (own question minus other questions) | 0.08 [0.06, 0.09] | ≥ 0.02 | PASS |
| Answer | Probe coverage (expected topics mentioned) | 0.65 [0.56, 0.73] | ≥ 0.50 | PASS |
| Answer | Locality (local proper nouns per answer) | 7.24 [5.97, 8.44] | - |  |
| Honesty | Answers with an evidence-gap section | 100% | ≥ 95% | PASS |
| Retrieval (judge) | Context precision / AP: withheld, relevance judge failed its control test | n/a | - | UNRELIABLE |
| Generation (judge) | Faithfulness, LLM judge over cited claims | 0.22 [0.16, 0.28] | - |  |

**LLM-judge control test** (9 claim and 8 relevance controls, run before scoring): a sentence copied from a passage should be *Supported* by it and *Unsupported* by an unrelated passage; the passage nearest a question should be *Relevant*, the farthest *Irrelevant*. Accept/reject accuracy: claim-support 78% / 100%, context-relevance 12% / 100%. A judge is used only if both its accept and reject rates are ≥ 75%. Claim-support judge: passed. Relevance judge: FAILED, not reported. Even a passing judge is the same 3B model that wrote the answers, so treat it as a second opinion.

## 2. Breakdown by layer and stakeholder

| Group | n | Src recall | Hit | Grounded | Relevancy | Probes | Locality | No hard flags | Latency s |
|---|---|---|---|---|---|---|---|---|---|
| Layer 1: stakeholder-specific | 24 | 0.336 | 0.792 | 1.0 | 0.834 | 0.538 | 8.917 | 83% | 139.954 |
| Layer 2: shared scenario | 8 | 0.25 | 1.0 | 1.0 | 0.885 | 0.958 | 2.25 | 88% | 107.213 |
| Layer 2: add-ons | 2 | 0.0 | 0.0 | 1.0 | 0.888 | 0.714 | 7.0 | 50% | 84.45 |

**Layer 1 by stakeholder**

| Group | n | Src recall | Hit | Grounded | Relevancy | Probes | Locality | No hard flags | Latency s |
|---|---|---|---|---|---|---|---|---|---|
| State / Regional Transportation Agencies | 3 | 0.333 | 1.0 | 1.0 | 0.845 | 0.405 | 7.333 | 67% | 85.867 |
| Local Government / Public Works | 3 | 0.417 | 0.667 | 1.0 | 0.84 | 0.429 | 7.333 | 67% | 99.4 |
| Emergency Responders / Healthcare Providers | 3 | 0.278 | 0.667 | 1.0 | 0.834 | 0.659 | 10.0 | 67% | 88.733 |
| Public Transit / Mobility Providers | 3 | 0.083 | 0.333 | 1.0 | 0.822 | 0.476 | 7.333 | 100% | 99.233 |
| Nearby Residents / Local Communities | 3 | 0.244 | 0.667 | 1.0 | 0.831 | 0.571 | 9.0 | 100% | 113.633 |
| Drivers / Daily Commuters | 3 | 0.417 | 1.0 | 1.0 | 0.811 | 0.714 | 9.333 | 100% | 417.3 |
| Pedestrians / Cyclists / Vulnerable Road Users | 3 | 0.361 | 1.0 | 1.0 | 0.837 | 0.571 | 10.0 | 100% | 108.3 |
| Freight / Rail Operators | 3 | 0.556 | 1.0 | 1.0 | 0.849 | 0.476 | 11.0 | 67% | 107.167 |

**Layer 1 by theme** (each stakeholder's three questions probe different concerns)

| # | Stakeholder | Theme | Src recall | Grounded | Relevancy | Probes | Locality | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | State | Prioritization | 0.25 | 100% | 0.87 | 0.50 | 9 | OK |
| 2 | State | Local Context & Decision Making | 0.25 | 100% | 0.84 | 0.14 | 9 | CHECK |
| 3 | State | Historical Precedents, Risks & Trade-offs | 0.50 | 100% | 0.82 | 0.57 | 4 | OK |
| 4 | Local Government | Implementation Feasibility / Infrastructure Conditions | 0.00 | 100% | 0.85 | 0.00 | 6 | CHECK |
| 5 | Local Government | Maintenance / Long-term Sustainability | 0.75 | 100% | 0.84 | 0.43 | 7 | OK |
| 6 | Local Government | Future Demand / Long-term Safety Performance | 0.50 | 100% | 0.84 | 0.86 | 9 | OK |
| 7 | Emergency Responders | Emergency Access / Response Time | 0.50 | 100% | 0.81 | 0.29 | 8 | OK |
| 8 | Emergency Responders | Safety Improvements vs. Emergency Operations | 0.33 | 100% | 0.83 | 0.83 | 11 | OK |
| 9 | Emergency Responders | Crash Severity / Post-Crash Response | 0.00 | 100% | 0.87 | 0.86 | 11 | CHECK |
| 10 | Public Transit | First / Last-Mile Safety & Access | 0.00 | 100% | 0.81 | 0.57 | 5 | CHECK |
| 11 | Public Transit | Value of Supporting Safety Projects | 0.00 | 100% | 0.83 | 0.43 | 9 | CHECK |
| 12 | Public Transit | Network Connectivity / Future Mobility Needs | 0.25 | 100% | 0.83 | 0.43 | 8 | OK |
| 13 | Nearby Residents | Safety & Quality of Life Near Homes | 0.40 | 100% | 0.83 | 0.71 | 6 | OK |
| 14 | Nearby Residents | Cut-Through Traffic & Neighborhood Impacts | 0.33 | 100% | 0.83 | 0.43 | 10 | OK |
| 15 | Nearby Residents | Construction Impacts & Community Engagement | 0.00 | 100% | 0.83 | 0.57 | 11 | CHECK |
| 16 | Drivers | Crash Risk & Traffic Conflicts | 0.75 | 100% | 0.82 | 0.71 | 12 | OK |
| 17 | Drivers | Delay, Queues & Travel-Time Reliability | 0.25 | 100% | 0.77 | 0.57 | 10 | CHECK |
| 18 | Drivers | Roadway Design Clarity & Driver Behavior | 0.25 | 100% | 0.84 | 0.86 | 6 | OK |
| 19 | Pedestrians | Crossing Safety & Visibility | 0.50 | 100% | 0.86 | 0.57 | 7 | OK |
| 20 | Pedestrians | Sidewalk / Path Continuity & Accessibility | 0.25 | 100% | 0.85 | 0.86 | 13 | OK |
| 21 | Pedestrians | Separation from Vehicles & Comfort | 0.33 | 100% | 0.80 | 0.29 | 10 | OK |
| 22 | Freight | Truck Interactions & Freight Routes | 0.67 | 100% | 0.81 | 0.14 | 9 | OK |
| 23 | Freight | Rail Crossing Safety & Conflict Risk | 0.33 | 100% | 0.83 | 0.57 | 8 | OK |
| 24 | Freight | Freight Access & Operational Impact | 0.67 | 100% | 0.91 | 0.71 | 16 | CHECK |

## 3. Retrieval ablation

Same questions, retrieval only, top-14 passages. Shows which pipeline stage earns its place. `hybrid_rules` is the full pipeline without the LLM query planner.

| Retriever | Source recall | Hit | MRR | Source precision | Keyword ctx recall |
|---|---|---|---|---|---|
| dense_only | 0.45 | 0.882 | 0.568 | 0.416 | 0.707 |
| bm25_only | 0.371 | 0.794 | 0.576 | 0.317 | 0.723 |
| hybrid_rules | 0.389 | 0.971 | 0.308 | 0.195 | 0.714 |
| hybrid_llm_planner | 0.296 | 0.794 | 0.275 | 0.186 | 0.693 |

Caveat: dense-only and BM25-only return the raw top-k with no per-document cap or MMR, so they can be dominated by one long document. Source precision is therefore not directly comparable across rows; recall and hit are.

## 4. RAG vs. the same LLM with no retrieval

The project's thesis is that a locally-grounded RAG gives more locally relevant insight than a general LLM. The baseline is the same model, same question, no context.

| Metric | RAG | No-retrieval baseline |
|---|---|---|
| Locality (local proper nouns) | 7.235 | 1.618 |
| Probe coverage | 0.647 | 0.72 |
| Answer relevancy, raw cosine | 0.849 | 0.891 |
| Relevancy margin | 0.079 | 0.131 |
| Words | 398.147 | 479.559 |
| Evidence-gap section | 100% | 0% |
| Latency s | 128.985 | 67.544 |

Locality is the metric that cleanly separates the two. The baseline has no citations and its specifics cannot be verified here, so this comparison says nothing about whether its unsourced claims are *correct*.

## 5. Layer 2: same scenario, different stakeholders

Scenario: *A safety improvement project at a Columbus intersection has reduced crashes from 8 to 2 per year. However, the two remaining crashes involved serious injuries. Traffic delay has improved, but pedestrian concerns remain.*

The test is not whether any one answer is good but whether the system reads the *same* evidence through *different* stakeholder lenses.

- **Perspective alignment: 38%** of the 8 answers use their own stakeholder's vocabulary more than any other stakeholder's (a reader could tell whose answer it is). Mean lift +1.75 own-terms over other stakeholders' terms.
- **Answer similarity: 0.90** mean pairwise embedding cosine across the eight answers. Higher means the answers are interchangeable; see the interpretation note below.
- **Shared evidence: 0.73** mean pairwise Jaccard overlap of retrieved documents. High overlap is expected and desirable here (same evidence), but it also means perspective differences come from generation, not retrieval.

| Stakeholder | Own terms | Others (mean) | Lift | Own rank first | Restates 8→2 | Own terms used |
|---|---|---|---|---|---|---|
| State / Regional Transportation Agencies | 4 | 1.57 | 2.43 | yes | yes | crash reduction, regional, serious injur, target |
| Local Government / Public Works | 0 | 0.71 | -0.71 | no | yes |  |
| Nearby Residents / Local Communities | 3 | 1.57 | 1.43 | no | yes | community, engagement, resident |
| Drivers / Daily Commuters | 3 | 0.86 | 2.14 | no | yes | commut, driver, speed |
| Pedestrians / Cyclists / Vulnerable Road Users | 5 | 0.86 | 4.14 | yes | yes | bicycl, crossing, cyclist, pedestrian, sidewalk |
| Emergency Responders / Healthcare Providers | 5 | 0.86 | 4.14 | yes | yes | emergency, incident, responder, response time, trauma |
| Public Transit / Mobility Providers | 2 | 1.57 | 0.43 | no | yes | mobility, transit |
| Freight / Rail Operators | 2 | 2 | 0 | no | yes | freight, rail |

*Interpretation:* embedding similarity between two answers to near-identical prompts is high by construction (they share the scenario text), so judge differentiation mainly by the alignment table above, not the raw similarity. Vocabulary alignment is a proxy: it shows the answer *speaks* like the stakeholder, not that its reasoning is right. The 'Others' counts use only terms unique to one stakeholder's list.

## 6. Per-question verdicts and failure analysis

| # | Layer | Stakeholder / theme | Problems |
|---|---|---|---|
| 2 | L1 | State / Local Context & Decision Making | hard flag: catalog_figure |
| 4 | L1 | Local Government / Implementation Feasibility / Infrastructure Conditions | retrieval miss (no expected source retrieved); hard flag: catalog_figure |
| 9 | L1 | Emergency Responders / Crash Severity / Post-Crash Response | retrieval miss (no expected source retrieved); hard flag: catalog_figure |
| 10 | L1 | Public Transit / First / Last-Mile Safety & Access | retrieval miss (no expected source retrieved) |
| 11 | L1 | Public Transit / Value of Supporting Safety Projects | retrieval miss (no expected source retrieved) |
| 15 | L1 | Nearby Residents / Construction Impacts & Community Engagement | retrieval miss (no expected source retrieved) |
| 17 | L1 | Drivers / Delay, Queues & Travel-Time Reliability | answer not specific to its question (margin -0.013) |
| 24 | L1 | Freight / Freight Access & Operational Impact | hard flag: catalog_figure |
| 25 | L2 | State / Shared scenario | hard flag: catalog_figure |
| 33 | L2-addon | All / Comparable Local Cases | retrieval miss (no expected source retrieved) |
| 34 | L2-addon | All / Local Evidence for Follow-Up Action | retrieval miss (no expected source retrieved); hard flag: catalog_figure |

**Retrieval misses and weak retrieval** (expected sources not reached):

- Q1 (Prioritization): recall 0.25; expected-but-missing: vision_zero_hin_map, vision_zero_action_plan_2023_2028, proj_
- Q2 (Local Context & Decision Making): recall 0.25; expected-but-missing: rtmc_mobility_study, proj_, morpc_ej
- Q4 (Implementation Feasibility / Infrastructure Conditions): recall 0.00; expected-but-missing: proj_, rtmc_mobility_study, morpc_tip
- Q8 (Safety Improvements vs. Emergency Operations): recall 0.33; expected-but-missing: proj_, rtmc_mobility_study
- Q9 (Crash Severity / Post-Crash Response): recall 0.00; expected-but-missing: vision_zero_action_plan_2023_2028, vision_zero_hin_map, morpc_mtp_2024_2050_attachment_06, proj_120250_fwsac_crash_stats
- Q10 (First / Last-Mile Safety & Access): recall 0.00; expected-but-missing: cota_park_and_ride_locations, rtmc_mobility_study, columbus_bike_plus_2025_report, linkus
- Q11 (Value of Supporting Safety Projects): recall 0.00; expected-but-missing: linkus_overview, linkus_west_broad_funding, cota_park_and_ride_locations, rtmc_mobility_study
- Q12 (Network Connectivity / Future Mobility Needs): recall 0.25; expected-but-missing: columbus_bike_plus_2025_report, linkus, morpc_mtp_2024_2050_attachment_10
- Q13 (Safety & Quality of Life Near Homes): recall 0.40; expected-but-missing: proj_119852, proj_120250, rtmc_appendix_k_engagement
- Q14 (Cut-Through Traffic & Neighborhood Impacts): recall 0.33; expected-but-missing: rtmc_appendix_k_engagement, proj_
- Q15 (Construction Impacts & Community Engagement): recall 0.00; expected-but-missing: proj_np37_hilliard_construction_update, proj_119852_engage_columbus, proj_120346_engage_columbus, rtmc_appendix_k_engagement
- Q17 (Delay, Queues & Travel-Time Reliability): recall 0.25; expected-but-missing: rtmc_mobility_study, proj_, morpc_mtp_2024_2050_attachment_06
- Q18 (Roadway Design Clarity & Driver Behavior): recall 0.25; expected-but-missing: proj_119852, proj_120250, proj_120346
- Q20 (Sidewalk / Path Continuity & Accessibility): recall 0.25; expected-but-missing: columbus_bike_plus_2025_report, morpc_ej_technical_appendix, rtmc_mobility_study
- Q21 (Separation from Vehicles & Comfort): recall 0.33; expected-but-missing: columbus_bike_plus_2025_report, vision_zero_hin_map
- Q23 (Rail Crossing Safety & Conflict Risk): recall 0.33; expected-but-missing: odot_tem_rail_crossings, fhwa_railway_crossing_resources
- Q25 (Shared scenario): recall 0.25; expected-but-missing: proj_120250_fwsac_crash_stats, proj_119852, morpc_mtp_2024_2050_attachment_13
- Q26 (Shared scenario): recall 0.25; expected-but-missing: proj_120250_fwsac_crash_stats, proj_119852, morpc_mtp_2024_2050_attachment_13
- Q27 (Shared scenario): recall 0.25; expected-but-missing: proj_120250_fwsac_crash_stats, proj_119852, morpc_mtp_2024_2050_attachment_13
- Q28 (Shared scenario): recall 0.25; expected-but-missing: proj_120250_fwsac_crash_stats, proj_119852, morpc_mtp_2024_2050_attachment_13
- Q29 (Shared scenario): recall 0.25; expected-but-missing: proj_120250_fwsac_crash_stats, proj_119852, morpc_mtp_2024_2050_attachment_13
- Q30 (Shared scenario): recall 0.25; expected-but-missing: proj_120250_fwsac_crash_stats, proj_119852, morpc_mtp_2024_2050_attachment_13
- Q31 (Shared scenario): recall 0.25; expected-but-missing: proj_120250_fwsac_crash_stats, proj_119852, morpc_mtp_2024_2050_attachment_13
- Q32 (Shared scenario): recall 0.25; expected-but-missing: proj_120250_fwsac_crash_stats, proj_119852, morpc_mtp_2024_2050_attachment_13
- Q33 (Comparable Local Cases): recall 0.00; expected-but-missing: proj_120250_fwsac_crash_stats, proj_119852, proj_120250, proj_np37_hilliard_construction_update
- Q34 (Local Evidence for Follow-Up Action): recall 0.00; expected-but-missing: vision_zero_action_plan_2023_2028, morpc_mtp_2024_2050_attachment_13, morpc_mtp_2024_2050_attachment_11, proj_120250_fwsac_crash_stats

**Hard-flagged answers** (detected by the pipeline's verification stages):

- Q2: 2 figure(s) attributed only to a dataset catalogue entry, whose records are not loaded - treat as unverified
- Q4: 1 figure(s) attributed only to a dataset catalogue entry, whose records are not loaded - treat as unverified
- Q9: 1 figure(s) attributed only to a dataset catalogue entry, whose records are not loaded - treat as unverified
- Q24: 1 figure(s) attributed only to a dataset catalogue entry, whose records are not loaded - treat as unverified
- Q25: 1 figure(s) attributed only to a dataset catalogue entry, whose records are not loaded - treat as unverified
- Q34: 1 figure(s) attributed only to a dataset catalogue entry, whose records are not loaded - treat as unverified

**Claims the LLM judge could not verify** (second opinion; a 3B judge over-rejects, review by hand):

- Q1: Based on the available local data and guidelines, the following areas in Columbus/Central Ohio should be prioritized for safety improvement initiatives or planning:
- Q1: The heat map analysis indicated frequent crashes involving vehicles, suggesting a need for enhanced safety measures at this location .
- Q2: The city's efforts include identifying HIN corridors (High Injury Network) where wide, multi-lane streets pose significant risks .
- Q2: This dataset identifies high-risk intersections based on crash frequency, which guides targeted safety improvements .
- Q3: One notable example is the implementation of the Safe Routes to School (SRTS) program, which has shown significant benefits but also faces challenges .
- Q3: This initiative, supported by COTA and the City of Columbus, aims to create safe routes for vulnerable road users such as children walking and biking to school .
- Q4: When implementing safety improvements in Columbus, certain areas face unique challenges due to their existing roadway or infrastructure conditions, local geometry, and surrounding conditions .
- Q4: For instance, the High Injury Network (HIN) corridors identified by MORPC present significant challenges .
- Q5: For safety improvements planned or implemented in Columbus, maintaining their safety benefits over time requires addressing specific challenges related to infrastructure maintenance and design .
- Q5: One significant challenge involves ensuring the longevity and reliability of traffic calming measures .
- Q6: However, as traffic, population, and development continue to evolve, it becomes crucial for local governments to monitor these changes closely to ensure the effectiveness of future safety initiatives .
- Q6: Specifically, the HIN (High Injury Network) corridors identified in the Vision Zero Action Plan, such as those along Bloomington Boulevard/Tanglewood Park Boulevard & Renner Road, Hilliard-Rome Road & Renner Road, and Ri
- Q7: The existing data suggests that certain areas within Columbus and Central Ohio face significant challenges for emergency responders to reach crash locations quickly and reliably .
- Q7: Specifically, the RTMC Mobility Study identified high-crash segments on Renner Road & Hilliard-Rome Road, as well as the McKinley Avenue corridor, indicating potential issues with roadway design and traffic conditions .
- Q8: To improve emergency response in the surrounding areas of Columbus and Central Ohio, planned safety improvement projects such as those outlined in the Vision Zero Columbus Action Plan 2023-2028 and the Central Ohio Trans
- Q8: Firstly, the implementation of Emergency Vehicle Preemption (EVP) through the HAAS Alert program will expedite first responder access to accident scenes .
- Q9: Based on the available data, particularly from the City of Columbus's High Injury Network (HIN) dataset and the Central Ohio Transportation Safety Plan (COTSP), there are specific areas in Columbus/central Ohio facing si
- Q9: Firstly, the intersection of Renner Road & Hilliard Road and Trabue Road & N .
- Q10: The safety and accessibility of Central Ohio's roadways and infrastructure for pedestrians and cyclists are critical issues, particularly when accessing public transit and Park & Ride facilities .
- Q10: The Central Ohio Transportation Safety Plan (COTSP) identifies numerous gaps and challenges in the region's transportation system, including those affecting vulnerable users such as pedestrians and cyclists .
- Q11: To understand how planned or existing safety improvement projects in Columbus/Central Ohio could benefit public transit or mobility services, we need to examine the context provided through various documents and datasets
- Q11: By analyzing these segments, transit operators and city planners can identify areas where safety improvements are most needed .
- Q12: The existing data suggests significant gaps in Columbus and Central Ohio's transportation network for improving accessibility to public transit through safer and more convenient mobility connections .
- Q12: However, the lack of detailed crash data analysis and site-specific audits indicates potential blind spots .
- Q13: The concerns regarding crash frequency, speeding, and noise on nearby roads appear most pronounced along certain corridors in Central Ohio .
- Q13: Specifically, the intersection of Renner Road and Hilliard Road, as well as Trabue Road and N .
- Q14: The potential for safety improvements on main roads or intersections in Columbus and Central Ohio to divert traffic onto residential streets is most evident along high-risk corridors identified by the High Injury Network
- Q14: To assess the impact on nearby residents, it would be essential to consider the following:
- Q15: For past or planned safety projects in Columbus/Central Ohio, specific construction impacts on nearby communities include detours, changes to home and school accessibility, and alterations to travel times .
- Q15: This integration aims to increase accessibility for all residents, particularly those who may be less familiar with public transit options .
- Q16: The Franklin County Local Systems map, particularly the intersection of Renner Road & Hilliard-Rome Road and Trabue Road & Wilson Road, is identified as high-priority areas based on crash frequency and severity .
- Q16: These high-crash locations are influenced by several local roadway and traffic characteristics:
- Q17: The areas of Columbus and Central Ohio most affected by congestion, queue spillback, or unreliable travel times for daily commutes include HIN corridors, particularly those identified as high-risk due to their anatomy of
- Q17: Specifically, the High Injury Network (HIN) corridors exhibit the anatomy of dangerous streets—wide, multi-lane streets which pose significant risks to vulnerable road users such as pedestrians and cyclists .
- Q18: To identify locations in Columbus/central Ohio where lane configuration, signage, signal timing, or interchange layout may confuse drivers or encourage speeding or risky lane changes, we need to examine specific corridor
- Q18: This suggests it might have problematic traffic configurations that could lead to confusion among drivers and potentially increase speeds or risky maneuvers .
- Q19: Where in Columbus/Central Ohio do pedestrian or cyclist crashes and near-misses cluster at crossings ?
- Q19: Pedestrian and cyclist crashes and near-misses cluster at intersections where there is a history of safety concerns .
- Q20: The existing data on sidewalk, bike facility, and accessible crossing conditions in Central Ohio is limited but provides some insights into areas needing improvement .
- Q20: However, this knowledge base does not contain counts, rates, locations, or trends, making it challenging to quantify the specific gaps affecting vulnerable road users (VRUs) such as older adults and people with disabilit
- Q21: In Columbus and Central Ohio, certain corridors and intersections are identified as having high vehicle speeds and volumes that make walking or cycling uncomfortable or unsafe .
- Q21: According to the Vision Zero Columbus Action Plan 1.0 (PDF page 35), HIN segments include high-risk areas where pedestrians and cyclists face significant safety challenges .
- Q22: The interaction between trucks and other road users such as cars, pedestrians, and cyclists creates significant crash risks in various locations across Columbus and Central Ohio .
- Q22: One notable area identified by the City of Columbus through its High Injury Network (HIN) program is the intersection of Renner Road and Hilliard Road, which experiences high frequency of fatal and serious injury crashes
- Q23: To address the safety concerns related to at-grade rail crossings in Columbus and Central Ohio, we need to examine specific locations and the existing plans and initiatives aimed at improving safety .
- Q23: The City of Columbus and MORPC are involved in various efforts to enhance safety along these crossings, particularly through the Safe Routes to School program and Vision Zero initiatives .
- Q24: The planned safety improvements in Columbus and Central Ohio, including lane reconfiguration, reduced roadway width, turning restrictions, and other design changes, could significantly impact freight access and operation
- Q24: For instance, under the COTSP, significant changes to infrastructure are being prioritized based on high-risk crash locations .
- Q25: To evaluate the outcome of the safety improvement project at the Columbus intersection based on the given information, we need to consider various aspects including crash reduction, severity of injuries, traffic delays, 
- Q25: Here’s an analysis from the perspective of State/Regional Transportation Agencies:
- Q26: From the perspective of the City of Columbus' Public Works department, the safety improvement project at the intersection of Renner Road & Hilliard Road and Trabue Road & N .
- Q26: Wilson Road has shown significant progress by reducing the number of annual crashes from 8 to 2 .
- Q27: Based on the information provided, it appears that the safety improvement project at an intersection in Columbus has shown promising results by reducing annual crash frequency from 8 to 2 incidents per year .
- Q27: However, the reduction in crash frequency masks significant concerns regarding the nature of the remaining crashes and their impact on nearby residents and communities .
- Q28: Based on the information provided, the safety improvement project at the intersection of Renner Road and Hilliard Road appears to have been effective in reducing crash frequency .
- Q28: The reduction from 8 to 2 crashes annually suggests an improvement in traffic safety .
- Q29: Based on the described safety improvement project at a Columbus intersection, the reduction from 8 to 2 annual crashes represents progress towards safer conditions for vulnerable road users (VRUs) .
- Q29: However, the persistence of serious injuries in these incidents highlights ongoing vulnerabilities and areas needing further attention .
- Q30: To evaluate the outcome of the safety improvement project from the perspective of Emergency Responders and Healthcare Providers, we need to consider the reduction in crash frequency and the nature of the remaining crashe
- Q30: They will need to ensure they are adequately prepared to handle such incidents, possibly through better training or resource allocation .
- Q31: From the perspective of public transit/mobility providers, the reduction in crash frequency from 8 to 2 per year is a positive development .
- Q31: However, the presence of serious injury crashes remains concerning .
- Q32: From the perspective of freight/rail operators, the reduction in annual crashes from 8 to 2 per year represents an important milestone towards improving safety at the intersection .
- Q32: While traffic delay has been alleviated, the concern remains regarding the two serious injury crashes involving pedestrians and cyclists .
- Q33: To determine if there are other Columbus/Central Ohio intersections where safety projects reduced total crashes and delays but left serious injury or pedestrian concerns unresolved, we need to look into specific examples
- Q33: However, this plan focuses more on identifying areas experiencing high frequency of fatal and serious injury crashes rather than detailed analysis of specific intersection improvements .
- Q34: To determine whether further action is warranted for a Columbus intersection similar to those mentioned in the scenario, the following local data sources need to be considered:
- Q34: Specifically, the intersections of Renner Road & Hilliard and Trabue Road & N .

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
| 1 | L1 | state | Prioritization | 0.25 | 1.00 | 0.09 | 100% | 0.87 | 0.50 | 9 | 12 | 3 | 90.1 |
| 2 | L1 | state | Local Context & Decision Making | 0.25 | 1.00 | 1.00 | 100% | 0.84 | 0.14 | 9 | 8 | 3 | 79.8 |
| 3 | L1 | state | Historical Precedents, Risks & Trade-offs | 0.50 | 1.00 | 0.11 | 100% | 0.82 | 0.57 | 4 | 7 | 1 | 87.7 |
| 4 | L1 | local | Implementation Feasibility / Infrastructure Conditions | 0.00 | 0.00 | 0.00 | 100% | 0.85 | 0.00 | 6 | 7 | 1 | 104.1 |
| 5 | L1 | local | Maintenance / Long-term Sustainability | 0.75 | 1.00 | 1.00 | 100% | 0.84 | 0.43 | 7 | 6 | 1 | 103.6 |
| 6 | L1 | local | Future Demand / Long-term Safety Performance | 0.50 | 1.00 | 0.50 | 100% | 0.84 | 0.86 | 9 | 5 | 4 | 90.5 |
| 7 | L1 | ems | Emergency Access / Response Time | 0.50 | 1.00 | 1.00 | 100% | 0.81 | 0.29 | 8 | 6 | 2 | 79.0 |
| 8 | L1 | ems | Safety Improvements vs. Emergency Operations | 0.33 | 1.00 | 0.50 | 100% | 0.83 | 0.83 | 11 | 5 | 1 | 95.6 |
| 9 | L1 | ems | Crash Severity / Post-Crash Response | 0.00 | 0.00 | 0.00 | 100% | 0.87 | 0.86 | 11 | 12 | 3 | 91.6 |
| 10 | L1 | transit | First / Last-Mile Safety & Access | 0.00 | 0.00 | 0.00 | 100% | 0.81 | 0.57 | 5 | 6 | 1 | 90.1 |
| 11 | L1 | transit | Value of Supporting Safety Projects | 0.00 | 0.00 | 0.00 | 100% | 0.83 | 0.43 | 9 | 9 | 1 | 103.9 |
| 12 | L1 | transit | Network Connectivity / Future Mobility Needs | 0.25 | 1.00 | 0.33 | 100% | 0.83 | 0.43 | 8 | 7 | 1 | 103.7 |
| 13 | L1 | resident | Safety & Quality of Life Near Homes | 0.40 | 1.00 | 0.10 | 100% | 0.83 | 0.71 | 6 | 11 | 3 | 114.2 |
| 14 | L1 | resident | Cut-Through Traffic & Neighborhood Impacts | 0.33 | 1.00 | 0.17 | 100% | 0.83 | 0.43 | 10 | 10 | 1 | 108.3 |
| 15 | L1 | resident | Construction Impacts & Community Engagement | 0.00 | 0.00 | 0.00 | 100% | 0.83 | 0.57 | 11 | 7 | 1 | 118.4 |
| 16 | L1 | driver | Crash Risk & Traffic Conflicts | 0.75 | 1.00 | 0.25 | 100% | 0.82 | 0.71 | 12 | 9 | 1 | 115.2 |
| 17 | L1 | driver | Delay, Queues & Travel-Time Reliability | 0.25 | 1.00 | 1.00 | 100% | 0.77 | 0.57 | 10 | 6 | 4 | 1036.5 |
| 18 | L1 | driver | Roadway Design Clarity & Driver Behavior | 0.25 | 1.00 | 0.10 | 100% | 0.84 | 0.86 | 6 | 10 | 4 | 100.2 |
| 19 | L1 | vru | Crossing Safety & Visibility | 0.50 | 1.00 | 1.00 | 100% | 0.86 | 0.57 | 7 | 8 | 4 | 110.0 |
| 20 | L1 | vru | Sidewalk / Path Continuity & Accessibility | 0.25 | 1.00 | 0.25 | 100% | 0.85 | 0.86 | 13 | 7 | 2 | 104.3 |
| 21 | L1 | vru | Separation from Vehicles & Comfort | 0.33 | 1.00 | 0.10 | 100% | 0.80 | 0.29 | 10 | 11 | 1 | 110.6 |
| 22 | L1 | freight | Truck Interactions & Freight Routes | 0.67 | 1.00 | 0.20 | 100% | 0.81 | 0.14 | 9 | 6 | 4 | 100.8 |
| 23 | L1 | freight | Rail Crossing Safety & Conflict Risk | 0.33 | 1.00 | 0.08 | 100% | 0.83 | 0.57 | 8 | 8 | 1 | 104.5 |
| 24 | L1 | freight | Freight Access & Operational Impact | 0.67 | 1.00 | 0.50 | 100% | 0.91 | 0.71 | 16 | 9 | 4 | 116.2 |
| 25 | L2 | state | Shared scenario | 0.25 | 1.00 | 0.08 | 100% | 0.93 | 1.00 | 3 | 9 | 4 | 127.8 |
| 26 | L2 | local | Shared scenario | 0.25 | 1.00 | 0.17 | 100% | 0.90 | 1.00 | 4 | 7 | 1 | 93.2 |
| 27 | L2 | resident | Shared scenario | 0.25 | 1.00 | 0.10 | 100% | 0.90 | 1.00 | 1 | 8 | 4 | 93.3 |
| 28 | L2 | driver | Shared scenario | 0.25 | 1.00 | 0.10 | 100% | 0.87 | 0.83 | 2 | 8 | 1 | 86.8 |
| 29 | L2 | vru | Shared scenario | 0.25 | 1.00 | 0.10 | 100% | 0.87 | 1.00 | 5 | 8 | 2 | 99.6 |
| 30 | L2 | ems | Shared scenario | 0.25 | 1.00 | 0.20 | 100% | 0.87 | 0.83 | 0 | 7 | 2 | 113.5 |
| 31 | L2 | transit | Shared scenario | 0.25 | 1.00 | 0.25 | 100% | 0.90 | 1.00 | 3 | 7 | 1 | 149.6 |
| 32 | L2 | freight | Shared scenario | 0.25 | 1.00 | 0.08 | 100% | 0.85 | 1.00 | 0 | 8 | 1 | 93.9 |
| 33 | L2-addon | all | Comparable Local Cases | 0.00 | 0.00 | 0.00 | 100% | 0.88 | 0.57 | 4 | 5 | 3 | 57.2 |
| 34 | L2-addon | all | Local Evidence for Follow-Up Action | 0.00 | 0.00 | 0.00 | 100% | 0.90 | 0.86 | 10 | 12 | 2 | 111.7 |
