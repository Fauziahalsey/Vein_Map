from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import db, auth

auth.init_users()
app = FastAPI()


def current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "login required")
    u = auth.verify(authorization[7:])
    if not u:
        raise HTTPException(401, "invalid or expired token")
    return u


def manager_only(u=Depends(current_user)):
    if u["r"] != "manager":
        raise HTTPException(403, "managers only")
    return u


class Login(BaseModel):
    username: str
    password: str


class Scan(BaseModel):
    event_id: str
    unit_id: str
    event_type: str
    facility_id: str
    scanned_at: str


@app.post("/api/login")
def login(b: Login):
    res = auth.login(b.username, b.password)
    if not res:
        raise HTTPException(401, "wrong username or password")
    return {"token": res[0], "role": res[1], "username": b.username}


@app.post("/api/scan")
def scan(s: Scan, u=Depends(current_user)):
    if s.event_type not in db.STATUSES:
        raise HTTPException(400, "unknown event type")
    flagged = db.add_event(s.unit_id, s.event_type, s.facility_id,
                           user=u["u"], role=u["r"],
                           scanned_at=s.scanned_at, event_id=s.event_id)
    return {"ok": True, "flagged": flagged}


@app.get("/api/unit/{unit_id}")
def unit(unit_id: str, u=Depends(current_user)):
    rows = db.connect().execute(
        "SELECT event_type, facility_id, user, scanned_at, flagged FROM scan_events "
        "WHERE unit_id=? ORDER BY scanned_at, rowid", (unit_id,)).fetchall()
    return {"unit_id": unit_id, "trail": rows}


@app.get("/api/audit")
def audit(u=Depends(manager_only)):
    rows = db.connect().execute(
        "SELECT scanned_at, unit_id, event_type, facility_id, user, role, flagged "
        "FROM scan_events ORDER BY scanned_at DESC, rowid DESC LIMIT 200").fetchall()
    return {"events": rows}


app.mount("/", StaticFiles(directory="static", html=True), name="static")