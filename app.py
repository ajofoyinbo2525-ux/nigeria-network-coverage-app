import os
import json
import streamlit as st
import folium
from streamlit_folium import st_folium

# =========================
# STREAMLIT PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Nigeria Mobile Network Coverage Planning System",
    layout="wide"
)

st.title("Nigeria Mobile Network Coverage Planning System")
st.caption("2G | 3G | 4G • Coverage • Gaps • Site Recommendation")

# =========================
# SAFE BASE DIRECTORY FIX
# =========================
BASE_DIR = os.path.dirname(os.path.realpath(_file_))

nga0_file = "gadm41_NGA_0.geojson"
nga1_file = "gadm41_NGA_1.geojson"

nga0_path = os.path.join(BASE_DIR, nga0_file)
nga1_path = os.path.join(BASE_DIR, nga1_file)

# =========================
# DEBUG (KEEP FOR NOW)
# =========================
st.write("📁 App directory:", BASE_DIR)
st.write("📄 Files found:", os.listdir(BASE_DIR))

# =========================
# FILE EXISTENCE CHECK
# =========================
if not os.path.exists(nga0_path):
    st.error(f"❌ {nga0_file} not found in app directory")
    st.stop()

if not os.path.exists(nga1_path):
    st.error(f"❌ {nga1_file} not found in app directory")
    st.stop()

# =========================
# LOAD GEOJSON FILES
# =========================
with open(nga0_path, "r", encoding="utf-8") as f:
    nigeria_geo = json.load(f)

with open(nga1_path, "r", encoding="utf-8") as f:
    states_geo = json.load(f)

st.success("✅ Nigeria boundary and states loaded successfully")

# =========================
# MAP TAB
# =========================
tab1, tab2, tab3 = st.tabs([
    "🗺️ National Map",
    "📊 Coverage Density",
    "📍 Site Recommendation"
])

# =========================
# TAB 1: NATIONAL MAP
# =========================
with tab1:
    m = folium.Map(location=[9.08, 8.67], zoom_start=6)

    folium.GeoJson(
        nigeria_geo,
        name="Nigeria Boundary",
        style_function=lambda x: {
            "fillColor": "#00000000",
            "color": "black",
            "weight": 2
        }
    ).add_to(m)

    folium.GeoJson(
        states_geo,
        name="States",
        style_function=lambda x: {
            "fillColor": "#3388ff33",
            "color": "blue",
            "weight": 1
        },
        tooltip=folium.GeoJsonTooltip(fields=["NAME_1"], aliases=["State"])
    ).add_to(m)

    folium.LayerControl().add_to(m)

    st_folium(m, width=1200, height=600)

# =========================
# TAB 2: COVERAGE DENSITY (PLACEHOLDER)
# =========================
with tab2:
    st.info("Coverage density per state will be visualized here.")
    st.write("Next step: aggregate coverage layers by state.")

# =========================
# TAB 3: SITE RECOMMENDATION (PLACEHOLDER)
# =========================
with tab3:
    st.info("Recommended new tower locations will appear here.")
    st.write("Population proxy + coverage gaps logic goes here.")
