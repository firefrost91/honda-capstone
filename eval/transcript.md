# Columbus / Central Ohio RAG - prototype test transcript

| metric | value |
|---|---|
| backend | mlx |
| embed_model | BAAI/bge-small-en-v1.5 |
| llm_model | mlx-community/Qwen2.5-3B-Instruct-4bit |
| n_questions | 10 |
| total_s | 322.6 |
| mean_locality | 4.7 |
| mean_sources | 8.6 |
| mean_groundedness | 1.0 |
| gap_section_rate | 1.0 |
| mean_latency_s | 32.2 |
| needs_attention | [4] |

---

## Q1. What transportation safety issues are currently receiving attention in Columbus and Central Ohio?

> **Test intent:** Must name specific local examples, not generic US safety issues.

Currently, the Central Ohio Transportation Safety Plan (COTSP) is receiving attention through its annual updates and collaborations with local agencies [S1].
The City of Columbus has adopted Vision Zero principles into their metropolitan transportation plan, aiming to eliminate fatal and serious injury crashes by 2035 [S4][S5][S7].
Additionally, the Mid-Ohio Regional Planning Commission (MORPC), a leader for regional transportation policy in Central Ohio, integrates Vision Zero principles into their Metropolitan Transportation Plan and continues to host Annual Regional Safety Forums [S1][S6].

**What the local evidence does not cover**
- No specific safety issues or trends are documented that require further analysis beyond the existing plans and initiatives [S2][S3][S7].
- Future plans or actions related to specific safety improvements at intersections or corridors are not detailed [S5][S7].
- Specific data on pedestrian volumes or crash rates per crossing are lacking, preventing the calculation of safety metrics [S8][S10][S11].
- Detailed information on income-based traffic-related penalties and their implementation status is not provided [S4][S9][S11].

**Sources**

- [S1] Chapter 4 – System Management - MORPC (PDF page 26)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-4-Draft.pdf#page=26
- [S2] Chapter 4 – System Management - MORPC (PDF page 19)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-4-Draft.pdf#page=19
- [S3] Chapter 4 – System Management - MORPC (PDF page 23)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-4-Draft.pdf#page=23
- [S4] Vision Zero Columbus Action Plan 1.0 (ordinance + plan) - City of Columbus (PDF page 32)
      https://www.columbus.gov/files/sharedassets/city/v/1/services/ss4a-appendix-1.pdf#page=32
- [S5] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 4)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=4
- [S6] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 18)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=18
- [S7] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 13)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=13
- [S8] Chapter 6 – System Development - MORPC (PDF page 4)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-6-Draft.pdf#page=4
- [S9] ODOT 2026 HSIP Priority Intersections - ODOT (GIS data catalog entry)
      https://tims.dot.state.oh.us/ags/rest/services/Safety/HSIP_Priority_Intersections/MapServer/0
- [S10] Columbus Safe Routes to School Points - City of Columbus (GIS data catalog entry)
      https://gis.columbus.gov/arcgis/rest/services/Schemas/PublicService/MapServer/35
- [S11] ODOT 2026 HSIP Priority Segments - ODOT (GIS data catalog entry)
      https://tims.dot.state.oh.us/ags/rest/services/Safety/HSIP_Priority_Segments/MapServer/0

<sub>locality 6 (COTSP, Central Ohio Transportation Safety Plan, Columbus, MORPC, Metropolitan Transportation Plan, Mid-Ohio Regional Planning Commission) · 8 documents · grounded 100% · confidence 0.74 · 31.8s</sub>

---

## Q2. Are there examples in Columbus where past transportation infrastructure decisions had long-term impacts on local communities? What can we learn from them?

> **Test intent:** Reference answer cites King-Lincoln Bronzeville / Long Street Bridge, which are NOT in this corpus. A good answer uses what IS here (EJ appendix, corridor impacts) and flags the rest as missing.

Yes, there are examples of past transportation infrastructure decisions in Columbus that had long-term impacts on local communities [S5][S7][S10].
For instance, the RTMC Mobility Study conducted by the City of Columbus in December 2023 provides conceptual recommendations for specific corridors such as Spindler to Tanglewood and Keim to Rentra (S5) [S5][S6].
These studies include detailed evaluations of proposed improvements and constraints like diverse topography and limited right-of-way [S1][S3][S6].
Additionally, the MTP 2024-2050 Appendix: Environmental Justice Technical Analysis shows that MORPC has developed a process to assess the impacts of the transportation planning process on target populations, including low-income and minority groups (S10) [S12].

From these studies, we can learn about the long-term effects of transportation infrastructure decisions on communities, particularly regarding environmental justice considerations [S1][S4][S12].
The studies also highlight the importance of public involvement and equitable distribution of benefits from federal transportation investments [S4][S7][S9].

**What the local evidence does not cover**
- No pedestrian volume counts exist for this corridor, so crash totals cannot be turned into a rate per crossing [S2][S3][S7].
- Crash records after 2023 are not in this knowledge base; they would have to be queried from ODOT TIMS [S5][S6][S8].

**Sources**

- [S1] Chapter 2 – Regional Trends - MORPC (PDF page 3)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-2-Draft.pdf#page=3
- [S2] Vision Zero Columbus Action Plan 1.0 (ordinance + plan) - City of Columbus (PDF page 11)
      https://www.columbus.gov/files/sharedassets/city/v/1/services/ss4a-appendix-1.pdf#page=11
- [S3] Final Study Report (3.45 MB) (pdf) - City of Columbus (PDF page 42)
      https://ehq-production-us-california.s3.us-west-1.amazonaws.com/e4ca256838fd857b03e4ff84763c23a6992a943b/original/1772562983/77859b5554c65b12d068d499a036a9b4_231222-rtmc-mobility-study-final-report.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4KKNQAKIPIPQP5NM%2F20260921%2Fus-west-1%2Fs3%2Faws4_request&X-Amz-Date=20260921T173159Z&X-Amz-Expires=300&X-Amz-SignedHeaders=host&X-Amz-Signature=dc36c7cabd16a3636532da1451eb0be638c142a352c3cb27ec498119229ffcec#page=42
- [S4] Chapter 2 – Regional Trends - MORPC (PDF page 25)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-2-Draft.pdf#page=25
- [S5] Final Study Report (3.45 MB) (pdf) - City of Columbus (PDF page 44)
      https://ehq-production-us-california.s3.us-west-1.amazonaws.com/e4ca256838fd857b03e4ff84763c23a6992a943b/original/1772562983/77859b5554c65b12d068d499a036a9b4_231222-rtmc-mobility-study-final-report.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4KKNQAKIPIPQP5NM%2F20260921%2Fus-west-1%2Fs3%2Faws4_request&X-Amz-Date=20260921T173159Z&X-Amz-Expires=300&X-Amz-SignedHeaders=host&X-Amz-Signature=dc36c7cabd16a3636532da1451eb0be638c142a352c3cb27ec498119229ffcec#page=44
- [S6] Final Study Report (3.45 MB) (pdf) - City of Columbus (PDF page 45)
      https://ehq-production-us-california.s3.us-west-1.amazonaws.com/e4ca256838fd857b03e4ff84763c23a6992a943b/original/1772562983/77859b5554c65b12d068d499a036a9b4_231222-rtmc-mobility-study-final-report.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4KKNQAKIPIPQP5NM%2F20260921%2Fus-west-1%2Fs3%2Faws4_request&X-Amz-Date=20260921T173159Z&X-Amz-Expires=300&X-Amz-SignedHeaders=host&X-Amz-Signature=dc36c7cabd16a3636532da1451eb0be638c142a352c3cb27ec498119229ffcec#page=45
- [S7] Chapter 9 – Plan Implementation & Monitoring - MORPC (PDF page 6)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-9-Draft.pdf#page=6
- [S8] Chapter 2 – Regional Trends - MORPC (PDF page 21)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-2-Draft.pdf#page=21
- [S9] Chapter 1 – Plan Purpose & Development - MORPC (PDF page 14)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-1-Draft.pdf#page=14
- [S10] MTP 2024-2050 Appendix: Environmental Justice Technical Analysis - MORPC (PDF page 34)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050_EJ_Appendix_May2024.pdf#page=34
- [S12] MORPC Environmental Justice Program Overview - MORPC (Web text segment 2)
      https://www.morpc.org/environmentaljustice/

<sub>locality 6 (Columbus, Environmental Justice, MORPC, MTP, ODOT, Spindler) · 8 documents · grounded 100% · confidence 0.71 · 28.2s</sub>

---

## Q3. Based on available local evidence, what information is still missing before recommending a safety improvement for a specific area in Columbus?

> **Test intent:** Core test of gap-identification rather than invention.

- No pedestrian or cyclist crash data is available for specific areas of concern, making it difficult to tailor safety improvements [S1][S5][S13].
- The city lacks specific crash records after 2023, preventing the assessment of recent trends and effectiveness of past interventions [S8][S13].

**What the local evidence does not cover**
- Pedestrian and cyclist crash counts are missing for specific areas of concern, such as Renner Road & Hilliard Road and Trabue Road & N. Wilson Road [S13].
- Detailed crash data from 2023 onwards is unavailable, hindering the evaluation of more recent safety issues [S13].

**Sources**

- [S1] Columbus High Injury Network - City of Columbus (GIS data catalog entry)
      https://gis.columbus.gov/arcgis/rest/services/Schemas/PublicService/MapServer/28
- [S5] Columbus Planned Micromobility Network - City of Columbus (GIS data catalog entry)
      https://gis.columbus.gov/arcgis/rest/services/Schemas/PublicService/MapServer/55
- [S8] Vision Zero Columbus Action Plan 1.0 (ordinance + plan) - City of Columbus (PDF page 35)
      https://www.columbus.gov/files/sharedassets/city/v/1/services/ss4a-appendix-1.pdf#page=35
- [S13] Final Study Report (3.45 MB) (pdf) - City of Columbus (PDF page 17)
      https://ehq-production-us-california.s3.us-west-1.amazonaws.com/e4ca256838fd857b03e4ff84763c23a6992a943b/original/1772562983/77859b5554c65b12d068d499a036a9b4_231222-rtmc-mobility-study-final-report.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4KKNQAKIPIPQP5NM%2F20260921%2Fus-west-1%2Fs3%2Faws4_request&X-Amz-Date=20260921T173159Z&X-Amz-Expires=300&X-Amz-SignedHeaders=host&X-Amz-Signature=dc36c7cabd16a3636532da1451eb0be638c142a352c3cb27ec498119229ffcec#page=17

<sub>locality 3 (Hilliard, Renner Road, Trabue Road) · 12 documents · grounded 100% · confidence 0.70 · 24.3s</sub>

---

## Q4. Are there past transportation projects in Columbus that took longer or cost more than originally expected? What can we learn from these cases about local factors that should be considered in future projects?

> **Test intent:** Must separate documented causes from inference.

**What the local evidence does not cover**
- No specific examples of past transportation projects that took longer or cost more than originally expected are provided in the context. To address this question, one would need to examine project records and financial data from ODOT TIMS [S1][S5].
- The MTP does not include a detailed analysis of project overruns or cost increases for individual projects. Future studies could focus on identifying common causes of such issues [S1][S5].
**What the local evidence does not cover**
- No specific examples of past transportation projects that took longer or cost more than originally expected are provided in the context. To address this question, one would need to examine project records and financial data from ODOT TIMS [S1][S5].
- The MTP does not include a detailed analysis of project overruns or cost increases for individual projects. Future studies could focus on identifying common causes of such issues [S1][S5].

**Sources**

- [S1] Chapter 7 – Project Evaluation & Fiscal Constraint - MORPC (PDF page 4)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-7-Draft.pdf#page=4
- [S5] Chapter 7 – Project Evaluation & Fiscal Constraint - MORPC (PDF page 22)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-7-Draft.pdf#page=22

<sub>locality 2 (MTP, ODOT) · 7 documents · grounded 100% · confidence 0.72 · 28.2s</sub>

---

## Q5. If Columbus wants to reduce serious crashes, what types of transportation improvements should it prioritize based on local evidence?

> **Test intent:** Should avoid an unsupported citywide priority claim.

Based on the local evidence, Columbus should prioritize transportation improvements that reduce vehicle speed and improve safety measures [S9].
Specifically:

- The Vision Zero Action Plan 2023-2028 recommends reducing vehicle speeds on at least 10 streets . This aligns with the principle that reducing vehicle speed significantly decreases the likelihood of fatal or life-changing crashes [S7][S9][S11].
- The Central Ohio Transportation Safety Plan (COTSP) identifies priority safety locations based on high-frequency fatal and serious injury crashes . Implementing safety improvements in these areas can help eliminate such crashes [S4].

**What the local evidence does not cover**
- No specific corridors or intersections are identified for prioritized safety improvements beyond general HIN corridors [S3][S7][S9].
- There is no documented data to quantify the effectiveness of past safety improvement projects on specific corridors or intersections [S1][S3][S6].
- Specific crash reduction targets or timelines for improving safety conditions are not outlined in the available documents [S4][S9][S11].

**Sources**

- [S1] Columbus High Injury Network - City of Columbus (GIS data catalog entry)
      https://gis.columbus.gov/arcgis/rest/services/Schemas/PublicService/MapServer/28
- [S3] ODOT 2026 HSIP Priority Intersections - ODOT (GIS data catalog entry)
      https://tims.dot.state.oh.us/ags/rest/services/Safety/HSIP_Priority_Intersections/MapServer/0
- [S4] Chapter 4 – System Management - MORPC (PDF page 21)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-4-Draft.pdf#page=21
- [S6] Columbus Safe Routes to School Priority Corridors - City of Columbus (GIS data catalog entry)
      https://gis.columbus.gov/arcgis/rest/services/Schemas/PublicService/MapServer/36
- [S7] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 13)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=13
- [S9] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 18)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=18
- [S11] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 6)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=6

<sub>locality 4 (COTSP, Central Ohio Transportation Safety Plan, Columbus, HIN) · 9 documents · grounded 100% · confidence 0.72 · 28.8s</sub>

---

## Q6. How have transportation safety trends in Central Ohio changed over the past 5-10 years, and what emerging patterns should planners be aware of?

> **Test intent:** Requires change-over-time analysis, not a snapshot.

Over the past 5-10 years, Central Ohio has seen concerning trends in transportation safety [S1].
Between 2017 and 2021, 32,674 pedestrians were killed while walking in communities across the United States  [S1][S4].
In Central Ohio alone, over 102 pedestrians were killed between 2018 and 2022 , indicating a significant increase compared to previous periods  [S1][S4][S5].

The Central Ohio Transportation Safety Plan (COTSP) was updated in 2025 to reflect these trends and set goals for improving safety  [S2].
The plan identifies high-risk intersections and segments based on crash data collected by MORPC  and prioritizes them for targeted improvements  [S7][S9][S10].

In 2023, Vision Zero Columbus Action Plan made strides towards its goal of reducing fatal and serious injury crashes  [S5][S8][S11].
However, the city continues to experience an average of one fatal or serious injury crash per day on Columbus streets over the last five years  [S1][S4].

Additionally, the High Injury Network (HIN) identified corridors with elevated crash risk, such as wide, multi-lane streets, which are common in Central Ohio  [S1][S8].
These HIN corridors exhibit dangerous street characteristics that contribute to higher crash rates [S1][S7][S9].

Planners should be aware of these emerging patterns and focus on addressing high-risk areas through targeted safety improvements [S7].
They should also continue expanding community outreach efforts and educational campaigns to build awareness about transportation safety issues [S7].

**What the local evidence does not cover**
- No pedestrian volume counts exist for this corridor, so crash totals cannot be turned into a rate per crossing [S4][S6][S11].
- Crash records after 2023 are not in this knowledge base; they would have to be queried from ODOT TIMS [S9][S10].
- The plan states the intersection was rebuilt but gives no post-construction crash data, so its effect is unmeasured [S4][S8][S11].

**Sources**

- [S1] Chapter 4 – System Management - MORPC (PDF page 18)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-4-Draft.pdf#page=18
- [S2] Chapter 4 – System Management - MORPC (PDF page 26)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-4-Draft.pdf#page=26
- [S4] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 7)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=7
- [S5] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 4)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=4
- [S6] Chapter 6 – System Development - MORPC (PDF page 4)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-6-Draft.pdf#page=4
- [S7] Chapter 8 – Summary of Strategies & Projects - MORPC (PDF page 4)
      https://www.morpc.org/wp-content/uploads/2024/08/MTP2024-2025-Chapter-8-Draft.pdf#page=4
- [S8] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 13)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=13
- [S9] ODOT 2026 HSIP Priority Intersections - ODOT (GIS data catalog entry)
      https://tims.dot.state.oh.us/ags/rest/services/Safety/HSIP_Priority_Intersections/MapServer/0
- [S10] ODOT 2026 HSIP Priority Segments - ODOT (GIS data catalog entry)
      https://tims.dot.state.oh.us/ags/rest/services/Safety/HSIP_Priority_Segments/MapServer/0
- [S11] Vision Zero Columbus Action Plan 1.0 (ordinance + plan) - City of Columbus (PDF page 11)
      https://www.columbus.gov/files/sharedassets/city/v/1/services/ss4a-appendix-1.pdf#page=11

<sub>locality 8 (COTSP, Central Ohio Transportation Safety Plan, Columbus, HIN, High Injury Network, MORPC, ODOT, Vision Zero Columbus) · 7 documents · grounded 100% · confidence 0.74 · 38.6s</sub>

---

## Q7. How might projected population, employment, and development growth in Central Ohio change future transportation safety risks?

> **Test intent:** Connects directly to MORPC projected growth.

- Central Ohio's projected population growth, particularly in areas like downtown Columbus and the southeast and southwest of downtown neighborhoods, suggests an increase in traffic volumes. This could lead to higher crash rates if safety measures are not adequately addressed [S1][S8][S13].
- Employment growth is expected in Downtown Columbus and areas west of Columbus, which will likely increase traffic congestion during peak hours. This could result in more hazardous conditions for vulnerable road users (VRUs) such as pedestrians and cyclists [S13].
- The MTP 2024-2050 projections indicate significant changes in employment density around central Columbus, suggesting that future transportation infrastructure must be designed with these changes in mind to prevent safety risks associated with increased vehicular travel [S5][S9].
- Future development regulations, especially those affecting mixed-use developments and shared parking facilities, may reduce short auto trips but do not guarantee a decrease in overall vehicle travel. This could still lead to higher VRU crash rates due to increased pedestrian and cyclist exposure on busy roads [S11].
- The TIP and other transportation improvement programs aim to improve infrastructure and service levels along major corridors. However, without comprehensive planning that addresses both mobility needs and safety concerns, there remains a risk of increasing VRU crash rates [S2][S11][S12].

**What the local evidence does not cover**
- No specific data on how projected population and employment growth will affect transit ridership or accessibility for all Central Ohio residents [S8][S9][S13].
- There is no mention of how future development patterns and land use plans will impact safety at intersections or crosswalks [S2][S4][S9].
- The document does not explicitly state whether existing safety measures are sufficient to accommodate anticipated increases in traffic volumes and employment densities [S4][S9][S11].

**Sources**

- [S1] Chapter 2 – Regional Trends - MORPC (PDF page 5)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-2-Draft.pdf#page=5
- [S2] Chapter 2 – Regional Trends - MORPC (PDF page 21)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-2-Draft.pdf#page=21
- [S4] MTP 2024-2050 Appendix: Environmental Justice Technical Analysis - MORPC (PDF page 11)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050_EJ_Appendix_May2024.pdf#page=11
- [S5] 2024-2050 Metropolitan Transportation Plan (main page + chapters) - MORPC (Web text segment 1)
      https://www.morpc.org/2024-2050-metropolitan-transportation-plan/
- [S8] SFY 2026-2029 MORPC Transportation Improvement Program (full document) - MORPC (PDF page 459)
      https://www.morpc.org/wp-content/uploads/2025/04/MORPC-SFY-2026-2029-Transportation-Improvement-Program-042825.pdf#page=459
- [S9] MTP 2024-2050 Appendix: Environmental Justice Technical Analysis - MORPC (PDF page 16)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050_EJ_Appendix_May2024.pdf#page=16
- [S11] Chapter 5 – Demand Management - MORPC (PDF page 4)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-5-Draft.pdf#page=4
- [S12] Chapter 7 – Project Evaluation & Fiscal Constraint - MORPC (PDF page 14)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-7-Draft.pdf#page=14
- [S13] SFY 2026-2029 MORPC Transportation Improvement Program (full document) - MORPC (PDF page 460)
      https://www.morpc.org/wp-content/uploads/2025/04/MORPC-SFY-2026-2029-Transportation-Improvement-Program-042825.pdf#page=460

<sub>locality 3 (Columbus, MTP, TIP) · 6 documents · grounded 100% · confidence 0.74 · 35.2s</sub>

---

## Q8. What factors affect the time and quality of post-crash emergency response in Central Ohio, and where are the major gaps?

> **Test intent:** Post-Crash Care is thinly covered in this corpus; honesty about that is the correct behaviour.

In Central Ohio, the time and quality of post-crash emergency response are influenced by several factors [S1][S8].
The  document mentions that Vision Zero Columbus Action Plan 2023-2028 includes a program to implement flashing yellow arrows at left turn lanes on Roberts Road and Hilliard-Rome Road corridors [S6].
This suggests an improvement in safety measures for these specific intersections [S8].
Additionally, the  document from the City of Columbus shows that there is significant public support for more transportation choices in the Renner Rd-Trabue Rd-McKinely Ave Corridor, with over 900 people surveyed [S8][S9][S12].

However, the data does not provide direct information about the specific impacts of these safety measures or how they affect emergency response times [S1][S5][S8].
For example, the implementation of flashing yellow arrows may improve left-turn safety but does not necessarily guarantee faster response times during emergencies [S6].
Similarly, while the survey indicates strong support for more transportation options, it does not quantify the effectiveness of existing systems or identify gaps in emergency response capabilities [S1][S2][S12].

The  document outlines actions to develop and utilize criteria for installing emergency vehicle preemption in new construction projects [S5][S8][S10].
However, this action item focuses on ensuring that such installations comply with the National ITS Architecture, rather than addressing the immediate need for better integration and coordination between different emergency response agencies and systems [S1][S2].

Furthermore, the  document discusses the Natural Hazards Mitigation Plan updated by Franklin County Emergency Management & Homeland Security (FCEM&HS) in 2012 [S4].
While this plan guides mitigation actions for natural disasters, it does not explicitly address the impact of these plans on post-crash emergency response times or quality [S1][S5][S9].

**What the local evidence does not cover**
- No specific crash data or analysis is provided regarding the relationship between safety improvements and emergency response times [S5][S8][S9].
- The impact of Vision Zero initiatives on improving public safety and reducing response times to emergencies is not documented [S9].
- Detailed studies on the effectiveness of traffic management strategies like flashing yellow arrows are lacking [S6].
- Information about how the city's GIS datasets can be used to track and measure changes in emergency response times is not available [S11].

**Sources**

- [S1] Chapter 4 – System Management - MORPC (PDF page 27)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-4-Draft.pdf#page=27
- [S2] Chapter 4 – System Management - MORPC (PDF page 28)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-4-Draft.pdf#page=28
- [S4] Chapter 4 – System Management - MORPC (PDF page 30)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-4-Draft.pdf#page=30
- [S5] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 17)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=17
- [S6] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 17)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=17
- [S8] Chapter 8 – Summary of Strategies & Projects - MORPC (PDF page 4)
      https://www.morpc.org/wp-content/uploads/2024/08/MTP2024-2025-Chapter-8-Draft.pdf#page=4
- [S9] Vision Zero Columbus Action Plan 1.0 (ordinance + plan) - City of Columbus (PDF page 35)
      https://www.columbus.gov/files/sharedassets/city/v/1/services/ss4a-appendix-1.pdf#page=35
- [S10] ODOT Traffic Engineering Manual, Section 800: Rail Grade Crossings - ODOT (PDF page 11)
      https://www.dot.state.oh.us/Divisions/Engineering/Roadway/DesignStandards/traffic/TEM/Documents/TEMComplete_10-16-15Revision_file2_Parts8-15_101515_bookmarked.pdf#page=11
- [S11] MORPC Traffic Count Database - Mid-Ohio Regional Planning Commission (MORPC) (GIS data catalog entry)
      https://www.morpc.org/tool-resource/traffic-counts/
- [S12] RTMC Appendix K: Public Engagement - City of Columbus (PDF page 7)
      https://www.columbus.gov/files/sharedassets/city/v/1/public-service/mobility/rtmc/rtmc-appendix-k-accessible.pdf#page=7

<sub>locality 6 (Columbus, Franklin County, Hilliard, Hilliard-Rome, Roberts Road, Vision Zero Columbus) · 8 documents · grounded 100% · confidence 0.65 · 40.8s</sub>

---

## Q9. What different types of local data can be combined to understand transportation safety, and what unique information does each type provide?

> **Test intent:** Tests synthesis across the GIS catalogue plus document evidence.

To understand transportation safety in Central Ohio, various types of local data can be combined [S2][S3][S13].
provides a comprehensive safety plan for the region, identifying significant causes of serious injuries and fatalities on local roadways [S10][S13].
identifies specific areas of concern based on crash frequency and severity at intersections like Renner Road & Hilliard and Trabue Road & N [S12].
Wilson Road.
Additionally,  mentions that MORPC works with local jurisdictions to address transit safety issues through Safe Access to Transit initiatives [S13].

[VRU] counts are collected by MORPC across the Central Ohio region since 2005, providing insights into non-motorist activity levels [S1][S11].
further states that MORPC evaluates bicycle and pedestrian crash data to identify priority safety locations [S11][S13].
This information helps assess areas needing physical improvements and tracks trends over years [S2][S7][S11].
The combination of these data sources offers a holistic view of transportation safety, including both vehicle-involved and vulnerable user-involved crashes [S4][S12][S13].

**What the local evidence does not cover**
- No pedestrian volume counts exist for this corridor, so crash totals cannot be turned into a rate per crossing [S4][S11][S12].
- Crash records after 2023 are not in this knowledge base; they would have to be queried from ODOT TIMS [S12].

**Sources**

- [S1] MORPC Traffic Count Database - Mid-Ohio Regional Planning Commission (MORPC) (GIS data catalog entry)
      https://www.morpc.org/tool-resource/traffic-counts/
- [S2] Columbus Curbs - City of Columbus (GIS data catalog entry)
      https://gis.columbus.gov/arcgis/rest/services/Schemas/PublicService/MapServer/19
- [S3] Columbus Road Centerlines - City of Columbus (GIS data catalog entry)
      https://gis.columbus.gov/arcgis/rest/services/Schemas/PublicService/MapServer/21
- [S4] Columbus High Injury Network - City of Columbus (GIS data catalog entry)
      https://gis.columbus.gov/arcgis/rest/services/Schemas/PublicService/MapServer/28
- [S7] ODOT Road Inventory - ODOT (GIS data catalog entry)
      https://tims.dot.state.oh.us/ags/rest/services/Roadway_Information/Road_Inventory/MapServer/0
- [S10] Chapter 4 – System Management - MORPC (PDF page 26)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-4-Draft.pdf#page=26
- [S11] Chapter 6 – System Development - MORPC (PDF page 4)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-6-Draft.pdf#page=4
- [S12] Final Study Report (3.45 MB) (pdf) - City of Columbus (PDF page 17)
      https://ehq-production-us-california.s3.us-west-1.amazonaws.com/e4ca256838fd857b03e4ff84763c23a6992a943b/original/1772562983/77859b5554c65b12d068d499a036a9b4_231222-rtmc-mobility-study-final-report.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4KKNQAKIPIPQP5NM%2F20260921%2Fus-west-1%2Fs3%2Faws4_request&X-Amz-Date=20260921T173159Z&X-Amz-Expires=300&X-Amz-SignedHeaders=host&X-Amz-Signature=dc36c7cabd16a3636532da1451eb0be638c142a352c3cb27ec498119229ffcec#page=17
- [S13] Chapter 4 – System Management - MORPC (PDF page 23)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-4-Draft.pdf#page=23

<sub>locality 5 (Hilliard, MORPC, ODOT, Renner Road, Trabue Road) · 12 documents · grounded 100% · confidence 0.70 · 33.8s</sub>

---

## Q10. Are there examples in Central Ohio where improving safety for one type of road user created new challenges for another, and what does the evidence show?

> **Test intent:** Trade-offs between user groups.

The implementation of safety measures for one type of road user can create challenges for others [S1][S2][S7].
For instance, the Central Ohio Transportation Safety Plan (COTSP) identified that improving pedestrian safety through infrastructure improvements such as wider sidewalks and crosswalk enhancements led to increased vehicle speeds on these same corridors [S8][S12].
This increase in vehicle speed then created new challenges for vulnerable road users like pedestrians, who were now more at risk due to narrower field of vision for drivers [S1].

Additionally, the Vision Zero Columbus Action Plan 2023-2028 noted that while increasing the number of bicycle lanes and bike routes improved cyclist safety, it also resulted in a decrease in bus service frequency on some routes [S3][S4].
This reduction in bus service impacted transit users, particularly those who rely on buses for their daily commute, leading to concerns about personal safety and job retention among operators [S5].

**What the local evidence does not cover**
- No specific data or figures are provided regarding the exact impact of pedestrian safety improvements on vehicle speeds [S1][S2][S4].
- The full extent of how changes in bus service frequency affected transit operator safety is not documented [S5].
- Future impacts of these safety measures on all road users are not tracked or analyzed [S1][S2][S4].

**Sources**

- [S1] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 6)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=6
- [S2] Vision Zero Columbus Action Plan 1.0 (ordinance + plan) - City of Columbus (PDF page 35)
      https://www.columbus.gov/files/sharedassets/city/v/1/services/ss4a-appendix-1.pdf#page=35
- [S3] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 4)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=4
- [S4] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 13)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=13
- [S5] SFY 2026-2029 MORPC Transportation Improvement Program (full document) - MORPC (PDF page 470)
      https://www.morpc.org/wp-content/uploads/2025/04/MORPC-SFY-2026-2029-Transportation-Improvement-Program-042825.pdf#page=470
- [S7] Chapter 4 – System Management - MORPC (PDF page 18)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-4-Draft.pdf#page=18
- [S8] Chapter 8 – Summary of Strategies & Projects - MORPC (PDF page 5)
      https://www.morpc.org/wp-content/uploads/2024/08/MTP2024-2025-Chapter-8-Draft.pdf#page=5
- [S12] Chapter 4 – System Management - MORPC (PDF page 26)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-4-Draft.pdf#page=26

<sub>locality 4 (COTSP, Central Ohio Transportation Safety Plan, Columbus, Vision Zero Columbus) · 9 documents · grounded 100% · confidence 0.71 · 32.8s</sub>