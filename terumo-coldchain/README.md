# Project detail

## 1. Scope and design principles

- **Custody, not clinical judgement.** The QR/barcode records where a unit is and what stage it is at. It never says a unit is safe or what to do with it.
- **AI suggests, a person decides.** The only AI feature is the fridge early warning. Hard rules and people override it. Donor messages come from a fixed template and need approval.
- **Works on weak networks.** Scanning must work with no signal; the dashboard is for better-connected managers.
- **Append-only history.** Nothing in the scan log is edited or deleted, so it doubles as the audit trail.
- **Data minimisation.** Messages to donors carry no patient or hospital information.

## 2. Data preparation (`coldchain.py`)

- Source: `temperature_logs.csv` (hourly, one fridge per facility), `power_outages.csv`, `facilities.csv`.
- Sensor glitches `-99.0`, `99.9`, `0.0` are removed before any excursion is counted.
- An **excursion hour** is a valid reading outside 2-6 °C.
- **Logger-offline hours** = hours in the year with no reading. They are shown separately and are never treated as safe.
- Outage linking: a reading counts as outage-related if it falls inside an outage window plus a 3-hour lag, since a fridge warms after power drops.

## 3. Findings

| Finding | Value |
|---|---|
| Facilities / hourly readings | 47 / 399,280 |
| Facilities with no fridge backup | 14 (30%) |
| Excursion hours inside or within 3 h after an outage | 73% (3,375 of 4,607) |
| Of those, hours when backup did not engage | 3,341 (99%) |
| Outage-linked excursion hours at sites with no backup | 2,817 (83%) |
| Outage-linked excursion hours at sites with backup | 558 (17%) |
| Outages at backup sites where backup did not engage | 203 of 1,664 (12%) |
| Excursion hours with no outage link | 1,232 (27%) |

Two separate problems follow: **install backup** (largest) and **maintain backup** (about 1 in 8 fails).

## 4. Early-warning model (`model.py`)

- **Task:** for each facility-hour where the fridge is currently in range, predict an excursion in the next 1-3 hours.
- **Features:** current temperature, 1 h change, 3 h change, in-outage flag, hours since outage start, backup power flag, grid reliability.
- **Model:** HistGradientBoostingClassifier.
- **Split:** train before 1 Jul 2026, test from 1 Jul 2026 (time-based, no leakage).
- **Threshold sweep (precision / recall / alerts):**

| Cutoff | Precision | Recall | Alerts |
|---|---|---|---|
| 0.05 | 0.245 | 0.199 | 1,516 |
| 0.10 | 0.393 | 0.172 | 815 |
| 0.15 | 0.463 | 0.159 | 642 |
| **0.20** | **0.489** | **0.156** | **593** |
| 0.30 | 0.538 | 0.148 | 513 |
| Rule baseline | 0.153 | 0.075 | 916 |

- **Why 0.2:** below it, precision collapses for little recall; above it, recall is already poor. It is adjustable in the dashboard.
- **Limitations:** hourly data hides fast failures; evaluation is per hour, not per episode; no lead-time measure yet.

## 5. Custody log (`db.py`)

`scan_events(event_id, unit_id, event_type, facility_id, user, role, scanned_at, synced_at, flagged)`

Statuses and allowed next steps:

```
collected   -> at_centre
at_centre   -> in_transit | at_hospital | discarded
in_transit  -> at_hospital | at_centre
at_hospital -> in_transit | transfused | discarded
transfused, discarded -> (end)
```

An out-of-order scan is stored with `flagged = 1` for review. A unit's current status is its latest event.

- `event_id` is created on the device, so a retry after a dropped connection cannot create a duplicate.
- `scanned_at` is the device time, so an offline scan keeps its true time.

## 6. API and access (`api.py`, `auth.py`)

| Endpoint | Access |
|---|---|
| `POST /api/login` | anyone |
| `POST /api/scan` | any logged-in user |
| `GET /api/unit/{id}` | any logged-in user |
| `GET /api/audit` | manager only |

Passwords are salted and hashed (PBKDF2). Tokens are signed and expire after 7 days. User and role on every scan come from the token, not from what the phone sends.

## 7. Scan page (`static/`)

Single HTML file, no framework. Camera scanning uses the browser's BarcodeDetector, with a bundled ZXing fallback (works on iPhones). A handheld scanner types into the Unit ID field and Enter records the scan. A service worker caches the page for offline loading. A QR label encodes `https://<host>/?unit=<unit_id>` for the demo; a real label would hold the unit ID or ISBT 128 code only.

## 8. Dashboard (`app.py`)

- **Map:** fill colour = excursion rate (green under 1%, amber 1-2.5%, red 2.5% or more, grey = no data); black outline = no backup; popup shows units currently held per status.
- **Alerts:** last 24 hours of the dataset, with reason, probability, and Accept / Change / Reject. A toggle switches to the rule fallback.
- **Donor thank-yous:** pending drafts with edit, Accept and send, or Reject; history of sent and decided messages.
- **Audit:** custody scans and alert decisions.

## 9. Donor thank-you flow (`donor_msgs.py`)

1. A scan with event `transfused` (and not flagged as out of order) triggers `queue_thank_you(unit_id)`. A failure here never blocks the scan.
2. The unit is traced unit → donation → donor (`units.csv`, `donations.csv`, `donors.csv`).
3. A draft is created only if the donor consented to contact, prefers SMS, and has not opted out. One draft per unit.
4. The message comes from a fixed template with the collection date. It contains no patient, hospital, diagnosis or blood group.
5. A manager reviews the draft and chooses Accept (optionally after editing the text) or Reject.
6. On Accept, `send_sms()` sends through Africa's Talking and the status (`sent`, `failed` or `dry_run`) and provider result are stored.
7. With no keys or no number on file, the function runs in dry-run mode, so the workflow still works.

Tables: `donor_messages(id, unit_id, donor_id, body, status, created_at, decided_by, decided_at, result)` and `sms_optout(donor_id, at)`.

**Phone numbers:** the dataset holds only `phone_last4`. Test numbers come from a git-ignored `data/demo_phones.csv` (or the host's secret file) and are never stored in the database or the audit log.

## 10. Deployment

One Docker service: nginx in front of FastAPI (`/`) and Streamlit (`/dash/`), sharing one SQLite file. HTTPS comes from the host, which the phone camera requires. Secrets (`APP_SECRET`, `AT_USERNAME`, `AT_API_KEY`, the demo phone file) are set as environment variables or secret files on the host and are not in the repository.

## 11. Designed, not built

- ISBT 128 parsing to map bag barcodes to unit IDs.
- Label printing at the processing centre (writes the first `collected` event).
- SMS/USSD scanning for sites with no data connection.
- Reply-to-opt-out syncing into `sms_optout`, a 24-72 hour send delay, and suppression where a small facility could identify a patient.
- WhatsApp as a second donor channel (a second `send` function; templates must be pre-approved).
- FHIR (Specimen/BiologicallyDerivedProduct, Observation) and DHIS2 mapping.
- Live logger ingestion and per-episode lead-time evaluation.
- Per-country settings for statuses, thresholds, language and branding.
