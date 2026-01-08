import streamlit as st
import pandas as pd
import folium
import json
import os
from geopy.distance import geodesic

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Nigeria Network Coverage & Planning",
    layout="wide"
)

st.title("📡 Nigeria Network Coverage & Planning Dashboard")

# ---------------- UTILS ----------------
def find_file(filename):
    for root, _, files in os.walk("."):
        if filename in files:
            return os.path.join(root, filename)
    return None

# ---------------- LOAD GEOJSON ----------------
nga0_path = find_file("gadm41_NGA_0.geojson")
nga1_path = find_file("gadm41_NGA_1.geojson")

nigeria_geo = None
states_geo = None

if nga0_path:
    with open(nga0_path, "r", encoding="utf-8") as f:
        nigeria_geo = json.load(f)

if nga1_path:
    with open(nga1_path, "r", encoding="utf-8") as f:
        states_geo = json.load(f)

# ---------------- SESSION STATE ----------------
if "run" not in st.session_state:
    st.session_state.run = False

# ---------------- LOAD NETWORK DATA ----------------
@st.cache_data
def load_data():
    return pd.read_csv("Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv")

try:
    df = load_data()
except:
    st.error("❌ Network CSV not found.")
    st.stop()

df.columns = df.columns.str.lower()

lat_col = [c for c in df.columns if "lat" in c][0]
lon_col = [c for c in df.columns if "lon" in c][0]
operator_col = [c for c in df.columns if "operator" in c][0]
tech_col = [c for c in df.columns if "gen" in c or "tech" in c][0]

# ---------------- SIDEBAR ----------------
st.sidebar.header("📍 Location Input")

lat = st.sidebar.number_input("Latitude", value=6.5244, format="%.6f")
lon = st.sidebar.number_input("Longitude", value=3.3792, format="%.6f")

mode = st.sidebar.radio(
    "Distance Mode",
    ["No Distance Limit", "Limit by Radius"]
)

radius_km = None
if mode == "Limit by Radius":
    radius_km = st.sidebar.slider("Radius (km)", 5, 200, 30)

if st.sidebar.button("🔍 Run Analysis"):
    st.session_state.run = True
    st.session_state.lat = lat
    st.session_state.lon = lon
    st.session_state.radius = radius_km
    st.session_state.mode = mode

# ---------------- TABS ----------------
tabs = st.tabs([
    "🗺 Coverage Map",
    "📊 Results",
    "🎯 Buffer",
    "🚫 Coverage Gaps",
    "🏗 Tower Recommendation",
    "🏙 Operator Summary",
    "🗾 State Boundaries",
    "📥 Export",
    "📘 User Guide"
])

# ---------------- ANALYSIS ----------------
if st.session_state.run:

    lat0 = st.session_state.lat
    lon0 = st.session_state.lon
    radius_km = st.session_state.radius
    mode = st.session_state.mode

    df["distance_km"] = df.apply(
        lambda r: geodesic((lat0, lon0), (r[lat_col], r[lon_col])).km,
        axis=1
    )

    nearby = df if mode == "No Distance Limit" else df[df["distance_km"] <= radius_km]

    nearby["confidence"] = nearby["distance_km"].apply(
        lambda d: "High" if d <= 5 else "Medium" if d <= 20 else "Low"
    )

    # ---------------- TAB 1: MAP ----------------
    with tabs[0]:
        m = folium.Map(location=[lat0, lon0], zoom_start=6)

        # Nigeria Boundary
        if nigeria_geo:
            folium.GeoJson(
                nigeria_geo,
                name="Nigeria Boundary",
                style_function=lambda x: {
                    "fillOpacity": 0,
                    "color": "black",
                    "weight": 2
                }
            ).add_to(m)

        # State Boundaries
        if states_geo:
            folium.GeoJson(
                states_geo,
                name="States",
                style_function=lambda x: {
                    "fillOpacity": 0,
                    "color": "gray",
                    "weight": 1
                }
            ).add_to(m)

        folium.Marker(
            [lat0, lon0],
            popup="Input Location",
            icon=folium.Icon(color="red")
        ).add_to(m)

        if radius_km:
            folium.Circle(
                [lat0, lon0],
                radius=radius_km * 1000,
                color="blue",
                fill=True,
                fill_opacity=0.1
            ).add_to(m)

        colors = {
            "mtn": "yellow",
            "airtel": "red",
            "glo": "green",
            "9mobile": "blue"
        }

        for _, r in nearby.iterrows():
            color = colors.get(str(r[operator_col]).lower(), "gray")
            folium.CircleMarker(
                [r[lat_col], r[lon_col]],
                radius=4,
                color=color,
                fill=True,
                fill_opacity=0.7,
                popup=f"""
                Operator: {r[operator_col]}<br>
                Tech: {r[tech_col]}<br>
                Distance: {r['distance_km']:.2f} km<br>
                Confidence: {r['confidence']}
                """
            ).add_to(m)

        st.components.v1.html(m.repr_html(), height=650)

    # ---------------- TAB 2: RESULTS ----------------
    with tabs[1]:
        st.dataframe(
            nearby[[operator_col, tech_col, "distance_km", "confidence"]]
            .sort_values("distance_km")
        )

    # ---------------- TAB 3: BUFFER ----------------
    with tabs[2]:
        st.write(f"Total sites found: {len(nearby)}")
        st.dataframe(
            nearby[[operator_col, tech_col, "distance_km"]]
            .sort_values("distance_km")
            .head(25)
        )

    # ---------------- TAB 4: GAPS ----------------
    with tabs[3]:
        status = "No Coverage" if nearby.empty else "Partial / Covered"
        st.success(f"Coverage Status: {status}")

    # ---------------- TAB 5: TOWER ----------------
    with tabs[4]:
        st.markdown("### 📍 Recommended Tower Location")
        st.write(f"Latitude: {lat0 + 0.02}")
        st.write(f"Longitude: {lon0 + 0.02}")

    # ---------------- TAB 6: OPERATOR SUMMARY ----------------
    with tabs[5]:
        summary = nearby.groupby(operator_col).size().reset_index(name="sites")
        st.dataframe(summary)
        st.bar_chart(summary.set_index(operator_col))

    # ---------------- TAB 7: STATES ----------------
    with tabs[6]:
        st.info("State boundaries displayed on map")

    # ---------------- TAB 8: EXPORT ----------------
    with tabs[7]:
        st.download_button(
            "⬇ Export Results",
            nearby.to_csv(index=False),
            "network_results.csv"
        )

    # ---------------- TAB 9: GUIDE ----------------
    with tabs[8]:
        st.markdown("""
        *How to use*
        1. Enter coordinates
        2. Choose distance mode
        3. Run analysis
        4. Explore maps and tables
        """)

else:
    st.info("👈 Enter coordinates and click Run Analysis")
