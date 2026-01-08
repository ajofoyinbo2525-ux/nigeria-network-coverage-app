import streamlit as st
import pandas as pd
import folium
from geopy.distance import geodesic
from streamlit_folium import st_folium
import json

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="Nigeria Network Coverage & Planning",
    layout="wide"
)

st.title("📡 Nigeria Network Coverage & Planning Dashboard")

# ---------------- CACHE LOADERS ----------------
@st.cache_data
def load_network_data():
    df = pd.read_csv("Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv")
    df.columns = df.columns.str.lower()
    return df

@st.cache_data
def load_geojson(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ---------------- LOAD DATA ----------------
df = load_network_data()
nga_boundary = load_geojson("gadm41_NGA_0.geojson")
nga_states = load_geojson("gadm41_NGA_1.geojson")

# Detect columns safely
lat_col = [c for c in df.columns if "lat" in c][0]
lon_col = [c for c in df.columns if "lon" in c][0]
operator_col = [c for c in df.columns if "operator" in c][0]
tech_col = [c for c in df.columns if "gen" in c or "tech" in c][0]

state_col = next((c for c in df.columns if c in ["state", "admin1", "region"]), None)

# ---------------- SIDEBAR ----------------
st.sidebar.header("📍 Location Input")

lat0 = st.sidebar.number_input("Latitude", value=6.5244, format="%.6f")
lon0 = st.sidebar.number_input("Longitude", value=3.3792, format="%.6f")

no_limit = st.sidebar.checkbox("🚀 No Distance Limit", value=True)

radius = None
if not no_limit:
    radius = st.sidebar.slider("Radius (km)", 5, 100, 20)

run = st.sidebar.button("▶ Run Analysis")

# ---------------- TABS ----------------
tabs = st.tabs([
    "🗺 Coverage Map",
    "🚫 No Coverage Map",
    "📊 Network Result Table",
    "📡 Network Predictor",
    "⚠ Coverage Gaps Analyzer",
    "🏗 New Tower Recommendation",
    "📥 Export Results",
    "🏢 Operator Summary",
    "📶 Technology Summary",
    "⭕ Buffer View",
    "🗾 Coverage Density (State)",
    "📘 User Guide"
])

# ---------------- RUN ANALYSIS ----------------
if run:

    # Distance calculation
    df["distance_km"] = df.apply(
        lambda r: geodesic((lat0, lon0), (r[lat_col], r[lon_col])).km,
        axis=1
    )

    if no_limit:
        nearby = df.copy()
    else:
        nearby = df[df["distance_km"] <= radius].copy()

    nearest_distance = df["distance_km"].min()

    # ================= TAB 1 =================
    with tabs[0]:
        m = folium.Map([lat0, lon0], zoom_start=7, tiles="cartodbpositron")

        folium.GeoJson(nga_boundary, name="Nigeria").add_to(m)
        folium.GeoJson(nga_states, name="States").add_to(m)

        folium.Marker(
            [lat0, lon0],
            icon=folium.Icon(color="red"),
            popup="Input Location"
        ).add_to(m)

        for _, r in nearby.iterrows():
            folium.CircleMarker(
                [r[lat_col], r[lon_col]],
                radius=3,
                popup=f"{r[operator_col]} | {r[tech_col]}",
                color="green"
            ).add_to(m)

        st_folium(m, height=600, use_container_width=True)

    # ================= TAB 2 =================
    with tabs[1]:
        m2 = folium.Map([lat0, lon0], zoom_start=7)

        folium.GeoJson(nga_boundary).add_to(m2)

        folium.Circle(
            [lat0, lon0],
            radius=50000,
            color="red",
            fill=True,
            fill_opacity=0.4,
            popup="NO COVERAGE AREA"
        ).add_to(m2)

        st_folium(m2, height=600, use_container_width=True)

    # ================= TAB 3 =================
    with tabs[2]:
        st.dataframe(
            nearby[[operator_col, tech_col, "distance_km"]]
            .sort_values("distance_km"),
            use_container_width=True
        )

    # ================= TAB 4 =================
    with tabs[3]:
        if nearby.empty:
            st.error("❌ No network detected")
            st.write(f"Nearest network is *{nearest_distance:.2f} km* away")
        else:
            nearest = nearby.sort_values("distance_km").iloc[0]
            st.success("✅ Network Available")
            st.metric("Operator", nearest[operator_col])
            st.metric("Technology", nearest[tech_col])
            st.metric("Distance (km)", f"{nearest.distance_km:.2f}")

    # ================= TAB 5 =================
    with tabs[4]:
        if nearby.empty:
            st.error("NO COVERAGE GAP")
            st.write(f"Nearest site: *{nearest_distance:.2f} km*")
        else:
            st.warning("PARTIAL COVERAGE")
            st.write(f"Sites found: *{len(nearby)}*")

    # ================= TAB 6 =================
    with tabs[5]:
        if nearby.empty:
            rec_lat, rec_lon = lat0, lon0
            reason = "No network coverage"
        else:
            rec_lat, rec_lon = lat0 + 0.02, lon0 + 0.02
            reason = "Weak coverage"

        st.success("Recommended Tower Location")
        st.write(f"Latitude: {rec_lat}")
        st.write(f"Longitude: {rec_lon}")
        st.write(f"Reason: {reason}")

        m3 = folium.Map([rec_lat, rec_lon], zoom_start=9)
        folium.Marker([rec_lat, rec_lon], icon=folium.Icon(color="green")).add_to(m3)
        st_folium(m3, height=500, use_container_width=True)

    # ================= TAB 7 =================
    with tabs[6]:
        st.download_button(
            "Download Network Results",
            nearby.to_csv(index=False),
            "network_results.csv"
        )

    # ================= TAB 8 =================
    with tabs[7]:
        st.dataframe(
            df.groupby(operator_col).size().reset_index(name="count"),
            use_container_width=True
        )

    # ================= TAB 9 =================
    with tabs[8]:
        st.dataframe(
            df.groupby(tech_col).size().reset_index(name="count"),
            use_container_width=True
        )

    # ================= TAB 10 =================
    with tabs[9]:
        m4 = folium.Map([lat0, lon0], zoom_start=8)
        folium.Circle([lat0, lon0], radius=30000, fill=True).add_to(m4)
        st_folium(m4, height=600, use_container_width=True)

    # ================= TAB 11 =================
    with tabs[10]:
        if state_col:
            density = df.groupby(state_col).size().reset_index(name="sites")
            st.bar_chart(density.set_index(state_col))
        else:
            st.warning("State column not available")

    # ================= TAB 12 =================
    with tabs[11]:
        st.markdown("""
        ### How to use this app
        1. Enter latitude & longitude
        2. Choose distance or no limit
        3. Click *Run Analysis*
        4. Navigate tabs (scroll right if hidden)
        """)

else:
    st.info("👈 Enter coordinates and click *Run Analysis*")
