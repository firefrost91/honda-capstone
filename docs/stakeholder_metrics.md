# Stakeholder metrics: what each group measures, and where the numbers will come from

The stakeholder evaluation set names eight groups who will use this tool. Each
reads the same crash history through a different set of numbers. This note
records, per group, the metrics that practice and regulation actually use,
the standard each comes from, and the stub tool in `rag/tools` that currently
produces a synthetic placeholder for it.

**Status.** Every value the tools return today is synthetic. The numbers are
deterministic (same location and year, same numbers), internally consistent,
and scaled to Central Ohio, but they are not measurements. Each tool passage
says so, the system prompt tells the model to say so once, and the API marks
the sources with `kind: "tool_metric"`. The point of the exercise is to fix
the *metric contract* (`rag/tools/metrics.py`) now, so that live services can
be swapped in tool by tool without touching the answer pipeline.

## The standards behind the metrics

| Standard | What it fixes | Used by |
|---|---|---|
| **FHWA safety performance measures (PM1)**, 23 CFR 490 Subpart B | Five measures on a five-year rolling average: fatalities, fatality rate per 100 million VMT, serious injuries (MMUCC "suspected serious injury", KABCO A), serious-injury rate, non-motorised fatalities + serious injuries. MPOs adopt the state targets or their own. | Agencies; the KSI vocabulary every other group inherits |
| **ODOT / MORPC targets** | Both apply a 2 % annual reduction across all five measures. MORPC's 2025 resolution lists five-year figures of 844.6 serious injuries and 155.6 non-motorised KSI for the planning area. | Agencies |
| **AASHTO Highway Safety Manual** network screening | Crash frequency; crash rate per million entering vehicles (intersections) or per 100 million VMT (segments); equivalent property damage only (EPDO) severity weighting; Empirical-Bayes expected and *excess* expected crashes (potential for safety improvement); before/after evaluation with Poisson statistics. | Agencies, public works |
| **MORPC high-crash-location methodology** | EPDO weights 37.56 (fatal + serious injury), 6.55 (visible injury), 4.44 (possible injury), 1.0 (PDO); severity index = EPDO / crashes; crash rate = (N/3) / (365 x ADT / 1,000,000) over three years. | Agencies, public works |
| **FHWA Proven Safety Countermeasures** | Published crash reduction factors: roundabouts 78 % fewer fatal + injury crashes from a two-way stop and 48 % from a signal; leading pedestrian interval 13 %; RRFB 47 %; pedestrian hybrid beacon 55 %; road diet 19-47 %; backplates 15 %; lighting 42 % of night-time injury pedestrian crashes; access management 25-31 %. Approximate summaries; verify against the current fact sheet before a funding application. | Agencies, public works, VRU advocates |
| **Highway Capacity Manual** | Control delay (s/veh) and level of service A-F (10 / 20 / 35 / 55 / 80 s breakpoints at signals), volume-to-capacity ratio, 95th-percentile queue. | Drivers, transit, EMS |
| **FHWA system performance measures (PM3)** | LOTTR = 80th / 50th percentile travel time, reliable below 1.50; TTTR = 95th / 50th for trucks on the Interstate (no fixed threshold, lower is better). | Drivers, freight |
| **NFPA 1710** | First responder on scene within 4 minutes and advanced life support within 8 minutes, each for 90 % of calls. Ohio does not publish medical response-time data, so a Columbus figure must come from the Division of Fire's CAD export. | EMS |
| **FHWA traffic incident management measures** | Roadway clearance time, incident clearance time, secondary crashes. ODOT's QuickClear programme reports these for the freeway system. | EMS, drivers, freight |
| **Ohio trauma system / SHSP post-crash care** | Time from crash to definitive care; Level I adult trauma centres serving Franklin County are OhioHealth Grant and OSU Wexner. The 2025 Ohio SHSP keeps post-crash care as an emphasis area. | EMS |
| **Level of Traffic Stress** (Mekuria, Furth & Nixon) | Bicycle LTS 1-4 by speed, lanes and separation; LTS 1 is tolerable by most children, LTS 4 only by "strong and fearless" riders. Pedestrian LTS uses the same scale from sidewalk width and buffer. | VRU, transit |
| **MUTCD pedestrian timing** | Pedestrian clearance interval = crossing distance / 3.5 ft/s. | VRU, public works |
| **ADA / PROWAG** | Curb-ramp and stop-landing compliance. | VRU, transit, public works |
| **ITE Trip Generation, land use 210** | Expected local-street volume from the homes on it; cut-through share = volume above that expectation; 0-25 % is the usual acceptable band. 85th-percentile speed against the posted limit is the traffic-calming trigger (many cities use 32 mph or limit + 7). | Residents |
| **FHWA noise abatement criteria**, 23 CFR 772 | 67 dBA Leq(h) for residences (activity category B); abatement is considered when levels approach it. | Residents |
| **FRA grade-crossing data** | Exposure index = AADT x trains per day (further factored by warning device, angle, speed in state hazard indices); FRA incident history; the FRA blocked-crossing portal; trespass casualties. | Freight / rail |
| **ASTM D6433 pavement condition index**, MUTCD marking retroreflectivity (50 mcd/m2/lx minimum) | Asset condition that decides whether a countermeasure stays effective. | Public works |

## Metrics by stakeholder

Metric ids are the catalogue ids in `rag/tools/metrics.py`; the tool column is
the stub that emits them today.

### State / regional transportation agencies (ODOT, MORPC)
Decide what to prioritise, against adopted targets, with evidence that explains the choice.

| Metric | Why they care | Tool |
|---|---|---|
| `ksi`, `crashes_fatal`, `crashes_serious_injury`, `crash_trend_5yr_pct` | The PM1 numbers they report | `crash_profile` |
| `crash_rate_mev` / `crash_rate_100mvmt`, `epdo_score`, `severity_index` | Normalised comparison between candidate locations | `crash_profile` |
| `fatalities_5yr_avg` ... `nonmotorized_ksi_5yr_avg`, `target_*`, `targets_on_track` | Whether the region is on the 2 %/yr pace | `safety_targets` |
| `expected_crashes_eb`, `excess_expected_crashes`, `psi_rank`, `hin_member`, `hsip_eligible` | Network screening: is this location really above its peers? | `network_screening` |
| `leading_countermeasure`, `ksi_reduction_expected`, `benefit_cost_ratio`, `project_cost_estimate_usd` | Alternatives comparison | `network_screening`, `countermeasure_reference` |
| `aadt_growth_2050_pct`, `forecast_crash_change_no_build_pct` | Future demand | `growth_outlook` |

### Local government / public works
Build, operate and maintain it; keep it working as the city grows.

| Metric | Why they care | Tool |
|---|---|---|
| `pci`, `pavement_age_yr`, `signal_equipment_age_yr`, `sidewalk_condition_rating`, `marking_retroreflectivity_mcd` | Condition decides whether a countermeasure keeps its benefit | `infrastructure_condition` |
| `row_width_ft`, `utility_conflicts`, `drainage_issues` | Feasibility of the footprint | `infrastructure_condition` |
| `project_cost_estimate_usd`, `annual_maintenance_cost_usd`, `construction_duration_months` | Budget and disruption | `infrastructure_condition` |
| `ada_ramp_compliance_pct` | Legal obligation that rides along with any rebuild | `infrastructure_condition` |
| `share_fixed_object`, `share_nighttime`, `share_angle` | Which fixable cause the remaining crashes point at | `crash_profile` |
| `expected_crashes_eb`, `hsip_eligible`, `planned_developments_count` | Funding and future load | `network_screening`, `growth_outlook` |

### Nearby residents / local communities
Safety near homes, perceived safety, noise, cut-through traffic, construction impacts.

| Metric | Why they care | Tool |
|---|---|---|
| `speed_85th`, `pct_over_limit`, `pct_over_limit_10`, `posted_speed` | Speeding is the complaint that arrives first | `speed_profile` |
| `local_street_adt`, `ite_expected_adt`, `cut_through_share_pct` | Did the main-road fix push traffic onto their street? | `community_impact_profile` |
| `noise_leq_dba`, `noise_nac_exceeded` | Noise against the federal criterion | `community_impact_profile` |
| `complaints_311_speeding_yr`, `complaints_311_noise_yr` | Their own record of concern | `community_impact_profile` |
| `detour_length_mi`, `construction_duration_months`, `schools_within_half_mile`, `residents_within_500ft` | Construction and daily-life impact | `community_impact_profile` |
| `ksi`, `pedestrian_crashes`, `pedestrian_ksi_3yr`, `hin_member` | Two serious crashes near homes are two too many | `crash_profile`, `vulnerable_user_profile` |

### Drivers / daily commuters
Crash risk, conflicts, delay, queues, reliability, clarity of the design.

| Metric | Why they care | Tool |
|---|---|---|
| `share_rear_end`, `share_angle`, `share_left_turn` | The conflict types a commuter experiences | `crash_profile` |
| `control_delay`, `los`, `vc_ratio`, `queue_95th_ft`, `cycle_length_s` | Delay and spillback | `traffic_operations` |
| `lottr`, `pti`, `tti` | Reliability: can they plan the trip? | `traffic_operations` |
| `speed_85th`, `mean_speed` | Whether the design produces the speed it posts | `speed_profile` |
| `aadt`, `peak_hour_volume` | Exposure | `traffic_operations` |

### Pedestrians / cyclists / vulnerable road users
Crossing safety, continuity, accessibility, visibility, separation, comfort.

| Metric | Why they care | Tool |
|---|---|---|
| `pedestrian_crashes_3yr`, `pedestrian_ksi_3yr`, `bicycle_crashes_3yr`, `bicycle_ksi_3yr`, `share_nighttime_vru` | Their crash history, over a long enough window to see it | `vulnerable_user_profile` |
| `crossing_distance_ft`, `ped_clearance_time_s`, `ped_clearance_provided_s` | Whether the signal gives time to cross | `vulnerable_user_profile` |
| `lighting_coverage_pct` | Visibility | `vulnerable_user_profile` |
| `sidewalk_gap_miles`, `ada_ramp_compliance_pct` | Continuity and accessibility | `vulnerable_user_profile` |
| `bike_lts`, `pedestrian_lts` | Comfort, in the scale planners use | `vulnerable_user_profile` |
| `daily_pedestrian_count`, `daily_bicycle_count` | Exposure, so crashes become rates | `vulnerable_user_profile` |
| `speed_85th`, `pct_over_limit` | Speed is the severity lever | `speed_profile` |
| `crf_leading_pedestrian_interval`, `crf_rrfb`, `crf_pedestrian_hybrid_beacon`, `crf_median_refuge` | What would help | `countermeasure_reference` |

### Emergency responders / healthcare providers
Response time, reliable access, severity, post-crash care.

| Metric | Why they care | Tool |
|---|---|---|
| `ems_response_mean_min`, `ems_response_90th_min`, `nfpa_als_8min_compliance_pct` | Against the NFPA 1710 benchmark | `emergency_response_profile` |
| `trauma_center_nearest`, `trauma_center_distance_mi`, `crash_to_hospital_mean_min` | Time to definitive care | `emergency_response_profile` |
| `roadway_clearance_mean_min`, `incident_clearance_mean_min`, `secondary_crash_share_pct` | Scene management and the crash the scene causes | `emergency_response_profile` |
| `mvc_ems_calls_per_year`, `serious_injury_transports_per_year` | Load | `emergency_response_profile` |
| `ems_access_constraints`, `queue_95th_ft`, `control_delay` | What slows the truck down | `emergency_response_profile`, `traffic_operations` |
| `ksi`, `severity_index`, `crashes_serious_injury` | Severity, not frequency, is their measure of a place | `crash_profile` |

### Public transit / mobility providers (COTA)
First/last mile, Park & Ride access, stop accessibility, bus movement.

| Metric | Why they care | Tool |
|---|---|---|
| `stops_quarter_mile`, `nearest_routes`, `daily_boardings_nearby` | Who is affected | `transit_access_profile` |
| `stops_with_sidewalk_pct`, `stops_ada_accessible_pct`, `sidewalk_gap_miles` | Can riders reach the stop? | `transit_access_profile`, `vulnerable_user_profile` |
| `ped_crashes_near_stops_3yr` | Stop-area safety (100 ft screening radius) | `transit_access_profile` |
| `park_ride_utilization_pct` | Park & Ride demand and access | `transit_access_profile` |
| `bus_delay_s_per_mile`, `control_delay`, `transit_involved_crashes_3yr` | Bus movement and bus crashes | `transit_access_profile` |

### Freight / rail operators
Truck and rail interactions, crossing safety, access, continuity during construction.

| Metric | Why they care | Tool |
|---|---|---|
| `truck_share_pct`, `daily_trucks`, `truck_involved_crashes_3yr` | Truck exposure and crash history | `freight_rail_profile` |
| `tttr` | Reliability as shippers measure it | `freight_rail_profile` |
| `design_vehicle_accommodated` | Whether a WB-67 still makes the turn after the redesign | `freight_rail_profile` |
| `rail_crossing_nearest`, `trains_per_day`, `crossing_exposure_index`, `crossing_warning_device` | Crossing risk | `freight_rail_profile` |
| `crossing_incidents_5yr`, `blocked_crossing_reports_yr`, `trespass_incidents_3yr` | Crossing history | `freight_rail_profile` |
| `queue_95th_ft`, `construction_duration_months`, `detour_length_mi` | Continuity | `traffic_operations`, `infrastructure_condition` |

### The shared scenario (layer 2)
"Crashes fell from 8 to 2 a year; both remaining crashes were serious; delay
improved; pedestrian concerns remain." The `project_outcome_evaluation` tool
reads the before/after pair from the question and returns `crash_change_pct`,
`ksi_before` / `ksi_after`, `epdo_before` / `epdo_after`, the Poisson interval
on the after count (`poisson_ci_after`, `significance_note`), `delay_change_pct`,
`ped_crash_share_after_pct` and `meets_pm1_pace`. The same table is handed to
every stakeholder; the perspective block in the prompt is what makes the
agency read "on pace" and the trauma surgeon read "two serious injuries".

## Where the live numbers will come from

| Tool | Live source to plug in |
|---|---|
| `crash_profile`, `network_screening`, `project_outcome_evaluation` | ODOT crash layers already catalogued in `data/gis_sources.json` (server-side `outStatistics`, as `rag/ingest/gis_aggregates.py` does), ODOT TIMS / GCAT, MORPC high-crash-location screening |
| `safety_targets` | ODOT / MORPC annual target resolutions |
| `traffic_operations` | ODOT TMS counts, NPMRDS / RITIS probe data for LOTTR and TTTR, Synchro or HCM runs for delay |
| `speed_profile` | City tube counts, probe speed data |
| `vulnerable_user_profile` | Columbus sidewalk and signal inventories (catalogued), count program, LTS network |
| `emergency_response_profile` | Columbus Division of Fire CAD, Ohio trauma registry, ODOT QuickClear TIM reporting |
| `transit_access_profile` | COTA stop inventory, APC boardings, Park & Ride counts |
| `freight_rail_profile` | ODOT truck counts, FRA crossing inventory and incident data, FRA blocked-crossing portal |
| `infrastructure_condition` | Columbus asset management (PCI, signals), 311, utility coordination |
| `community_impact_profile` | Tube counts on local streets, FHWA TNM noise modelling, 311 |
| `growth_outlook` | MORPC 2024-2050 MTP travel demand model |

## Sources consulted

- FHWA, [Safety Performance Management fact sheet](https://www.fhwa.dot.gov/tpm/rule/safetyfactsheet.pdf) and [safety performance guidance](https://www.fhwa.dot.gov/tpm/guidance/safety_performance.pdf); 23 CFR 490.207 via [LII](https://www.law.cornell.edu/cfr/text/23/490.207)
- MORPC, [Resolution T-14-24 supporting ODOT 2025 safety targets](https://morpc.org/2023/wp-content/uploads/2024/12/Resolution-T-14-24-Support-ODOT-Safety-Targets-for-2025-TAC.pdf) and [Resolution T-19-25 (2026 targets)](https://www.morpc.org/wp-content/uploads/2025/12/Resolution-T-19-25.pdf)
- MORPC, [High crash location methodology (EPDO weights, crash rate formula)](https://www.morpc.org/wordpress/wp-content/uploads/2018/08/HCL_Methodology_18.pdf)
- MassDOT, [intersection crash rate scales per million entering vehicles](https://gisstg.massdot.state.ma.us/arcgis/rest/services/Roads/CrashClusters/MapServer/0); City of Madison, [HIN methodology with EPDO weights](https://www.cityofmadison.com/transportation/documents/vision-zero/HIN%20Methodology.pdf)
- FHWA Office of Operations, [PM3 reliability measures, LOTTR and TTTR](https://ops.fhwa.dot.gov/publications/fhwahop22069/chap4.htm); WSDOT, [PM3 explainer](https://wsdot.wa.gov/about/data/gray-notebook/gnbhome/executive/tpm/pm3.htm)
- NASEMSO, [response time measures and NFPA 1710 benchmarks](https://nasemso.org/nasemso-document/dmc-response-time-evolution-nasemso-2013); EMS World, [EMS response time standards](https://hmpgloballearningnetwork.com/site/emsworld/article/10324786/ems-response-time-standards)
- ODOT, [Ohio Strategic Highway Safety Plan (post-crash care emphasis area)](https://dam.assets.ohio.gov/image/upload/transportation.ohio.gov/safety/highway-safety/OhioStrategicHighwaySafetyPlan.pdf); MORPC, [CORPO Safety Action Plan and dashboard](https://www.morpc.org/2023/wp-content/uploads/2024/10/CORPO-Safety-Action-Plan-and-Dashboard.pdf)
- Peter Furth, [Level of Traffic Stress criteria tables](https://peterfurth.sites.northeastern.edu/level-of-traffic-stress); CCRPC, [LTS evaluation methodology](https://www.ccrpcvt.org/wp-content/uploads/2016/01/20140611_Level_of_Traffic_Stress_Evaluation_Methodology.pdf); WSDOT, [pedestrian LTS design bulletin](https://appstest.wsdot.wa.gov/sites/default/files/2022-06/DesignBulletin2022-01.pdf)
- FRA, [data analysis of grade crossing incidents (traffic moment exposure)](https://railroads.dot.gov/sites/fra.dot.gov/files/fra_net/123/RR_Data_Analysis_of_Grade_Crossing_Incidents_final.pdf); Iowa DOT, [crossing exposure index](https://publications.iowa.gov/44898/1/DOT_exposure_index_list_by_comp_FRA_number_1986_OCR_.pdf)
- North Florida TPO, [first/last-mile transit safety study (crashes near stops, sidewalk gaps)](https://northfloridatpo.com/uploads/FINAL-FLM-NormandyStudy_JUNE2025-reduced.pdf); arXiv, [pedestrian crashes near bus stops](https://arxiv.org/html/2410.22253v4)
- Town of Cary / Mount Prospect / SFMTA / Prattville traffic-calming policies for 85th-percentile and cut-through triggers, e.g. [Prattville neighborhood traffic calming policy](https://prattvilleal.gov/departments/engineering/neighborhood-traffic-calming-policy/), [Chevy Chase cut-through study](https://townofchevychase.org/DocumentCenter/View/3196/Cut-Through-and-Traffic-Calming-Study-), [FHWA traffic calming ePrimer](https://highways.dot.gov/safety/speed-management/traffic-calming-eprimer/module-8-traffic-calming-case-studies)
- City of Columbus, [Vision Zero annual report 2024](https://www.columbus.gov/files/sharedassets/city/v/1/public-service/vision-zero/vision-zero-columbus-annual-report-2024.pdf) and [Vision Zero newsletter, February 2026](https://www.columbus.gov/files/sharedassets/city/v/1/public-service/vision-zero/vz-newsletter-feb-2026.pdf) (52 deaths in 2024, 31 year-to-date in 2025); [Axios Columbus pedestrian safety ranking](https://www.axios.com/local/columbus/2026/06/17/pedestrian-safety-rankings-report)
- COTA, [2023 annual report](https://cota.com/2023annualreport/) and [2025 annual report](https://cota.com/2025-annual-report/impact/) (about 3,000 active stops); [LinkUS](https://cota.com/linkus)
- Local anchors already in this repository: `data/derived/columbus_coc_crash_data_summary.json` (12,033 crashes, 81 fatal, 340 serious-injury in 2021; 49 fatal, 263 serious-injury in 2024).
