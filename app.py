import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import math
import json

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Nigeria Network Coverage & Planning",
    layout="wide"
)
st.title("📡 Nigeria Network Coverage & Planning Dashboard")

# ---------------- DISTANCE FUNCTION ----------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)*2 + math.cos(phi1)*math.cos(phi2)*math.sin(dl/2)*2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# ---------------- COLOR FUNCTIONS ----------------
def get_operator_color(op):
    if not isinstance(op, str):
        return "blue"
    op = op.lower()
    if "mtn" in op:
        return "orange"
    if "airtel" in op:
        return "red"
    if "glo" in op:
        return "green"
    if "9" in op:
        return "black"
    return "blue"

def get_technology_color(tech):
    if not isinstance(tech, str):
        return "purple"
    tech = tech.lower()
    if "2g" in tech:
        return "gray"
    if "3g" in tech:
        return "blue"
    if "4g" in tech:
        return "green"
    return "purple"

# ---------------- LOAD DATA ----------------
@st.cache_data
def load_network_data():
    df = pd.read_csv("Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv")
    df.columns = df.columns.str.lower()
    return df

@st.cache_data
def load_geojson(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

df = load_network_data()
nga_boundary = load_geojson("gadm41_NGA_0.geojson")
nga_states = load_geojson("gadm41_NGA_1.geojson")

# Column mapping (SAFE)
LAT = "latitude"
LON = "longitude"
OP = "network_operator"
TECH = "network_generation"
STATE = "state" if "state" in df.columns else None

# ---------------- SIDEBAR ----------------
st.sidebar.header("📍 Location Input")

lat0 = st.sidebar.number_input("Latitude", value=6.5244, format="%.6f")
lon0 = st.sidebar.number_input("Longitude", value=3.3792, format="%.6f")

no_limit = st.sidebar.checkbox("🚀 No Distance Limit", value=True)
radius_km = None
if not no_limit:
    radius_km = st.sidebar.slider("Radius (km)", 5, 200, 50)

run = st.sidebar.button("▶ Run Analysis")

# ---------------- SESSION STATE ----------------
if "results" not in st.session_state:
    st.session_state.results = None

# ---------------- ANALYSIS ----------------
if run:
    df["distance_km"] = df.apply(
        lambda r: haversine(lat0, lon0, r[LAT], r[LON]), axis=1
    )

    if no_limit:
        st.session_state.results = df.copy()
    else:
        st.session_state.results = df[df["distance_km"] <= radius_km].copy()

# ---------------- TABS ----------------
tabs = st.tabs([
    "🗺 Coverage Map",
    "🚫 No Coverage Map",
    "📊 Network Results",
    "📡 Network Predictor",
    "⚠ Coverage Gaps",
    "🏗 New Tower Recommendation",
    "📤 Export Results",
    "🏢 Operator Summary",
    "📶 Technology Summary",
    "⭕ Buffer View",
    "📊 Coverage Density (State)",
    "📘 User Guide"
])

if st.session_state.results is not None:
    res = st.session_state.results

    # ---------------- TAB 1 ----------------
    with tabs[0]:
        m = folium.Map([lat0, lon0], zoom_start=7, tiles="cartodbpositron")
        folium.GeoJson(nga_boundary).add_to(m)
        folium.GeoJson(nga_states).add_to(m)

        folium.Marker(
            [lat0, lon0],
            icon=folium.Icon(color="red"),
            popup="Input Location"
        ).add_to(m)

        for _, r in res.iterrows():
            folium.CircleMarker(
                [r[LAT], r[LON]],
                radius=5,
                color=get_operator_color(r[OP]),
                fill=True,
                fill_color=get_technology_color(r[TECH]),
                fill_opacity=0.85,
                popup=f"""
                Operator: {r[OP]}<br>
                Technology: {r[TECH]}<br>
                Distance: {r['distance_km']:.2f} km
                """
            ).add_to(m)

        st_folium(m, use_container_width=True, height=650)

    # ---------------- TAB 2 ----------------
    with tabs[1]:
        if res.empty:
            st.error("❌ No coverage found in this area")
        else:
            st.success("Coverage exists around this location")

    # ---------------- TAB 3 ----------------
    with tabs[2]:
        st.dataframe(
            res[[OP, TECH, "distance_km"]].sort_values("distance_km"),
            use_container_width=True
        )

    # ---------------- TAB 4 ----------------
    with tabs[3]:
        if res.empty:
            st.error("No network detected")
            st.write(f"Nearest site is *{df['distance_km'].min():.2f} km* away")
        else:
            nearest = res.sort_values("distance_km").iloc[0]
            st.success("Network Available")
            st.metric("Operator", nearest[OP])
            st.metric("Technology", nearest[TECH])
            st.metric("Distance (km)", f"{nearest['distance_km']:.2f}")

    # ---------------- TAB 5 ----------------
    with tabs[4]:
        st.metric("Sites Found", len(res))
        if res.empty:
            st.warning("Coverage Gap Detected")

    # ---------------- TAB 6 ----------------
    with tabs[5]:
        if res.empty:
            st.success("Recommended new tower at input location")
            st.write(f"Lat: {lat0}, Lon: {lon0}")
        else:
            st.info("Existing coverage – densification recommended")

    # ---------------- TAB 7 ----------------
    with tabs[6]:
        st.download_button(
            "Download Results CSV",
            res.to_csv(index=False),
            "network_results.csv"
        )

    # ---------------- TAB 8 ----------------
    with tabs[7]:
        st.bar_chart(res[OP].value_counts())

    # ---------------- TAB 9 ----------------
    with tabs[8]:
        st.bar_chart(res[TECH].value_counts())

    # ---------------- TAB 10 ----------------
    with tabs[9]:
        m2 = folium.Map([lat0, lon0], zoom_start=8)
        folium.Circle(
            [lat0, lon0],
            radius=(radius_km or 50) * 1000,
            fill=True,
            fill_opacity=0.2
        ).add_to(m2)
        st_folium(m2, use_container_width=True, height=600)

    # ---------------- TAB 11 ----------------
    with tabs[10]:
        if STATE:
            density = df.groupby(STATE).size()
            st.bar_chart(density)
        else:
            st.warning("State column not available")

    # ---------------- TAB 12 ----------------
    with tabs[11]:
        st.markdown("""
        *How to use*
        1. Enter coordinates
        2. Choose distance or no limit
        3. Click Run Analysis
        4. Navigate tabs (scroll if needed)
        """)

else:
    st.info("👈 Enter coordinates and click *Run Analysis*")
