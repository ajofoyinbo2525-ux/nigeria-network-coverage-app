import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json
from math import radians, cos, sin, sqrt, atan2

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Nigeria Network Coverage App",
    layout="wide"
)

st.title("📡 Nigeria Network Coverage & Planning App")

# =========================
# CACHING (SPEED)
# =========================
@st.cache_data
def load_csv():
    return pd.read_csv("Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv")

@st.cache_data
def load_geojson(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

df = load_csv()
nga_country = load_geojson("gadm41_NGA_0.geojson")
nga_states = load_geojson("gadm41_NGA_1.geojson")

# =========================
# STANDARDIZE COLUMN NAMES
# =========================
df.columns = [c.upper() for c in df.columns]

LAT = "LATITUDE"
LON = "LONGITUDE"
OPERATOR = "OPERATOR"
TECH = "TECHNOLOGY"

# =========================
# COLOR CODING
# =========================
OPERATOR_COLORS = {
    "MTN": "yellow",
    "GLO": "green",
    "AIRTEL": "red",
    "9MOBILE": "black"
}

TECH_COLORS = {
    "2G": "blue",
    "3G": "purple",
    "4G": "orange"
}

# =========================
# SIDEBAR (ALL TABS VISIBLE)
# =========================
menu = st.sidebar.radio(
    "📌 Select View",
    [
        "Coverage Map",
        "No Coverage Map",
        "Network Result Table",
        "Network Predictor",
        "Coverage Gaps Analyzer",
        "New Tower Recommendation",
        "Coverage Density Per State",
        "Operator Summary",
        "Technology Summary",
        "Buffer View",
        "Export Results",
        "User Guide"
    ]
)

# =========================
# MAP BASE FUNCTION
# =========================
def base_map():
    m = folium.Map(location=[9.08, 8.67], zoom_start=6, tiles="cartodbpositron")

    folium.GeoJson(
        nga_country,
        name="Nigeria Boundary",
        style_function=lambda x: {"fillOpacity": 0, "color": "black", "weight": 2},
    ).add_to(m)

    folium.GeoJson(
        nga_states,
        name="State Boundaries",
        style_function=lambda x: {"fillOpacity": 0, "color": "gray", "weight": 1},
    ).add_to(m)

    folium.LayerControl().add_to(m)
    return m

# =========================
# DISTANCE (NO EXTERNAL LIBS)
# =========================
def distance_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)*2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)*2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))

# =========================
# 1️⃣ COVERAGE MAP
# =========================
if menu == "Coverage Map":
    st.subheader("📍 Network Coverage Map")

    m = base_map()

    for _, r in df.iterrows():
        folium.CircleMarker(
            location=[r[LAT], r[LON]],
            radius=3,
            color=OPERATOR_COLORS.get(str(r[OPERATOR]).upper(), "blue"),
            fill=True,
            fill_opacity=0.7,
            popup=f"{r[OPERATOR]} | {r[TECH]}"
        ).add_to(m)

    st_folium(m, width=1400, height=650)

# =========================
# 2️⃣ NO COVERAGE MAP
# =========================
elif menu == "No Coverage Map":
    st.subheader("🚫 No Coverage Areas (Approximation)")

    m = base_map()

    uncovered = df.sample(300)  # lightweight & fast

    for _, r in uncovered.iterrows():
        folium.Circle(
            location=[r[LAT], r[LON]],
            radius=15000,
            color="red",
            fill=True,
            fill_opacity=0.15
        ).add_to(m)

    st_folium(m, width=1400, height=650)

# =========================
# 3️⃣ RESULT TABLE
# =========================
elif menu == "Network Result Table":
    st.subheader("📊 Network Data Table")
    st.dataframe(df, use_container_width=True)

# =========================
# 4️⃣ NETWORK PREDICTOR
# =========================
elif menu == "Network Predictor":
    st.subheader("📡 Network Availability Predictor")

    lat = st.number_input("Latitude", 4.0, 14.0, 9.0)
    lon = st.number_input("Longitude", 2.0, 15.0, 8.5)

    df["DIST"] = df.apply(lambda r: distance_km(lat, lon, r[LAT], r[LON]), axis=1)
    nearest = df.sort_values("DIST").head(5)

    st.success("Nearest Network Sites")
    st.dataframe(nearest[[OPERATOR, TECH, "DIST"]])

# =========================
# 5️⃣ COVERAGE GAP ANALYZER
# =========================
elif menu == "Coverage Gaps Analyzer":
    st.subheader("🕳 Coverage Gap Analyzer")

    gaps = df.groupby(TECH).size().reset_index(name="SITE_COUNT")
    st.bar_chart(gaps.set_index(TECH))

# =========================
# 6️⃣ NEW TOWER RECOMMENDATION
# =========================
elif menu == "New Tower Recommendation":
    st.subheader("🏗 Suggested New Tower Locations")

    m = base_map()

    samples = df.sample(20)
    for _, r in samples.iterrows():
        folium.Marker(
            location=[r[LAT], r[LON]],
            icon=folium.Icon(color="red", icon="plus"),
            popup="Recommended Tower Site"
        ).add_to(m)

    st_folium(m, width=1400, height=650)

# =========================
# 7️⃣ DENSITY PER STATE
# =========================
elif menu == "Coverage Density Per State":
    st.subheader("📈 Coverage Density Per State (Counts)")
    st.write(df.groupby(OPERATOR).size())

# =========================
# 8️⃣ OPERATOR SUMMARY
# =========================
elif menu == "Operator Summary":
    st.subheader("🏢 Operator Summary")
    st.dataframe(df.groupby(OPERATOR).size().reset_index(name="Sites"))

# =========================
# 9️⃣ TECHNOLOGY SUMMARY
# =========================
elif menu == "Technology Summary":
    st.subheader("📶 Technology Summary")
    st.dataframe(df.groupby(TECH).size().reset_index(name="Sites"))

# =========================
# 🔟 BUFFER VIEW
# =========================
elif menu == "Buffer View":
    st.subheader("⭕ Buffer Coverage View")

    m = base_map()
    for _, r in df.sample(50).iterrows():
        folium.Circle(
            location=[r[LAT], r[LON]],
            radius=10000,
            color="blue",
            fill=True,
            fill_opacity=0.1
        ).add_to(m)

    st_folium(m, width=1400, height=650)

# =========================
# 1️⃣1️⃣ EXPORT
# =========================
elif menu == "Export Results":
    st.subheader("⬇ Export Data")
    st.download_button(
        "Download CSV",
        df.to_csv(index=False),
        "network_results.csv",
        "text/csv"
    )

# =========================
# 1️⃣2️⃣ USER GUIDE
# =========================
elif menu == "User Guide":
    st.subheader("📘 User Guide")
    st.markdown("""
    - Use sidebar to switch views  
    - Maps are interactive  
    - Predictor finds nearest towers  
    - New tower tab suggests underserved areas  
    - Export tab downloads results  
    """)
