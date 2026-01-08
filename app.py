import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from math import cos, sin, radians

# ================= PAGE CONFIG =================
st.set_page_config("Nigeria Network Coverage", layout="wide")
st.title("📡 Nigeria Network Coverage & Planning Dashboard")

# ================= SESSION =================
if "run" not in st.session_state:
    st.session_state.run = False

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
state_col = "state" if "state" in df.columns else None

# ================= FAST DISTANCE =================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(np.radians,[lat1,lon1,lat2,lon2])
    dlat = lat2-lat1
    dlon = lon2-lon1
    a = np.sin(dlat/2)*2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)*2
    return 2*R*np.arcsin(np.sqrt(a))

# ================= SIDEBAR =================
st.sidebar.header("📍 Location Input")

lat0 = st.sidebar.number_input("Latitude", 6.5244, format="%.6f")
lon0 = st.sidebar.number_input("Longitude", 3.3792, format="%.6f")
radius = st.sidebar.slider("Analysis Radius (km)", 5, 200, 30)
no_limit = st.sidebar.checkbox("🔓 No Distance Limit")

if st.sidebar.button("🔍 Run Analysis"):
    st.session_state.run = True
    st.session_state.lat0 = lat0
    st.session_state.lon0 = lon0
    st.session_state.radius = radius
    st.session_state.no_limit = no_limit

# ================= TABS =================
tabs = st.tabs([
    "🗺 Coverage Map",
    "🚫 No Coverage Map",
    "📊 Network Result Table",
    "🧠 Network Predictor",
    "🚨 Coverage Gaps Analyzer",
    "🏗 New Tower Recommendation",
    "📥 Export Results",
    "📦 Operator Summary",
    "📡 Technology Summary",
    "⭕ Buffer View",
    "🏙 Coverage Density per State",
    "📘 User Guide",
    "⚙ Settings"
])

# ================= ANALYSIS =================
if st.session_state.run:

    lat0 = st.session_state.lat0
    lon0 = st.session_state.lon0

    df["distance_km"] = haversine(lat0, lon0, df[lat_col], df[lon_col])

    if st.session_state.no_limit:
        nearby = df.copy()
    else:
        nearby = df[df["distance_km"] <= st.session_state.radius]

    nearby["confidence"] = pd.cut(
        nearby["distance_km"],
        bins=[0,5,15,9999],
        labels=["High","Medium","Low"]
    )

    # ================= TAB 1: COVERAGE MAP =================
    with tabs[0]:
        m = folium.Map([lat0, lon0], zoom_start=10)
        folium.Marker([lat0, lon0], icon=folium.Icon(color="red"), popup="Input Location").add_to(m)

        for _, r in nearby.iterrows():
            folium.CircleMarker(
                [r[lat_col], r[lon_col]],
                radius=4,
                popup=f"{r[operator_col]} | {r[tech_col]} | {r.distance_km:.1f} km"
            ).add_to(m)

        st_folium(m, height=600)

    # ================= TAB 2: NO COVERAGE =================
    with tabs[1]:
        if nearby.empty:
            st.error("❌ NO NETWORK COVERAGE FOUND")
        else:
            st.success("✅ Coverage exists in this area")

    # ================= TAB 3: TABLE =================
    with tabs[2]:
        st.dataframe(
            nearby[[operator_col, tech_col, "distance_km", "confidence"]]
            .sort_values("distance_km")
        )

    # ================= TAB 4: PREDICTOR =================
    with tabs[3]:
        if nearby.empty:
            st.warning("No network to predict")
        else:
            best_op = nearby[operator_col].mode()[0]
            best_tech = nearby[tech_col].mode()[0]
            st.metric("Best Operator", best_op)
            st.metric("Best Technology", best_tech)

    # ================= TAB 5: GAPS =================
    with tabs[4]:
        if nearby.empty:
            st.error("Severe Coverage Gap")
        elif nearby["distance_km"].min() > 20:
            st.warning("Partial Coverage Gap")
        else:
            st.success("Good Coverage")

    # ================= TAB 6: NEW TOWER =================
    with tabs[5]:
        st.write("📍 Recommended Tower Location")
        st.write(f"Latitude: {lat0}")
        st.write(f"Longitude: {lon0}")
        st.write("Suggested Tech: 4G")

    # ================= TAB 7: EXPORT =================
    with tabs[6]:
        st.download_button("⬇ Export Network CSV", nearby.to_csv(index=False), "network.csv")

    # ================= TAB 8: OPERATOR SUMMARY =================
    with tabs[7]:
        st.bar_chart(nearby[operator_col].value_counts())

    # ================= TAB 9: TECHNOLOGY =================
    with tabs[8]:
        st.bar_chart(nearby[tech_col].value_counts())

    # ================= TAB 10: BUFFER + SECTORS =================
    with tabs[9]:
        m = folium.Map([lat0, lon0], zoom_start=10)
        folium.Circle([lat0, lon0], radius=radius*1000, fill=True).add_to(m)

        for angle in range(0,360,45):
            end_lat = lat0 + 0.3*cos(radians(angle))
            end_lon = lon0 + 0.3*sin(radians(angle))
            folium.PolyLine([[lat0,lon0],[end_lat,end_lon]]).add_to(m)

        st_folium(m, height=600)

    # ================= TAB 11: STATE DENSITY =================
    with tabs[10]:
        if state_col:
            density = df.groupby(state_col).size()
            st.bar_chart(density)
        else:
            st.warning("No state column found")

    # ================= TAB 12: USER GUIDE =================
    with tabs[11]:
        st.markdown("""
        *How to use:*
        1. Enter coordinates
        2. Click Run Analysis
        3. View all tabs
        4. Toggle no distance limit if needed
        """)

    # ================= TAB 13: SETTINGS =================
    with tabs[12]:
        st.write("No distance limit:", st.session_state.no_limit)

else:
    st.info("👈 Enter coordinates and click Run Analysis")
