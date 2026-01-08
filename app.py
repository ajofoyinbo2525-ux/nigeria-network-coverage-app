import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Nigeria Network Coverage", layout="wide")
st.title("📡 Nigeria Network Coverage & Planning Dashboard")

# ================= SESSION =================
if "analyzed" not in st.session_state:
    st.session_state.analyzed = False

# ================= LOAD DATA =================
@st.cache_data
def load_data():
    return pd.read_csv("Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv")

df = load_data()
df.columns = df.columns.str.lower()

lat_col = "latitude"
lon_col = "longitude"
operator_col = "network_operator"
tech_col = "network_generation"

# ================= FAST HAVERSINE =================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)*2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)*2
    return 2 * R * np.arcsin(np.sqrt(a))

# ================= SIDEBAR =================
st.sidebar.header("📍 Input Coordinates")

lat0 = st.sidebar.number_input("Latitude", 6.5244, format="%.6f")
lon0 = st.sidebar.number_input("Longitude", 3.3792, format="%.6f")
radius = st.sidebar.slider("Analysis Radius (km)", 5, 200, 30)
no_limit = st.sidebar.checkbox("🔓 No Distance Limit")

if st.sidebar.button("🔍 Run Analysis"):
    st.session_state.analyzed = True
    st.session_state.lat0 = lat0
    st.session_state.lon0 = lon0
    st.session_state.radius = radius
    st.session_state.no_limit = no_limit

# ================= TABS =================
tabs = st.tabs([
    "🗺 Coverage Map",
    "🚫 No Coverage Map",
    "📊 Network Results",
    "🧠 Network Predictor",
    "🚨 Coverage Gaps",
    "🏗 New Tower Recommendation",
    "📥 Export Results",
    "📘 User Guide"
])

# ================= ANALYSIS =================
if st.session_state.analyzed:

    lat0 = st.session_state.lat0
    lon0 = st.session_state.lon0

    df["distance_km"] = haversine(lat0, lon0, df[lat_col], df[lon_col])

    if st.session_state.no_limit:
        nearby = df.copy()
    else:
        nearby = df[df["distance_km"] <= st.session_state.radius].copy()

    nearest_distance = df["distance_km"].min()

    # ================= TAB 1: COVERAGE MAP =================
    with tabs[0]:
        m = folium.Map([lat0, lon0], zoom_start=10)

        folium.Marker(
            [lat0, lon0],
            popup="Input Location",
            icon=folium.Icon(color="red")
        ).add_to(m)

        folium.Circle(
            [lat0, lon0],
            radius=radius * 1000,
            color="blue",
            fill=True,
            fill_opacity=0.1
        ).add_to(m)

        for _, r in nearby.iterrows():
            folium.CircleMarker(
                [r[lat_col], r[lon_col]],
                radius=4,
                popup=f"{r[operator_col]} | {r[tech_col]} | {r.distance_km:.1f} km"
            ).add_to(m)

        st_folium(m, height=550)

    # ================= TAB 2: NO COVERAGE MAP =================
    with tabs[1]:
        m2 = folium.Map([lat0, lon0], zoom_start=10)

        folium.Marker(
            [lat0, lon0],
            popup="Input Location",
            icon=folium.Icon(color="red")
        ).add_to(m2)

        if nearby.empty:
            folium.Circle(
                [lat0, lon0],
                radius=radius * 1000,
                color="red",
                fill=True,
                fill_opacity=0.3
            ).add_to(m2)

            st.error("❌ NO NETWORK COVERAGE FOUND")
            st.write(f"📏 Nearest existing network is *{nearest_distance:.2f} km* away")

        else:
            st.success("✅ Coverage exists within selected radius")

        st_folium(m2, height=550)

    # ================= TAB 3: RESULTS TABLE =================
    with tabs[2]:
        if nearby.empty:
            st.warning("No network results")
        else:
            nearby["confidence"] = nearby["distance_km"].apply(
                lambda d: "High" if d <= 5 else "Medium" if d <= 15 else "Low"
            )

            st.dataframe(
                nearby[[operator_col, tech_col, "distance_km", "confidence"]]
                .sort_values("distance_km")
            )

    # ================= TAB 4: NETWORK PREDICTOR =================
    with tabs[3]:
        if nearby.empty:
            st.error("No coverage to predict from")
        else:
            st.metric("Best Operator", nearby[operator_col].mode()[0])
            st.metric("Best Technology", nearby[tech_col].mode()[0])

    # ================= TAB 5: COVERAGE GAPS =================
    with tabs[4]:
        if nearby.empty:
            st.error("Severe Coverage Gap Detected")
        elif nearby["distance_km"].min() > 20:
            st.warning("Partial Coverage Gap")
        else:
            st.success("Good Coverage")

    # ================= TAB 6: NEW TOWER =================
    with tabs[5]:
        if nearby.empty:
            st.success("🏗 New Tower Recommended")
            st.write("📍 Location:", lat0, lon0)
            st.write("📡 Suggested Technology: 4G")
            st.write(f"📏 Nearest Network: {nearest_distance:.2f} km away")
            st.write("📄 Reason: No coverage detected in this area")
        else:
            st.info("Existing coverage available — tower may not be required")

    # ================= TAB 7: EXPORT =================
    with tabs[6]:
        if not nearby.empty:
            st.download_button(
                "⬇ Export Network Results",
                nearby.to_csv(index=False),
                "network_results.csv",
                "text/csv"
            )

    # ================= TAB 8: USER GUIDE =================
    with tabs[7]:
        st.markdown("""
        *How to use this app*
        1. Enter coordinates
        2. Select radius or enable no distance limit
        3. Click Run Analysis
        4. Review coverage, gaps & recommendations
        """)

else:
    st.info("👈 Enter coordinates and click *Run Analysis*")
