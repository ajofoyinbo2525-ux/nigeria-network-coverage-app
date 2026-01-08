import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
import json
from math import cos, radians

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Nigeria Network Coverage & Planning App",
    layout="wide"
)

st.title("📡 Nigeria Network Coverage & Planning App")

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------
@st.cache_data
def load_csv():
    df = pd.read_csv("Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv")

    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
    df = df.dropna(subset=["Latitude", "Longitude"])

    df["Network_Operator"] = (
        df["Network_Operator"]
        .astype(str)
        .str.strip()
        .replace({
            "MTN": "MTN Nigeria",
            "AIRTEL": "Airtel Nigeria",
            "GLO": "Globacom",
            "9MOBILE": "9mobile"
        }, regex=True)
    )

    df["Network_Generation"] = (
        df["Network_Generation"]
        .astype(str)
        .str.upper()
        .replace({
            "LTE": "4G",
            "4 G": "4G",
            "3 G": "3G",
            "2 G": "2G"
        })
    )

    return df


@st.cache_data
def load_geojson(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


df = load_csv()
nga = load_geojson("gadm41_NGA_0.geojson")
states = load_geojson("gadm41_NGA_1.geojson")

# --------------------------------------------------
# COLORS
# --------------------------------------------------
OPERATOR_COLORS = {
    "MTN Nigeria": "#FFD700",
    "Airtel Nigeria": "#FF0000",
    "Globacom": "#008000",
    "9mobile": "#000000"
}

TECH_COLORS = {
    "2G": "#9E9E9E",
    "3G": "#2196F3",
    "4G": "#9C27B0"
}

# --------------------------------------------------
# HAVERSINE (CORRECT & FAST)
# --------------------------------------------------
def haversine_np(lat, lon, lats, lons):
    R = 6371
    lat = np.radians(lat)
    lon = np.radians(lon)
    lats = np.radians(lats)
    lons = np.radians(lons)

    dlat = lats - lat
    dlon = lons - lon

    a = (
        np.sin(dlat / 2) ** 2 +
        np.cos(lat) * np.cos(lats) * np.sin(dlon / 2) ** 2
    )

    return 2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

# --------------------------------------------------
# SIDEBAR INPUTS
# --------------------------------------------------
st.sidebar.header("📍 Analysis Settings")

lat = st.sidebar.number_input("Latitude", value=6.5244, format="%.6f")
lon = st.sidebar.number_input("Longitude", value=3.3792, format="%.6f")
radius_km = st.sidebar.slider("Coverage Radius (km)", 5, 100, 30)

analyze = st.sidebar.button("🔍 Analyze")

# --------------------------------------------------
# SESSION STATE INIT
# --------------------------------------------------
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False

# --------------------------------------------------
# RUN ANALYSIS (ONLY WHEN CLICKED)
# --------------------------------------------------
if analyze:
    df["distance_km"] = haversine_np(
        lat, lon,
        df["Latitude"].values,
        df["Longitude"].values
    )

    nearby = df[df["distance_km"] <= radius_km]

    tech_weight = {"2G": 1, "3G": 2, "4G": 3}

    if not nearby.empty:
        nearby["weight"] = (
            (1 / (nearby["distance_km"] + 0.5)) *
            nearby["Network_Generation"].map(tech_weight)
        )

        score = (
            nearby
            .groupby(["Network_Operator", "Network_Generation"])["weight"]
            .sum()
            .reset_index()
            .sort_values("weight", ascending=False)
        )

        best = score.iloc[0]
        confidence = int(best["weight"] / score["weight"].sum() * 100)
    else:
        best = None
        confidence = 0

    st.session_state.nearby = nearby
    st.session_state.best = best
    st.session_state.confidence = confidence
    st.session_state.analysis_done = True
    st.session_state.lat = lat
    st.session_state.lon = lon
    st.session_state.radius_km = radius_km

# --------------------------------------------------
# DISPLAY RESULTS (PERSISTENT)
# --------------------------------------------------
if st.session_state.analysis_done:

    nearby = st.session_state.nearby

    # ================= MAP =================
    st.header("📶 Coverage Analysis")

    m = folium.Map(
        location=[st.session_state.lat, st.session_state.lon],
        zoom_start=8
    )

    folium.GeoJson(nga, style_function=lambda x: {
        "fillOpacity": 0, "color": "black", "weight": 1
    }).add_to(m)

    folium.GeoJson(states, style_function=lambda x: {
        "fillOpacity": 0, "color": "gray", "weight": 0.5
    }).add_to(m)

    for _, r in nearby.iterrows():
        folium.CircleMarker(
            [r["Latitude"], r["Longitude"]],
            radius=6,
            color=TECH_COLORS.get(r["Network_Generation"], "gray"),
            fill=True,
            fill_color=OPERATOR_COLORS.get(r["Network_Operator"], "blue"),
            fill_opacity=0.9,
            popup=f"""
            <b>Operator:</b> {r['Network_Operator']}<br>
            <b>Technology:</b> {r['Network_Generation']}<br>
            <b>Distance:</b> {r['distance_km']:.2f} km
            """
        ).add_to(m)

    folium.Circle(
        [st.session_state.lat, st.session_state.lon],
        radius=st.session_state.radius_km * 1000,
        color="blue",
        fill=False
    ).add_to(m)

    st_folium(m, height=520, width=1100)

    # ================= PREDICTOR =================
    st.subheader("📡 Network Predictor")

    if nearby.empty:
        st.error("❌ No network detected within radius")
    else:
        st.success(
            f"Best Network: {st.session_state.best['Network_Operator']} "
            f"({st.session_state.best['Network_Generation']})"
        )
        st.info(f"Confidence Level: {st.session_state.confidence}%")
        st.dataframe(
            nearby[[
                "Network_Operator",
                "Network_Generation",
                "distance_km"
            ]].sort_values("distance_km")
        )

    # ================= NO COVERAGE =================
    st.header("🚫 No Coverage & New Tower Recommendation")

    gap_map = folium.Map(
        location=[st.session_state.lat, st.session_state.lon],
        zoom_start=8
    )

    MIN_SIGNAL_KM = 8
    uncovered = []

    for dx in range(-radius_km, radius_km + 1, 15):
        for dy in range(-radius_km, radius_km + 1, 15):
            glat = st.session_state.lat + dx / 111
            glon = st.session_state.lon + dy / (111 * cos(radians(st.session_state.lat)))

            dist = haversine_np(
                glat, glon,
                df["Latitude"].values,
                df["Longitude"].values
            ).min()

            if dist > MIN_SIGNAL_KM:
                uncovered.append((glat, glon))
                folium.Circle(
                    [glat, glon],
                    radius=3000,
                    color="red",
                    fill=True,
                    fill_opacity=0.4
                ).add_to(gap_map)

    st_folium(gap_map, height=520, width=1100)

    if uncovered:
        rlat, rlon = uncovered[0]

        if st.session_state.radius_km <= 15:
            rec = "4G (Urban / High Capacity)"
        elif st.session_state.radius_km <= 40:
            rec = "3G + 4G (Suburban)"
        else:
            rec = "2G + 3G (Rural Coverage)"

        st.error("🚨 No Coverage Detected")
        st.success(f"📍 New Tower Location: {rlat:.4f}, {rlon:.4f}")
        st.info(f"📡 Recommended Network: {rec}")

else:
    st.info("👈 Enter coordinates and click Analyze")
