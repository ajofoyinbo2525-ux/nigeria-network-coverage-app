[4:31 PM, 1/8/2026] Holex Properties: import streamlit as st
import pandas as pd
import folium
import json
import os
from geopy.distance import geodesic
from streamlit_folium import st_folium

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Nigeria Network Coverage Dashboard", layout="wide")
st.title("📡 Nigeria Network Coverage & Planning Dashboard")

# ---------------- CONSTANTS ----------------
CSV_FILE = "Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv"
NGA0 = "gadm41_NGA_0.geojson"
NGA1 = "gadm41_NGA_1.geojson"

OPERATOR_COLORS = {
    "MTN": "yellow",
    "AIRTEL": "red",
    "GLO": "green",
    "9MOBILE": "blue"
}

TECH_COLORS = {
    "2G": "gray",
    "3G": "orange",
    "4G": "blue"
}

# ---------------- HELPERS ----------------
def load_geojson(path):
    with …
[4:40 PM, 1/8/2026] Holex Properties: import streamlit as st
import pandas as pd
import folium
import json
from geopy.distance import geodesic
from streamlit_folium import st_folium

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Nigeria Network Coverage", layout="wide")
st.title("📡 Nigeria Network Coverage & Planning Dashboard")

# ================= CONSTANTS =================
CSV_FILE = "Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv"
NGA0 = "gadm41_NGA_0.geojson"
NGA1 = "gadm41_NGA_1.geojson"

OPERATOR_COLORS = {
    "MTN": "yellow",
    "AIRTEL": "red",
    "GLO": "green",
    "9MOBILE": "blue"
}

# ================= LOADERS =================
@st.cache_data
def load_csv():
    return pd.read_csv(CSV_FILE)

def load_geo(path):
    with open(path, "r", encoding="u…
[4:50 PM, 1/8/2026] Holex Properties: https://nigeria-network-coverage-app-nhq55xaxat4b3dn5r6rpzg.streamlit.app/
[5:23 PM, 1/8/2026] Holex Properties: import streamlit as st
import pandas as pd
import folium
from geopy.distance import geodesic
from streamlit_folium import st_folium

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Nigeria Network Coverage & Planning",
    layout="wide"
)

st.title("📡 Nigeria Network Coverage & Planning Dashboard")

# ---------------- LOAD DATA ----------------
@st.cache_data
def load_data():
    return pd.read_csv("Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv")

try:
    df = load_data()
except:
    st.error("❌ CSV file not found")
    st.stop()

# ---------------- VALIDATE COLUMNS ----------------
required_cols = ["Latitude", "Longitude", "Network_Operator", "Network_Generation"]
for col in required_cols:
    if col not in df.columns:
    …
[6:07 PM, 1/8/2026] Holex Properties: import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from math import radians, cos, sin, sqrt, atan2
import json
import numpy as np

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Nigeria Network Coverage & Planning App",
    layout="wide"
)

st.title("📡 Nigeria Network Coverage & Planning App")

# --------------------------------------------------
# LOAD & CLEAN DATA
# --------------------------------------------------
@st.cache_data
def load_csv():
    df = pd.read_csv("Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv")

    # force numeric (fixes your error)
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
    df = df.dropna(subset=["Latitude", "Longitude"])

    # ---- NORMALIZE OPERATOR NAMES (FIX COLOR ISSUE) ----
    df["Network_Operator"] = (
        df["Network_Operator"]
        .astype(str)
        .str.strip()
        .str.replace("MTN.*", "MTN Nigeria", regex=True)
        .str.replace("Airtel.*", "Airtel Nigeria", regex=True)
        .str.replace("Glo.|Globacom.", "Globacom", regex=True)
        .str.replace("9.*", "9mobile", regex=True)
    )

    # normalize technology
    df["Network_Generation"] = (
        df["Network_Generation"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    return df

@st.cache_data
def load_geojson(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

df = load_csv()
nga_boundary = load_geojson("gadm41_NGA_0.geojson")
state_boundary = load_geojson("gadm41_NGA_1.geojson")

# --------------------------------------------------
# COLOR CODING (GUARANTEED)
# --------------------------------------------------
OPERATOR_COLORS = {
    "MTN Nigeria": "#FFD700",      # Yellow
    "Airtel Nigeria": "#FF0000",   # Red
    "Globacom": "#008000",         # Green
    "9mobile": "#000000"           # Black
}

TECH_COLORS = {
    "2G": "#9E9E9E",   # Gray
    "3G": "#2196F3",   # Blue
    "4G": "#9C27B0"    # Purple
}

# --------------------------------------------------
# HAVERSINE (SAFE)
# --------------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    if any(pd.isna([lat1, lon1, lat2, lon2])):
        return np.nan

    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)*2 + cos(lat1) * cos(lat2) * sin(dlon/2)*2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
st.sidebar.header("📍 Analysis Settings")

lat = st.sidebar.number_input("Latitude", value=6.5244)
lon = st.sidebar.number_input("Longitude", value=3.3792)
radius_km = st.sidebar.slider("Coverage Radius (km)", 5, 100, 30)

analyze = st.sidebar.button("🔍 Analyze")

# --------------------------------------------------
# ANALYSIS
# --------------------------------------------------
if analyze:

    df["distance_km"] = df.apply(
        lambda r: haversine(lat, lon, r["Latitude"], r["Longitude"]),
        axis=1
    )

    nearby = df[df["distance_km"] <= radius_km].copy()

    # ==================================================
    # COVERAGE MAP
    # ==================================================
    st.header("📶 Coverage Analysis")

    m = folium.Map(location=[lat, lon], zoom_start=8)

    folium.GeoJson(nga_boundary, style_function=lambda x: {
        "fillOpacity": 0, "color": "black", "weight": 1
    }).add_to(m)

    folium.GeoJson(state_boundary, style_function=lambda x: {
        "fillOpacity": 0, "color": "gray", "weight": 0.5
    }).add_to(m)

    # ---- DUAL COLOR MARKERS ----
    for _, r in nearby.iterrows():
        folium.CircleMarker(
            location=[r["Latitude"], r["Longitude"]],
            radius=6,
            color=OPERATOR_COLORS.get(r["Network_Operator"], "blue"),  # BORDER
            fill=True,
            fill_color=TECH_COLORS.get(r["Network_Generation"], "gray"),  # FILL
            fill_opacity=0.9,
            weight=2,
            popup=f"""
            <b>Operator:</b> {r['Network_Operator']}<br>
            <b>Technology:</b> {r['Network_Generation']}<br>
            <b>Distance:</b> {r['distance_km']:.2f} km
            """
        ).add_to(m)

    folium.Circle(
        location=[lat, lon],
        radius=radius_km * 1000,
        color="blue",
        fill=False
    ).add_to(m)

    st_folium(m, height=520, width=1100)

    # ==================================================
    # NETWORK PREDICTOR
    # ==================================================
    st.subheader("📡 Network Predictor")

    if nearby.empty:
        st.error("❌ No network detected in this area")
    else:
        summary = nearby.groupby(
            ["Network_Operator", "Network_Generation"]
        ).size().reset_index(name="Count")

        best = summary.sort_values("Count", ascending=False).iloc[0]
        confidence = int((best["Count"] / summary["Count"].sum()) * 100)

        st.success(
            f"✅ Best Network: {best['Network_Operator']} ({best['Network_Generation']})"
        )
        st.info(f"📊 Confidence Level: {confidence}%")
        st.dataframe(summary)

    # ==================================================
    # NO COVERAGE MAP + NEW TOWER
    # ==================================================
    st.header("🚫 No Coverage Area & New Tower Recommendation")

    gap_map = folium.Map(location=[lat, lon], zoom_start=8)

    folium.GeoJson(nga_boundary, style_function=lambda x: {
        "fillOpacity": 0, "color": "black", "weight": 1
    }).add_to(gap_map)

    uncovered = []

    for dx in range(-radius_km, radius_km + 1, 10):
        for dy in range(-radius_km, radius_km + 1, 10):
            glat = lat + dx / 111
            glon = lon + dy / (111 * cos(radians(lat)))

            min_dist = df.apply(
                lambda r: haversine(glat, glon, r["Latitude"], r["Longitude"]),
                axis=1
            ).min()

            if pd.notna(min_dist) and min_dist > radius_km:
                uncovered.append((glat, glon))
                folium.Circle(
                    location=[glat, glon],
                    radius=3000,
                    color="red",
                    fill=True,
                    fill_opacity=0.4
                ).add_to(gap_map)

    st_folium(gap_map, height=520, width=1100)

    if uncovered:
        rec_lat, rec_lon = uncovered[0]
        st.error("🚨 No Coverage Detected")
        st.success(f"📍 Recommended New Tower Location: {rec_lat:.4f}, {rec_lon:.4f}")
        st.info("📡 Recommended Network: 4G (Highest Capacity)")
    else:
        st.success("✅ No major coverage gaps found")

else:
    st.info("👈 Enter coordinates and click *Analyze*")
