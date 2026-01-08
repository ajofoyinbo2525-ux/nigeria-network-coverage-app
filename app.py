import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from math import radians, cos, sin, sqrt, atan2
import json

# -------------------- PAGE CONFIG --------------------
st.set_page_config(
    page_title="Nigeria Network Coverage & Planning App",
    layout="wide"
)

st.title("📡 Nigeria Network Coverage & Planning App")

# -------------------- LOAD DATA --------------------
@st.cache_data
def load_csv():
    return pd.read_csv("Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv")

@st.cache_data
def load_geojson(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

df = load_csv()
nga_boundary = load_geojson("gadm41_NGA_0.geojson")
state_boundary = load_geojson("gadm41_NGA_1.geojson")

# -------------------- COLOR CODING --------------------
OPERATOR_COLORS = {
    "MTN Nigeria": "yellow",
    "Airtel Nigeria": "red",
    "Globacom": "green",
    "9mobile": "black"
}

TECH_COLORS = {
    "2G": "gray",
    "3G": "blue",
    "4G": "purple"
}

# -------------------- UTILITIES --------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)*2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)*2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))

def generate_grid(lat, lon, radius_km, step_km=5):
    points = []
    for dx in range(-radius_km, radius_km + 1, step_km):
        for dy in range(-radius_km, radius_km + 1, step_km):
            glat = lat + dx / 111
            glon = lon + dy / (111 * cos(radians(lat)))
            points.append((glat, glon))
    return points

# -------------------- SIDEBAR --------------------
st.sidebar.header("📍 Analysis Settings")

lat = st.sidebar.number_input("Latitude", value=6.5244)
lon = st.sidebar.number_input("Longitude", value=3.3792)
radius_km = st.sidebar.slider("Coverage Radius (km)", 5, 100, 30)

analyze_btn = st.sidebar.button("🔍 Analyze")

# -------------------- MAIN CONTENT --------------------
if analyze_btn:

    df["distance_km"] = df.apply(
        lambda r: haversine(lat, lon, r["Latitude"], r["Longitude"]),
        axis=1
    )

    nearby = df[df["distance_km"] <= radius_km]

    # ==================================================
    # COVERAGE ANALYSIS
    # ==================================================
    st.header("📶 Coverage Analysis")

    # -------- Coverage Map --------
    st.subheader("Coverage Map")

    m = folium.Map(location=[lat, lon], zoom_start=8)

    folium.GeoJson(nga_boundary, style_function=lambda x: {
        "fillOpacity": 0, "color": "black", "weight": 1
    }).add_to(m)

    folium.GeoJson(state_boundary, style_function=lambda x: {
        "fillOpacity": 0, "color": "gray", "weight": 0.5
    }).add_to(m)

    for _, r in nearby.iterrows():
        folium.CircleMarker(
            location=[r["Latitude"], r["Longitude"]],
            radius=4,
            color=OPERATOR_COLORS.get(r["Network_Operator"], "blue"),
            fill=True,
            fill_opacity=0.8,
            popup=f"""
            Operator: {r['Network_Operator']}<br>
            Technology: {r['Network_Generation']}
            """
        ).add_to(m)

    folium.Circle(
        location=[lat, lon],
        radius=radius_km * 1000,
        color="blue",
        fill=False
    ).add_to(m)

    st_folium(m, height=500, width=1100)

    # -------- Network Predictor --------
    st.subheader("Network Predictor")

    if nearby.empty:
        st.error("❌ No network detected in this area")
    else:
        summary = nearby.groupby(
            ["Network_Operator", "Network_Generation"]
        ).size().reset_index(name="Count")

        best = summary.sort_values("Count", ascending=False).iloc[0]

        confidence = min(100, int((best["Count"] / len(nearby)) * 100))

        st.success(
            f"✅ Best Network: *{best['Network_Operator']} ({best['Network_Generation']})*"
        )
        st.info(f"📊 Confidence Level: *{confidence}%*")

        st.dataframe(summary)

    # ==================================================
    # GAP & PLANNING
    # ==================================================
    st.header("🛠 Gap & Planning")

    st.subheader("No Coverage Map & New Tower Recommendation")

    gap_map = folium.Map(location=[lat, lon], zoom_start=8)

    folium.GeoJson(nga_boundary, style_function=lambda x: {
        "fillOpacity": 0, "color": "black", "weight": 1
    }).add_to(gap_map)

    grid = generate_grid(lat, lon, radius_km)
    uncovered_points = []

    for glat, glon in grid:
        min_dist = df.apply(
            lambda r: haversine(glat, glon, r["Latitude"], r["Longitude"]),
            axis=1
        ).min()

        if min_dist > radius_km:
            uncovered_points.append((glat, glon))
            folium.Circle(
                location=[glat, glon],
                radius=2500,
                color="red",
                fill=True,
                fill_opacity=0.4
            ).add_to(gap_map)

    st_folium(gap_map, height=500, width=1100)

    if uncovered_points:
        rec_lat, rec_lon = uncovered_points[0]
        st.error("🚨 No Coverage Detected")
        st.success(
            f"📍 Recommended New Tower Location: *({rec_lat:.4f}, {rec_lon:.4f})*"
        )
        st.info("📡 Suggested Network: *4G (MTN Nigeria)*")
    else:
        st.success("✅ No major coverage gaps detected")

    # ==================================================
    # STATISTICS
    # ==================================================
    st.header("📊 Statistics")

    st.subheader("Operator Summary")
    st.dataframe(df["Network_Operator"].value_counts().reset_index(
        name="Total Sites"
    ))

    st.subheader("Technology Summary")
    st.dataframe(df["Network_Generation"].value_counts().reset_index(
        name="Total Sites"
    ))

    # ==================================================
    # EXPORT
    # ==================================================
    st.header("📤 Export")

    st.download_button(
        "⬇ Download Nearby Network Results",
        nearby.to_csv(index=False),
        file_name="network_results.csv",
        mime="text/csv"
    )

    if uncovered_points:
        export_df = pd.DataFrame(
            uncovered_points, columns=["Latitude", "Longitude"]
        )
        st.download_button(
            "⬇ Download Tower Recommendations",
            export_df.to_csv(index=False),
            file_name="tower_recommendations.csv",
            mime="text/csv"
        )

    # ==================================================
    # USER GUIDE
    # ==================================================
    st.header("📘 User Guide")

    st.markdown("""
    *How to use this app:*
    1. Enter coordinates in the sidebar
    2. Select coverage radius
    3. Click *Analyze*
    4. View coverage, gaps, statistics & recommendations
    """)

else:
    st.info("👈 Enter coordinates and click *Analyze* to begin")
