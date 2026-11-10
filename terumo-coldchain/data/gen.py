"""
Terumo BCT Africa Hackathon 2026 - Starter dataset generator.
Synthetic, Kenya-modelled blood system: 1 Nov 2025 to 31 Oct 2026.
Every record is generated. No real donors, patients or facility data.
"""
import heapq, math, os, random, sqlite3
from datetime import date, datetime, timedelta
import numpy as np
import pandas as pd

SEED = 2026
rng = np.random.default_rng(SEED)
random.seed(SEED)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

START = date(2025, 9, 1)   # simulation start (burn-in)
OUT_START = date(2025, 11, 1)  # published period start
END = date(2026, 10, 31)
DAYS = [START + timedelta(d) for d in range((END - START).days + 1)]
ND = len(DAYS)
didx = {d: i for i, d in enumerate(DAYS)}

GROUPS = ["O+", "A+", "B+", "AB+", "O-", "A-", "B-", "AB-"]
GROUP_P = np.array([0.455, 0.255, 0.205, 0.040, 0.020, 0.012, 0.010, 0.003])
GROUP_P = GROUP_P / GROUP_P.sum()
SHELF = {"RBC": 42, "WB": 35, "PLT": 5, "FFP": 365, "CRYO": 365}

# ---------------------------------------------------------------- facilities
F = []
def fac(fid, name, ftype, county, lat, lon, level, beds, power, conn, centre=None, plt=False, sep=False):
    F.append(dict(facility_id=fid, name=name, facility_type=ftype, county=county, lat=lat, lon=lon,
                  keph_level=level, beds=beds, grid_reliability=power, connectivity=conn,
                  supply_centre_id=centre, makes_platelets=plt, separates_components=sep))

# Regional blood transfusion centres (RBTC)
fac("RBTC-NBO", "Nairobi Regional Blood Transfusion Centre", "regional_blood_centre", "Nairobi", -1.300, 36.807, None, 0, 0.97, "4G", None, True, True)
fac("RBTC-MSA", "Mombasa Regional Blood Transfusion Centre", "regional_blood_centre", "Mombasa", -4.050, 39.668, None, 0, 0.93, "4G", None, True, True)
fac("RBTC-KSM", "Kisumu Regional Blood Transfusion Centre", "regional_blood_centre", "Kisumu", -0.091, 34.768, None, 0, 0.90, "4G", None, True, True)
fac("RBTC-ELD", "Eldoret Regional Blood Transfusion Centre", "regional_blood_centre", "Uasin Gishu", 0.514, 35.270, None, 0, 0.91, "4G", None, True, True)
fac("RBTC-NKR", "Nakuru Regional Blood Transfusion Centre", "regional_blood_centre", "Nakuru", -0.303, 36.080, None, 0, 0.92, "4G", None, False, True)
fac("RBTC-EMB", "Embu Regional Blood Transfusion Centre", "regional_blood_centre", "Embu", -0.531, 37.450, None, 0, 0.88, "4G", None, False, False)
# Satellite collection/storage sites
for fid, nm, cty, la, lo, pw, cn, c in [
    ("SAT-NYR", "Nyeri Satellite Blood Centre", "Nyeri", -0.420, 36.951, 0.88, "4G", "RBTC-NKR"),
    ("SAT-KAK", "Kakamega Satellite Blood Centre", "Kakamega", 0.283, 34.752, 0.84, "4G", "RBTC-KSM"),
    ("SAT-KSI", "Kisii Satellite Blood Centre", "Kisii", -0.681, 34.766, 0.83, "3G", "RBTC-KSM"),
    ("SAT-GSA", "Garissa Satellite Blood Centre", "Garissa", -0.453, 39.646, 0.72, "3G", "RBTC-NBO"),
    ("SAT-MKS", "Machakos Satellite Blood Centre", "Machakos", -1.517, 37.263, 0.87, "4G", "RBTC-NBO"),
    ("SAT-MRU", "Meru Satellite Blood Centre", "Meru", 0.047, 37.649, 0.85, "4G", "RBTC-EMB"),
    ("SAT-KTL", "Kitale Satellite Blood Centre", "Trans Nzoia", 1.016, 35.006, 0.82, "3G", "RBTC-ELD"),
    ("SAT-LDW", "Lodwar Satellite Blood Centre", "Turkana", 3.119, 35.597, 0.62, "2G", "RBTC-ELD"),
    ("SAT-MLD", "Malindi Satellite Blood Centre", "Kilifi", -3.219, 40.117, 0.80, "3G", "RBTC-MSA"),
]:
    fac(fid, nm, "satellite_blood_centre", cty, la, lo, None, 0, pw, cn, c)
# Hospitals (names are generic and synthetic)
H = [
 # id, name, type, county, lat, lon, level, beds, power, conn, centre, demand_weight, profile
 ("HSP-001", "National Referral Hospital (Nairobi)", "national_referral", "Nairobi", -1.301, 36.807, 6, 1800, 0.98, "4G", "RBTC-NBO", 9.0, "tertiary"),
 ("HSP-002", "Eastlands County Hospital", "county_hospital", "Nairobi", -1.283, 36.880, 4, 260, 0.93, "4G", "RBTC-NBO", 2.2, "urban"),
 ("HSP-003", "City Maternity Hospital", "maternity_hospital", "Nairobi", -1.276, 36.837, 5, 350, 0.94, "4G", "RBTC-NBO", 2.8, "maternity"),
 ("HSP-004", "Westlands Private Hospital", "private_hospital", "Nairobi", -1.265, 36.805, 5, 280, 0.99, "4G", "RBTC-NBO", 2.0, "private"),
 ("HSP-005", "Kiambu County Referral Hospital", "county_referral", "Kiambu", -1.171, 36.835, 5, 300, 0.93, "4G", "RBTC-NBO", 2.0, "urban"),
 ("HSP-006", "Thika Level 5 Hospital", "county_referral", "Kiambu", -1.039, 37.083, 5, 330, 0.92, "4G", "RBTC-NBO", 2.1, "highway"),
 ("HSP-007", "Kajiado County Referral Hospital", "county_referral", "Kajiado", -1.852, 36.776, 4, 160, 0.85, "3G", "RBTC-NBO", 1.0, "rural"),
 ("HSP-008", "Coast Teaching and Referral Hospital", "county_referral", "Mombasa", -4.058, 39.672, 5, 700, 0.93, "4G", "RBTC-MSA", 4.5, "tertiary"),
 ("HSP-009", "Kilifi County Hospital", "county_referral", "Kilifi", -3.631, 39.849, 4, 220, 0.83, "3G", "RBTC-MSA", 1.6, "malaria"),
 ("HSP-010", "Msambweni County Referral Hospital", "county_referral", "Kwale", -4.468, 39.480, 4, 180, 0.80, "3G", "RBTC-MSA", 1.1, "malaria"),
 ("HSP-011", "Voi County Hospital", "county_hospital", "Taita Taveta", -3.396, 38.556, 4, 150, 0.82, "3G", "RBTC-MSA", 1.2, "highway"),
 ("HSP-012", "Kisumu County Referral Hospital", "county_referral", "Kisumu", -0.098, 34.762, 5, 500, 0.90, "4G", "RBTC-KSM", 3.6, "malaria"),
 ("HSP-013", "Homa Bay County Referral Hospital", "county_referral", "Homa Bay", -0.527, 34.457, 4, 230, 0.80, "3G", "RBTC-KSM", 1.7, "malaria"),
 ("HSP-014", "Siaya County Referral Hospital", "county_referral", "Siaya", 0.061, 34.288, 4, 200, 0.78, "3G", "RBTC-KSM", 1.6, "malaria"),
 ("HSP-015", "Busia County Referral Hospital", "county_referral", "Busia", 0.460, 34.111, 4, 190, 0.79, "3G", "RBTC-KSM", 1.3, "malaria"),
 ("HSP-016", "Migori County Referral Hospital", "county_referral", "Migori", -1.063, 34.473, 4, 180, 0.78, "3G", "RBTC-KSM", 1.2, "malaria"),
 ("HSP-017", "Lake Region Mission Hospital", "mission_hospital", "Kisii", -0.677, 34.780, 4, 210, 0.86, "3G", "RBTC-KSM", 1.3, "rural"),
 ("HSP-018", "Western Rift Teaching and Referral Hospital", "national_referral", "Uasin Gishu", 0.517, 35.283, 6, 1000, 0.94, "4G", "RBTC-ELD", 5.5, "tertiary"),
 ("HSP-019", "Kapsabet County Hospital", "county_hospital", "Nandi", 0.204, 35.105, 4, 150, 0.84, "3G", "RBTC-ELD", 0.9, "rural"),
 ("HSP-020", "Iten County Hospital", "county_hospital", "Elgeyo Marakwet", 0.670, 35.508, 4, 120, 0.82, "3G", "RBTC-ELD", 0.7, "rural"),
 ("HSP-021", "Lodwar County Referral Hospital", "county_referral", "Turkana", 3.120, 35.598, 4, 170, 0.62, "2G", "RBTC-ELD", 1.0, "remote"),
 ("HSP-022", "Nakuru County Referral Hospital", "county_referral", "Nakuru", -0.288, 36.068, 5, 450, 0.91, "4G", "RBTC-NKR", 3.4, "highway"),
 ("HSP-023", "Naivasha Sub-County Hospital", "sub_county_hospital", "Nakuru", -0.717, 36.432, 4, 160, 0.88, "4G", "RBTC-NKR", 1.5, "highway"),
 ("HSP-024", "Narok County Referral Hospital", "county_referral", "Narok", -1.080, 35.871, 4, 160, 0.80, "3G", "RBTC-NKR", 1.0, "rural"),
 ("HSP-025", "Highlands Private Hospital", "private_hospital", "Nakuru", -0.281, 36.071, 4, 120, 0.98, "4G", "RBTC-NKR", 0.9, "private"),
 ("HSP-026", "Kericho County Referral Hospital", "county_referral", "Kericho", -0.369, 35.284, 4, 200, 0.87, "4G", "RBTC-NKR", 1.1, "rural"),
 ("HSP-027", "Embu Level 5 Hospital", "county_referral", "Embu", -0.532, 37.457, 5, 380, 0.89, "4G", "RBTC-EMB", 2.0, "urban"),
 ("HSP-028", "Meru Teaching and Referral Hospital", "county_referral", "Meru", 0.049, 37.655, 5, 400, 0.88, "4G", "RBTC-EMB", 2.0, "urban"),
 ("HSP-029", "Kitui County Referral Hospital", "county_referral", "Kitui", -1.367, 38.011, 4, 220, 0.80, "3G", "RBTC-EMB", 1.2, "rural"),
 ("HSP-030", "Isiolo County Referral Hospital", "county_referral", "Isiolo", 0.354, 37.582, 4, 140, 0.76, "3G", "RBTC-EMB", 0.7, "remote"),
 ("HSP-031", "Marsabit County Referral Hospital", "county_referral", "Marsabit", 2.334, 37.990, 4, 130, 0.65, "2G", "RBTC-EMB", 0.6, "remote"),
 ("HSP-032", "Garissa County Referral Hospital", "county_referral", "Garissa", -0.455, 39.640, 5, 260, 0.72, "3G", "RBTC-NBO", 1.3, "remote"),
]
HMETA = {}
for h in H:
    fac(h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7], h[8], h[9], h[10])
    HMETA[h[0]] = dict(weight=h[11], profile=h[12])
FD = {f["facility_id"]: f for f in F}
CENTRES = [f["facility_id"] for f in F if f["facility_type"] == "regional_blood_centre"]
SATS = [f["facility_id"] for f in F if f["facility_type"] == "satellite_blood_centre"]
HOSP = [h[0] for h in H]

def hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, [a["lat"], a["lon"], b["lat"], b["lon"]])
    x = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(x))

routes = []
for a in F:
    for b in F:
        if a is b: continue
        km = hav(a, b) * 1.32
        remote = min(a["grid_reliability"], b["grid_reliability"]) < 0.75
        speed = 38 if remote else (30 if km < 25 else 52)
        hrs = km / speed + 0.3
        routes.append(dict(from_facility_id=a["facility_id"], to_facility_id=b["facility_id"],
                           road_km=round(km, 1), typical_travel_hours=round(hrs, 2),
                           road_quality="poor" if remote else ("good" if km < 400 else "fair")))
RT = {(r["from_facility_id"], r["to_facility_id"]): r for r in routes}

# Hospital ordering behaviour
for hid in HOSP:
    f = FD[hid]; m = HMETA[hid]
    r = RT[(f["supply_centre_id"], hid)]
    f["routine_deliveries_per_week"] = 3 if r["road_km"] < 120 else (2 if r["road_km"] < 320 else 1)
    f["has_blood_fridge_backup_power"] = bool(rng.random() < (0.95 if f["grid_reliability"] > 0.9 else 0.55))
    # over-orderers waste, under-orderers stock out
    m["par_factor"] = {"private": 1.9, "tertiary": 1.25, "maternity": 1.3}.get(m["profile"], 1.0) * float(rng.uniform(0.85, 1.15))
    if hid in ("HSP-021", "HSP-031", "HSP-030"):
        m["par_factor"] *= 0.7
for fid in CENTRES + SATS:
    FD[fid]["has_blood_fridge_backup_power"] = bool(rng.random() < 0.9)
    FD[fid]["routine_deliveries_per_week"] = None

# ---------------------------------------------------------------- seasonality
def school_term(d):
    # Kenyan school calendar 2025/26 (approximate): long holiday Nov-early Jan, April and August breaks
    if date(2025, 10, 25) <= d < date(2026, 1, 5): return False
    if date(2026, 4, 2) <= d <= date(2026, 4, 26): return False
    if date(2026, 7, 31) <= d <= date(2026, 8, 30): return False
    if d >= date(2026, 10, 30): return False
    return True

def trauma_mult(d):
    m = 1.0
    if d.month == 12 and d.day >= 15: m = 1.6
    if d.month == 1 and d.day <= 5: m = 1.5
    if date(2026, 4, 2) <= d <= date(2026, 4, 7): m = 1.45  # Easter 2026
    if d.weekday() in (4, 5, 6): m *= 1.2
    return m

def malaria_mult(d, profile):
    if profile != "malaria": return 1.0
    base = {1: .9, 2: .85, 3: .95, 4: 1.25, 5: 1.6, 6: 1.75, 7: 1.5, 8: 1.15, 9: 1.0, 10: 1.05, 11: 1.3, 12: 1.35}
    return base[d.month]

# ---------------------------------------------------------------- donors and drives
SITES = CENTRES + SATS
site_catch = {s: FD[s]["county"] for s in SITES}
VENUES = [("secondary_school", .38), ("university_college", .16), ("church", .12), ("mosque", .04),
          ("corporate", .09), ("market_or_stage", .08), ("community_event", .06), ("fixed_site_walk_in", .07)]
site_capacity = {"RBTC-NBO": 3.2, "RBTC-MSA": 1.6, "RBTC-KSM": 1.6, "RBTC-ELD": 1.5, "RBTC-NKR": 1.4, "RBTC-EMB": 1.0}
for s in SATS: site_capacity[s] = 0.45 if s not in ("SAT-LDW", "SAT-GSA") else 0.25

drives = []
did = 0
for d in DAYS:
    term = school_term(d)
    for s in SITES:
        lam = site_capacity[s] * (0.55 if d.weekday() == 6 else 1.0)
        n = rng.poisson(lam * 0.19)
        for _ in range(n):
            vp = np.array([w for _, w in VENUES])
            if not term:
                vp[0] *= 0.03; vp[1] *= 0.35
            if d.weekday() == 6: vp[2] *= 2.5
            if d.weekday() == 4: vp[3] *= 2.5
            vp = vp / vp.sum()
            venue = VENUES[rng.choice(len(VENUES), p=vp)][0]
            target = {"secondary_school": 70, "university_college": 85, "church": 35, "mosque": 30, "corporate": 40,
                      "market_or_stage": 25, "community_event": 45, "fixed_site_walk_in": 12}[venue]
            did += 1
            registered = max(5, int(rng.normal(target, target * 0.3)))
            drives.append(dict(drive_id=f"DRV-{did:05d}", date=d, collecting_site_id=s, county=site_catch[s],
                               venue_type=venue, registered_donors=registered))
# National-level appeals after reported shortages (mid Jan, late Aug)
for d0 in (date(2026, 1, 19), date(2026, 8, 24)):
    for k in range(6):
        for s in ("RBTC-NBO", "RBTC-MSA", "RBTC-KSM", "RBTC-ELD"):
            did += 1
            drives.append(dict(drive_id=f"DRV-{did:05d}", date=d0 + timedelta(k), collecting_site_id=s, county=site_catch[s],
                               venue_type="emergency_appeal", registered_donors=int(rng.normal(60, 15))))

donors = []
donor_pool = {s: [] for s in SITES}  # repeat-eligible donor indices per site
def new_donor(site, venue, d):
    i = len(donors)
    if venue == "secondary_school":
        age = int(rng.integers(16, 20)); cat = "student"
    elif venue == "university_college":
        age = int(rng.integers(18, 26)); cat = "student"
    elif venue == "corporate":
        age = int(rng.integers(23, 55)); cat = "corporate"
    elif venue in ("church", "mosque"):
        age = int(rng.integers(18, 60)); cat = "faith_group"
    elif venue == "emergency_appeal":
        age = int(rng.integers(18, 55)); cat = "general_public"
    else:
        age = int(rng.integers(18, 58)); cat = "general_public" if rng.random() < .8 else "family_replacement"
    sex = "F" if rng.random() < (0.42 if cat == "student" else 0.30) else "M"
    bdate = d - timedelta(days=int(age * 365.25 + rng.integers(0, 365)))
    donors.append(dict(donor_id=f"DNR-{i+1:06d}", sex=sex, birth_date=bdate, blood_group=GROUPS[rng.choice(8, p=GROUP_P)],
                       home_county=FD[site]["county"] if rng.random() < .85 else FD[random.choice(SITES)]["county"],
                       donor_category=cat, registration_date=d, registration_site_id=site,
                       preferred_channel=rng.choice(["SMS", "WhatsApp", "voice_call", "USSD", "email"], p=[.45, .3, .12, .08, .05]),
                       consent_to_contact=bool(rng.random() < .82), phone_last4=f"{rng.integers(0, 10000):04d}",
                       loyal=float(rng.beta(1.2, 6))))
    return i

donations = []
units = []
pending_release = {i: [] for i in range(ND + 10)}
last_don = {}
DEFER = [("low_haemoglobin", .46), ("high_blood_pressure", .12), ("underweight", .1), ("recent_illness_or_malaria", .12),
         ("medication", .06), ("recent_tattoo_or_piercing", .04), ("travel_or_exposure_risk", .05), ("other", .05)]
TTI = [("HBV", .0346), ("HCV", .0321), ("syphilis", .0156), ("HIV", .0115)]
dn = 0
for dr in sorted(drives, key=lambda x: x["date"]):
    d = dr["date"]; s = dr["collecting_site_id"]
    n = dr["registered_donors"]
    for _ in range(n):
        # repeat donor?
        pool = donor_pool[s]
        donor_i = None
        if pool and rng.random() < (0.6 if dr["venue_type"] not in ("secondary_school",) else 0.22):
            cand = pool[int(rng.integers(0, len(pool)))]
            gap = (d - last_don.get(cand, date(2000, 1, 1))).days
            mingap = 120 if donors[cand]["sex"] == "F" else 90
            if rng.random() < donors[cand]["loyal"] * 4.0 and (gap >= mingap or rng.random() < 0.015):
                donor_i = cand
        if donor_i is None:
            donor_i = new_donor(s, dr["venue_type"], d)
            pool.append(donor_i)
        dn += 1
        don = donors[donor_i]
        defer = None
        pdef = 0.085 + (0.07 if don["sex"] == "F" else 0) + (0.03 if dr["venue_type"] == "emergency_appeal" else 0)
        if rng.random() < pdef:
            defer = DEFER[rng.choice(len(DEFER), p=[w for _, w in DEFER])][0]
            if don["sex"] == "F" and rng.random() < .3: defer = "low_haemoglobin"
        rec = dict(donation_id=f"DON-{dn:06d}", donor_id=don["donor_id"], drive_id=dr["drive_id"], collection_date=d,
                   collecting_site_id=s, outcome="deferred" if defer else "collected", deferral_reason=defer,
                   volume_ml=None, screening_result=None, tti_marker=None, tested_date=None)
        last_don[donor_i] = d if not defer else last_don.get(donor_i, date(2000, 1, 1))
        if not defer:
            if rng.random() < .025:
                rec["outcome"] = "incomplete_collection"; rec["volume_ml"] = int(rng.integers(150, 380))
            else:
                rec["volume_ml"] = int(rng.normal(452, 12))
            lag = int(rng.choice([1, 2, 3, 4, 6], p=[.35, .35, .17, .08, .05]))
            if s in ("SAT-LDW", "SAT-GSA", "SAT-MLD"): lag += int(rng.integers(1, 4))
            rec["tested_date"] = d + timedelta(lag)
            reactive = None
            for mk, p in TTI:
                if rng.random() < p * 0.85 * (1.15 if don["sex"] == "M" else 1.0) * (0.55 if donor_i in pool[:-1] and don["registration_date"] < d else 1.0):
                    reactive = mk; break
            rec["screening_result"] = "reactive" if reactive else "non_reactive"
            rec["tti_marker"] = reactive
            if rec["outcome"] == "collected" and not reactive:
                pending_release[min(didx.get(rec["tested_date"], ND), ND + 9)].append((dn - 1, s, don["blood_group"], d))
        donations.append(rec)

# ---------------------------------------------------------------- simulation
# inventory[(facility, component, group)] = heap of (expiry_idx, unit_index)
inv = {}
def inv_push(f, comp, grp, exp, ui):
    heapq.heappush(inv.setdefault((f, comp, grp), []), (exp, ui))

def mk_unit(don_i, comp, grp, cdate, centre, held_by):
    ui = len(units)
    exp = cdate + timedelta(SHELF[comp])
    units.append(dict(unit_id=f"U{cdate:%y%m}-{centre[-3:]}-{ui+1:06d}-{comp}", donation_id=donations[don_i]["donation_id"],
                      component=comp, blood_group=grp, collection_date=cdate, expiry_date=exp, processed_at_id=centre,
                      current_facility_id=held_by, status="in_stock", status_date=None, temp_excursion_exposed=False,
                      issued_request_id=None))
    return ui, exp

def centre_of(site):
    return site if site in CENTRES else FD[site]["supply_centre_id"]

transfers = []
requests = []
tx = 0
rq = 0
# hospital par levels per group (RBC/WB units)
par = {}
for hid in HOSP:
    w = HMETA[hid]["weight"] * HMETA[hid]["par_factor"]
    for g, p in zip(GROUPS, GROUP_P):
        par[(hid, g)] = max(0, int(round(w * 9 * p * 2.2))) + (1 if g in ("O+",) else 0)
hosp_comp = {hid: ("WB" if FD[FD[hid]["supply_centre_id"]]["separates_components"] is False or HMETA[hid]["profile"] == "remote" else "RBC") for hid in HOSP}

CAT = [("obstetric_haemorrhage", .22), ("trauma_road_traffic", .17), ("paediatric_severe_anaemia", .16), ("surgery", .17),
       ("medical_anaemia", .1), ("sickle_cell_disease", .05), ("oncology_haematology", .06), ("renal", .03), ("other", .04)]

def compatible_rbc(g):
    abo, rh = g[:-1], g[-1]
    abo_ok = {"O": ["O"], "A": ["A", "O"], "B": ["B", "O"], "AB": ["AB", "A", "B", "O"]}[abo]
    rh_ok = ["-"] if rh == "-" else ["+", "-"]
    out = [g]
    for a in abo_ok:
        for r in rh_ok:
            gg = a + r
            if gg not in out: out.append(gg)
    return out

def pop_unit(fid, comp, groups, d_i, fifo=True):
    for g in groups:
        h = inv.get((fid, comp, g))
        while h and h[0][0] < d_i:
            _, ui = heapq.heappop(h)
            units[ui]["status"] = "expired"; units[ui]["status_date"] = units[ui]["expiry_date"]
        if h:
            if fifo or len(h) < 3:
                return heapq.heappop(h)[1]
            k = int(rng.integers(0, len(h)))
            item = h.pop(k); heapq.heapify(h)
            return item[1]
    return None

def count(fid, comp, g):
    h = inv.get((fid, comp, g)); return len(h) if h else 0

# outages and temperature: pre-generate outages per facility
outages = []
oid = 0
outage_hours = {}  # (fid, day_idx) -> list of (start_h, dur_h, backup)
for f in F:
    rel = f["grid_reliability"]
    for i, d in enumerate(DAYS):
        p = (1 - rel) * 0.9
        if d.month in (4, 5, 11): p *= 1.4  # rains
        if rng.random() < p:
            dur = float(np.clip(rng.lognormal(1.0, 0.8), 0.25, 30))
            st = float(rng.uniform(0, 24))
            backup = f["has_blood_fridge_backup_power"] and rng.random() < 0.88
            oid += 1
            sdt = datetime.combine(d, datetime.min.time()) + timedelta(hours=st)
            outages.append(dict(outage_id=f"OUT-{oid:05d}", facility_id=f["facility_id"], start_time=sdt,
                                end_time=sdt + timedelta(hours=dur), duration_hours=round(dur, 2),
                                backup_power_engaged=backup))
            outage_hours.setdefault((f["facility_id"], i), []).append((st, dur, backup))

# temperature logs hourly, compute excursions (>6C for >=2h)
temps = []
excursion_days = {}
for f in F:
    fid = f["facility_id"]
    t = 4.0
    off_until = -1
    rising_hours = 0
    offline_until = -1
    total_h = ND * 24
    # build outage mask
    mask = np.zeros(total_h + 48, dtype=bool)
    for (ff, i), lst in outage_hours.items():
        if ff != fid: continue
        for st, dur, backup in lst:
            if backup: continue
            a = i * 24 + int(st); b = a + int(math.ceil(dur))
            mask[a:b] = True
    door = rng.random(total_h) < 0.02
    run = 0
    for h in range(total_h):
        if mask[h]:
            t = min(t + rng.uniform(0.6, 1.1), 24)
        else:
            t = t - (t - 4.0) * 0.45 + rng.normal(0, 0.18)
            if door[h]: t += rng.uniform(0.8, 2.2)
        run = run + 1 if t > 6 else 0
        if run == 4:
            excursion_days.setdefault(fid, set()).add(h // 24)
        # logger offline gaps (poor connectivity facilities lose data)
        if h > offline_until and rng.random() < {"4G": 0.0004, "3G": 0.0015, "2G": 0.004}[f["connectivity"]]:
            offline_until = h + int(rng.integers(3, 60))
        if h <= offline_until:
            continue
        temps.append((fid, datetime.combine(START, datetime.min.time()) + timedelta(hours=h), round(float(t), 1)))

def ship(src, dst, ui, d_i, kind, req=None):
    global tx
    r = RT[(src, dst)]
    tx += 1
    disp = datetime.combine(DAYS[d_i], datetime.min.time()) + timedelta(hours=float(rng.uniform(7, 15) if kind == "routine" else rng.uniform(0, 23)))
    if kind != "routine":
        disp = disp
    hrs = r["typical_travel_hours"] * float(rng.uniform(0.85, 1.6 if r["road_quality"] == "poor" else 1.3))
    rec = disp + timedelta(hours=hrs)
    maxt = round(float(rng.normal(4.8, 0.9) + (2.5 if rng.random() < (0.12 if r["road_quality"] == "poor" else 0.03) else 0)), 1)
    transfers.append(dict(transfer_id=f"TRF-{tx:06d}", unit_id=units[ui]["unit_id"], from_facility_id=src, to_facility_id=dst,
                          transfer_type=kind, request_id=req, dispatched_at=disp,
                          received_at=None if rng.random() < 0.03 else rec,
                          transport_mode=rng.choice(["vehicle", "motorbike", "public_service_vehicle"], p=[.6, .3, .1]) if kind != "routine" else "vehicle",
                          coolbox_max_temp_c=maxt))
    units[ui]["current_facility_id"] = dst
    if maxt > 10: units[ui]["temp_excursion_exposed"] = True
    return rec

PLT_HOSP = [h for h in HOSP if HMETA[h]["profile"] in ("tertiary",)] + ["HSP-012", "HSP-022", "HSP-004"]

for i, d in enumerate(DAYS):
    # 1. release screened units into centres (components made at the centre)
    for (don_i, site, grp, cdate) in pending_release.get(i, []):
        c = centre_of(site)
        fdc = FD[c]
        if fdc["separates_components"] and rng.random() < 0.72:
            ui, exp = mk_unit(don_i, "RBC", grp, cdate, c, c); inv_push(c, "RBC", grp, didx.get(exp, ND + 99), ui)
            if rng.random() < 0.35:
                comp = "CRYO" if rng.random() < 0.06 else "FFP"
                ui, exp = mk_unit(don_i, comp, grp, cdate, c, c); inv_push(c, comp, grp, didx.get(exp, ND + 999), ui)
            if fdc["makes_platelets"] and rng.random() < 0.15:
                ui, exp = mk_unit(don_i, "PLT", grp, cdate, c, c); inv_push(c, "PLT", grp, didx.get(exp, ND + 99), ui)
        else:
            ui, exp = mk_unit(don_i, "WB", grp, cdate, c, c); inv_push(c, "WB", grp, didx.get(exp, ND + 99), ui)

    # 2. cold-chain excursions: units in the facility fridge are discarded (mostly)
    for f in F:
        fid = f["facility_id"]
        if i in excursion_days.get(fid, ()):
            for comp in ("RBC", "WB", "PLT"):
                for g in GROUPS:
                    h = inv.get((fid, comp, g))
                    if not h: continue
                    keep = []
                    for exp, ui in h:
                        units[ui]["temp_excursion_exposed"] = True
                        if rng.random() < 0.45:
                            units[ui]["status"] = "discarded_temperature"; units[ui]["status_date"] = d
                        else:
                            keep.append((exp, ui))  # kept in use despite exposure (a real-world risk)
                    heapq.heapify(keep); inv[(fid, comp, g)] = keep

    # 3. routine restock: centre -> hospitals on delivery days
    for hid in HOSP:
        f = FD[hid]; per = f["routine_deliveries_per_week"]
        days_ok = {3: (0, 2, 4), 2: (1, 4), 1: (2,)}[per]
        if d.weekday() not in days_ok: continue
        c = f["supply_centre_id"]; comp = hosp_comp[hid]
        for g in GROUPS:
            need = par[(hid, g)] * (7 / per) / 3.5 - count(hid, comp, g)
            need = int(round(need))
            for _ in range(max(0, need)):
                ui = pop_unit(c, comp, [g], i)
                if ui is None: ui = pop_unit(c, "WB" if comp == "RBC" else "RBC", [g], i)
                if ui is None: break
                ship(c, hid, ui, i, "routine")
                inv_push(hid, units[ui]["component"], g, didx.get(units[ui]["expiry_date"], ND + 99), ui)
        if hid in PLT_HOSP or HMETA[hid]["profile"] in ("tertiary", "maternity"):
            for g in ("O+", "A+", "B+", "AB+"):
                tgt = 2 if HMETA[hid]["profile"] != "tertiary" else 6
                for _ in range(max(0, tgt - count(hid, "FFP", g))):
                    ui = pop_unit(c, "FFP", [g], i)
                    if ui is None: break
                    ship(c, hid, ui, i, "routine"); inv_push(hid, "FFP", g, didx.get(units[ui]["expiry_date"], ND + 999), ui)

    # 4. weekly balancing from Nairobi to centres running low
    if d.weekday() == 0:
        for c in CENTRES[1:]:
            for g in ("O+", "O-", "A+", "B+"):
                comp = "RBC" if FD[c]["separates_components"] else "WB"
                if count(c, comp, g) < (4 if g.endswith("-") else 20):
                    for _ in range(int(rng.integers(5, 25)) if g.endswith("+") else 2):
                        ui = pop_unit("RBTC-NBO", comp, [g], i)
                        if ui is None: ui = pop_unit("RBTC-NBO", "RBC", [g], i)
                        if ui is None: break
                        ship("RBTC-NBO", c, ui, i, "inter_centre_rebalancing")
                        inv_push(c, units[ui]["component"], g, didx.get(units[ui]["expiry_date"], ND + 99), ui)

    # 5. clinical requests at hospitals
    for hid in HOSP:
        m = HMETA[hid]; prof = m["profile"]
        lam = m["weight"] * 0.78
        lam *= 0.75 if d.weekday() == 6 else 1.0
        for _ in range(rng.poisson(lam)):
            cp = np.array([w for _, w in CAT])
            if prof == "maternity": cp[0] *= 4
            if prof == "malaria": cp[2] *= 2.2 * malaria_mult(d, prof); cp[5] *= 2
            if prof in ("highway",): cp[1] *= 1.8
            cp[1] *= trauma_mult(d)
            if prof == "tertiary": cp[6] *= 2.5; cp[3] *= 1.4; cp[7] *= 2
            cp = cp / cp.sum()
            cat = CAT[rng.choice(len(CAT), p=cp)][0]
            grp = GROUPS[rng.choice(8, p=GROUP_P)]
            urgency = {"obstetric_haemorrhage": .8, "trauma_road_traffic": .85, "paediatric_severe_anaemia": .55}.get(cat, .2)
            u = "emergency" if rng.random() < urgency else ("urgent" if rng.random() < .5 else "routine")
            comp = "RBC"
            if cat in ("oncology_haematology",) and rng.random() < .5 and hid in PLT_HOSP: comp = "PLT"
            if cat in ("obstetric_haemorrhage", "trauma_road_traffic") and rng.random() < .12: comp = "FFP"
            nunits = int(rng.choice([1, 2, 3, 4, 6], p=[.38, .34, .14, .1, .04]))
            if cat == "paediatric_severe_anaemia": nunits = 1
            if comp == "PLT": nunits = int(rng.choice([1, 4, 6], p=[.3, .5, .2]))
            rq += 1
            rid = f"REQ-{rq:06d}"
            rt = datetime.combine(d, datetime.min.time()) + timedelta(hours=float(rng.uniform(0, 24)))
            got = 0; got_sub = 0; local = 0
            last_t = rt
            comps = [comp] if comp != "RBC" else [hosp_comp[hid], "RBC" if hosp_comp[hid] == "WB" else "WB"]
            fifo = rng.random() < (0.9 if prof in ("tertiary", "private") else 0.78)
            grp_list = compatible_rbc(grp) if comp in ("RBC", "WB") else [grp, "O+", "A+", "B+", "AB+"]
            for _ in range(nunits):
                ui = None
                for cc in comps:
                    ui = pop_unit(hid, cc, grp_list, i, fifo)
                    if ui is not None: break
                if ui is None: break
                got += 1; local += 1
                if units[ui]["blood_group"] != grp: got_sub += 1
                units[ui]["status"] = "transfused"; units[ui]["status_date"] = d; units[ui]["issued_request_id"] = rid
                last_t = rt + timedelta(minutes=float(rng.uniform(20, 90)))
            emergency_from = None
            if got < nunits and u != "routine":
                # emergency order from supply centre, then other centres
                c = FD[hid]["supply_centre_id"]
                order = [c] + sorted([x for x in CENTRES if x != c], key=lambda x: RT[(x, hid)]["road_km"])[:2]
                for src in order:
                    while got < nunits:
                        ui = None
                        for cc in comps:
                            ui = pop_unit(src, cc, grp_list, i)
                            if ui is not None: break
                        if ui is None: break
                        kind = "emergency_request" if src == c else "emergency_cross_region"
                        arr = ship(src, hid, ui, i, kind, rid)
                        # emergency dispatch timed from request
                        transfers[-1]["dispatched_at"] = rt + timedelta(hours=float(rng.uniform(0.5, 3.5)))
                        rr = RT[(src, hid)]
                        arr = transfers[-1]["dispatched_at"] + timedelta(hours=rr["typical_travel_hours"] * float(rng.uniform(.9, 1.5)))
                        if transfers[-1]["received_at"] is not None: transfers[-1]["received_at"] = arr
                        got += 1; emergency_from = emergency_from or src
                        if units[ui]["blood_group"] != grp: got_sub += 1
                        units[ui]["status"] = "transfused"; units[ui]["status_date"] = d; units[ui]["issued_request_id"] = rid
                        last_t = max(last_t, arr)
                    if got >= nunits: break
            outcome = "fulfilled" if got >= nunits else ("partially_fulfilled" if got > 0 else "not_fulfilled")
            if outcome == "not_fulfilled" and u == "routine" and rng.random() < .6: outcome = "deferred_to_later"
            requests.append(dict(request_id=rid, facility_id=hid, facility_name_raw=FD[hid]["name"], requested_at=rt,
                                 clinical_indication=cat, patient_sex=("F" if cat == "obstetric_haemorrhage" else rng.choice(["F", "M"])),
                                 patient_age_band=("0-4" if cat == "paediatric_severe_anaemia" and rng.random() < .8 else
                                                   rng.choice(["5-14", "15-24", "25-34", "35-49", "50-64", "65+"])) if cat != "obstetric_haemorrhage" else rng.choice(["15-24", "25-34", "35-49"]),
                                 patient_blood_group=grp, component_requested=comp, units_requested=nunits, urgency=u,
                                 units_issued=got, units_issued_group_substituted=got_sub, units_from_local_stock=local,
                                 emergency_supplied_from_id=emergency_from,
                                 last_unit_available_at=last_t if got else None, outcome=outcome))

    # 6. expiry sweep at all facilities (end of day) + snapshot
    if i % 1 == 0:
        pass

# end-of-period sweep: anything past expiry
for key, h in inv.items():
    for exp, ui in h:
        if exp < ND and units[ui]["status"] == "in_stock":
            units[ui]["status"] = "expired"; units[ui]["status_date"] = units[ui]["expiry_date"]
# units whose expiry passed but never swept get status_date
for u in units:
    if u["status"] == "expired" and u["status_date"] is None:
        u["status_date"] = min(u["expiry_date"], END)
for d_ in donations:
    pass
# TTI discards as units are not created; record discarded donations
print("built", len(donors), len(donations), len(units), len(requests), len(transfers), len(temps))

# ---------------------------------------------------------------- daily stock snapshots (reconstructed)
U = pd.DataFrame(units)
T = pd.DataFrame(transfers)
# location timeline: unit at processed centre from collection(test) until first transfer, etc.
# reconstruct via intervals: [arrive, leave) at each facility
U["release_date"] = U["donation_id"].map({x["donation_id"]: x["tested_date"] for x in donations})
segs = []
tt = T.sort_values("dispatched_at").groupby("unit_id")
tmap = {k: v for k, v in tt}
end_date = U["status_date"].where(U["status"] != "in_stock", END + timedelta(1))
for r, ed in zip(U.itertuples(index=False), end_date):
    start = r.release_date
    loc = r.processed_at_id
    if r.unit_id in tmap:
        for tr in tmap[r.unit_id].itertuples(index=False):
            dd = tr.dispatched_at.date()
            segs.append((loc, r.component, r.blood_group, start, dd))
            loc = tr.to_facility_id; start = dd
    segs.append((loc, r.component, r.blood_group, start, ed if ed is not None else END + timedelta(1)))
S = pd.DataFrame(segs, columns=["facility_id", "component", "blood_group", "a", "b"])
S = S[S["a"] < S["b"]]
S["ai"] = S["a"].map(lambda x: didx.get(x, ND))
S["bi"] = S["b"].map(lambda x: didx.get(x, ND))
S = S[S["ai"] < ND]
key = S.groupby(["facility_id", "component", "blood_group"])
snaps = []
for (fid, comp, g), grp in key:
    delta = np.zeros(ND + 1, dtype=int)
    np.add.at(delta, grp["ai"].values, 1)
    np.add.at(delta, np.minimum(grp["bi"].values, ND), -1)
    lvl = np.cumsum(delta)[:ND]
    for k in range(ND):
        snaps.append((DAYS[k], fid, comp, g, int(lvl[k])))
SNAP = pd.DataFrame(snaps, columns=["date", "facility_id", "component", "blood_group", "units_in_stock_end_of_day"])

# ---------------------------------------------------------------- data quality issues (deliberate, documented)
D = pd.DataFrame(donors).drop(columns=["loyal"])
# 1) duplicate donor registrations (same person, new ID)
dup = D.sample(frac=0.018, random_state=SEED).copy()
dup["donor_id"] = [f"DNR-{len(D)+k+1:06d}" for k in range(len(dup))]
dup["registration_date"] = dup["registration_date"].map(lambda x: x + timedelta(days=int(rng.integers(30, 300))))
dup = dup[dup["registration_date"] <= END]
D = pd.concat([D, dup], ignore_index=True)
# 2) blood group missing for some walk-in records
D.loc[D.sample(frac=0.012, random_state=1).index, "blood_group"] = None
DON = pd.DataFrame(donations)
R = pd.DataFrame(requests)
# 3) inconsistent free-text facility names on requests
variants = {}
for hid in HOSP:
    n = FD[hid]["name"]
    variants[hid] = [n, n.upper(), n.replace("County Referral Hospital", "CRH").replace("Hospital", "Hosp."), n.split(" (")[0] + " "]
idx = R.sample(frac=0.14, random_state=2).index
R.loc[idx, "facility_name_raw"] = [random.choice(variants[f]) for f in R.loc[idx, "facility_id"]]
# 4) patient group recorded as unknown in some emergencies
idx = R[(R.urgency == "emergency")].sample(frac=0.05, random_state=3).index
R.loc[idx, "patient_blood_group"] = "unknown"
# 5) temperature logger readings: occasional sensor glitch values
TL = pd.DataFrame(temps, columns=["facility_id", "recorded_at", "temp_c"])
gi = TL.sample(n=60, random_state=4).index
TL.loc[gi, "temp_c"] = rng.choice([-99.0, 99.9, 0.0], size=len(gi))

FAC = pd.DataFrame(F)
DRV = pd.DataFrame(drives)
DRV["donations_collected"] = DRV["drive_id"].map(DON[DON.outcome == "collected"].groupby("drive_id").size()).fillna(0).astype(int)
DRV["donors_deferred"] = DRV["drive_id"].map(DON[DON.outcome == "deferred"].groupby("drive_id").size()).fillna(0).astype(int)
RT_DF = pd.DataFrame(routes)
OUTG = pd.DataFrame(outages)
U = U.drop(columns=["release_date"])
U["status_date"] = U["status_date"].where(U["status"] != "in_stock", None)

OS = OUT_START
OSDT = datetime.combine(OS, datetime.min.time())
U = U[U["status_date"].map(lambda v: v is None or (isinstance(v, float)) or v >= OS)].copy()
U["opening_stock"] = U["collection_date"] < OS
keep_don = set(U["donation_id"])
DON = DON[(DON["collection_date"] >= OS) | DON["donation_id"].isin(keep_don)].copy()
DRV = DRV[(DRV["date"] >= OS) | DRV["drive_id"].isin(set(DON["drive_id"]))].copy()
D = D[(D["registration_date"] >= OS) | D["donor_id"].isin(set(DON["donor_id"]))].copy()
T = T[(T["dispatched_at"] >= OSDT) & T["unit_id"].isin(set(U["unit_id"]))].copy()
R = R[(R["requested_at"] >= OSDT) | R["request_id"].isin(set(T["request_id"].dropna()) | set(U["issued_request_id"].dropna()))].copy()
OUTG = OUTG[OUTG["start_time"] >= OSDT].copy()
TL = TL[TL["recorded_at"] >= OSDT].copy()
SNAP = SNAP[SNAP["date"] >= OS].copy()
SNAP = SNAP[~((SNAP.groupby(["facility_id","component","blood_group"])["units_in_stock_end_of_day"].transform("max")) == 0)]
tables = {
    "facilities": FAC, "routes": RT_DF, "donors": D, "drives": DRV, "donations": DON, "units": U,
    "transfers": T, "requests": R, "power_outages": OUTG, "temperature_logs": TL, "daily_stock": SNAP,
}
for name, df in tables.items():
    for c in df.columns:
        if str(df[c].dtype).startswith("datetime"):
            df[c] = df[c].dt.floor("s")
        elif df[c].dtype == object and len(df) and isinstance(df[c].dropna().iloc[0] if df[c].notna().any() else None, datetime):
            df[c] = pd.to_datetime(df[c]).dt.floor("s")
for name, df in tables.items():
    df.to_csv(os.path.join(OUT, f"{name}.csv"), index=False)
    print(name, len(df))
db = os.path.join(OUT, "blood_system.sqlite")
if os.path.exists(db): os.remove(db)
con = sqlite3.connect(db)
for name, df in tables.items():
    df2 = df.copy()
    for c in df2.columns:
        if df2[c].dtype == object:
            df2[c] = df2[c].map(lambda v: v.isoformat() if hasattr(v, "isoformat") else v)
    df2.to_sql(name, con, index=False)
con.close()
