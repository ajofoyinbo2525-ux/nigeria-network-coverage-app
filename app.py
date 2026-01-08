import os
import json
import pandas as pd
import numpy as np
import streamlit as st
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
from geopy.distance import geodesic

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Nigeria Network Coverage & Planning",
    layout="wide"
)

st.title("📡 Nigeria Mobile Network Coverage & Planning System")

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------
if "run" not in st.session_state:
    st.session_state.run = False
if "lat" not in st.session_state:
    st.session_state.lat = None
if "lon" not in st.session_state:
    st.session_state.lon = None
if "results" not in st.session_state:
    st.session_state.results = pd.DataFrame()

# --------------------------------------------------
# FILE FINDER
# --------------------------------------------------
def find_file(name):
    for root, _, files in os.walk("."):
        if name in files:
            return os.path.join(root, name)
    return None

# --------------------------------------------------
# LOAD GEOJSON
# --------------------------------------------------
nga0 = find_file("gadm41_NGA_0.geojson")
nga1 = find_file("gadm41_NGA_1.geojson")

if not nga0 or not nga1:
    st.error("❌ Nigeria GeoJSON files not found")
    st.stop()

with open(nga0, "r", encoding="utf-8") as f:
    nigeria_geo = json.load(f)

with open(nga1, "r", encoding="utf-8") as f:
    states_geo = json.load(f)

st.success("✅ Nigeria boundary & states loaded successfully")

# --------------------------------------------------
# LOAD NETWORK CSV (CORRECT NAME)
# --------------------------------------------------
csv_path = find_file("Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv")

if not csv_path:
    st.error("❌ Network CSV not found")
    st.stop()

df = pd.read_csv(csv_path)

st.success("✅ Network dataset loaded successfully")

# --------------------------------------------------
# SIDEBAR INPUT
# --------------------------------------------------
st.sidebar.header("📍 Input Location")

lat = st.sidebar.number_input("Latitude", value=9.0820, format="%.6f")
lon = st.sidebar.number_input("Longitude", value=8.6753, format="%.6f")

radius = st.sidebar.slider("Coverage Buffer Radius (km)", 5, 100, 30)

distance_mode = st.sidebar.radio(
    "Distance Mode",
    ["Close Proximity", "Unlimited Distance"]
)

if st.sidebar.button("▶ Run Network Analysis"):
    st.session_state.run = True
    st.session_state.lat = lat
    st.session_state.lon = lon

# --------------------------------------------------
# ANALYSIS
# --------------------------------------------------
if st.session_state.run:

    lat0 = st.session_state.lat
    lon0 = st.session_state.lon

    df["distance_km"] = df.apply(
        lambda r: geodesic(
            (lat0, lon0),
            (r["Latitude"], r["Longitude"])
        ).km,
        axis=1
    )

    if distance_mode == "Close Proximity":
        res = df[df["distance_km"] <= radius].copy()
    else:
        res = df.copy()

    res["confidence_level"] = np.where(
        res["distance_km"] <= radius / 2, "High",
        np.where(res["distance_km"] <= radius, "Medium", "Low")
    )

    st.session_state.results = res

# --------------------------------------------------
# TABS (CORRECT STRUCTURE)
# --------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "Coverage Map",
    "Coverage Buffers",
    "No Coverage / Gaps",
    "Network Prediction",
    "New Tower Recommendation",
    "Coverage Density",
    "Results & Export",
    "User Guide"
])

# --------------------------------------------------
# TAB 1 – COVERAGE MAP
# --------------------------------------------------
with tab1:
    if st.session_state.run:
        m = folium.Map(location=[lat0, lon0], zoom_start=7)
        folium.GeoJson(nigeria_geo).add_to(m)

        folium.Marker(
            [lat0, lon0],
            tooltip="Input Location",
            icon=folium.Icon(color="red")
        ).add_to(m)

        for _, r in st.session_state.results.iterrows():
            folium.CircleMarker(
                [r["Latitude"], r["Longitude"]],
                radius=4,
                tooltip=f"{r['Network_Operator']} | {r['Network_Generation']}",
                fill=True
            ).add_to(m)

        st_folium(m, height=550)

# --------------------------------------------------
# TAB 2 – COVERAGE BUFFERS
# --------------------------------------------------
with tab2:
    if st.session_state.run:
        m = folium.Map(location=[lat0, lon0], zoom_start=7)

        folium.Circle(
            [lat0, lon0],
            radius=radius * 1000,
            color="blue",
            fill=True,
            fill_opacity=0.2,
            tooltip=f"{radius} km buffer"
        ).add_to(m)

        st_folium(m, height=550)

# --------------------------------------------------
# TAB 3 – NO COVERAGE / GAPS
# --------------------------------------------------
with tab3:
    st.info("📍 Areas outside the buffer represent potential no-network coverage zones.")

# --------------------------------------------------
# TAB 4 – NETWORK PREDICTION
# --------------------------------------------------
with tab4:
    if st.session_state.run:
        st.dataframe(
            st.session_state.results[
                ["Network_Operator", "Network_Generation",
                 "Radio_Technology", "distance_km", "confidence_level"]
            ].sort_values("distance_km")
        )

# --------------------------------------------------
# TAB 5 – NEW TOWER RECOMMENDATION
# --------------------------------------------------
with tab5:
    if st.session_state.run:
        rec_lat = lat0 + 0.05
        rec_lon = lon0 + 0.05

        st.success("📡 Recommended New Tower Location")
        st.write(f"Latitude: {rec_lat}")
        st.write(f"Longitude: {rec_lon}")

        m = folium.Map(location=[rec_lat, rec_lon], zoom_start=8)
        folium.Marker([rec_lat, rec_lon], icon=folium.Icon(color="green")).add_to(m)
        st_folium(m, height=400)

# --------------------------------------------------
# TAB 6 – COVERAGE DENSITY
# --------------------------------------------------
with tab6:
    heat_data = df[["Latitude", "Longitude"]].dropna().values.tolist()
    m = folium.Map(location=[9, 8], zoom_start=6)
    HeatMap(heat_data, radius=8).add_to(m)
    st_folium(m, height=550)

# --------------------------------------------------
# TAB 7 – EXPORT
# --------------------------------------------------
with tab7:
    if st.session_state.run:
        st.download_button(
            "⬇ Export Results CSV",
            st.session_state.results.to_csv(index=False),
            "network_analysis_results.csv",
            "text/csv"
        )

# --------------------------------------------------
# TAB 8 – USER GUIDE
# --------------------------------------------------
with tab8:
    st.markdown("""
    ### 📘 How to Use This App
    1. Enter latitude & longitude
    2. Select buffer distance
    3. Click *Run Network Analysis*
    4. All tabs update automatically
    5. Export results anytime
    """)
