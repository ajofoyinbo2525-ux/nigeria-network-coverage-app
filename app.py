import os
import json
import streamlit as st
import pandas as pd
import folium
from geopy.distance import geodesic
from streamlit_folium import st_folium

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Nigeria Network Coverage Dashboard",
    layout="wide"
)

st.title("📡 Nigeria Network Coverage & Planning Dashboard")

# ---------------- CONSTANTS ----------------
CSV_FILE = "Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv"

OPERATOR_COLORS = {
    "MTN": "yellow",
    "AIRTEL": "red",
    "GLO": "green",
    "9MOBILE": "blue"
}

TECH_ICONS = {
    "2G": "signal",
    "3G": "wifi",
    "4G": "tower-broadcast"
}

# ---------------- SESSION STATE ----------------
if "run" not in st.session_state:
    st.session_state.run = False

# ---------------- FILE FINDER ----------------
def find_file(filename):
    for root, _, files in os.walk("."):
        if filename in files:
            return os.path.join(root, filename)
    return None

nga0_path = find_file("gadm41_NGA_0.geojson")
nga1_path = find_file("gadm41_NGA_1.geojson")

# ---------------- LOAD DATA ----------------
@st.cache_data
def load_network_data():
    return pd.read_csv(CSV_FILE)

try:
    df = load_network_data()
except:
    st.error("❌ Network CSV not found. Ensure the file name is correct.")
    st.stop()

# Validate columns
required_cols = ["Latitude", "Longitude", "Network_Operator", "Network_Generation"]
for col in required_cols:
    if col not in df.columns:
        st.error(f"❌ Missing required column: {col}")
        st.stop()

# ---------------- SIDEBAR ----------------
st.sidebar.header("📍 Location Input")

lat = st.sidebar.number_input("Latitude", value=6.5244, format="%.6f")
lon = st.sidebar.number_input("Longitude", value=3.3792, format="%.6f")

radius_km = st.sidebar.slider("Buffer Radius (km)", 1, 100, 20)
no_limit = st.sidebar.checkbox("No distance limit")

if st.sidebar.button("🔍 Analyze Location"):
    st.session_state.run = True
    st.session_state.lat = lat
    st.session_state.lon = lon
    st.session_state.radius = radius_km
    st.session_state.no_limit = no_limit

# ---------------- TABS ----------------
tabs = st.tabs([
    "🗺 Coverage Map",
    "⭕ Buffer View",
    "🚫 No Coverage Map",
    "📊 Network Results",
    "🔮 Network Predictor",
    "⚠ Coverage Gap Analyzer",
    "🏗 New Tower Recommendation",
    "🏙 Coverage Density (State)",
    "📡 Operator Summary",
    "📶 Technology Summary",
    "📥 Export Results",
    "📘 User Guide"
])

# ---------------- ANALYSIS ----------------
if st.session_state.run:
    lat0 = st.session_state.lat
    lon0 = st.session_state.lon
    radius_km = st.session_state.radius
    no_limit = st.session_state.no_limit

    df["distance_km"] = df.apply(
        lambda r: geodesic(
            (lat0, lon0),
            (r["Latitude"], r["Longitude"])
        ).km,
        axis=1
    )

    if no_limit:
        nearby = df.copy()
    else:
        nearby = df[df["distance_km"] <= radius_km].copy()

    nearby["confidence"] = nearby["distance_km"].apply(
        lambda d: "High" if d <= 5 else "Medium" if d <= 15 else "Low"
    )

    # ---------------- TAB 1: COVERAGE MAP ----------------
    with tabs[0]:
        m = folium.Map([lat0, lon0], zoom_start=10)

        if nga0_path:
            folium.GeoJson(nga0_path, name="Nigeria Boundary").add_to(m)
        if nga1_path:
            folium.GeoJson(nga1_path, name="State Boundary").add_to(m)

        folium.Marker(
            [lat0, lon0],
            icon=folium.Icon(color="black"),
            popup="Input Location"
        ).add_to(m)

        for _, r in nearby.iterrows():
            op = str(r["Network_Operator"]).upper()
            tech = str(r["Network_Generation"]).upper()

            folium.Marker(
                [r["Latitude"], r["Longitude"]],
                icon=folium.Icon(
                    color=OPERATOR_COLORS.get(op, "gray"),
                    icon=TECH_ICONS.get(tech, "signal"),
                    prefix="fa"
                ),
                popup=f"""
                <b>Operator:</b> {op}<br>
                <b>Technology:</b> {tech}<br>
                <b>Distance:</b> {r['distance_km']:.2f} km<br>
                <b>Confidence:</b> {r['confidence']}
                """
            ).add_to(m)

        st_folium(m, height=600, use_container_width=True)

    # ---------------- TAB 2: BUFFER VIEW ----------------
    with tabs[1]:
        m = folium.Map([lat0, lon0], zoom_start=11)

        folium.Circle(
            [lat0, lon0],
            radius=radius_km * 1000,
            color="blue",
            fill=True,
            fill_opacity=0.15
        ).add_to(m)

        for _, r in nearby.iterrows():
            folium.CircleMarker(
                [r["Latitude"], r["Longitude"]],
                radius=4,
                color=OPERATOR_COLORS.get(str(r["Network_Operator"]).upper(), "gray"),
                fill=True
            ).add_to(m)

        st_folium(m, height=600, use_container_width=True)

    # ---------------- TAB 3: NO COVERAGE MAP ----------------
    with tabs[2]:
        if nearby.empty:
            st.success("✅ No network coverage detected here.")
        else:
            st.warning("⚠ Coverage exists in this area.")

    # ---------------- TAB 4: RESULTS TABLE ----------------
    with tabs[3]:
        st.dataframe(
            nearby[[
                "Network_Operator",
                "Network_Generation",
                "distance_km",
                "confidence"
            ]].sort_values("distance_km")
        )

    # ---------------- TAB 5: NETWORK PREDICTOR ----------------
    with tabs[4]:
        st.metric("Detected Networks", len(nearby))
        st.dataframe(
            nearby[[
                "Network_Operator",
                "Network_Generation",
                "distance_km",
                "confidence"
            ]]
        )

    # ---------------- TAB 6: COVERAGE GAP ANALYZER ----------------
    with tabs[5]:
        status = "No Coverage" if nearby.empty else "Partial Coverage"
        st.write("Coverage Status:", status)

    # ---------------- TAB 7: NEW TOWER RECOMMENDATION ----------------
    with tabs[6]:
        if nearby.empty:
            st.success("📍 Recommend building a new tower at input location.")
        else:
            st.info("📶 Improve existing coverage.")

    # ---------------- TAB 8: COVERAGE DENSITY ----------------
    with tabs[7]:
        if "State" in df.columns:
            density = df.groupby("State").size().sort_values(ascending=False)
            st.bar_chart(density)

    # ---------------- TAB 9: OPERATOR SUMMARY ----------------
    with tabs[8]:
        st.bar_chart(df["Network_Operator"].value_counts())

    # ---------------- TAB 10: TECHNOLOGY SUMMARY ----------------
    with tabs[9]:
        st.bar_chart(df["Network_Generation"].value_counts())

    # ---------------- TAB 11: EXPORT ----------------
    with tabs[10]:
        st.download_button(
            "⬇ Export Network Results",
            nearby.to_csv(index=False),
            "network_results.csv",
            "text/csv"
        )

    # ---------------- TAB 12: USER GUIDE ----------------
    with tabs[11]:
        st.markdown("""
        *How to use this app*
        1. Enter coordinates
        2. Choose buffer or no limit
        3. Click Analyze
        4. View all tabs
        """)

else:
    st.info("👈 Enter coordinates and click *Analyze Location*")
