import os
import json
import math
import pandas as pd
import streamlit as st
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from shapely.geometry import Point, shape
import geopandas as gpd

# ===============================
# PAGE CONFIG
# ===============================
st.set_page_config(
    page_title="Nigeria Mobile Network Coverage Planning System",
    layout="wide"
)

st.title("📡 Nigeria Mobile Network Coverage Planning System")
st.caption("2G | 3G | 4G • Coverage • Gaps • Site Recommendation")

# ===============================
# SAFE GEOJSON LOADER
# ===============================
BASE_DIR = os.getcwd()

nga0_path = os.path.join(BASE_DIR, "gadm41_NGA_0.geojson")
nga1_path = os.path.join(BASE_DIR, "gadm41_NGA_1.geojson")

if not os.path.exists(nga0_path):
    st.error("❌ gadm41_NGA_0.geojson not found")
    st.stop()

if not os.path.exists(nga1_path):
    st.error("❌ gadm41_NGA_1.geojson not found")
    st.stop()

with open(nga0_path, "r", encoding="utf-8") as f:
    nigeria_geo = json.load(f)

with open(nga1_path, "r", encoding="utf-8") as f:
    states_geo = json.load(f)

st.success("✅ GeoJSON files loaded successfully")
# ===============================
# LOAD CSV DATA
# ===============================
@st.cache_data
def load_data():
    return pd.read_csv("Nigeria_2G_3G_4G_All_Operators.csv")

df = load_data()

required_cols = [
    "Country", "MCC", "MNC", "Network_Operator",
    "Radio_Technology", "Network_Generation",
    "Latitude", "Longitude"
]

missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"❌ Missing required columns: {missing}")
    st.stop()

# ===============================
# GEO DATAFRAME
# ===============================
gdf = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df.Longitude, df.Latitude),
    crs="EPSG:4326"
)

states_gdf = gpd.GeoDataFrame.from_features(states_geo["features"], crs="EPSG:4326")

# ===============================
# SIDEBAR FILTERS
# ===============================
st.sidebar.header("🔎 Filters")

operator = st.sidebar.multiselect(
    "Network Operator",
    sorted(df["Network_Operator"].unique()),
    default=sorted(df["Network_Operator"].unique())
)

generation = st.sidebar.multiselect(
    "Network Generation",
    sorted(df["Network_Generation"].unique()),
    default=sorted(df["Network_Generation"].unique())
)

filtered = df[
    (df["Network_Operator"].isin(operator)) &
    (df["Network_Generation"].isin(generation))
]

# ===============================
# TABS
# ===============================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📍 Network Map",
    "📶 Coverage Buffer",
    "📊 Coverage Density",
    "🚫 No Coverage Areas",
    "🗼 Recommended Sites"
])

# ===============================
# TAB 1: NETWORK MAP
# ===============================
with tab1:
    m = folium.Map(location=[9.1, 8.7], zoom_start=6, tiles="cartodbpositron")

    folium.GeoJson(nigeria_geo, name="Nigeria").add_to(m)
    folium.GeoJson(states_geo, name="States").add_to(m)

    cluster = MarkerCluster().add_to(m)

    for _, r in filtered.iterrows():
        folium.CircleMarker(
            location=[r.Latitude, r.Longitude],
            radius=3,
            color="blue",
            fill=True,
            popup=f"""
            Operator: {r.Network_Operator}<br>
            Generation: {r.Network_Generation}<br>
            Technology: {r.Radio_Technology}
            """
        ).add_to(cluster)

    folium.LayerControl().add_to(m)
    st_folium(m, height=600)

# ===============================
# TAB 2: COVERAGE BUFFER
# ===============================
with tab2:
    buffer_km = st.slider("Coverage Radius (km)", 1, 20, 5)

    m2 = folium.Map(location=[9.1, 8.7], zoom_start=6, tiles="cartodbpositron")
    folium.GeoJson(states_geo).add_to(m2)

    for _, r in filtered.iterrows():
        folium.Circle(
            location=[r.Latitude, r.Longitude],
            radius=buffer_km * 1000,
            color="green",
            fill=True,
            fill_opacity=0.1
        ).add_to(m2)

    st_folium(m2, height=600)

# ===============================
# TAB 3: COVERAGE DENSITY PER STATE
# ===============================
with tab3:
    joined = gpd.sjoin(gdf, states_gdf, predicate="within")
    density = joined.groupby("NAME_1").size().reset_index(name="Sites")

    st.dataframe(density.sort_values("Sites", ascending=False))

# ===============================
# TAB 4: NO COVERAGE AREAS (BASIC GRID)
# ===============================
with tab4:
    st.info("Approximate no-coverage zones based on sparse site density.")

    bounds = states_gdf.total_bounds
    minx, miny, maxx, maxy = bounds

    empty_points = []

    for x in range(50):
        for y in range(50):
            lon = minx + (maxx - minx) * x / 50
            lat = miny + (maxy - miny) * y / 50
            p = Point(lon, lat)

            if gdf.distance(p).min() > 0.3:
                empty_points.append([lat, lon])

    m4 = folium.Map(location=[9.1, 8.7], zoom_start=6)

    for p in empty_points:
        folium.CircleMarker(p, radius=2, color="red").add_to(m4)

    st_folium(m4, height=600)

# ===============================
# TAB 5: RECOMMENDED NEW SITES
# ===============================
with tab5:
    st.subheader("📍 Recommended New Tower Locations")

    rec_sites = pd.DataFrame(empty_points, columns=["Latitude", "Longitude"])
    rec_sites["Population_Proxy"] = rec_sites.index % 100
    rec_sites = rec_sites.sort_values("Population_Proxy", ascending=False).head(50)

    st.dataframe(rec_sites)

    csv = rec_sites.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download Recommended Sites",
        csv,
        "recommended_sites.csv",
        "text/csv"
    )

    m5 = folium.Map(location=[9.1, 8.7], zoom_start=6)
    for _, r in rec_sites.iterrows():
        folium.Marker(
            [r.Latitude, r.Longitude],
            icon=folium.Icon(color="red", icon="signal")
        ).add_to(m5)

    st_folium(m5, height=600)




