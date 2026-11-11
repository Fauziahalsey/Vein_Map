import pandas as pd

GLITCHES = {-99.0, 99.9, 0.0}
SAFE_MIN, SAFE_MAX = 2.0, 6.0


def load_temps():
    t = pd.read_csv("data/temperature_logs.csv", parse_dates=["recorded_at"])
    t["is_glitch"] = t["temp_c"].isin(GLITCHES)
    t["is_excursion"] = (~t["is_glitch"]) & (
        (t["temp_c"] < SAFE_MIN) | (t["temp_c"] > SAFE_MAX)
    )
    return t


def facility_summary(t):
    span = int((t["recorded_at"].max() - t["recorded_at"].min()).total_seconds() // 3600) + 1
    s = t.groupby("facility_id").agg(
        readings=("temp_c", "size"),
        glitches=("is_glitch", "sum"),
        excursion_hours=("is_excursion", "sum"),
    )
    s["offline_hours"] = span - s["readings"]
    s["valid_readings"] = s["readings"] - s["glitches"]
    s["excursion_rate"] = s["excursion_hours"] / s["valid_readings"]
    return s.reset_index()

def load_outages():
    return pd.read_csv("data/power_outages.csv", parse_dates=["start_time", "end_time"])


def tag_outages(t, o, lag_hours=3):
    """Mark each reading as inside an outage window (plus lag, since a fridge warms after power drops)."""
    o = o.sort_values("start_time").copy()
    o["window_end"] = o["end_time"] + pd.Timedelta(hours=lag_hours)
    t = t.sort_values("recorded_at")
    m = pd.merge_asof(
        t,
        o[["facility_id", "start_time", "window_end", "backup_power_engaged"]],
        left_on="recorded_at",
        right_on="start_time",
        by="facility_id",
        direction="backward",
    )
    m["in_outage"] = m["recorded_at"] <= m["window_end"]
    m["backup_engaged"] = m["backup_power_engaged"].where(m["in_outage"])
    return m.drop(columns=["start_time", "window_end", "backup_power_engaged"])