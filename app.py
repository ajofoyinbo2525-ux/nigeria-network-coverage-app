import streamlit as st
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
        st.error(f"❌ Missing column: {col}")
        st.stop()

# ---------------- COLOR MAPS ----------------
OPERATOR_COLORS = {
    "MTN": "yellow",
    "Airtel": "red",
    "Glo": "green",
    "9mobile": "blue"
}

# ---------------- SIDEBAR ----------------
st.sidebar.header("📍 Input Coordinates")

lat = st.sidebar.number_input("Latitude", value=6.5244, format="%.6f")
lon = st.sidebar.number_input("Longitude", value=3.3792, format="%.6f")
radius = st.sidebar.slider("Analysis Radius (km)", 5, 50, 20)

run = st.sidebar.button("🔍 Analyze Location")

# ---------------- SESSION STATE ----------------
if "nearby" not in st.session_state:
    st.session_state.nearby = None

# ---------------- ANALYSIS ----------------
if run:
    df["distance_km"] = df.apply(
        lambda r: geodesic((lat, lon), (r.Latitude, r.Longitude)).km,
        axis=1
    )

    nearby = df[df.distance_km <= radius].copy()

    nearby["confidence"] = nearby.distance_km.apply(
        lambda d: "High" if d <= 5 else "Medium" if d <= 15 else "Low"
    )

    st.session_state.nearby = nearby

# ---------------- TABS ----------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🗺 Coverage Analysis",
    "🚧 Gap & Planning",
    "📊 Statistics",
    "📥 Export",
    "ℹ️ User Guide"
])

# ================= TAB 1: COVERAGE ANALYSIS =================
with tab1:
    if st.session_state.nearby is None:
        st.info("👈 Enter coordinates and click Analyze")
    else:
        st.subheader("📡 Coverage Map")

        m = folium.Map([lat, lon], zoom_start=11)

        folium.Marker(
            [lat, lon],
            tooltip="Input Location",
            icon=folium.Icon(color="black")
        ).add_to(m)

        folium.Circle(
            [lat, lon],
            radius=radius * 1000,
            color="blue",
            fill=True,
            fill_opacity=0.1
        ).add_to(m)

        for _, r in st.session_state.nearby.iterrows():
            folium.CircleMarker(
                [r.Latitude, r.Longitude],
                radius=5,
                color=OPERATOR_COLORS.get(r.Network_Operator, "gray"),
                fill=True,
                fill_opacity=0.8,
                popup=f"""
                Operator: {r.Network_Operator}<br>
                Technology: {r.Network_Generation}<br>
                Distance: {r.distance_km:.2f} km<br>
                Confidence: {r.confidence}
                """
            ).add_to(m)

        st_folium(m, height=550, width="100%")

        st.subheader("🧠 Network Predictor")

        if st.session_state.nearby.empty:
            st.error("❌ No network detected at this location")
        else:
            tech_score = {"2G": 1, "3G": 2, "4G": 3}
            pred = st.session_state.nearby.copy()
            pred["tech_score"] = pred.Network_Generation.map(tech_score)

            summary = pred.groupby("Network_Operator").agg(
                sites=("Network_Operator", "count"),
                avg_distance=("distance_km", "mean"),
                avg_tech=("tech_score", "mean")
            ).reset_index()

            summary["score"] = (
                summary.avg_tech * 0.5 +
                (summary.sites / summary.sites.max()) * 0.3 +
                (1 / (summary.avg_distance + 1)) * 0.2
            )

            best = summary.sort_values("score", ascending=False).iloc[0]

            st.success(f"🏆 Best Network: *{best.Network_Operator}*")
            st.dataframe(summary.sort_values("score", ascending=False))

# ================= TAB 2: GAP & PLANNING =================
with tab2:
    if st.session_state.nearby is None:
        st.info("Run analysis first")
    elif st.session_state.nearby.empty:
        st.error("🚫 NO COVERAGE GAP DETECTED")

        st.markdown(f"""
        *Recommended New Tower Location*
        - Latitude: {lat}
        - Longitude: {lon}
        - Technology: *4G*
        - Operator: *Highest national presence*
        """)
    else:
        farthest = st.session_state.nearby.sort_values("distance_km").iloc[-1]

        st.warning("⚠ Partial Coverage Detected")

        st.markdown(f"""
        *Suggested Expansion Site*
        - Latitude: {farthest.Latitude:.6f}
        - Longitude: {farthest.Longitude:.6f}
        - Operator: {farthest.Network_Operator}
        - Technology: {farthest.Network_Generation}
        - Distance: {farthest.distance_km:.2f} km
        """)

# ================= TAB 3: STATISTICS =================
with tab3:
    if st.session_state.nearby is not None:
        st.subheader("📊 Operator Summary")
        st.bar_chart(st.session_state.nearby.Network_Operator.value_counts())

        st.subheader("📡 Technology Summary")
        st.bar_chart(st.session_state.nearby.Network_Generation.value_counts())

# ================= TAB 4: EXPORT =================
with tab4:
    if st.session_state.nearby is not None:
        st.download_button(
            "⬇ Export Network Results",
            st.session_state.nearby.to_csv(index=False),
            "network_results.csv"
        )

        if st.session_state.nearby.empty:
            tower_df = pd.DataFrame([{
                "Latitude": lat,
                "Longitude": lon,
                "Recommended_Tech": "4G",
                "Reason": "No coverage"
            }])

            st.download_button(
                "⬇ Export Tower Recommendation",
                tower_df.to_csv(index=False),
                "tower_recommendation.csv"
            )

# ================= TAB 5: USER GUIDE =================
with tab5:
    st.markdown("""
    ### How to Use
    1. Enter coordinates
    2. Click *Analyze Location*
    3. View coverage, gaps, and recommendations

    ### Color Coding
    - 🟡 MTN
    - 🔴 Airtel
    - 🟢 Glo
    - 🔵 9mobile

    ### Confidence Levels
    - High: ≤ 5 km
    - Medium: 5–15 km
    - Low: > 15 km
    """)
