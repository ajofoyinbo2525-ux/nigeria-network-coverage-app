import streamlit as st
import pandas as pd
import folium
import numpy as np
from geopy.distance import geodesic
from streamlit_folium import st_folium
from math import cos, sin, radians

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Nigeria Network Coverage & Planning", layout="wide")
st.title("📡 Nigeria Network Coverage, Gap Analysis & 5G Planning Dashboard")

# ---------------- SESSION ----------------
if "run" not in st.session_state:
    st.session_state.run = False

# ---------------- LOAD DATA ----------------
@st.cache_data
def load_data():
    return pd.read_csv("Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv")

df = load_data()
df.columns = df.columns.str.lower()

lat_col = [c for c in df.columns if "lat" in c][0]
lon_col = [c for c in df.columns if "lon" in c][0]
operator_col = [c for c in df.columns if "operator" in c][0]
tech_col = [c for c in df.columns if "gen" in c or "tech" in c][0]

state_col = next((c for c in df.columns if c in ["state", "admin1", "region"]), None)

# ---------------- UTILS ----------------
def destination_point(lat, lon, km, bearing):
    R = 6371
    brng = radians(bearing)
    lat1 = radians(lat)
    lon1 = radians(lon)

    lat2 = np.arcsin(
        np.sin(lat1) * np.cos(km / R)
        + np.cos(lat1) * np.sin(km / R) * np.cos(brng)
    )
    lon2 = lon1 + np.arctan2(
        np.sin(brng) * np.sin(km / R) * np.cos(lat1),
        np.cos(km / R) - np.sin(lat1) * np.sin(lat2)
    )

    return np.degrees(lat2), np.degrees(lon2)

def operator_color(op, tech):
    tech = str(tech).lower()
    op = str(op).lower()
    if "5g" in tech:
        return "purple"
    if "mtn" in op:
        return "orange"
    if "airtel" in op:
        return "red"
    if "glo" in op:
        return "green"
    if "9" in op:
        return "darkgreen"
    return "blue"

# ---------------- SIDEBAR ----------------
st.sidebar.header("📍 Location Input")
lat0 = st.sidebar.number_input("Latitude", value=6.5244, format="%.6f")
lon0 = st.sidebar.number_input("Longitude", value=3.3792, format="%.6f")

radius_km = st.sidebar.slider("Analysis Radius (km)", 5, 200, 20)
no_limit = st.sidebar.checkbox("🚀 No Distance Limit")

if st.sidebar.button("🔍 Run Analysis"):
    st.session_state.run = True

# ---------------- TABS (11) ----------------
tabs = st.tabs([
    "🗺 Coverage Map",
    "📊 Results Table",
    "📥 Export Results",
    "🏗 New Tower Recommendation",
    "🏙 State Density",
    "🚫 Coverage Gaps",
    "📡 Sector Coverage",
    "🚧 Sector Tower Planning",
    "📘 User Guide",
    "🟣 5G Coverage",
    "🚀 5G Rollout Plan"
])

# ---------------- ANALYSIS ----------------
if st.session_state.run:

    df["distance_km"] = df.apply(
        lambda r: geodesic((lat0, lon0), (r[lat_col], r[lon_col])).km,
        axis=1
    )

    nearby = df if no_limit else df[df["distance_km"] <= radius_km]
    nearby = nearby.copy()

    # ---------------- TAB 1 ----------------
    with tabs[0]:
        m = folium.Map(location=[lat0, lon0], zoom_start=11)
        folium.Marker([lat0, lon0], icon=folium.Icon(color="red"), popup="Input").add_to(m)
        folium.Circle([lat0, lon0], radius=radius_km * 1000, color="blue", fill_opacity=0.1).add_to(m)

        for _, r in nearby.iterrows():
            folium.CircleMarker(
                [r[lat_col], r[lon_col]],
                radius=4,
                color=operator_color(r[operator_col], r[tech_col]),
                popup=f"{r[operator_col]} | {r[tech_col]} | {r['distance_km']:.2f} km"
            ).add_to(m)

        st_folium(m, height=600)

    # ---------------- TAB 2 ----------------
    with tabs[1]:
        st.dataframe(nearby[[operator_col, tech_col, "distance_km"]].sort_values("distance_km"))

    # ---------------- TAB 3 ----------------
    with tabs[2]:
        st.download_button("⬇ Export Network CSV", nearby.to_csv(index=False), "network_results.csv")

    # ---------------- TAB 4 ----------------
    with tabs[3]:
        rec_lat, rec_lon = lat0 + 0.02, lon0 + 0.02
        tower_df = pd.DataFrame([{
            "recommended_lat": rec_lat,
            "recommended_lon": rec_lon,
            "reason": "Coverage improvement / gap fill"
        }])
        st.dataframe(tower_df)
        st.download_button("⬇ Export Tower Recommendation", tower_df.to_csv(index=False), "tower_recommendation.csv")

    # ---------------- TAB 5 ----------------
    with tabs[4]:
        if state_col:
            density = df.groupby(state_col).size().reset_index(name="site_count")
            st.dataframe(density.sort_values("site_count", ascending=False))

    # ---------------- TAB 6 ----------------
    with tabs[5]:
        gap = "No Coverage" if nearby.empty else "Partial Coverage"
        gap_df = pd.DataFrame([{
            "latitude": lat0,
            "longitude": lon0,
            "status": gap,
            "network_count": len(nearby)
        }])
        st.dataframe(gap_df)
        st.download_button("⬇ Export Coverage Gap", gap_df.to_csv(index=False), "coverage_gap.csv")

    # ---------------- TAB 7 ----------------
    with tabs[6]:
        sector_map = folium.Map(location=[lat0, lon0], zoom_start=12)
        for i in range(6):
            lat_s, lon_s = destination_point(lat0, lon0, radius_km / 2, i * 60)
            folium.PolyLine([[lat0, lon0], [lat_s, lon_s]]).add_to(sector_map)
        st_folium(sector_map, height=600)

    # ---------------- TAB 8 ----------------
    with tabs[7]:
        sector_plan = []
        for i in range(6):
            lat_s, lon_s = destination_point(lat0, lon0, 1, i * 60)
            sector_plan.append({"sector": i + 1, "lat": lat_s, "lon": lon_s})
        sector_df = pd.DataFrame(sector_plan)
        st.dataframe(sector_df)

    # ---------------- TAB 9 ----------------
    with tabs[8]:
        st.markdown("""
        *How to use this app*
        - Enter coordinates
        - Choose radius or no limit
        - View coverage, gaps & recommendations
        - Export all planning data
        """)

    # ---------------- TAB 10 (5G) ----------------
    with tabs[9]:
        df["is_5g"] = df[tech_col].astype(str).str.contains("5g", case=False)
        fiveg = nearby[nearby["is_5g"]]
        st.write("Detected 5G Sites:", len(fiveg))

    # ---------------- TAB 11 (5G PLAN) ----------------
    with tabs[10]:
        plan = []
        for i in range(6):
            lat_p, lon_p = destination_point(lat0, lon0, 0.8, i * 60)
            plan.append({
                "lat": lat_p,
                "lon": lon_p,
                "band": "n78 (3.5GHz)",
                "type": "Small Cell"
            })
        plan_df = pd.DataFrame(plan)
        st.dataframe(plan_df)
        st.download_button("⬇ Export 5G Plan", plan_df.to_csv(index=False), "5g_plan.csv")

else:
    st.info("👈 Enter coordinates and click Run Analysis")
