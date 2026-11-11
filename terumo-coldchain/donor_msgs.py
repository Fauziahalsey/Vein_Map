from dotenv import load_dotenv
load_dotenv()
import os, sqlite3
from datetime import datetime
from functools import lru_cache
import pandas as pd

DB = "scans.db"

def _norm(p):
    s = str(p).strip().replace(" ", "").replace("-", "")
    if s.startswith("+"):
        return s
    if s.startswith("254"):
        return "+" + s
    if s.startswith("0"):
        return "+254" + s[1:]
    return s


def _demo_phones():
    out = {}
    path = os.environ.get("DEMO_PHONES_FILE", "data/demo_phones.csv")
    if os.path.exists(path):
        df = pd.read_csv(path, dtype=str).dropna(subset=["phone"])
        for _, r in df.iterrows():
            out[r["donor_id"].strip()] = _norm(r["phone"])
    for pair in os.environ.get("DEMO_PHONES", "").split(","):   # optional extra override
        if ":" in pair:
            k, v = pair.split(":", 1)
            out[k.strip()] = _norm(v)
    return out

def _conn():
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS donor_messages(
        id INTEGER PRIMARY KEY, unit_id TEXT UNIQUE, donor_id TEXT, body TEXT,
        status TEXT, created_at TEXT, decided_by TEXT, decided_at TEXT, result TEXT)""")
    c.execute("CREATE TABLE IF NOT EXISTS sms_optout(donor_id TEXT PRIMARY KEY, at TEXT)")
    return c


@lru_cache(maxsize=1)
def _tables():
    u = pd.read_csv("data/units.csv", usecols=["unit_id", "donation_id"])
    d = pd.read_csv("data/donations.csv", usecols=["donation_id", "donor_id", "collection_date"])
    o = pd.read_csv("data/donors.csv", usecols=["donor_id", "consent_to_contact", "preferred_channel"])
    return u, d, o


def _lookup(unit_id):
    u, d, o = _tables()
    a = u[u.unit_id == unit_id]
    if a.empty:
        return None
    b = d[d.donation_id == a.iloc[0].donation_id]
    if b.empty:
        return None
    b = b.iloc[0]
    c = o[o.donor_id == b.donor_id]
    if c.empty:
        return None
    c = c.iloc[0]
    consent = str(c.consent_to_contact).strip().upper() == "TRUE"
    return b.donor_id, b.collection_date, consent, c.preferred_channel


def queue_thank_you(unit_id):
    """Draft only. Nothing is sent until a manager approves."""
    info = _lookup(unit_id)
    if not info:
        return "unknown unit"
    donor_id, date, consent, channel = info
    conn = _conn()
    opted_out = conn.execute("SELECT 1 FROM sms_optout WHERE donor_id=?", (donor_id,)).fetchone()
    if donor_id in _demo_phones():      # test donors who agreed to receive texts
        consent, channel = True, "SMS"
    if not consent or channel != "SMS" or opted_out:
        return "skipped"
    when = pd.to_datetime(date).strftime("%d %b %Y")
    body = (f"Thank you. Your blood donation of {when} has been used to help a patient. "
            "Reply STOP to opt out.")
    conn.execute(
        "INSERT OR IGNORE INTO donor_messages(unit_id,donor_id,body,status,created_at) VALUES (?,?,?,?,?)",
        (unit_id, donor_id, body, "pending", datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    return "queued"


def send_sms(body, to):
    sid, tok, frm = (os.environ.get(k) for k in ("TWILIO_SID", "TWILIO_TOKEN", "TWILIO_FROM"))
    if not to:
        return "dry_run", "no phone number on file, nothing sent"
    if not (sid and tok and frm):
        return "dry_run", "Twilio keys not set, nothing sent"
    try:
        from twilio.rest import Client
        m = Client(sid, tok).messages.create(body=body, from_=frm, to=to)
        return "sent", f"twilio {m.sid}"
    except Exception as e:
        return "failed", str(e)[:200]


def pending():
    return pd.read_sql_query("SELECT id, unit_id, body FROM donor_messages WHERE status='pending' ORDER BY id", _conn())


def approve(msg_id, user, body=None):
    conn = _conn()
    row = conn.execute("SELECT body, status, donor_id FROM donor_messages WHERE id=?", (msg_id,)).fetchone()
    if not row or row[1] != "pending":
        return "already handled"
    text = body or row[0]
    status, result = send_sms(text, _demo_phones().get(row[2]))
    conn.execute("UPDATE donor_messages SET body=?, status=?, decided_by=?, decided_at=?, result=? WHERE id=?",
                 (text, status, user, datetime.now().isoformat(timespec="seconds"), result, msg_id))
    conn.commit()
    return f"{status}: {result}"


def reject(msg_id, user):
    conn = _conn()
    conn.execute("UPDATE donor_messages SET status='rejected', decided_by=?, decided_at=? WHERE id=? AND status='pending'",
                 (user, datetime.now().isoformat(timespec="seconds"), msg_id))
    conn.commit()