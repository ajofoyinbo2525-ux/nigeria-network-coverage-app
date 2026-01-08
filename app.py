import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from math import radians, cos
import numpy as np
import json

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

    # Normalize operators
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

    # Normalize technology
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
# COLOR CODING
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
# FAST HAVERSINE (VECTORIZED)
# --------------------------------------------------
def haversine_np(lat, lon, lats, lons):
    R = 6371
    lat, lon = radians(lat), radians(lon)
    lats, lons = np.radians(lats), np.radians(lons)

    dlat = lats - lat
    dlon = lons - lon

    a = np.sin(dlat/2)*2 + np.cos(lat)*np.cos(lats)*np.sin(dlon/2)*2
    return 2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
st.sidebar.header("📍 Analysis Settings")
lat = st.sidebar.number_input("Latitude", value=6.5244)
lon = st.sidebar.number_input("Longitude", value=3.3792)
radius_km = st.sidebar.slider("Coverage Radius (km)", 5, 100, 30)
analyze = st.sidebar.button("🔍 Analyze")

# --------------------------------------------------
# MAIN
# --------------------------------------------------
if analyze:

    df["distance_km"] = haversine_np(
        lat, lon, df["Latitude"].values, df["Longitude"].values
    )

    nearby = df[df["distance_km"] <= radius_km]

    # ================= COVERAGE MAP =================
    st.header("📶 Coverage Analysis")

    m = folium.Map(location=[lat, lon], zoom_start=8)

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
            color=OPERATOR_COLORS.get(r["Network_Operator"], "blue"),
            fill=True,
            fill_color=TECH_COLORS.get(r["Network_Generation"], "gray"),
            fill_opacity=0.9,
            popup=f"""
            <b>Operator:</b> {r['Network_Operator']}<br>
            <b>Technology:</b> {r['Network_Generation']}
            """
        ).add_to(m)

    folium.Circle([lat, lon], radius=radius_km*1000, color="blue").add_to(m)
    st_folium(m, height=520, width=1100)

    # ================= NETWORK PREDICTOR =================
    st.subheader("📡 Network Predictor")

    if nearby.empty:
        st.error("❌ No network detected")
    else:
        summary = nearby.groupby(
            ["Network_Operator", "Network_Generation"]
        ).size().reset_index(name="Count")

        best = summary.sort_values("Count", ascending=False).iloc[0]
        confidence = int(best["Count"] / summary["Count"].sum() * 100)

        st.success(
            f"Best Network: {best['Network_Operator']} ({best['Network_Generation']})"
        )
        st.info(f"Confidence Level: {confidence}%")
        st.dataframe(summary)

    # ================= NO COVERAGE MAP =================
    st.header("🚫 No Coverage & New Tower Recommendation")

    gap_map = folium.Map(location=[lat, lon], zoom_start=8)

    folium.GeoJson(nga, style_function=lambda x: {
        "fillOpacity": 0, "color": "black", "weight": 1
    }).add_to(gap_map)

    uncovered = []

    for dx in range(-radius_km, radius_km + 1, 15):
        for dy in range(-radius_km, radius_km + 1, 15):
            glat = lat + dx / 111
            glon = lon + dy / (111 * cos(radians(lat)))

            dist = haversine_np(
                glat, glon,
                df["Latitude"].values,
                df["Longitude"].values
            ).min()

            if dist > radius_km:
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
        st.error("🚨 No Coverage Detected")
        st.success(f"📍 New Tower Location: {rlat:.4f}, {rlon:.4f}")
        st.info("📡 Recommended Network: 4G (High Capacity)")

else:
    st.info("👈 Enter coordinates and click Analyze")
