import sys, os
import pandas as pd
import qrcode

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
u = pd.read_csv("data/units.csv")
demo = u[u["status"] == "in_stock"].sample(5, random_state=1)["unit_id"]

os.makedirs("demo_qr", exist_ok=True)
for uid in demo:
    qrcode.make(f"{BASE}/?unit={uid}").save(f"demo_qr/{uid}.png")
    print(uid)