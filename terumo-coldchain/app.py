import pandas as pd
import folium
import streamlit as st
from streamlit_folium import st_folium

st.set_page_config(page_title="Cold Chain Map", layout="wide")


@st.cache_data
def load_facilities():
    return pd.read_csv("data/facilities.csv")


def fmt(v):
    return "n/a" if pd.isna(v) else v


df = load_facilities()

st.title("Cold chain risk: facility map")
st.caption("Red = no backup power for the blood fridge. Bigger circle = less reliable grid.")

# m = folium.Map(location=[-0.5, 37.0], zoom_start=6, tiles="CartoDB positron")
m = folium.Map(location=[-0.5, 37.0], zoom_start=6, tiles="OpenStreetMap")

for _, r in df.iterrows():
    has_backup = bool(r["has_blood_fridge_backup_power"])
    color = "green" if has_backup else "red"
    radius = 6 + (1 - r["grid_reliability"]) * 20  # assumes grid_reliability is 0-1

    popup_html = (
        f"<b>{r['name']}</b><br>"
        f"{r['facility_type']} · {r['county']}<br>"
        f"KEPH level: {fmt(r['keph_level'])}<br>"
        f"Grid reliability: {r['grid_reliability']}<br>"
        f"Backup power: {'Yes' if has_backup else 'No'}<br>"
        f"Connectivity: {r['connectivity']}"
    )

    folium.CircleMarker(
        location=[r["lat"], r["lon"]],
        radius=radius,
        color=color,
        fill=True,
        fill_opacity=0.6,
        popup=folium.Popup(popup_html, max_width=280),
        tooltip=r["name"],
    ).add_to(m)

st_folium(m, height=600, use_container_width=True, returned_objects=[])