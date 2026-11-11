import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import precision_score, recall_score
import coldchain as c

FEATS = ["temp", "d1", "d3", "in_outage", "hrs_since_outage_start", "backup", "grid"]


def build():
    t = c.load_temps()
    t.loc[t.is_glitch, "temp_c"] = np.nan
    idx = pd.date_range(t.recorded_at.min(), t.recorded_at.max(), freq="h")
    parts = []
    for fid, g in t.groupby("facility_id"):
        s = g.set_index("recorded_at")["temp_c"].reindex(idx)
        exc = ((s < 2) | (s > 6)).astype(float).where(s.notna())
        fut = pd.concat([exc.shift(-k) for k in (1, 2, 3)], axis=1)
        d = pd.DataFrame({
            "facility_id": fid, "temp": s,
            "d1": s.diff(1), "d3": s.diff(3),
            "now_exc": exc, "target": fut.max(axis=1),
        })
        parts.append(d.rename_axis("recorded_at").reset_index())
    d = pd.concat(parts).sort_values("recorded_at")

    o = c.load_outages().sort_values("start_time")
    o["window_end"] = o["end_time"] + pd.Timedelta(hours=3)
    d = pd.merge_asof(
        d, o[["facility_id", "start_time", "window_end"]],
        left_on="recorded_at", right_on="start_time", by="facility_id",
    )
    d["in_outage"] = (d["recorded_at"] <= d["window_end"]).astype(int)
    d["hrs_since_outage_start"] = (
        (d["recorded_at"] - d["start_time"]).dt.total_seconds() / 3600
    ).where(d["in_outage"] == 1, -1)

    f = pd.read_csv("data/facilities.csv")[
        ["facility_id", "has_blood_fridge_backup_power", "grid_reliability"]
    ]
    d = d.merge(f, on="facility_id")
    d["backup"] = d["has_blood_fridge_backup_power"].astype(int)
    d["grid"] = d["grid_reliability"]

    # only moments where the fridge is currently in range and the future is known
    return d[(d["now_exc"] == 0) & d["temp"].notna() & d["target"].notna()].copy()


def evaluate(threshold=0.3):
    d = build()
    train = d[d["recorded_at"] < "2026-07-01"]
    test = d[d["recorded_at"] >= "2026-07-01"].copy()

    model = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.1, random_state=0)
    model.fit(train[FEATS], train["target"])
    test["p"] = model.predict_proba(test[FEATS])[:, 1]

    y = test["target"]
    rule = ((test["in_outage"] == 1) & (test["backup"] == 0)).astype(int)
    ai = (test["p"] >= threshold).astype(int)

    print(f"test rows: {len(test)}, excursions starting within 3h: {int(y.sum())}")
    print("reactive threshold: recall 0.00, lead time 0 h (it only fires after the excursion)")
    for name, pred in [("rule (outage + no backup)", rule), (f"model (p>={threshold})", ai)]:
        print(f"{name}: precision {precision_score(y, pred):.3f}, "
              f"recall {recall_score(y, pred):.3f}, alerts {int(pred.sum())}")
    return model, test


if __name__ == "__main__":
    evaluate()