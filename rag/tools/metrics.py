"""Catalogue of the metrics each stakeholder reasons with.

Every metric a tool can emit is declared here once, with its unit, a one-line
definition and the standard it comes from. The catalogue is the contract
between the stub tools in :mod:`rag.tools.synthetic` and the real analytics
tools that will replace them: a real tool must emit the same ``metric_id`` with
the same unit, and nothing else about the pipeline has to change.

Where the metrics come from (see ``docs/stakeholder_metrics.md`` for the
write-up and sources):

* **Federal safety performance measures (PM1, 23 CFR 490 Subpart B).** Five
  measures on a five-year rolling average: fatalities, fatality rate per 100
  million VMT, serious injuries (KABCO "A"), serious-injury rate, and
  non-motorised fatalities + serious injuries. Ohio and MORPC set a 2 % annual
  reduction target on all five.
* **Highway Safety Manual network screening.** Crash frequency, crash rate
  (per million entering vehicles at intersections, per 100 million VMT on
  segments), equivalent-property-damage-only (EPDO) index, and
  Empirical-Bayes expected / excess expected crashes (potential for safety
  improvement). MORPC's published EPDO weights are 37.56 (fatal + serious
  injury), 6.55 (visible injury), 4.44 (possible injury), 1.0 (PDO).
* **Federal reliability measures (PM3).** LOTTR = 80th / 50th percentile
  travel time (reliable below 1.50); TTTR = 95th / 50th for trucks on the
  Interstate. Highway Capacity Manual control delay and level of service.
* **Post-crash care.** NFPA 1710 benchmarks (first responder within 4 min,
  advanced life support within 8 min, 90 % of calls); FHWA traffic incident
  management measures (roadway clearance time, incident clearance time,
  secondary crashes); time to a Level I trauma centre.
* **Active-transportation stress.** Bicycle Level of Traffic Stress 1-4
  (Furth / Mekuria); pedestrian LTS; MUTCD pedestrian clearance at 3.5 ft/s.
* **Neighbourhood traffic.** 85th-percentile speed against the posted limit;
  cut-through share = local volume above the ITE land-use-210 expectation;
  FHWA noise abatement criterion of 67 dBA Leq(h) for residences.
* **Freight and rail.** Truck share of AADT; TTTR; FRA crossing exposure
  (AADT x trains per day); FRA incident, blocked-crossing and trespass counts.
"""
from __future__ import annotations

from dataclasses import dataclass

#: Stakeholder ids, shared with :mod:`rag.tools.stakeholders`.
AGENCY = "agency"
LOCAL_GOV = "local_gov"
RESIDENTS = "residents"
DRIVERS = "drivers"
VRU = "vru"
EMERGENCY = "emergency"
TRANSIT = "transit"
FREIGHT = "freight"
ALL = (AGENCY, LOCAL_GOV, RESIDENTS, DRIVERS, VRU, EMERGENCY, TRANSIT, FREIGHT)


@dataclass(frozen=True)
class MetricSpec:
    id: str
    name: str
    unit: str                 # "" for a label / yes-no value
    definition: str
    basis: str                # the standard or practice the metric comes from
    stakeholders: tuple[str, ...]
    #: "lower" = lower is better, "higher" = higher is better, "neutral" = context
    direction: str = "neutral"
    decimals: int = 0


def _m(id, name, unit, definition, basis, stakeholders, direction="neutral", decimals=0):
    return MetricSpec(id, name, unit, definition, basis, tuple(stakeholders), direction, decimals)


_PM1 = "FHWA safety performance measures, 23 CFR 490.207"
_HSM = "AASHTO Highway Safety Manual network screening"
_MORPC_EPDO = "MORPC high-crash-location methodology (EPDO weights 37.56 / 6.55 / 4.44 / 1.0)"
_HCM = "Highway Capacity Manual"
_PM3 = "FHWA system-performance measures (PM3), 23 CFR 490 Subpart E/F"
_NFPA = "NFPA 1710 response-time benchmarks"
_TIM = "FHWA traffic incident management performance measures"
_LTS = "Level of Traffic Stress (Mekuria, Furth & Nixon)"
_MUTCD = "MUTCD pedestrian clearance interval at 3.5 ft/s"
_ITE = "ITE Trip Generation (land use 210) cut-through method"
_NAC = "FHWA noise abatement criteria, 23 CFR 772 (67 dBA Leq(h), activity category B)"
_FRA = "FRA grade-crossing inventory and accident prediction (exposure = AADT x trains/day)"
_PSC = "FHWA Proven Safety Countermeasures crash reduction factors"
_ADA = "ADA / PROWAG accessibility compliance"
_PAVE = "ASTM D6433 pavement condition index"

METRIC_LIST: list[MetricSpec] = [
    # ---- crash profile (KABCO) --------------------------------------------
    _m("crashes_total", "Total reported crashes", "crashes/yr",
       "All police-reported crashes in the year at the location.", _HSM, ALL, "lower"),
    _m("crashes_fatal", "Fatal crashes (K)", "crashes/yr",
       "Crashes with at least one death within 30 days.", _PM1, ALL, "lower"),
    _m("crashes_serious_injury", "Suspected serious injury crashes (A)", "crashes/yr",
       "Crashes with at least one MMUCC 'suspected serious injury'.", _PM1, ALL, "lower"),
    _m("crashes_minor_injury", "Suspected minor injury crashes (B)", "crashes/yr",
       "Crashes whose worst injury is a suspected minor injury.", _HSM, (AGENCY, LOCAL_GOV, EMERGENCY), "lower"),
    _m("crashes_possible_injury", "Possible injury crashes (C)", "crashes/yr",
       "Crashes whose worst injury is a possible injury.", _HSM, (AGENCY, LOCAL_GOV, EMERGENCY), "lower"),
    _m("crashes_pdo", "Property-damage-only crashes (O)", "crashes/yr",
       "Crashes with no reported injury.", _HSM, (AGENCY, LOCAL_GOV, DRIVERS), "lower"),
    _m("ksi", "Killed or seriously injured crashes (K+A)", "crashes/yr",
       "Fatal plus suspected-serious-injury crashes; the Vision Zero headline measure.",
       _PM1, ALL, "lower"),
    _m("pedestrian_crashes", "Pedestrian-involved crashes", "crashes/yr",
       "Crashes involving at least one pedestrian.", _PM1, (AGENCY, VRU, RESIDENTS, TRANSIT, EMERGENCY), "lower"),
    _m("bicycle_crashes", "Bicycle-involved crashes", "crashes/yr",
       "Crashes involving at least one bicyclist.", _PM1, (AGENCY, VRU, RESIDENTS, TRANSIT), "lower"),
    _m("crash_rate_mev", "Intersection crash rate", "crashes per million entering vehicles",
       "Annual crashes / (365 x entering ADT / 1,000,000).", _MORPC_EPDO, (AGENCY, LOCAL_GOV, DRIVERS), "lower", 2),
    _m("crash_rate_100mvmt", "Crash rate per 100 million VMT", "crashes per 100M VMT",
       "Annual crashes divided by annual vehicle-miles travelled in units of 100 million.",
       _PM1, (AGENCY, LOCAL_GOV, DRIVERS), "lower", 1),
    _m("entering_adt", "Entering average daily traffic", "veh/day",
       "Sum of daily traffic entering the intersection on all approaches.", _HSM, (AGENCY, DRIVERS)),
    _m("annual_vmt_100m", "Annual VMT", "units of 100 million VMT",
       "Vehicle-miles travelled in the area in the year, in 100-million units.", _PM1, (AGENCY,), "neutral", 1),
    _m("epdo_score", "EPDO score", "PDO-equivalents/yr",
       "Severity-weighted crash total using MORPC weights.", _MORPC_EPDO, (AGENCY, LOCAL_GOV), "lower"),
    _m("severity_index", "Severity index", "EPDO per crash",
       "EPDO score divided by total crashes; 1.0 means every crash was PDO.", _MORPC_EPDO, (AGENCY, LOCAL_GOV, EMERGENCY), "lower", 2),
    _m("crash_trend_5yr_pct", "Five-year crash trend", "% change",
       "Change in total crashes versus five years earlier.", _PM1, (AGENCY, LOCAL_GOV, RESIDENTS), "lower"),
    _m("share_angle", "Angle crash share", "% of crashes",
       "Share of crashes coded angle / right-angle.", _HSM, (DRIVERS, AGENCY, LOCAL_GOV)),
    _m("share_rear_end", "Rear-end crash share", "% of crashes",
       "Share of crashes coded rear-end; a congestion and queue-spillback signature.", _HSM, (DRIVERS, AGENCY)),
    _m("share_left_turn", "Left-turn crash share", "% of crashes",
       "Share of crashes involving a left-turning vehicle.", _HSM, (DRIVERS, AGENCY, VRU)),
    _m("share_fixed_object", "Fixed-object crash share", "% of crashes",
       "Share of single-vehicle crashes into a fixed object; a speed and run-off-road signature.", _HSM, (DRIVERS, LOCAL_GOV)),
    _m("share_nighttime", "Night-time crash share", "% of crashes",
       "Share of crashes between dusk and dawn; a lighting signature.", _HSM, (VRU, LOCAL_GOV, EMERGENCY)),
    _m("share_speed_related", "Speed-related crash share", "% of crashes",
       "Share of crashes with unsafe speed as a contributing factor.", _PM1, (RESIDENTS, DRIVERS, AGENCY)),

    # ---- regional safety targets (PM1) -------------------------------------
    _m("fatalities_5yr_avg", "Fatalities, five-year rolling average", "deaths/yr", "PM1 measure 1.", _PM1, (AGENCY,), "lower", 1),
    _m("fatality_rate_5yr_avg", "Fatality rate, five-year rolling average", "deaths per 100M VMT", "PM1 measure 2.", _PM1, (AGENCY,), "lower", 3),
    _m("serious_injuries_5yr_avg", "Serious injuries, five-year rolling average", "injuries/yr", "PM1 measure 3.", _PM1, (AGENCY,), "lower", 1),
    _m("serious_injury_rate_5yr_avg", "Serious-injury rate, five-year rolling average", "injuries per 100M VMT", "PM1 measure 4.", _PM1, (AGENCY,), "lower", 3),
    _m("nonmotorized_ksi_5yr_avg", "Non-motorised fatalities + serious injuries, five-year average", "people/yr", "PM1 measure 5.", _PM1, (AGENCY, VRU), "lower", 1),
    _m("target_fatalities", "Fatalities target", "deaths/yr", "Five-year-average target after the 2 % annual reduction ODOT and MORPC adopt.", _PM1, (AGENCY,), "lower", 1),
    _m("target_serious_injuries", "Serious-injuries target", "injuries/yr", "Five-year-average target after the 2 % annual reduction.", _PM1, (AGENCY,), "lower", 1),
    _m("target_nonmotorized_ksi", "Non-motorised KSI target", "people/yr", "Five-year-average target after the 2 % annual reduction.", _PM1, (AGENCY, VRU), "lower", 1),
    _m("targets_on_track", "Targets on track", "", "Whether the current five-year averages meet the adopted targets.", _PM1, (AGENCY,)),

    # ---- network screening -------------------------------------------------
    _m("expected_crashes_eb", "Expected crashes (Empirical Bayes)", "crashes/yr",
       "Long-run expected crash frequency combining observed crashes with the SPF prediction.", _HSM, (AGENCY, LOCAL_GOV), "lower", 1),
    _m("excess_expected_crashes", "Excess expected crashes (PSI)", "crashes/yr",
       "Expected minus predicted crashes: the potential for safety improvement.", _HSM, (AGENCY, LOCAL_GOV), "lower", 1),
    _m("psi_rank", "PSI rank among city intersections", "rank",
       "Rank of the location by excess expected crashes (1 = worst).", _HSM, (AGENCY, LOCAL_GOV), "higher"),
    _m("hin_member", "On the Columbus High Injury Network", "", "Whether the location lies on the Vision Zero High Injury Network.", "Vision Zero Columbus High Injury Network", (AGENCY, LOCAL_GOV, RESIDENTS, VRU)),
    _m("hsip_eligible", "HSIP-eligible", "", "Whether the crash history makes the location eligible for Highway Safety Improvement Program funding.", "FHWA HSIP eligibility", (AGENCY, LOCAL_GOV)),
    _m("benefit_cost_ratio", "Benefit-cost ratio of the leading countermeasure", "ratio",
       "Present value of crash-cost savings divided by project cost.", _HSM, (AGENCY, LOCAL_GOV), "higher", 1),
    _m("ksi_reduction_expected", "Expected KSI reduction from the leading countermeasure", "% reduction",
       "Crash reduction factor applied to KSI crashes.", _PSC, (AGENCY, LOCAL_GOV, VRU), "higher"),
    _m("leading_countermeasure", "Leading countermeasure", "", "The countermeasure the screening ranks first for the crash pattern.", _PSC, (AGENCY, LOCAL_GOV)),

    # ---- countermeasure reference values (published, not synthetic) -------
    _m("crf_roundabout_from_two_way_stop", "Roundabout (from two-way stop)", "% fewer fatal+injury crashes", "Crash reduction factor.", _PSC, (AGENCY, LOCAL_GOV)),
    _m("crf_roundabout_from_signal", "Roundabout (from signal)", "% fewer fatal+injury crashes", "Crash reduction factor.", _PSC, (AGENCY, LOCAL_GOV)),
    _m("crf_leading_pedestrian_interval", "Leading pedestrian interval", "% fewer pedestrian-vehicle crashes", "Crash reduction factor.", _PSC, (AGENCY, LOCAL_GOV, VRU)),
    _m("crf_rrfb", "Rectangular rapid-flashing beacon", "% fewer pedestrian crashes", "Crash reduction factor.", _PSC, (AGENCY, LOCAL_GOV, VRU)),
    _m("crf_pedestrian_hybrid_beacon", "Pedestrian hybrid beacon", "% fewer pedestrian crashes", "Crash reduction factor.", _PSC, (AGENCY, LOCAL_GOV, VRU)),
    _m("crf_road_diet", "Road diet (4 to 3 lanes)", "% fewer total crashes", "Crash reduction factor, range.", _PSC, (AGENCY, LOCAL_GOV, VRU, RESIDENTS)),
    _m("crf_backplates", "Signal backplates with retroreflective borders", "% fewer total crashes", "Crash reduction factor at urban signals.", _PSC, (AGENCY, LOCAL_GOV, DRIVERS)),
    _m("crf_lighting", "Intersection lighting", "% fewer night-time injury pedestrian crashes", "Crash reduction factor.", _PSC, (AGENCY, LOCAL_GOV, VRU)),
    _m("crf_access_management", "Corridor access management", "% fewer fatal+injury crashes", "Crash reduction factor, range.", _PSC, (AGENCY, LOCAL_GOV, FREIGHT)),
    _m("crf_median_refuge", "Medians and pedestrian refuge islands", "% fewer pedestrian crashes", "Crash reduction factor.", _PSC, (AGENCY, LOCAL_GOV, VRU)),

    # ---- traffic operations ------------------------------------------------
    _m("aadt", "Annual average daily traffic", "veh/day", "Two-way daily traffic on the main road.", _HCM, (DRIVERS, AGENCY, LOCAL_GOV, FREIGHT)),
    _m("peak_hour_volume", "Peak-hour volume", "veh/h", "Highest hourly two-way volume.", _HCM, (DRIVERS, AGENCY)),
    _m("control_delay", "Control delay", "s/veh", "Average delay per vehicle at the intersection in the peak hour.", _HCM, (DRIVERS, TRANSIT, EMERGENCY), "lower", 1),
    _m("los", "Level of service", "", "HCM intersection level of service A-F from control delay.", _HCM, (DRIVERS, AGENCY, LOCAL_GOV)),
    _m("vc_ratio", "Volume-to-capacity ratio", "ratio", "Peak-hour demand divided by capacity; above 1.0 the queue grows.", _HCM, (DRIVERS, AGENCY), "lower", 2),
    _m("queue_95th_ft", "95th-percentile queue", "ft", "Queue length exceeded only 5 % of the time on the worst approach.", _HCM, (DRIVERS, EMERGENCY, FREIGHT), "lower"),
    _m("lottr", "Level of travel time reliability (LOTTR)", "ratio", "80th / 50th percentile travel time; reliable below 1.50.", _PM3, (DRIVERS, AGENCY, TRANSIT), "lower", 2),
    _m("pti", "Planning time index", "ratio", "95th-percentile travel time / free-flow travel time.", _PM3, (DRIVERS, EMERGENCY), "lower", 2),
    _m("tti", "Travel time index", "ratio", "Mean peak travel time / free-flow travel time.", _PM3, (DRIVERS,), "lower", 2),
    _m("truck_share_pct", "Heavy-vehicle share of AADT", "% of vehicles", "Trucks (FHWA class 4+) as a share of daily traffic.", _PM3, (FREIGHT, AGENCY, RESIDENTS)),
    _m("cycle_length_s", "Signal cycle length", "s", "Peak-period signal cycle length.", _HCM, (DRIVERS, VRU)),

    # ---- speed -------------------------------------------------------------
    _m("posted_speed", "Posted speed limit", "mph", "Regulatory speed limit on the main road.", "ODOT speed zoning", (RESIDENTS, DRIVERS, VRU, LOCAL_GOV)),
    _m("mean_speed", "Mean speed", "mph", "Average free-flow speed from tube or radar counts.", "ODOT speed zoning", (RESIDENTS, DRIVERS, VRU), "lower", 1),
    _m("speed_85th", "85th-percentile speed", "mph", "Speed at or below which 85 % of drivers travel.", "ODOT speed zoning / FHWA traffic calming", (RESIDENTS, DRIVERS, VRU, LOCAL_GOV), "lower", 1),
    _m("pct_over_limit", "Share of drivers over the limit", "% of vehicles", "Vehicles exceeding the posted limit.", "FHWA speed management", (RESIDENTS, VRU, LOCAL_GOV), "lower"),
    _m("pct_over_limit_10", "Share of drivers 10+ mph over", "% of vehicles", "Vehicles exceeding the posted limit by 10 mph or more.", "FHWA speed management", (RESIDENTS, VRU, EMERGENCY), "lower", 1),

    # ---- vulnerable road users --------------------------------------------
    _m("pedestrian_crashes_3yr", "Pedestrian crashes, three years", "crashes", "Pedestrian-involved crashes within 250 ft in the last three years.", _PM1, (VRU, RESIDENTS, TRANSIT), "lower"),
    _m("pedestrian_ksi_3yr", "Pedestrian KSI, three years", "crashes", "Pedestrian crashes with a death or serious injury.", _PM1, (VRU, RESIDENTS, EMERGENCY), "lower"),
    _m("bicycle_crashes_3yr", "Bicycle crashes, three years", "crashes", "Bicycle-involved crashes within 250 ft in the last three years.", _PM1, (VRU,), "lower"),
    _m("bicycle_ksi_3yr", "Bicycle KSI, three years", "crashes", "Bicycle crashes with a death or serious injury.", _PM1, (VRU,), "lower"),
    _m("crossing_distance_ft", "Longest marked crossing", "ft", "Curb-to-curb distance of the longest crosswalk.", "FHWA pedestrian safety guide", (VRU, TRANSIT), "lower"),
    _m("ped_clearance_time_s", "Pedestrian clearance time needed", "s", "Crossing distance / 3.5 ft/s.", _MUTCD, (VRU,), "neutral", 1),
    _m("ped_clearance_provided_s", "Pedestrian clearance time provided", "s", "Flashing-don't-walk interval in the signal timing.", _MUTCD, (VRU, LOCAL_GOV), "higher", 1),
    _m("lighting_coverage_pct", "Lighting coverage", "% of crossings lit", "Marked crossings with overhead lighting meeting the IES level.", "IES RP-8 roadway lighting", (VRU, LOCAL_GOV, EMERGENCY), "higher"),
    _m("sidewalk_gap_miles", "Sidewalk gap", "miles", "Street frontage within a half mile with no sidewalk on either side.", "Columbus sidewalk inventory", (VRU, TRANSIT, RESIDENTS, LOCAL_GOV), "lower", 2),
    _m("ada_ramp_compliance_pct", "ADA-compliant curb ramps", "% of ramps", "Curb ramps meeting PROWAG slope and detectable-warning requirements.", _ADA, (VRU, TRANSIT, LOCAL_GOV), "higher"),
    _m("bike_lts", "Bicycle level of traffic stress", "LTS 1-4", "1 = comfortable for most children, 4 = only strong and fearless riders.", _LTS, (VRU, TRANSIT), "lower"),
    _m("pedestrian_lts", "Pedestrian level of traffic stress", "PLTS 1-4", "1 = comfortable for all ages, 4 = most pedestrians avoid it.", _LTS, (VRU, TRANSIT, RESIDENTS), "lower"),
    _m("daily_pedestrian_count", "Daily pedestrian crossings", "people/day", "Pedestrians crossing at the location per day.", "Count program exposure", (VRU, TRANSIT, AGENCY)),
    _m("daily_bicycle_count", "Daily bicycle volume", "riders/day", "Bicyclists passing the location per day.", "Count program exposure", (VRU, AGENCY)),
    _m("share_nighttime_vru", "Night-time share of pedestrian and bicycle crashes", "% of VRU crashes", "VRU crashes between dusk and dawn.", _HSM, (VRU, LOCAL_GOV), "lower"),

    # ---- emergency response -------------------------------------------------
    _m("ems_response_mean_min", "Mean EMS response time", "min", "Call receipt to arrival on scene, mean.", _NFPA, (EMERGENCY, RESIDENTS), "lower", 1),
    _m("ems_response_90th_min", "90th-percentile EMS response time", "min", "Call receipt to arrival on scene, 90th percentile.", _NFPA, (EMERGENCY, AGENCY), "lower", 1),
    _m("nfpa_als_8min_compliance_pct", "ALS within 8 minutes", "% of calls", "Share of calls with advanced life support on scene within 8 minutes (NFPA 1710 asks for 90 %).", _NFPA, (EMERGENCY,), "higher"),
    _m("trauma_center_nearest", "Nearest Level I trauma centre", "", "The closest adult Level I trauma centre.", "Ohio Department of Health trauma designations", (EMERGENCY,)),
    _m("trauma_center_distance_mi", "Distance to Level I trauma centre", "miles", "Road distance to the nearest adult Level I trauma centre.", "Ohio trauma system", (EMERGENCY, RESIDENTS), "lower", 1),
    _m("crash_to_hospital_mean_min", "Crash-to-hospital time", "min", "Mean time from crash notification to hospital arrival for serious-injury transports.", "Ohio trauma registry / SHSP post-crash care", (EMERGENCY, AGENCY), "lower"),
    _m("roadway_clearance_mean_min", "Roadway clearance time", "min", "Incident notification to all lanes reopened, mean.", _TIM, (EMERGENCY, DRIVERS, FREIGHT), "lower"),
    _m("incident_clearance_mean_min", "Incident clearance time", "min", "Incident notification to last responder departing, mean.", _TIM, (EMERGENCY, DRIVERS), "lower"),
    _m("secondary_crash_share_pct", "Secondary crash share", "% of incidents", "Incidents that caused a further crash in the queue.", _TIM, (EMERGENCY, DRIVERS, AGENCY), "lower", 1),
    _m("mvc_ems_calls_per_year", "EMS calls for motor-vehicle crashes", "calls/yr", "EMS dispatches coded motor-vehicle crash within the area.", "NEMSIS EMS records", (EMERGENCY,), "lower"),
    _m("serious_injury_transports_per_year", "Serious-injury transports", "transports/yr", "Trauma-activation transports from crashes in the area.", "Ohio trauma registry", (EMERGENCY,), "lower"),
    _m("ems_access_constraints", "Emergency-access constraints", "", "Roadway features that slow responder access to the location.", "Fire and EMS access review", (EMERGENCY, LOCAL_GOV)),

    # ---- transit access ------------------------------------------------------
    _m("stops_quarter_mile", "Transit stops within a quarter mile", "stops", "COTA stops within 1/4 mile of the location.", "COTA stop inventory", (TRANSIT, VRU, RESIDENTS)),
    _m("nearest_routes", "Nearest COTA routes", "", "Routes serving the nearby stops.", "COTA network", (TRANSIT, RESIDENTS)),
    _m("daily_boardings_nearby", "Daily boardings at nearby stops", "boardings/day", "Average weekday boardings summed over the nearby stops.", "COTA automatic passenger counts", (TRANSIT,)),
    _m("stops_with_sidewalk_pct", "Stops with sidewalk access", "% of stops", "Nearby stops connected to a continuous sidewalk.", "COTA / Columbus sidewalk inventory", (TRANSIT, VRU), "higher"),
    _m("stops_ada_accessible_pct", "ADA-accessible stops", "% of stops", "Nearby stops with an accessible landing pad and ramp.", _ADA, (TRANSIT, VRU), "higher"),
    _m("ped_crashes_near_stops_3yr", "Pedestrian crashes within 100 ft of stops, three years", "crashes", "Pedestrian crashes near the nearby stops.", "Transit stop safety screening", (TRANSIT, VRU), "lower"),
    _m("park_ride_utilization_pct", "Park & Ride utilisation", "% of spaces", "Occupied spaces at the nearest Park & Ride on a weekday.", "COTA Park & Ride counts", (TRANSIT, DRIVERS)),
    _m("bus_delay_s_per_mile", "Bus delay", "s/mile", "Bus running time above free-flow per mile on the corridor.", "Transit signal priority screening", (TRANSIT,), "lower"),
    _m("transit_involved_crashes_3yr", "Transit-vehicle-involved crashes, three years", "crashes", "Crashes involving a bus on the corridor.", "COTA safety reporting", (TRANSIT,), "lower"),

    # ---- freight and rail ----------------------------------------------------
    _m("daily_trucks", "Daily trucks", "trucks/day", "AADT times the heavy-vehicle share.", _PM3, (FREIGHT, RESIDENTS)),
    _m("truck_involved_crashes_3yr", "Truck-involved crashes, three years", "crashes", "Crashes involving a heavy vehicle.", "FMCSA / ODOT crash records", (FREIGHT, AGENCY), "lower"),
    _m("tttr", "Truck travel time reliability (TTTR)", "ratio", "95th / 50th percentile truck travel time.", _PM3, (FREIGHT, AGENCY), "lower", 2),
    _m("design_vehicle_accommodated", "Design vehicle accommodated", "", "Largest design vehicle whose turning path fits the intersection.", "AASHTO Green Book design vehicles", (FREIGHT, LOCAL_GOV)),
    _m("rail_crossing_nearest", "Nearest at-grade rail crossing", "", "The closest public highway-rail grade crossing.", _FRA, (FREIGHT, EMERGENCY)),
    _m("trains_per_day", "Trains per day at the crossing", "trains/day", "Daily train movements over the crossing.", _FRA, (FREIGHT, RESIDENTS)),
    _m("crossing_exposure_index", "Crossing exposure index", "AADT x trains/day", "Product of road and rail traffic over the crossing.", _FRA, (FREIGHT, AGENCY), "lower"),
    _m("crossing_incidents_5yr", "Crossing incidents, five years", "incidents", "FRA-reported highway-rail incidents at the crossing.", _FRA, (FREIGHT, EMERGENCY), "lower"),
    _m("blocked_crossing_reports_yr", "Blocked-crossing reports", "reports/yr", "Public reports of a blocked crossing to the FRA portal.", "FRA blocked crossing portal", (FREIGHT, EMERGENCY, RESIDENTS), "lower"),
    _m("trespass_incidents_3yr", "Trespass incidents, three years", "incidents", "Rail trespass casualties within a half mile of the crossing.", _FRA, (FREIGHT,), "lower"),
    _m("crossing_warning_device", "Crossing warning device", "", "Highest warning device class at the crossing.", _FRA, (FREIGHT, LOCAL_GOV)),

    # ---- infrastructure condition and implementation ----------------------
    _m("pci", "Pavement condition index", "0-100", "ASTM D6433 pavement condition; below 55 is poor.", _PAVE, (LOCAL_GOV, DRIVERS), "higher"),
    _m("pavement_age_yr", "Years since last resurfacing", "years", "Age of the surface course.", _PAVE, (LOCAL_GOV,), "lower"),
    _m("signal_equipment_age_yr", "Signal equipment age", "years", "Age of the controller and heads.", "Columbus signal asset inventory", (LOCAL_GOV,), "lower"),
    _m("sidewalk_condition_rating", "Sidewalk condition", "1-5", "1 = failed, 5 = new.", "Columbus sidewalk inventory", (LOCAL_GOV, VRU), "higher"),
    _m("marking_retroreflectivity_mcd", "Pavement marking retroreflectivity", "mcd/m2/lx", "Night-time visibility of longitudinal markings; MUTCD minimum 50.", "MUTCD marking retroreflectivity", (LOCAL_GOV, DRIVERS), "higher"),
    _m("drainage_issues", "Open drainage work orders", "count", "Ponding or inlet complaints on record.", "Columbus 311 / asset management", (LOCAL_GOV,), "lower"),
    _m("utility_conflicts", "Utility conflicts in the footprint", "count", "Utilities that would need relocation for a rebuild.", "Utility coordination review", (LOCAL_GOV, AGENCY), "lower"),
    _m("row_width_ft", "Available right-of-way", "ft", "Public right-of-way width at the narrowest point.", "Franklin County auditor parcels", (LOCAL_GOV, AGENCY)),
    _m("annual_maintenance_cost_usd", "Annual maintenance cost", "USD/yr", "Routine maintenance of the asset per year.", "Columbus asset management", (LOCAL_GOV,), "lower"),
    _m("project_cost_estimate_usd", "Project cost estimate", "USD", "Planning-level construction cost of the leading countermeasure.", "ODOT cost estimating", (LOCAL_GOV, AGENCY), "lower"),
    _m("construction_duration_months", "Construction duration", "months", "Expected construction period.", "Project schedule", (LOCAL_GOV, RESIDENTS, FREIGHT, TRANSIT), "lower"),

    # ---- community impact ------------------------------------------------------
    _m("local_street_adt", "Local-street daily traffic", "veh/day", "Daily traffic on the adjacent residential street.", _ITE, (RESIDENTS, LOCAL_GOV), "lower"),
    _m("ite_expected_adt", "Expected local traffic from land use", "veh/day", "Daily trips the street's own homes would generate.", _ITE, (RESIDENTS, LOCAL_GOV)),
    _m("cut_through_share_pct", "Cut-through share", "% of local volume", "Local-street volume above the land-use expectation; 0-25 % is typically acceptable.", _ITE, (RESIDENTS, LOCAL_GOV), "lower"),
    _m("noise_leq_dba", "Peak-hour noise level", "dBA Leq(h)", "Traffic noise at the nearest residence.", _NAC, (RESIDENTS,), "lower", 1),
    _m("noise_nac_exceeded", "Noise abatement criterion exceeded", "", "Whether the level approaches or exceeds 67 dBA.", _NAC, (RESIDENTS, LOCAL_GOV)),
    _m("complaints_311_speeding_yr", "311 speeding complaints", "complaints/yr", "Resident speeding complaints logged for the street.", "Columbus 311", (RESIDENTS, LOCAL_GOV), "lower"),
    _m("complaints_311_noise_yr", "311 traffic-noise complaints", "complaints/yr", "Resident noise complaints logged for the street.", "Columbus 311", (RESIDENTS,), "lower"),
    _m("detour_length_mi", "Construction detour length", "miles", "Added distance of the signed detour during construction.", "Maintenance-of-traffic plan", (RESIDENTS, DRIVERS, FREIGHT, EMERGENCY), "lower", 1),
    _m("residents_within_500ft", "Residents within 500 ft", "people", "Population living within 500 ft of the location.", "Census block data", (RESIDENTS, AGENCY)),
    _m("schools_within_half_mile", "Schools within a half mile", "schools", "K-12 schools within walking distance.", "Safe Routes to School", (RESIDENTS, VRU)),
    _m("zero_vehicle_households_pct", "Zero-vehicle households", "% of households", "Households without a car within a half mile.", "ACS / MORPC environmental justice", (RESIDENTS, TRANSIT, VRU, AGENCY)),

    # ---- growth outlook ---------------------------------------------------------
    _m("aadt_growth_2050_pct", "Forecast traffic growth to 2050", "% growth", "MTP travel-demand model growth in AADT.", "MORPC 2024-2050 MTP forecasts", (AGENCY, LOCAL_GOV, DRIVERS)),
    _m("population_growth_2050_pct", "Forecast population growth to 2050", "% growth", "Growth in the surrounding traffic analysis zones.", "MORPC 2024-2050 MTP forecasts", (AGENCY, LOCAL_GOV)),
    _m("employment_growth_2050_pct", "Forecast employment growth to 2050", "% growth", "Growth in jobs in the surrounding zones.", "MORPC 2024-2050 MTP forecasts", (AGENCY, LOCAL_GOV)),
    _m("forecast_crash_change_no_build_pct", "Forecast crash change with no action", "% change", "SPF-based change in expected crashes from forecast volume growth.", _HSM, (AGENCY, LOCAL_GOV), "lower"),
    _m("planned_developments_count", "Planned developments nearby", "count", "Approved developments within a mile that add trips.", "Local development review", (LOCAL_GOV, RESIDENTS, DRIVERS)),

    # ---- project outcome evaluation (shared scenario) ----------------------
    _m("crashes_before", "Crashes per year before the project", "crashes/yr", "Average annual crashes in the before period.", _HSM, ALL, "lower"),
    _m("crashes_after", "Crashes per year after the project", "crashes/yr", "Average annual crashes in the after period.", _HSM, ALL, "lower"),
    _m("crash_change_pct", "Change in crashes", "% change", "(after - before) / before.", _HSM, ALL, "lower"),
    _m("ksi_before", "KSI crashes before", "crashes/yr", "Fatal + serious-injury crashes before.", _PM1, ALL, "lower"),
    _m("ksi_after", "KSI crashes after", "crashes/yr", "Fatal + serious-injury crashes after.", _PM1, ALL, "lower"),
    _m("epdo_before", "EPDO before", "PDO-equivalents/yr", "Severity-weighted total before.", _MORPC_EPDO, (AGENCY, LOCAL_GOV), "lower"),
    _m("epdo_after", "EPDO after", "PDO-equivalents/yr", "Severity-weighted total after.", _MORPC_EPDO, (AGENCY, LOCAL_GOV), "lower"),
    _m("poisson_ci_after", "95 % interval on the after count", "crashes/yr", "Poisson confidence interval; small counts are noisy.", "HSM before-after statistics", (AGENCY, LOCAL_GOV)),
    _m("significance_note", "Statistical reading", "", "Whether the change is distinguishable from chance.", "HSM before-after statistics", ALL),
    _m("delay_change_pct", "Change in control delay", "% change", "Peak-hour delay after versus before.", _HCM, (DRIVERS, TRANSIT, EMERGENCY, FREIGHT), "lower"),
    _m("ped_crash_share_after_pct", "Pedestrian share of after-period crashes", "% of crashes", "Share of remaining crashes that involved a pedestrian.", _PM1, (VRU, RESIDENTS, TRANSIT), "lower"),
    _m("meets_pm1_pace", "Meets the 2 % per year reduction pace", "", "Whether the KSI change beats the adopted target pace.", _PM1, (AGENCY,)),
]

METRICS: dict[str, MetricSpec] = {m.id: m for m in METRIC_LIST}
assert len(METRICS) == len(METRIC_LIST), "duplicate metric id"


def metrics_for(stakeholder: str) -> list[MetricSpec]:
    return [m for m in METRIC_LIST if stakeholder in m.stakeholders]


def format_value(spec: MetricSpec, value) -> str:
    """Render a value the way a planner would write it."""
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "yes" if value else "no"
    if spec.decimals == 0:
        return f"{int(round(value)):,}"
    return f"{value:,.{spec.decimals}f}"
