# Data dictionary

All data is synthetic. Times are East Africa Time (UTC+3). Empty cells mean "not applicable" or "not recorded".

Blood groups: `O+ A+ B+ AB+ O- A- B- AB-`. Components: `RBC` red cells, `WB` whole blood, `PLT` platelets, `FFP` fresh frozen plasma, `CRYO` cryoprecipitate.

## facilities.csv
| Column | Meaning |
|---|---|
| facility_id | `RBTC-xxx` regional blood transfusion centre, `SAT-xxx` satellite centre, `HSP-xxx` hospital |
| name | Generic facility name (not a real facility's data) |
| facility_type | regional_blood_centre, satellite_blood_centre, national_referral, county_referral, county_hospital, sub_county_hospital, maternity_hospital, mission_hospital, private_hospital |
| county | Kenyan county |
| lat, lon | Approximate location |
| keph_level | Kenya Essential Package for Health level (hospitals only) |
| beds | Approximate bed count (hospitals only) |
| grid_reliability | Share of days with no power cut (0 to 1) |
| connectivity | Best mobile data available: 4G, 3G, 2G |
| supply_centre_id | Regional centre that supplies this site |
| makes_platelets, separates_components | Processing capability (centres) |
| has_blood_fridge_backup_power | Generator, solar or UPS on the blood fridge |
| routine_deliveries_per_week | Scheduled deliveries from the supply centre (hospitals) |

## routes.csv
| Column | Meaning |
|---|---|
| from_facility_id, to_facility_id | Pair of facilities |
| road_km | Estimated road distance |
| typical_travel_hours | Typical drive time |
| road_quality | good, fair, poor |

## donors.csv
| Column | Meaning |
|---|---|
| donor_id | Donor record ID (some people have two records, see README) |
| sex | F or M |
| birth_date | Date of birth |
| blood_group | ABO and RhD group (sometimes missing) |
| home_county | County of residence |
| donor_category | student, general_public, faith_group, corporate, family_replacement |
| registration_date, registration_site_id | When and where first registered |
| preferred_channel | SMS, WhatsApp, voice_call, USSD, email |
| consent_to_contact | Agreed to be contacted for future donation |
| phone_last4 | Last 4 digits of a made-up phone number, for matching duplicates |

## drives.csv
| Column | Meaning |
|---|---|
| drive_id | Drive ID |
| date | Drive date |
| collecting_site_id | Centre running the drive |
| county | County of the collecting site |
| venue_type | secondary_school, university_college, church, mosque, corporate, market_or_stage, community_event, fixed_site_walk_in, emergency_appeal |
| registered_donors | People who registered |
| donations_collected, donors_deferred | Outcomes |

## donations.csv
| Column | Meaning |
|---|---|
| donation_id | Donation attempt ID |
| donor_id, drive_id | Who and where |
| collection_date, collecting_site_id | When and by which centre |
| outcome | collected, deferred, incomplete_collection |
| deferral_reason | low_haemoglobin, high_blood_pressure, underweight, recent_illness_or_malaria, medication, recent_tattoo_or_piercing, travel_or_exposure_risk, other |
| volume_ml | Volume collected |
| screening_result | non_reactive or reactive |
| tti_marker | Infection the donation was reactive for: HBV, HCV, syphilis, HIV |
| tested_date | Date screening finished |

## units.csv
| Column | Meaning |
|---|---|
| unit_id | Unit label: `U<yymm>-<centre>-<serial>-<component>` |
| donation_id | Source donation |
| component | RBC, WB, PLT, FFP, CRYO |
| blood_group | Group of the unit |
| collection_date, expiry_date | Shelf life window |
| processed_at_id | Centre that processed the unit |
| current_facility_id | Last known location |
| status | in_stock, transfused, expired, discarded_temperature |
| status_date | Date of final status |
| temp_excursion_exposed | Unit was in a fridge or cool box that went out of range |
| issued_request_id | Request it was issued for |
| opening_stock | Collected before 1 Nov 2025 and still on the shelf at the start |

## transfers.csv
| Column | Meaning |
|---|---|
| transfer_id | Movement ID |
| unit_id | Unit moved |
| from_facility_id, to_facility_id | Origin and destination |
| transfer_type | routine, emergency_request, emergency_cross_region, inter_centre_rebalancing |
| request_id | Linked request for emergency moves |
| dispatched_at, received_at | Times (received sometimes missing) |
| transport_mode | vehicle, motorbike, public_service_vehicle |
| coolbox_max_temp_c | Highest cool box temperature on the trip (above 10°C is an excursion) |

## requests.csv
| Column | Meaning |
|---|---|
| request_id | Request ID |
| facility_id | Requesting hospital (use this, not the name) |
| facility_name_raw | Name as typed by the hospital (messy) |
| requested_at | Time of request |
| clinical_indication | obstetric_haemorrhage, trauma_road_traffic, paediatric_severe_anaemia, surgery, medical_anaemia, sickle_cell_disease, oncology_haematology, renal, other |
| patient_sex, patient_age_band | Patient profile |
| patient_blood_group | Patient group, sometimes `unknown` in emergencies |
| component_requested | RBC, PLT, FFP |
| units_requested | Units asked for |
| urgency | emergency, urgent, routine |
| units_issued | Units the patient received |
| units_issued_group_substituted | Of those, units of a different but compatible group |
| units_from_local_stock | Of those, units already in the hospital |
| emergency_supplied_from_id | Centre that sent emergency units |
| last_unit_available_at | When the last issued unit was ready at the bedside |
| outcome | fulfilled, partially_fulfilled, not_fulfilled, deferred_to_later |

## daily_stock.csv
| Column | Meaning |
|---|---|
| date | Day |
| facility_id | Facility |
| component, blood_group | What |
| units_in_stock_end_of_day | Count on the shelf at the end of the day |

## power_outages.csv
| Column | Meaning |
|---|---|
| outage_id | Outage ID |
| facility_id | Facility |
| start_time, end_time, duration_hours | When and how long |
| backup_power_engaged | Whether backup kept the blood fridge running |

## temperature_logs.csv
| Column | Meaning |
|---|---|
| facility_id | Facility |
| recorded_at | Hour of reading |
| temp_c | Blood fridge temperature. Safe range for red cells and whole blood is 2 to 6°C. Gaps mean the logger was offline. -99.0, 99.9 and 0.0 are sensor glitches. |
