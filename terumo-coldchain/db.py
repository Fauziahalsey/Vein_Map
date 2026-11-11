import sqlite3, uuid
from datetime import datetime

DB = "scans.db"
STATUSES = ["collected", "at_centre", "in_transit", "at_hospital", "transfused", "discarded"]
ALLOWED_NEXT = {
    "collected": {"at_centre"},
    "at_centre": {"in_transit", "at_hospital", "discarded"},
    "in_transit": {"at_hospital", "at_centre"},
    "at_hospital": {"in_transit", "transfused", "discarded"},
    "transfused": set(),
    "discarded": set(),
}


def connect():
    conn = sqlite3.connect(DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS scan_events(
        event_id TEXT PRIMARY KEY, unit_id TEXT, event_type TEXT, facility_id TEXT,
        user TEXT, role TEXT, scanned_at TEXT, synced_at TEXT, flagged INTEGER)""")
    return conn


def current_status(conn, unit_id):
    r = conn.execute(
        "SELECT event_type FROM scan_events WHERE unit_id=? ORDER BY scanned_at DESC, rowid DESC LIMIT 1",
        (unit_id,),
    ).fetchone()
    return r[0] if r else None


def add_event(unit_id, event_type, facility_id, user, role, scanned_at=None, event_id=None):
    """Append only. Flags out-of-order scans but never blocks them."""
    conn = connect()
    prev = current_status(conn, unit_id)
    flagged = int(prev is not None and event_type not in ALLOWED_NEXT.get(prev, set()))
    conn.execute(
        "INSERT OR IGNORE INTO scan_events VALUES (?,?,?,?,?,?,?,?,?)",
        (event_id or str(uuid.uuid4()), unit_id, event_type, facility_id, user, role,
         scanned_at or datetime.now().isoformat(timespec="seconds"),
         datetime.now().isoformat(timespec="seconds"), flagged),
    )
    conn.commit()
    return flagged