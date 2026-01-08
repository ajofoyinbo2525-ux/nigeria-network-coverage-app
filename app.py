import streamlit as st
import pandas as pd
import folium
from geopy.distance import geodesic
from streamlit_folium import st_folium

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="Nigeria Network Coverage & Planning",
    layout="wide"
)

st.title("📡 Nigeria Network Coverage & Planning Dashboard")

# -------------------------------------------------
# SESSION STATE (PERSIST RESULTS)
# -------------------------------------------------
if "analyzed" not in st.session_state:
    st.session_state.analyzed = False

# -------------------------------------------------
# LOAD DATA
# -------------------------------------------------
@st.cache_data
def load_data():
    return pd.read_csv("Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv")

df = load_data()
df.columns = df.columns.str.lower()

lat_col = [c for c in df.columns if "lat" in c][0]
lon_col = [c for c in df.columns if "lon" in c][0]
operator_col = [c for c in df.columns if "operator" in c][0]
tech_col = [c for c in df.columns if "2g" in c or "3g" in c or "4g" in c or "tech" in c or "gen" in c][0]

state_col = None
for c in df.columns:
    if c in ["state", "admin1", "region"]:
        state_col = c
        break

# -------------------------------------------------
# SIDEBAR INPUT
# -------------------------------------------------
st.sidebar.header("📍 Location Input")

lat = st.sidebar.number_input("Latitude", value=6.5244, format="%.6f")
lon = st.sidebar.number_input("Longitude", value=3.3792, format="%.6f")

radius_km = st.sidebar.slider("Analysis Radius (km)", 5, 100, 20)

if st.sidebar.button("🔍 Run Analysis"):
    st.session_state.analyzed = True
    st.session_state.lat = lat
    st.session_state.lon = lon
    st.session_state.radius = radius_km

# -------------------------------------------------
# TABS (11)
# -------------------------------------------------
tabs = st.tabs([
    "🗺 Coverage Map",
    "📊 Results Table",
    "🏢 Operator Summary",
    "📡 Technology Summary",
    "⭕ Buffer View",
    "📈 Coverage Confidence",
    "🚫 Coverage Gaps",
    "❌ No Coverage",
    "🏗 Tower Recommendation",
    "🏙 State Density",
    "📥 Export Center"
])

# -------------------------------------------------
# RUN ANALYSIS
# -------------------------------------------------
if st.session_state.analyzed:

    lat0 = st.session_state.lat
    lon0 = st.session_state.lon
    radius_km = st.session_state.radius

    df["distance_km"] = df.apply(
        lambda r: geodesic(
            (lat0, lon0),
            (r[lat_col], r[lon_col])
        ).km,
        axis=1
    )

    nearby = df[df["distance_km"] <= radius_km].copy()

    nearby["confidence"] = nearby["distance_km"].apply(
        lambda d: "High" if d <= 5 else "Medium" if d <= 15 else "Low"
    )

    # -------------------------------------------------
    # TAB 1: MAP
    # -------------------------------------------------
    with tabs[0]:
        m = folium.Map(location=[lat0, lon0], zoom_start=10)

        folium.Marker(
            [lat0, lon0],
            popup="Input Location",
            icon=folium.Icon(color="red")
        ).add_to(m)

        folium.Circle(
            [lat0, lon0],
            radius=radius_km * 1000,
            color="blue",
            fill=True,
            fill_opacity=0.15
        ).add_to(m)

        for _, r in nearby.iterrows():
            folium.CircleMarker(
                [r[lat_col], r[lon_col]],
                radius=4,
                popup=f"{r[operator_col]} | {r[tech_col]} | {r['distance_km']:.2f} km",
                color="green"
            ).add_to(m)

        st_folium(m, height=650, width="100%")

    # -------------------------------------------------
    # TAB 2: TABLE
    # -------------------------------------------------
    with tabs[1]:
        st.dataframe(
            nearby[[operator_col, tech_col, "distance_km", "confidence"]]
            .sort_values("distance_km")
        )

    # -------------------------------------------------
    # TAB 3: OPERATOR SUMMARY
    # -------------------------------------------------
    with tabs[2]:
        st.dataframe(
            nearby.groupby(operator_col).size().reset_index(name="site_count")
        )

    # -------------------------------------------------
    # TAB 4: TECHNOLOGY SUMMARY
    # -------------------------------------------------
    with tabs[3]:
        st.dataframe(
            nearby.groupby(tech_col).size().reset_index(name="site_count")
        )

    # -------------------------------------------------
    # TAB 5: BUFFER VIEW
    # -------------------------------------------------
    with tabs[4]:
        st.success(f"Buffer radius: {radius_km} km")
        st.write(f"Sites inside buffer: {len(nearby)}")

    # -------------------------------------------------
    # TAB 6: CONFIDENCE
    # -------------------------------------------------
    with tabs[5]:
        st.dataframe(
            nearby.groupby("confidence").size().reset_index(name="count")
        )

    # -------------------------------------------------
    # TAB 7: COVERAGE GAPS
    # -------------------------------------------------
    with tabs[6]:
        if nearby.empty:
            st.error("No coverage detected in this radius")
        else:
            st.warning("Partial coverage detected")

    # -------------------------------------------------
    # TAB 8: NO COVERAGE
    # -------------------------------------------------
    with tabs[7]:
        st.write("No-coverage logic based on empty radius result")

    # -------------------------------------------------
    # TAB 9: TOWER RECOMMENDATION
    # -------------------------------------------------
    with tabs[8]:
        rec_df = pd.DataFrame([{
            "recommended_lat": lat0,
            "recommended_lon": lon0,
            "reason": "Improve coverage in low density area"
        }])
        st.dataframe(rec_df)

    # -------------------------------------------------
    # TAB 10: STATE DENSITY
    # -------------------------------------------------
    with tabs[9]:
        if state_col:
            st.dataframe(
                df.groupby(state_col).size().reset_index(name="site_count")
            )
        else:
            st.info("State column not available")

    # -------------------------------------------------
    # TAB 11: EXPORT
    # -------------------------------------------------
    with tabs[10]:
        st.download_button(
            "⬇ Export Nearby Sites",
            nearby.to_csv(index=False),
            "nearby_sites.csv",
            "text/csv"
        )

else:
    st.info("👈 Enter coordinates and click *Run Analysis*")
