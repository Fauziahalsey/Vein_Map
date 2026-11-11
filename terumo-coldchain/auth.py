import base64, hashlib, hmac, json, os, time
import db

SECRET = os.environ.get("APP_SECRET", "dev-secret-change-me").encode()
TTL = 7 * 24 * 3600
DEMO = [("tech1", "technician", "tech-demo-1"),
        ("tech2", "technician", "tech-demo-2"),
        ("manager1", "manager", "manager-demo-1")]


def _hash(pw, salt):
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 100_000).hex()


def init_users():
    conn = db.connect()
    conn.execute("CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, role TEXT, salt BLOB, pw_hash TEXT)")
    for u, r, p in DEMO:
        if not conn.execute("SELECT 1 FROM users WHERE username=?", (u,)).fetchone():
            salt = os.urandom(16)
            conn.execute("INSERT INTO users VALUES (?,?,?,?)", (u, r, salt, _hash(p, salt)))
    conn.commit()


def login(username, password):
    row = db.connect().execute(
        "SELECT role, salt, pw_hash FROM users WHERE username=?", (username,)).fetchone()
    if not row or not hmac.compare_digest(_hash(password, row[1]), row[2]):
        return None
    return make_token(username, row[0]), row[0]


def make_token(username, role):
    body = base64.urlsafe_b64encode(
        json.dumps({"u": username, "r": role, "exp": int(time.time()) + TTL}).encode()).decode()
    sig = hmac.new(SECRET, body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def verify(token):
    try:
        body, sig = token.rsplit(".", 1)
        good = hmac.new(SECRET, body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, good):
            return None
        d = json.loads(base64.urlsafe_b64decode(body))
        return d if d["exp"] > time.time() else None
    except Exception:
        return None