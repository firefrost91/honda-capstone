# Columbus / Central Ohio RAG - prototype test transcript

| metric | value |
|---|---|
| backend | mlx |
| embed_model | BAAI/bge-small-en-v1.5 |
| llm_model | mlx-community/Qwen2.5-3B-Instruct-4bit |
| n_questions | 10 |
| total_s | 700.4 |
| mean_locality | 7.5 |
| mean_sources | 8.5 |
| mean_groundedness | 1.0 |
| gap_section_rate | 1.0 |
| mean_latency_s | 70.0 |
| needs_attention | [] |

---

## Q1. What transportation safety issues are currently receiving attention in Columbus and Central Ohio?

> **Test intent:** Must name specific local examples, not generic US safety issues.

The transportation safety issues currently receiving attention in Columbus and Central Ohio are primarily focused on high-risk intersections and segments, as well as specific corridors and infrastructure improvements [S1][S2][S11].
The Mid-Ohio Regional Planning Commission (MORPC) is working to address these issues through various plans and initiatives [S1][S2][S7].

One of the key areas of focus is the implementation of countermeasures at priority locations identified by ODOT's Highway Safety Improvement Program (HSIP) [S9][S10].
For instance, MORPC has integrated Vision Zero principles into its Metropolitan Transportation Plan and continues to host annual regional safety forums [S1][S2][S7].
These forums serve as platforms for advocating for public policies supporting Vision Zero principles and emphasizing safety improvements in federal transportation funding criteria [S4][S6][S8].

Additionally, MORPC collaborates with local agencies such as COTA and the City of Columbus on projects like the Safe Routes to School Program [S1][S2].
This program aims to improve pedestrian safety throughout the city by advancing $4 million in pedestrian improvements [S2][S11][S13].
Furthermore, the city continues to build Complete Street Infrastructure, which includes proven measures to decrease speeds and separate vulnerable road users, such as those found along transit routes and school zones [S11][S13].

Specifically, the High Injury Network (HIN) corridors that exhibit dangerous street characteristics—wide, multi-lane streets—are prioritized for targeted safety improvements [S8][S9][S11].
For example, HIN corridor 283, located between East Broad Street and East Third Street, is a focal point for safety efforts [S8][S11][S12].
The city also focuses on enhancing connectivity of traffic signals and cameras to further improve safety, particularly in high-risk areas [S2][S11].

Furthermore, the Central Ohio Transportation Safety Plan (COTSP), developed by MORPC, serves as a comprehensive safety plan that identifies critical safety priorities and sets benchmarks for improvement [S1].
The plan addresses various aspects of transportation safety, including transit safety, bicycle and pedestrian counts, and crash data analysis [S11].
MORPC regularly evaluates pedestrian- and bicyclist-involved crashes and identifies priority safety locations for further study, helping to identify areas needing physical safety improvements [S2][S5].

In summary, the transportation safety issues currently receiving attention in Columbus and Central Ohio include high-risk intersections and segments identified through ODOT's HSIP, specific corridors like HIN corridor 283, and infrastructure improvements such as Complete Street Infrastructure and enhanced traffic signal connectivity [S2][S9][S11].
These efforts are coordinated through plans and initiatives led by local agencies and organizations, with a focus on implementing countermeasures at priority locations to reduce serious injuries and fatalities [S2][S11].

**What the local evidence does not cover**
- Specific educational initiatives and their impacts on regional safety emphasis areas are not quantified or tracked here [S2][S3][S11].

**Sources**

- [S1] Chapter 4 – System Management - MORPC (PDF page 26)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-4-Draft.pdf#page=26
- [S2] Chapter 4 – System Management - MORPC (PDF page 23)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-4-Draft.pdf#page=23
- [S3] Chapter 4 – System Management - MORPC (PDF page 19)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-4-Draft.pdf#page=19
- [S4] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 4)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=4
- [S5] Chapter 6 – System Development - MORPC (PDF page 4)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-6-Draft.pdf#page=4
- [S6] Vision Zero Columbus Action Plan 1.0 (ordinance + plan) - City of Columbus (PDF page 32)
      https://www.columbus.gov/files/sharedassets/city/v/1/services/ss4a-appendix-1.pdf#page=32
- [S7] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 18)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=18
- [S8] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 13)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=13
- [S9] ODOT 2026 HSIP Priority Intersections - ODOT (GIS data catalog entry)
      https://tims.dot.state.oh.us/ags/rest/services/Safety/HSIP_Priority_Intersections/MapServer/0
- [S10] ODOT 2026 HSIP Priority Segments - ODOT (GIS data catalog entry)
      https://tims.dot.state.oh.us/ags/rest/services/Safety/HSIP_Priority_Segments/MapServer/0
- [S11] Chapter 8 – Summary of Strategies & Projects - MORPC (PDF page 4)
      https://www.morpc.org/wp-content/uploads/2024/08/MTP2024-2025-Chapter-8-Draft.pdf#page=4
- [S12] Vision Zero Columbus Action Plan 1.0 (ordinance + plan) - City of Columbus (PDF page 22)
      https://www.columbus.gov/files/sharedassets/city/v/1/services/ss4a-appendix-1.pdf#page=22
- [S13] Vision Zero Columbus Action Plan 1.0 (ordinance + plan) - City of Columbus (PDF page 23)
      https://www.columbus.gov/files/sharedassets/city/v/1/services/ss4a-appendix-1.pdf#page=23

<sub>locality 12 (COTA, COTSP, Central Ohio Transportation Safety Plan, Columbus, HIN, HSIP, High Injury Network, MORPC, Metropolitan Transportation Plan, Mid-Ohio Regional Planning Commission, ODOT, Safe Routes to School) · 7 documents · grounded 100% · confidence 0.74 · 75.7s</sub>

---

## Q2. Are there examples in Columbus where past transportation infrastructure decisions had long-term impacts on local communities? What can we learn from them?

> **Test intent:** Reference answer cites King-Lincoln Bronzeville / Long Street Bridge, which are NOT in this corpus. A good answer uses what IS here (EJ appendix, corridor impacts) and flags the rest as missing.

The context provided does not explicitly detail specific examples of long-term impacts from past transportation infrastructure decisions in Central Ohio [S4][S9][S12].
However, we can infer some relevant information based on the documents and their focus on safety, equity, and community engagement [S5][S9][S10].

One notable example is the RTMC Mobility Study (Section 16), which evaluates corridor conditions and future conditions for the Spindler to Tanglewood route [S4][S8].
The study highlights challenges such as diverse topography, limited right-of-way, railroad crossings, and multiple bridges [S8][S9][S10].
Despite these constraints, the document suggests that future improvements will require additional feasibility analysis and potential alterations to existing concepts [S8].
This indicates a recognition of the need for adaptive planning due to the complex nature of the corridor [S6][S8][S10].

Another relevant example is the Vision Zero Columbus Action Plan (pages 4-5) [S2][S3][S11].
The plan outlines strategies aimed at reducing traffic fatalities and serious injuries through various means, including increasing pedestrian and cyclist infrastructure [S10][S11].
For instance, BP 7: Ensure neighborhoods and activity centers have safe and comfortable connections for walking and bicycling to transit networks [S10].
This strategy underscores the importance of ensuring equitable access to safe transportation options across the city [S6][S7][S10].

Furthermore, the MTP 2024-2050 Appendix: Environmental Justice Technical Analysis (page 34) mentions the Central Ohio area's transportation expansion investments, indicating significant funding for both maintenance and major projects [S12].
While this does not directly address long-term impacts, it reflects the substantial investment in infrastructure over time [S1][S9][S12].

From these examples, we can learn that past decisions have had lasting implications on communities, particularly regarding safety and accessibility [S1][S8][S9].
The context emphasizes the need for community engagement and equity in transportation planning, suggesting that future infrastructure decisions should prioritize sustainable development and equitable access [S6][S7].
Additionally, recognizing the complexity of corridors like the Spindler to Tanglewood route highlights the necessity of adaptive planning to accommodate diverse challenges [S8][S10].

**What the local evidence does not cover**
- No specific examples of long-term impacts from past transportation infrastructure decisions are provided [S4][S6][S12].
- There are no documented studies or analyses focusing solely on the long-term effects of past decisions on particular communities [S1][S9][S12].
- Future plans do not explicitly outline strategies to mitigate negative impacts from previous infrastructure choices [S9][S10][S12].

**Sources**

- [S1] Chapter 2 – Regional Trends - MORPC (PDF page 3)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-2-Draft.pdf#page=3
- [S2] Vision Zero Columbus Action Plan 1.0 (ordinance + plan) - City of Columbus (PDF page 11)
      https://www.columbus.gov/files/sharedassets/city/v/1/services/ss4a-appendix-1.pdf#page=11
- [S3] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 4)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=4
- [S4] Final Study Report (3.45 MB) (pdf) - City of Columbus (PDF page 44)
      https://ehq-production-us-california.s3.us-west-1.amazonaws.com/e4ca256838fd857b03e4ff84763c23a6992a943b/original/1772562983/77859b5554c65b12d068d499a036a9b4_231222-rtmc-mobility-study-final-report.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4KKNQAKIPIPQP5NM%2F20260921%2Fus-west-1%2Fs3%2Faws4_request&X-Amz-Date=20260921T173159Z&X-Amz-Expires=300&X-Amz-SignedHeaders=host&X-Amz-Signature=dc36c7cabd16a3636532da1451eb0be638c142a352c3cb27ec498119229ffcec#page=44
- [S5] Final Study Report (3.45 MB) (pdf) - City of Columbus (PDF page 26)
      https://ehq-production-us-california.s3.us-west-1.amazonaws.com/e4ca256838fd857b03e4ff84763c23a6992a943b/original/1772562983/77859b5554c65b12d068d499a036a9b4_231222-rtmc-mobility-study-final-report.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4KKNQAKIPIPQP5NM%2F20260921%2Fus-west-1%2Fs3%2Faws4_request&X-Amz-Date=20260921T173159Z&X-Amz-Expires=300&X-Amz-SignedHeaders=host&X-Amz-Signature=dc36c7cabd16a3636532da1451eb0be638c142a352c3cb27ec498119229ffcec#page=26
- [S6] Chapter 9 – Plan Implementation & Monitoring - MORPC (PDF page 6)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-9-Draft.pdf#page=6
- [S7] Chapter 1 – Plan Purpose & Development - MORPC (PDF page 14)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-1-Draft.pdf#page=14
- [S8] Final Study Report (3.45 MB) (pdf) - City of Columbus (PDF page 45)
      https://ehq-production-us-california.s3.us-west-1.amazonaws.com/e4ca256838fd857b03e4ff84763c23a6992a943b/original/1772562983/77859b5554c65b12d068d499a036a9b4_231222-rtmc-mobility-study-final-report.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4KKNQAKIPIPQP5NM%2F20260921%2Fus-west-1%2Fs3%2Faws4_request&X-Amz-Date=20260921T173159Z&X-Amz-Expires=300&X-Amz-SignedHeaders=host&X-Amz-Signature=dc36c7cabd16a3636532da1451eb0be638c142a352c3cb27ec498119229ffcec#page=45
- [S9] Chapter 2 – Regional Trends - MORPC (PDF page 25)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-2-Draft.pdf#page=25
- [S10] Chapter 8 – Summary of Strategies & Projects - MORPC (PDF page 5)
      https://www.morpc.org/wp-content/uploads/2024/08/MTP2024-2025-Chapter-8-Draft.pdf#page=5
- [S11] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 13)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=13
- [S12] MTP 2024-2050 Appendix: Environmental Justice Technical Analysis - MORPC (PDF page 34)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050_EJ_Appendix_May2024.pdf#page=34

<sub>locality 5 (Columbus, Environmental Justice, MTP, Spindler, Vision Zero Columbus) · 8 documents · grounded 100% · confidence 0.71 · 61.1s</sub>

---

## Q3. Based on available local evidence, what information is still missing before recommending a safety improvement for a specific area in Columbus?

> **Test intent:** Core test of gap-identification rather than invention.

Based on the available local evidence, several critical pieces of information are still missing before recommending a safety improvement for specific areas in Columbus [S7][S12][S13].
Specifically:

- **Intersection Safety Data**: The source document mentions concerns at intersections such as Renner Road & Hilliard and Trabue Road & N. Wilson Road due to crash frequency and severity. However, there is no detailed intersection-specific data or analysis that would help prioritize these locations further. Without this intersection-level data, it is difficult to target improvements effectively [S4][S11].

- **Pedestrian and Cyclist Crash Patterns**: While the study identified areas of concern based on crash frequency and severity, including McKinley Avenue from just north of Lake Shore Drive to Fisher Road, there is no specific mention of pedestrian and cyclist crash patterns within these areas. Understanding where these crashes occur more frequently can guide targeted interventions [S11].

- **Public Engagement Feedback**: Although public engagement was conducted through an open house meeting, the responses were not systematically analyzed or documented. This means that while feedback was collected, its implications for future conditions assessment have not been fully explored. Comprehensive analysis of the public comments could provide valuable insights into community needs and priorities [S12].

**What the local evidence does not cover**
- No pedestrian volume counts exist for these corridors, so crash totals cannot be turned into a rate per crossing [S2][S9][S11].
- There is no specific mention of intersection safety data or intersection-level crash patterns at Renner Road & Hilliard and Trabue Road & N. Wilson Road [S11].
- Public engagement responses generated during the open house meeting are not systematically analyzed, leaving room for further detailed interpretation of community feedback [S12].

**Sources**

- [S2] Columbus High Injury Network - City of Columbus (GIS data catalog entry)
      https://gis.columbus.gov/arcgis/rest/services/Schemas/PublicService/MapServer/28
- [S4] ODOT 2026 HSIP Priority Intersections - ODOT (GIS data catalog entry)
      https://tims.dot.state.oh.us/ags/rest/services/Safety/HSIP_Priority_Intersections/MapServer/0
- [S7] Vision Zero Columbus Action Plan 1.0 (ordinance + plan) - City of Columbus (PDF page 35)
      https://www.columbus.gov/files/sharedassets/city/v/1/services/ss4a-appendix-1.pdf#page=35
- [S9] MORPC Traffic Count Database - Mid-Ohio Regional Planning Commission (MORPC) (GIS data catalog entry)
      https://www.morpc.org/tool-resource/traffic-counts/
- [S11] Final Study Report (3.45 MB) (pdf) - City of Columbus (PDF page 17)
      https://ehq-production-us-california.s3.us-west-1.amazonaws.com/e4ca256838fd857b03e4ff84763c23a6992a943b/original/1772562983/77859b5554c65b12d068d499a036a9b4_231222-rtmc-mobility-study-final-report.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4KKNQAKIPIPQP5NM%2F20260921%2Fus-west-1%2Fs3%2Faws4_request&X-Amz-Date=20260921T173159Z&X-Amz-Expires=300&X-Amz-SignedHeaders=host&X-Amz-Signature=dc36c7cabd16a3636532da1451eb0be638c142a352c3cb27ec498119229ffcec#page=17
- [S12] Final Study Report (3.45 MB) (pdf) - City of Columbus (PDF page 26)
      https://ehq-production-us-california.s3.us-west-1.amazonaws.com/e4ca256838fd857b03e4ff84763c23a6992a943b/original/1772562983/77859b5554c65b12d068d499a036a9b4_231222-rtmc-mobility-study-final-report.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4KKNQAKIPIPQP5NM%2F20260921%2Fus-west-1%2Fs3%2Faws4_request&X-Amz-Date=20260921T173159Z&X-Amz-Expires=300&X-Amz-SignedHeaders=host&X-Amz-Signature=dc36c7cabd16a3636532da1451eb0be638c142a352c3cb27ec498119229ffcec#page=26
- [S13] Chapter 8 – Summary of Strategies & Projects - MORPC (PDF page 4)
      https://www.morpc.org/wp-content/uploads/2024/08/MTP2024-2025-Chapter-8-Draft.pdf#page=4

<sub>locality 5 (Columbus, Hilliard, McKinley Avenue, Renner Road, Trabue Road) · 12 documents · grounded 100% · confidence 0.70 · 48.5s</sub>

---

## Q4. Are there past transportation projects in Columbus that took longer or cost more than originally expected? What can we learn from these cases about local factors that should be considered in future projects?

> **Test intent:** Must separate documented causes from inference.

To determine if there are past transportation projects in Columbus that took longer or cost more than originally expected, we need to examine specific examples from the provided documents [S9][S10][S12].
The MTP 2024-2050 Appendix: Environmental Justice Technical Analysis (S10) mentions a technical analysis for environmental justice impacts but does not provide direct evidence of overruns or delays [S11].

However, S8 provides an example of projected improvements and evaluation for the intersection study [S9].
While it does not explicitly mention costs or timelines, it describes conceptual plans for various improvements including widened freeways, lane management additions, and modified intersections [S9][S10].
These improvements suggest significant investments in infrastructure, which could potentially lead to cost overruns or schedule delays due to unforeseen complexities during implementation [S1][S10][S12].

Additionally, S9 details the RTMC Mobility Study, which outlines proposed improvements at intersections [S9].
The source document notes that while some improvements were recommended, others were dismissed due to physical constraints [S9].
This suggests that future projects may face similar challenges related to feasibility and budgeting constraints [S1][S5][S10].

Furthermore, S10 lists several projects with estimated costs and time periods [S5][S10][S12].
For instance, the "Unmapped/Grouped Projects" section includes items such as widening freeways, adding lanes, and modifying intersections [S9][S10][S12].
However, these sections do not include detailed information on actual project outcomes or cost overruns [S5][S9][S12].

Given these observations, we can infer that local factors such as physical constraints, unexpected engineering issues, and changes in community support or land use plans could significantly impact the timeline and budget of transportation projects [S1][S2][S6].
Future projects should therefore be carefully scoped and monitored to account for potential delays and increased costs [S1][S5][S10].

**What the local evidence does not cover**
- No specific examples of past projects that took longer or cost more than originally expected are provided [S1][S5][S10].
- Detailed data on actual project outcomes and cost overruns is lacking from the documents [S1][S5][S9].
- Information on how specific local conditions influenced project timelines and budgets is not documented [S1][S5][S8].

**Sources**

- [S1] Chapter 7 – Project Evaluation & Fiscal Constraint - MORPC (PDF page 4)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-7-Draft.pdf#page=4
- [S2] Chapter 2 – Regional Trends - MORPC (PDF page 5)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-2-Draft.pdf#page=5
- [S5] Chapter 7 – Project Evaluation & Fiscal Constraint - MORPC (PDF page 22)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-7-Draft.pdf#page=22
- [S6] Chapter 2 – Regional Trends - MORPC (PDF page 21)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-2-Draft.pdf#page=21
- [S8] Chapter 2 – Regional Trends - MORPC (PDF page 6)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-2-Draft.pdf#page=6
- [S9] Final Study Report (3.45 MB) (pdf) - City of Columbus (PDF page 42)
      https://ehq-production-us-california.s3.us-west-1.amazonaws.com/e4ca256838fd857b03e4ff84763c23a6992a943b/original/1772562983/77859b5554c65b12d068d499a036a9b4_231222-rtmc-mobility-study-final-report.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4KKNQAKIPIPQP5NM%2F20260921%2Fus-west-1%2Fs3%2Faws4_request&X-Amz-Date=20260921T173159Z&X-Amz-Expires=300&X-Amz-SignedHeaders=host&X-Amz-Signature=dc36c7cabd16a3636532da1451eb0be638c142a352c3cb27ec498119229ffcec#page=42
- [S10] Chapter 8 – Summary of Strategies & Projects - MORPC (PDF page 8)
      https://www.morpc.org/wp-content/uploads/2024/08/MTP2024-2025-Chapter-8-Draft.pdf#page=8
- [S11] MTP 2024-2050 Appendix: Environmental Justice Technical Analysis - MORPC (PDF page 34)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050_EJ_Appendix_May2024.pdf#page=34
- [S12] Chapter 8 – Summary of Strategies & Projects - MORPC (PDF page 9)
      https://www.morpc.org/wp-content/uploads/2024/08/MTP2024-2025-Chapter-8-Draft.pdf#page=9

<sub>locality 3 (Columbus, Environmental Justice, MTP) · 7 documents · grounded 100% · confidence 0.73 · 56.8s</sub>

---

## Q5. If Columbus wants to reduce serious crashes, what types of transportation improvements should it prioritize based on local evidence?

> **Test intent:** Should avoid an unsupported citywide priority claim.

If Columbus wants to reduce serious crashes, it should prioritize transportation improvements based on the existing evidence and plans [S3][S5][S7].
The High Injury Network (HIN) map, identified by the Central Ohio Transportation Safety Plan (COTSP), highlights corridors with concentrated severe crashes [S9].
Specifically, the HIN includes high-risk intersections such as Renner Road & Hilliard Road and Trabue Road & N [S9][S10][S12].
Wilson Road.
Additionally, McKinley Avenue from just north of Lake Shore Drive to Fisher Road has experienced two serious crashes over a three-year period [S12].

The Vision Zero Action Plan 2023-2028 emphasizes systemic change towards safety for all users, including pedestrians, cyclists, motorists, and transit users [S4][S6][S7].
It focuses on redundancy in safety measures, particularly reducing crash severity through factors like vehicle speed [S6][S11].
Given these priorities, Columbus should focus on implementing countermeasures that address priority safety locations, especially those highlighted by the HIN map and COTSP [S8].
This includes:

1. **Traffic Calming Measures**: Implement traffic calming measures at high-risk intersections such as Renner Road & Hilliard Road and Trabue Road & N [S6][S10][S11].
Wilson Road.
These could include speed humps, narrowed lanes, and raised crossings to slow down vehicles [S6][S11].

2. **Pedestrian and Bicycle Infrastructure**: Enhance pedestrian and bicycle infrastructure along McKinley Avenue and other high-risk areas [S4][S6][S11].
This might include adding crosswalks, bike lanes, and protected bike routes to improve safety for vulnerable road users [S4][S6][S11].

3. **Speed Management**: Address excessive speeds on wide, multi-lane streets identified as HIN corridors [S4][S6][S11].
Speed management strategies such as traffic calming measures, reduced speed limits, and enforcement can help reduce the risk of serious crashes [S6][S8][S11].

4. **Public Awareness Campaigns**: Continue community outreach efforts to raise awareness about the importance of safe driving practices and encourage a culture of transportation safety [S3][S4][S11].
Public campaigns can be effective in changing attitudes towards safety and accountability [S3][S4][S11].

5. **Data-Driven Decision Making**: Utilize data from ODOT's HSIP Priority Intersections and the Vision Zero Action Plan to target specific areas for improvement [S2][S3][S10].
The city should focus resources on implementing countermeasures at priority locations based on crash frequency and severity [S8][S11].

By prioritizing these improvements, Columbus can make significant strides toward reducing serious crashes and achieving its vision of zero fatal and serious injury crashes by 2035 [S4][S6][S7].

**What the local evidence does not cover**
- There are no specific areas of concern identified for crashes involving pedestrians and cyclists, which limits targeted improvements [S3][S6][S12].

**Sources**

- [S2] Vision Zero Columbus Action Plan 1.0 (ordinance + plan) - City of Columbus (PDF page 33)
      https://www.columbus.gov/files/sharedassets/city/v/1/services/ss4a-appendix-1.pdf#page=33
- [S3] Vision Zero Columbus Action Plan 1.0 (ordinance + plan) - City of Columbus (PDF page 35)
      https://www.columbus.gov/files/sharedassets/city/v/1/services/ss4a-appendix-1.pdf#page=35
- [S4] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 13)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=13
- [S5] Vision Zero Columbus Action Plan 1.0 (ordinance + plan) - City of Columbus (PDF page 39)
      https://www.columbus.gov/files/sharedassets/city/v/1/services/ss4a-appendix-1.pdf#page=39
- [S6] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 6)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=6
- [S7] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 4)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=4
- [S8] Chapter 4 – System Management - MORPC (PDF page 21)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-4-Draft.pdf#page=21
- [S9] Vision Zero Columbus High Injury Network Map - City of Columbus (source catalog entry)
      https://vision-zero-columbus.hub.arcgis.com/maps/10084bf09a9e4180838832300dba4da7
- [S10] ODOT 2026 HSIP Priority Intersections - ODOT (GIS data catalog entry)
      https://tims.dot.state.oh.us/ags/rest/services/Safety/HSIP_Priority_Intersections/MapServer/0
- [S11] Chapter 8 – Summary of Strategies & Projects - MORPC (PDF page 4)
      https://www.morpc.org/wp-content/uploads/2024/08/MTP2024-2025-Chapter-8-Draft.pdf#page=4
- [S12] Final Study Report (3.45 MB) (pdf) - City of Columbus (PDF page 17)
      https://ehq-production-us-california.s3.us-west-1.amazonaws.com/e4ca256838fd857b03e4ff84763c23a6992a943b/original/1772562983/77859b5554c65b12d068d499a036a9b4_231222-rtmc-mobility-study-final-report.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4KKNQAKIPIPQP5NM%2F20260921%2Fus-west-1%2Fs3%2Faws4_request&X-Amz-Date=20260921T173159Z&X-Amz-Expires=300&X-Amz-SignedHeaders=host&X-Amz-Signature=dc36c7cabd16a3636532da1451eb0be638c142a352c3cb27ec498119229ffcec#page=17

<sub>locality 11 (COTSP, Central Ohio Transportation Safety Plan, Columbus, HIN, HSIP, High Injury Network, Hilliard, McKinley Avenue, ODOT, Renner Road, Trabue Road) · 8 documents · grounded 100% · confidence 0.72 · 102.5s</sub>

---

## Q6. How have transportation safety trends in Central Ohio changed over the past 5-10 years, and what emerging patterns should planners be aware of?

> **Test intent:** Requires change-over-time analysis, not a snapshot.

To understand transportation safety trends in Central Ohio over the past 5-10 years, we need to examine specific data and plans that have been updated or revised during this period [S1][S2][S10].
The Metropolitan Transportation Plan (MTP) provides a comprehensive overview of safety trends from 2017 to 2022 [S1][S2][S10].
According to MORPC's report on the MTP, there were significant changes in crash numbers and types [S1][S2][S9].
Specifically, while the total number of crashes decreased by nearly 20% compared to the previous five-year span (2018-2022), the proportion of individuals who were seriously injured increased by 21%, and the proportion of those who died increased by 62% [S1].
This suggests an increase in both the severity and frequency of serious injuries and fatalities [S1][S10].

Additionally, the Vision Zero Columbus Action Plan, which was developed based on the MTP, has also highlighted these trends [S6][S8].
For instance, the plan notes that vulnerable road users accounted for less than 6% of all commuters but made up 53% of all crash fatalities [S1][S7].
This indicates a disproportionate impact on pedestrians and cyclists [S1][S7][S12].
Furthermore, the HIN corridors identified as having dangerous street characteristics—wide, multi-lane streets—have shown high rates of fatal and serious injury crashes [S1][S10].
These findings suggest that planners should be particularly vigilant about these high-risk areas [S1][S4][S10].

The Central Ohio Transportation Safety Plan (COTSP) is another important document that outlines specific strategies and benchmarks for improving transportation safety [S3].
The COTSP identifies priority safety locations and focuses on eliminating fatal and serious injury crashes [S3][S10].
However, it does not include post-construction crash data for the intersection mentioned in S4, meaning its effectiveness cannot be fully measured [S10][S11][S12].
Given this gap, planners need to ensure continuous monitoring and evaluation of safety improvements [S1][S10][S12].

In summary, while there have been some decreases in total crash numbers, the trend towards more severe injuries and deaths remains concerning [S1].
Planners must focus on high-risk areas such as HIN corridors and prioritize safety measures to address these emerging patterns effectively [S10].

**What the local evidence does not cover**
- The Central Ohio Transportation Safety Plan (COTSP) does not include specific benchmarks or measures for reducing fatalities and serious injuries in HIN corridors [S3].

**Sources**

- [S1] Chapter 4 – System Management - MORPC (PDF page 18)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-4-Draft.pdf#page=18
- [S2] Chapter 4 – System Management - MORPC (PDF page 19)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-4-Draft.pdf#page=19
- [S3] Chapter 4 – System Management - MORPC (PDF page 26)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-4-Draft.pdf#page=26
- [S4] ODOT 2026 HSIP Priority Intersections - ODOT (GIS data catalog entry)
      https://tims.dot.state.oh.us/ags/rest/services/Safety/HSIP_Priority_Intersections/MapServer/0
- [S6] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 4)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=4
- [S7] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 7)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=7
- [S8] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 13)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=13
- [S9] Chapter 6 – System Development - MORPC (PDF page 4)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-6-Draft.pdf#page=4
- [S10] Chapter 8 – Summary of Strategies & Projects - MORPC (PDF page 4)
      https://www.morpc.org/wp-content/uploads/2024/08/MTP2024-2025-Chapter-8-Draft.pdf#page=4
- [S11] ODOT Crash Data - 2023 - ODOT (GIS data catalog entry)
      https://tims.dot.state.oh.us/ags/rest/services/Safety/2023_Crash_Locations/MapServer/0
- [S12] Vision Zero Columbus Action Plan 1.0 (ordinance + plan) - City of Columbus (PDF page 35)
      https://www.columbus.gov/files/sharedassets/city/v/1/services/ss4a-appendix-1.pdf#page=35

<sub>locality 8 (COTSP, Central Ohio Transportation Safety Plan, Columbus, HIN, MORPC, MTP, Metropolitan Transportation Plan, Vision Zero Columbus) · 8 documents · grounded 100% · confidence 0.73 · 93.0s</sub>

---

## Q7. How might projected population, employment, and development growth in Central Ohio change future transportation safety risks?

> **Test intent:** Connects directly to MORPC projected growth.

The projected population, employment, and development growth in Central Ohio suggest significant changes that could impact future transportation safety risks [S1][S3][S5].
The MTP 2024-2050 projections indicate substantial increases in population and employment density, particularly in downtown Columbus and the southeast and southwest neighborhoods of downtown [S5][S9][S13].
These areas are expected to see significant population growth due to job centers such as Intel's investment in Licking County [S1][S8][S13].

Additionally, the MTP projects a shift towards more mixed-use development patterns, which aligns with strategies outlined by MORPC to reduce short non-vehicular trips through updated zoning codes [S5][S7][S11].
This transition is crucial for enhancing safety on streets and reducing reliance on personal vehicles [S2][S9][S11].
However, the implementation of these plans requires careful coordination among various stakeholders including COTA, MORPC, ODOT, New Albany City Council, and Licking County officials [S8].

Furthermore, the MTP also includes measures aimed at improving accessibility to transit services [S5][S9][S11].
For instance, Figure 12 from the SFY 2026-2029 MORPC Transportation Improvement Program (full document) shows an increase in population density near New Albany, where Intel Corporation plans to invest over $20 billion [S8].
This growth necessitates robust planning to ensure equitable access to this new job center [S1][S3][S13].
The MTP aims to achieve this through comprehensive public engagement processes and strategic investments in infrastructure improvements [S5][S7][S9].

However, the MTP does not explicitly detail how future transportation systems will mitigate safety risks associated with increased vehicular traffic and pedestrian exposure [S4][S9].
The SRTS program mentioned in the MTP Appendix suggests that Safe Routes to School initiatives could improve safety along school routes but do not address broader urban areas [S5][S7][S9].
Additionally, while the TIP (Transportation Improvement Program) funds roadwork and other infrastructure improvements, it does not systematically assess or prioritize safety enhancements based on projected growth patterns [S12].

The HIN (High Injury Network) data from Vision Zero Columbus action plans highlight specific intersections and corridors prone to high injury rates [S4][S5][S9].
However, without detailed crash records for future projections beyond 2023, it is unclear how these findings will be incorporated into long-term planning strategies [S3][S4][S9].
Future studies should focus on identifying high-risk corridors and developing targeted interventions to reduce safety risks as Central Ohio experiences continued growth and development [S1][S5][S11].

**What the local evidence does not cover**
- Future projections of population and employment growth do not include specific metrics on vulnerable road user (VRU) safety impacts [S3][S4][S9].

**Sources**

- [S1] Chapter 2 – Regional Trends - MORPC (PDF page 5)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-2-Draft.pdf#page=5
- [S2] Chapter 2 – Regional Trends - MORPC (PDF page 21)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-2-Draft.pdf#page=21
- [S3] Chapter 2 – Regional Trends - MORPC (PDF page 6)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-2-Draft.pdf#page=6
- [S4] MTP 2024-2050 Appendix: Environmental Justice Technical Analysis - MORPC (PDF page 11)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050_EJ_Appendix_May2024.pdf#page=11
- [S5] 2024-2050 Metropolitan Transportation Plan (main page + chapters) - MORPC (Web text segment 1)
      https://www.morpc.org/2024-2050-metropolitan-transportation-plan/
- [S7] 2024-2050 Metropolitan Transportation Plan (main page + chapters) - MORPC (Web text segment 2)
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

<sub>locality 12 (COTA, Columbus, HIN, High Injury Network, Licking County, MORPC, MTP, ODOT, Safe Routes to School, TIP, Transportation Improvement Program, Vision Zero Columbus) · 6 documents · grounded 100% · confidence 0.74 · 79.7s</sub>

---

## Q8. What factors affect the time and quality of post-crash emergency response in Central Ohio, and where are the major gaps?

> **Test intent:** Post-Crash Care is thinly covered in this corpus; honesty about that is the correct behaviour.

The time and quality of post-crash emergency response in Central Ohio are significantly influenced by the availability and accessibility of data, as well as the effectiveness of planning strategies [S1][S5][S12].
The City of Columbus's Vision Zero Action Plan 2023-2028 emphasizes transparency and accountability, which includes collecting and analyzing a wide range of data to better understand safety issues [S7].
However, there is no specific mention of how this data is collected or where it is stored for post-crash response times [S5][S7][S11].

Additionally, the RTMC Mobility Study conducted on October 9, 2023, at the Franklin County Engineer Maintenance Facility highlights the importance of public engagement [S11].
While the study involved gathering comments from the public, these responses were not analyzed further regarding their impact on improving emergency response times [S10][S11].
There is a gap in understanding whether the gathered feedback led to actionable changes that could improve response times [S10][S11][S12].

Furthermore, the implementation of countermeasures such as reducing speed limits and incorporating new speed limit standards on HIN corridors (High Injury Network) suggests an effort towards enhancing safety but does not explicitly address the immediate need for more efficient and timely emergency response procedures [S1][S5][S12].
The lack of detailed analysis on how these measures affect response times indicates another area requiring further investigation [S11].

Lastly, while the city aims to increase the use of ITS technologies like HAAS Alert Collision Prevention and flashing yellow arrows, the document does not detail how these systems are integrated into the broader emergency response process [S6][S8].
This integration is crucial for ensuring that emergency responders can effectively utilize these technologies during incidents to reduce response times [S1][S3][S5].

**What the local evidence does not cover**
- No specific mention exists regarding how crash data collected through various plans and studies are utilized to inform and improve emergency response times [S7].
- Detailed analyses of how public engagement efforts have impacted post-crash response times are lacking [S7][S10][S11].
- Implementation details of countermeasures like reduced speed limits and new speed limit standards on HIN corridors do not include any discussion on their effect on emergency response times [S8][S12].
- Integration of Intelligent Transportation Systems (ITS) technologies with emergency response processes is not documented or analyzed [S1][S3][S9].

**Sources**

- [S1] Chapter 4 – System Management - MORPC (PDF page 27)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-4-Draft.pdf#page=27
- [S3] Chapter 4 – System Management - MORPC (PDF page 28)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-4-Draft.pdf#page=28
- [S5] Chapter 8 – Summary of Strategies & Projects - MORPC (PDF page 4)
      https://www.morpc.org/wp-content/uploads/2024/08/MTP2024-2025-Chapter-8-Draft.pdf#page=4
- [S6] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 17)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=17
- [S7] Vision Zero Columbus Action Plan 1.0 (ordinance + plan) - City of Columbus (PDF page 35)
      https://www.columbus.gov/files/sharedassets/city/v/1/services/ss4a-appendix-1.pdf#page=35
- [S8] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 17)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=17
- [S9] SFY 2026-2029 MORPC Transportation Improvement Program (full document) - MORPC (PDF page 74)
      https://www.morpc.org/wp-content/uploads/2025/04/MORPC-SFY-2026-2029-Transportation-Improvement-Program-042825.pdf#page=74
- [S10] RTMC Appendix K: Public Engagement - City of Columbus (PDF page 7)
      https://www.columbus.gov/files/sharedassets/city/v/1/public-service/mobility/rtmc/rtmc-appendix-k-accessible.pdf#page=7
- [S11] Final Study Report (3.45 MB) (pdf) - City of Columbus (PDF page 26)
      https://ehq-production-us-california.s3.us-west-1.amazonaws.com/e4ca256838fd857b03e4ff84763c23a6992a943b/original/1772562983/77859b5554c65b12d068d499a036a9b4_231222-rtmc-mobility-study-final-report.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4KKNQAKIPIPQP5NM%2F20260921%2Fus-west-1%2Fs3%2Faws4_request&X-Amz-Date=20260921T173159Z&X-Amz-Expires=300&X-Amz-SignedHeaders=host&X-Amz-Signature=dc36c7cabd16a3636532da1451eb0be638c142a352c3cb27ec498119229ffcec#page=26
- [S12] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 18)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=18

<sub>locality 4 (Columbus, Franklin County, HIN, High Injury Network) · 7 documents · grounded 100% · confidence 0.66 · 42.7s</sub>

---

## Q9. What different types of local data can be combined to understand transportation safety, and what unique information does each type provide?

> **Test intent:** Tests synthesis across the GIS catalogue plus document evidence.

To understand transportation safety in Central Ohio, various types of local data can be combined to provide a comprehensive view [S4][S5][S12].
The City of Columbus maintains GIS datasets such as the Columbus Curbs, Columbus Guardrails, and Columbus Active Micromobility Network, which offer insights into infrastructure and active transportation facilities [S1][S8].
For instance, the Columbus Curbs dataset provides information on curb locations and conditions, helping to assess their impact on pedestrian safety [S1].
Similarly, the Columbus Guardrails dataset reveals the distribution and condition of guardrails along roads, aiding in understanding how they mitigate crash severity [S3].

The City of Columbus also compiles data from the ODOT Crash Data - 2023 dataset, which contains public crash records for 2023 [S7].
This data is crucial for identifying areas with high crash frequency and severity [S2][S4][S10].
Specifically, the intersection of Renner Road & Hilliard and Trabue Road & N [S10].
Wilson Road were identified as areas of concern based on crash history [S10].
By combining this data with the city's active transportation network (Columbus Active Micromobility Network), planners can gain insight into where these crashes are occurring relative to shared-use paths and sidewalks, providing context on how different modes of transportation interact and contribute to safety issues [S8].

Furthermore, the Central Ohio Transportation Safety Plan (COTSP) serves as a framework for improving safety throughout the region [S13].
Developed by MORPC in collaboration with local agencies, the COTSP identifies significant causes of serious injuries and fatalities on local roadways [S13].
The plan establishes goals and benchmarks for safety improvements and sets up a collaborative framework for enhancing regional safety [S9][S13].
For example, the city's efforts to collect bicycle and pedestrian volume counts through automated devices and short-duration counts provide valuable information on non-motorist activity levels [S11][S12].
These data points help identify trends and prioritize areas for safety improvements [S2][S9].

By integrating datasets such as those from the City of Columbus and MORPC, planners can create a more holistic understanding of transportation safety in Central Ohio [S11][S12][S13].
GIS datasets offer detailed infrastructure information, while crash records and census data on active transportation facilities provide insights into specific crash locations and volumes [S4][S7][S10].
This comprehensive approach enables planners to target interventions effectively and measure their impact over time [S9].

**What the local evidence does not cover**
- Specific trends and volumes of active transportation users on shared-use paths and sidewalks are not quantified, limiting the city's ability to target safety improvements effectively [S8][S9][S12].

**Sources**

- [S1] Columbus Curbs - City of Columbus (GIS data catalog entry)
      https://gis.columbus.gov/arcgis/rest/services/Schemas/PublicService/MapServer/19
- [S2] ODOT 2026 HSIP Priority Segments - ODOT (GIS data catalog entry)
      https://tims.dot.state.oh.us/ags/rest/services/Safety/HSIP_Priority_Segments/MapServer/0
- [S3] Columbus Guardrails - City of Columbus (GIS data catalog entry)
      https://gis.columbus.gov/arcgis/rest/services/Schemas/PublicService/MapServer/18
- [S4] Columbus High Injury Network - City of Columbus (GIS data catalog entry)
      https://gis.columbus.gov/arcgis/rest/services/Schemas/PublicService/MapServer/28
- [S5] Columbus Road Centerlines - City of Columbus (GIS data catalog entry)
      https://gis.columbus.gov/arcgis/rest/services/Schemas/PublicService/MapServer/21
- [S7] ODOT Crash Data - 2023 - ODOT (GIS data catalog entry)
      https://tims.dot.state.oh.us/ags/rest/services/Safety/2023_Crash_Locations/MapServer/0
- [S8] Columbus Active Micromobility Network - City of Columbus (GIS data catalog entry)
      https://gis.columbus.gov/arcgis/rest/services/Schemas/PublicService/MapServer/54
- [S9] Vision Zero Columbus Action Plan 1.0 (ordinance + plan) - City of Columbus (PDF page 35)
      https://www.columbus.gov/files/sharedassets/city/v/1/services/ss4a-appendix-1.pdf#page=35
- [S10] Final Study Report (3.45 MB) (pdf) - City of Columbus (PDF page 17)
      https://ehq-production-us-california.s3.us-west-1.amazonaws.com/e4ca256838fd857b03e4ff84763c23a6992a943b/original/1772562983/77859b5554c65b12d068d499a036a9b4_231222-rtmc-mobility-study-final-report.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4KKNQAKIPIPQP5NM%2F20260921%2Fus-west-1%2Fs3%2Faws4_request&X-Amz-Date=20260921T173159Z&X-Amz-Expires=300&X-Amz-SignedHeaders=host&X-Amz-Signature=dc36c7cabd16a3636532da1451eb0be638c142a352c3cb27ec498119229ffcec#page=17
- [S11] Chapter 6 – System Development - MORPC (PDF page 4)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-6-Draft.pdf#page=4
- [S12] Chapter 6 – System Development - MORPC (PDF page 3)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-6-Draft.pdf#page=3
- [S13] Chapter 4 – System Management - MORPC (PDF page 26)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-4-Draft.pdf#page=26

<sub>locality 8 (COTSP, Central Ohio Transportation Safety Plan, Columbus, Hilliard, MORPC, ODOT, Renner Road, Trabue Road) · 12 documents · grounded 100% · confidence 0.70 · 70.0s</sub>

---

## Q10. Are there examples in Central Ohio where improving safety for one type of road user created new challenges for another, and what does the evidence show?

> **Test intent:** Trade-offs between user groups.

The evidence from Central Ohio demonstrates that improving safety for one type of road user can create new challenges for another [S2][S8][S12].
One notable example is the implementation of the Central Ohio Greenways, which serves as the backbone of the bicycle network and consists primarily of north-south trails or multi-use paths along the region's five major waterways [S7][S12].

In 2009, MORPC (Mid-Ohio Regional Planning Commission) and local partners created a Bike User Map for the region, both in printed map form and an interactive online version [S6][S7].
The map was based on Bicycle Level-of-Comfort (LOC) data, illustrating the usability and comfort of roads for bicycling [S7].
Public input was also used to verify and finalize the information presented on the map [S1][S7][S12].
The LOC categorizes road conditions into Good, Moderate, Poor, and Residential designations [S7].

However, this infrastructure improvement led to increased pedestrian activity along these greenways [S12].
According to the Vision Zero Columbus Action Plan 2023-2028, vulnerable road users accounted for only 6% of all commuters but represented 53% of all crash fatalities [S4][S5].
This highlights the need for additional safety measures to protect pedestrians who are using the newly improved bike facilities [S6][S8][S12].

Additionally, the City of Columbus' COTA (Central Ohio Transit Authority) operators expressed concerns about reduced route frequency impacting their personal safety [S9].
With schedule changes leading to fewer service offerings, operators faced challenges ensuring adequate coverage for passengers, particularly during peak hours when more people use public transit [S9].
These issues underscored the interconnected nature of transportation planning and highlighted how improvements for one user group can affect another [S12].

Furthermore, the implementation of the Central Ohio Greenways network has resulted in significant increases in non-motorist traffic [S6][S7][S12].
The High Injury Network dataset catalog entry indicates that high-injury roadway segments with crash totals and vulnerable road user crash counts have been identified through regular evaluations by MORPC [S3].
This data supports the notion that while improving bicycle infrastructure enhances comfort and safety for cyclists, it also necessitates corresponding enhancements to ensure pedestrian safety and accessibility [S7][S12].

In summary, the Central Ohio Greenways project exemplifies how improvements for one type of road user (bicyclists) create new challenges for another (pedestrians), emphasizing the importance of comprehensive and coordinated transportation planning to address these interdependencies effectively [S12].

**What the local evidence does not cover**
- The High Injury Network dataset catalog entry indicates that high-injury roadway segments with crash totals and vulnerable road user crash counts have been identified through regular evaluations by MORPC. However, the records of these crashes are NOT loaded here, making it impossible to compute rates or trends from them [S3].
- While the Vision Zero Action Plan mentions increased non-motorist activity along greenways, specific data on how this impacts pedestrian safety is lacking, as the records of pedestrian crashes are not included in the knowledge base [S2][S4][S5].

**Sources**

- [S1] Vision Zero Columbus Action Plan 1.0 (ordinance + plan) - City of Columbus (PDF page 35)
      https://www.columbus.gov/files/sharedassets/city/v/1/services/ss4a-appendix-1.pdf#page=35
- [S2] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 6)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=6
- [S3] Columbus High Injury Network - City of Columbus (GIS data catalog entry)
      https://gis.columbus.gov/arcgis/rest/services/Schemas/PublicService/MapServer/28
- [S4] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 7)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=7
- [S5] Vision Zero Columbus Action Plan 2023-2028 - City of Columbus (PDF page 4)
      https://www.columbus.gov/files/sharedassets/city/v/1/design-amp-construction/contractor-information/vision-zero-home/vision-zero-columbus-action-plan-2023-2028.pdf#page=4
- [S6] Chapter 6 – System Development - MORPC (PDF page 4)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-6-Draft.pdf#page=4
- [S7] Chapter 3 – The Transportation System - MORPC (PDF page 9)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-3-Draft.pdf#page=9
- [S8] Chapter 4 – System Management - MORPC (PDF page 18)
      https://www.morpc.org/wp-content/uploads/2024/05/MTP2024-2050-Chapter-4-Draft.pdf#page=18
- [S9] SFY 2026-2029 MORPC Transportation Improvement Program (full document) - MORPC (PDF page 470)
      https://www.morpc.org/wp-content/uploads/2025/04/MORPC-SFY-2026-2029-Transportation-Improvement-Program-042825.pdf#page=470
- [S12] Chapter 8 – Summary of Strategies & Projects - MORPC (PDF page 5)
      https://www.morpc.org/wp-content/uploads/2024/08/MTP2024-2025-Chapter-8-Draft.pdf#page=5

<sub>locality 7 (COTA, Central Ohio Transit Authority, Columbus, High Injury Network, MORPC, Mid-Ohio Regional Planning Commission, Vision Zero Columbus) · 10 documents · grounded 100% · confidence 0.70 · 70.1s</sub>