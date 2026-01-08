import streamlit as st
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
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ================= LOAD DATA =================
try:
    df = load_csv()
except:
    st.error("❌ Network CSV not found")
    st.stop()

try:
    nigeria_geo = load_geo(NGA0)
    states_geo = load_geo(NGA1)
except:
    st.error("❌ GeoJSON files not found")
    st.stop()

required = ["Latitude", "Longitude", "Network_Operator", "Network_Generation"]
for c in required:
    if c not in df.columns:
        st.error(f"❌ Missing column: {c}")
        st.stop()

# ================= SESSION =================
if "run" not in st.session_state:
    st.session_state.run = False

# ================= SIDEBAR =================
st.sidebar.header("📍 Location Input")
lat = st.sidebar.number_input("Latitude", value=6.5244, format="%.6f")
lon = st.sidebar.number_input("Longitude", value=3.3792, format="%.6f")
radius = st.sidebar.slider("Analysis Radius (km)", 5, 200, 20)
no_limit = st.sidebar.checkbox("No distance limit")

if st.sidebar.button("🔍 Analyze Location"):
    st.session_state.run = True
    st.session_state.lat = lat
    st.session_state.lon = lon
    st.session_state.radius = radius
    st.session_state.no_limit = no_limit

# ================= TABS =================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🗺 Coverage Analysis",
    "⚠ Gap & Planning",
    "📊 Statistics",
    "📥 Export",
    "📘 User Guide"
])

# ================= ANALYSIS =================
if st.session_state.run:
    lat0 = st.session_state.lat
    lon0 = st.session_state.lon

    df["distance_km"] = df.apply(
        lambda r: geodesic((lat0, lon0), (r["Latitude"], r["Longitude"])).km,
        axis=1
    )

    if st.session_state.no_limit:
        nearby = df.copy()
    else:
        nearby = df[df["distance_km"] <= st.session_state.radius].copy()

    nearby["confidence"] = nearby["distance_km"].apply(
        lambda d: "High" if d <= 5 else "Medium" if d <= 20 else "Low"
    )

    # ================= TAB 1 =================
    with tab1:
        st.subheader("Coverage & No-Coverage Map")

        m = folium.Map(location=[lat0, lon0], zoom_start=7)
        folium.GeoJson(nigeria_geo, name="Nigeria").add_to(m)

        # Input point
        folium.Marker(
            [lat0, lon0],
            popup="Input Location",
            icon=folium.Icon(color="black")
        ).add_to(m)

        # Analysis radius
        if not st.session_state.no_limit:
            folium.Circle(
                [lat0, lon0],
                radius=st.session_state.radius * 1000,
                color="blue",
                fill=False
            ).add_to(m)

        # Network sites
        for _, r in nearby.iterrows():
            op = str(r["Network_Operator"]).upper()
            folium.CircleMarker(
                [r["Latitude"], r["Longitude"]],
                radius=5,
                color=OPERATOR_COLORS.get(op, "gray"),
                fill=True,
                fill_opacity=0.8,
                popup=f"""
                Operator: {op}<br>
                Technology: {r['Network_Generation']}<br>
                Distance: {r['distance_km']:.2f} km<br>
                Confidence: {r['confidence']}
                """
            ).add_to(m)

        # NO COVERAGE VISUAL
        if nearby.empty:
            folium.Circle(
                [lat0, lon0],
                radius=30000,
                color="red",
                fill=True,
                fill_opacity=0.2,
                popup="NO NETWORK COVERAGE AREA"
            ).add_to(m)

        st_folium(m, height=650, width="100%")

        st.subheader("Network Predictor Result")
        if nearby.empty:
            st.error("❌ No network coverage detected")
        else:
            st.dataframe(
                nearby[[
                    "Network_Operator",
                    "Network_Generation",
                    "distance_km",
                    "confidence"
                ]].sort_values("distance_km")
            )

    # ================= TAB 2 =================
    with tab2:
        st.subheader("Coverage Gap & New Tower Recommendation")

        if nearby.empty:
            nearest = df.sort_values("distance_km").iloc[0]
            st.error("NO COVERAGE")
            st.write(f"Nearest network is *{nearest['distance_km']:.2f} km* away")

            rec_lat, rec_lon = lat0, lon0
            reason = "No coverage detected"
        else:
            rec_lat, rec_lon = lat0 + 0.02, lon0 + 0.02
            reason = "Coverage reinforcement"

        rec_df = pd.DataFrame([{
            "Recommended_Latitude": rec_lat,
            "Recommended_Longitude": rec_lon,
            "Reason": reason
        }])

        st.dataframe(rec_df)

    # ================= TAB 3 =================
    with tab3:
        st.subheader("Operator Summary")
        st.bar_chart(df["Network_Operator"].value_counts())

        st.subheader("Technology Summary")
        st.bar_chart(df["Network_Generation"].value_counts())

        if "State" in df.columns:
            st.subheader("Coverage Density per State")
            st.bar_chart(df["State"].value_counts())

    # ================= TAB 4 =================
    with tab4:
        st.download_button(
            "⬇ Export Network Results",
            nearby.to_csv(index=False),
            "network_results.csv"
        )
        st.download_button(
            "⬇ Export Tower Recommendation",
            rec_df.to_csv(index=False),
            "recommended_tower.csv"
        )

    # ================= TAB 5 =================
    with tab5:
        st.markdown("""
        ### How to use
        - Enter coordinates
        - Select radius or no distance limit
        - Click Analyze
        - View coverage, gaps & recommendations
        """)

else:
    st.info("👈 Enter coordinates and click Analyze Location")
