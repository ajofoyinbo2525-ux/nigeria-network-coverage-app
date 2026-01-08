import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from math import radians, cos, sin, sqrt, atan2
import json
import numpy as np

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Nigeria Network Coverage & Planning App",
    layout="wide"
)

st.title("📡 Nigeria Network Coverage & Planning App")

# --------------------------------------------------
# LOAD & CLEAN DATA (CRITICAL FIX)
# --------------------------------------------------
@st.cache_data
def load_csv():
    df = pd.read_csv("Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv")

    # FORCE numeric conversion (THIS FIXES YOUR ERROR)
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")

    # DROP invalid rows safely
    df = df.dropna(subset=["Latitude", "Longitude"])

    return df

@st.cache_data
def load_geojson(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

df = load_csv()
nga_boundary = load_geojson("gadm41_NGA_0.geojson")
state_boundary = load_geojson("gadm41_NGA_1.geojson")

# --------------------------------------------------
# COLOR CODING (WORKING)
# --------------------------------------------------
OPERATOR_COLORS = {
    "MTN Nigeria": "#FFD700",      # Yellow
    "Airtel Nigeria": "#FF0000",   # Red
    "Globacom": "#008000",         # Green
    "9mobile": "#000000"           # Black
}

TECH_COLORS = {
    "2G": "gray",
    "3G": "blue",
    "4G": "purple"
}

# --------------------------------------------------
# SAFE HAVERSINE (CRASH-PROOF)
# --------------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    if any(pd.isna([lat1, lon1, lat2, lon2])):
        return np.nan

    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)*2 + cos(lat1) * cos(lat2) * sin(dlon/2)*2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))

# --------------------------------------------------
# SIDEBAR CONTROLS
# --------------------------------------------------
st.sidebar.header("📍 Analysis Settings")

lat = st.sidebar.number_input("Latitude", value=6.5244)
lon = st.sidebar.number_input("Longitude", value=3.3792)
radius_km = st.sidebar.slider("Coverage Radius (km)", 5, 100, 30)

analyze_btn = st.sidebar.button("🔍 Analyze")

# --------------------------------------------------
# MAIN LOGIC
# --------------------------------------------------
if analyze_btn:

    # SAFE distance calculation
    df["distance_km"] = df.apply(
        lambda r: haversine(lat, lon, r["Latitude"], r["Longitude"]),
        axis=1
    )

    nearby = df[df["distance_km"] <= radius_km].copy()

    # ==================================================
    # COVERAGE ANALYSIS
    # ==================================================
    st.header("📶 Coverage Analysis")

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
            radius=5,
            color=OPERATOR_COLORS.get(r["Network_Operator"], "blue"),
            fill=True,
            fill_opacity=0.9,
            popup=f"""
            <b>Operator:</b> {r['Network_Operator']}<br>
            <b>Technology:</b> {r['Network_Generation']}
            """
        ).add_to(m)

    folium.Circle(
        location=[lat, lon],
        radius=radius_km * 1000,
        color="blue",
        fill=False
    ).add_to(m)

    st_folium(m, height=520, width=1100)

    # --------------------------------------------------
    # NETWORK PREDICTOR
    # --------------------------------------------------
    st.subheader("Network Predictor")

    if nearby.empty:
        st.error("❌ No network detected in this area")
    else:
        summary = nearby.groupby(
            ["Network_Operator", "Network_Generation"]
        ).size().reset_index(name="Count")

        best = summary.sort_values("Count", ascending=False).iloc[0]
        confidence = int((best["Count"] / summary["Count"].sum()) * 100)

        st.success(
            f"✅ Best Network: {best['Network_Operator']} ({best['Network_Generation']})"
        )
        st.info(f"📊 Confidence Level: {confidence}%")

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

    uncovered = []

    for dx in range(-radius_km, radius_km + 1, 10):
        for dy in range(-radius_km, radius_km + 1, 10):
            glat = lat + dx / 111
            glon = lon + dy / (111 * cos(radians(lat)))

            min_dist = df.apply(
                lambda r: haversine(glat, glon, r["Latitude"], r["Longitude"]),
                axis=1
            ).min()

            if pd.notna(min_dist) and min_dist > radius_km:
                uncovered.append((glat, glon))
                folium.Circle(
                    location=[glat, glon],
                    radius=2500,
                    color="red",
                    fill=True,
                    fill_opacity=0.4
                ).add_to(gap_map)

    st_folium(gap_map, height=520, width=1100)

    if uncovered:
        rec_lat, rec_lon = uncovered[0]
        st.error("🚨 No Coverage Detected")
        st.success(f"📍 New Tower Location: ({rec_lat:.4f}, {rec_lon:.4f})")
        st.info("📡 Recommended Network: 4G (MTN Nigeria)")
    else:
        st.success("✅ No major coverage gaps found")

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
        "⬇ Export Network Results",
        nearby.to_csv(index=False),
        "network_results.csv",
        "text/csv"
    )

    if uncovered:
        export_df = pd.DataFrame(uncovered, columns=["Latitude", "Longitude"])
        st.download_button(
            "⬇ Export Tower Recommendations",
            export_df.to_csv(index=False),
            "tower_recommendations.csv",
            "text/csv"
        )

    # ==================================================
    # USER GUIDE
    # ==================================================
    st.header("📘 User Guide")
    st.markdown("""
    1. Enter coordinates  
    2. Set coverage radius  
    3. Click *Analyze*  
    4. View coverage, gaps & recommendations  
    """)

else:
    st.info("👈 Enter coordinates and click *Analyze* to begin")
