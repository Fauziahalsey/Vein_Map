import sqlite3
import pandas as pd
import folium
import streamlit as st
from streamlit_folium import st_folium
import coldchain, auth, model
import donor_msgs


st.set_page_config(page_title="Cold Chain", layout="wide")

# ---------- login (manager only) ----------
auth.init_users()
if "mgr" not in st.session_state:
    st.session_state.mgr = None

if not st.session_state.mgr:
    st.title("Manager dashboard")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Log in"):
        res = auth.login(u.strip(), p)
        if res and res[1] == "manager":
            st.session_state.mgr = u.strip()
            st.rerun()
        else:
            st.error("Managers only. Check username and password.")
    st.stop()

st.sidebar.write(f"Signed in: **{st.session_state.mgr}** (manager)")
if st.sidebar.button("Log out"):
    st.session_state.mgr = None
    st.rerun()


def q(sql, params=()):
    conn = sqlite3.connect("scans.db")
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


def log_decision(alert_key, decision, note):
    conn = sqlite3.connect("scans.db")
    conn.execute("""CREATE TABLE IF NOT EXISTS alert_decisions(
        id INTEGER PRIMARY KEY, alert_key TEXT, decision TEXT, note TEXT, user TEXT, decided_at TEXT)""")
    conn.execute("INSERT INTO alert_decisions(alert_key,decision,note,user,decided_at) VALUES (?,?,?,?,datetime('now','localtime'))",
                 (alert_key, decision, note, st.session_state.mgr))
    conn.commit(); conn.close()


@st.cache_data
def load_facilities():
    fac = pd.read_csv("data/facilities.csv")
    summ = coldchain.facility_summary(coldchain.load_temps())
    return fac.merge(summ, on="facility_id", how="left")


def rate_color(r):
    if pd.isna(r): return "#888888"
    if r < 0.01: return "#2e7d32"
    if r < 0.025: return "#f9a825"
    return "#c62828"


fac = load_facilities()
# tab_map, tab_alerts, tab_audit = st.tabs(["Map", "Fridge alerts", "Audit log"])
tab_map, tab_alerts, tab_donors, tab_audit = st.tabs(["Map", "Fridge alerts", "Donor thank-yous", "Audit log"])


# ---------- MAP ----------
with tab_map:
    st.caption("Fill = share of valid hourly readings outside 2-6 °C (green <1%, amber 1-2.5%, red ≥2.5%, grey = no data). "
               "Black outline = no backup power on the blood fridge. Popups show units currently held, from scans.")
    # latest status per unit -> units currently at each facility
    latest = q("""SELECT unit_id, event_type, facility_id FROM scan_events
                  WHERE rowid IN (SELECT MAX(rowid) FROM scan_events GROUP BY unit_id)""")
    held = latest.groupby(["facility_id", "event_type"]).size().unstack(fill_value=0) if len(latest) else pd.DataFrame()

    m = folium.Map(location=[-0.5, 37.0], zoom_start=6, tiles="OpenStreetMap")
    for _, r in fac.iterrows():
        has_backup = bool(r["has_blood_fridge_backup_power"])
        rate = r["excursion_rate"]
        units_html = ""
        if r["facility_id"] in held.index:
            row = held.loc[r["facility_id"]]
            units_html = "<br><b>Units (latest scan):</b><br>" + "<br>".join(
                f"{k}: {int(v)}" for k, v in row.items() if v > 0)
        popup = (f"<b>{r['name']}</b><br>{r['facility_type']} · {r['county']}<br>"
                 f"Excursion rate: {'no data' if pd.isna(rate) else f'{rate:.1%}'}<br>"
                 f"Logger offline hours: {r['offline_hours']:.0f}<br>"
                 f"Backup power: {'Yes' if has_backup else 'No'}{units_html}")
        folium.CircleMarker([r["lat"], r["lon"]], radius=9,
            color="#000000" if not has_backup else rate_color(rate),
            weight=4 if not has_backup else 2, fill=True, fill_color=rate_color(rate),
            fill_opacity=0.8, popup=folium.Popup(popup, max_width=300), tooltip=r["name"]).add_to(m)
    st_folium(m, height=550, use_container_width=True, returned_objects=[])

    st.subheader("Unit trail")
    uid = st.text_input("Unit ID")
    if uid:
        trail = q("SELECT scanned_at, event_type, facility_id, user, flagged FROM scan_events WHERE unit_id=? ORDER BY scanned_at, rowid", (uid.strip(),))
        st.dataframe(trail, use_container_width=True) if len(trail) else st.info("No scans for this unit yet.")

# ---------- ALERTS ----------
with tab_alerts:
    st.caption("The model only suggests. Every alert needs a person's decision. "
               "If the model is switched off, the outage + no-backup rule takes over.")
    use_model = st.toggle("Use AI model (off = rule fallback)", value=True)
    th = st.slider("Alert threshold (higher = fewer, more certain alerts)", 0.05, 0.5, 0.2, 0.05)
    @st.cache_resource
    def get_eval():
        return model.evaluate(threshold=0.2)   # p doesn't depend on the threshold

    try:
        _, test = get_eval()
    except Exception as e:
        st.error(f"Model unavailable ({e}). Rule fallback in use.")
        use_model, test = False, None


    if test is not None:
        test = test.copy()
        test["flag"] = (test["p"] >= th) if use_model else ((test["in_outage"] == 1) & (test["backup"] == 0))
        last = test["recorded_at"].max()
        recent = test[test["recorded_at"] >= last - pd.Timedelta(hours=24)]
        al = recent[recent["flag"]].sort_values("p", ascending=False).drop_duplicates("facility_id").head(10)
        st.write(f"Alerts in the last 24 h of the dataset ({last:%d %b %Y}): **{len(al)}**")
        for _, a in al.iterrows():
            key = f"{a['facility_id']}|{a['recorded_at']}"
            why = []
            if a["in_outage"] == 1: why.append("a power outage is in progress or just ended")
            if a["backup"] == 0: why.append("no backup power on the blood fridge")
            if a["d3"] > 0.3: why.append(f"temperature rose {a['d3']:.1f} °C in 3 h")
            conf = f"{a['p']:.0%}" if use_model else "n/a (rule-based)"
            with st.container(border=True):
                st.markdown(f"**{a['facility_id']}** · {a['recorded_at']:%d %b %H:%M} · now {a['temp']:.1f} °C")
                st.write("Why: " + ("; ".join(why) if why else "pattern in recent readings"))
                st.write(f"Chance of leaving 2-6 °C within 3 h: **{conf}** (an estimate, not a fact).")
                c1, c2, c3 = st.columns(3)
                note = st.text_input("Note (required for Change)", key=f"n{key}")
                if c1.button("Accept", key=f"a{key}"):
                    log_decision(key, "accepted", note); st.success("Logged: accepted")
                if c2.button("Change", key=f"c{key}"):
                    if note: log_decision(key, "changed", note); st.success("Logged: changed")
                    else: st.warning("Add a note describing the change.")
                if c3.button("Reject", key=f"r{key}"):
                    log_decision(key, "rejected", note); st.success("Logged: rejected")

# ---------- AUDIT ----------
with tab_audit:
    st.subheader("Custody scans")
    st.dataframe(q("SELECT scanned_at, unit_id, event_type, facility_id, user, role, flagged FROM scan_events ORDER BY scanned_at DESC, rowid DESC LIMIT 200"), use_container_width=True)
    st.subheader("Alert decisions")
    try:
        st.dataframe(q("SELECT decided_at, alert_key, decision, note, user FROM alert_decisions ORDER BY id DESC LIMIT 200"), use_container_width=True)
    except Exception:
        st.info("No alert decisions yet.")