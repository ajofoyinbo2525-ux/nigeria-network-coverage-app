import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
import json
from math import radians, cos

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(
    page_title="Nigeria Network Coverage & Planning App",
    layout="wide"
)

st.title("📡 Nigeria Network Coverage & Planning App")

# ==================================================
# DATA LOADING
# ==================================================
@st.cache_data
def load_csv():
    df = pd.read_csv("Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv")

    for col in ["Latitude", "Longitude", "Network_Operator", "Network_Generation", "State"]:
        if col not in df.columns:
            df[col] = "UNKNOWN"

    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
    df = df.dropna(subset=["Latitude", "Longitude"])

    df["Network_Operator"] = df["Network_Operator"].astype(str).str.upper()
    df["Network_Operator"] = df["Network_Operator"].replace({
        r".*MTN.*": "MTN Nigeria",
        r".*AIRTEL.*": "Airtel Nigeria",
        r".*GLO.*": "Globacom",
        r".*9.*MOBILE.*": "9mobile"
    }, regex=True)

    df["Network_Generation"] = df["Network_Generation"].astype(str).str.upper()
    df["Network_Generation"] = df["Network_Generation"].replace({
        r".*LTE.*": "4G",
        r".*4G.*": "4G",
        r".*UMTS.*": "3G",
        r".*HSPA.*": "3G",
        r".*3G.*": "3G",
        r".*EDGE.*": "2G",
        r".*GSM.*": "2G",
        r".*2G.*": "2G"
    }, regex=True)

    df["Network_Operator"] = df["Network_Operator"].fillna("UNKNOWN")
    df["Network_Generation"] = df["Network_Generation"].fillna("UNKNOWN")

    return df

@st.cache_data
def load_geojson(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

df = load_csv()
nga = load_geojson("gadm41_NGA_0.geojson")
states = load_geojson("gadm41_NGA_1.geojson")

# ==================================================
# COLORS
# ==================================================
OPERATOR_COLORS = {
    "MTN Nigeria": "#FFD700",
    "Airtel Nigeria": "#FF0000",
    "Globacom": "#008000",
    "9mobile": "#000000"
}

TECH_COLORS = {
    "2G": "#9E9E9E",
    "3G": "#2196F3",
    "4G": "#9C27B0"
}

# ==================================================
# HAVERSINE FUNCTION
# ==================================================
def haversine_np(lat, lon, lats, lons):
    R = 6371
    lat = np.radians(lat)
    lon = np.radians(lon)
    lats = np.radians(lats)
    lons = np.radians(lons)
    dlat = lats - lat
    dlon = lons - lon
    a = np.sin(dlat / 2)**2 + np.cos(lat) * np.cos(lats) * np.sin(dlon / 2)**2
    return 2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

# ==================================================
# SIDEBAR INPUTS
# ==================================================
st.sidebar.header("📍 Analysis Settings")
lat = st.sidebar.number_input("Latitude", value=6.5244, format="%.6f")
lon = st.sidebar.number_input("Longitude", value=3.3792, format="%.6f")
radius_km = st.sidebar.slider("Coverage Radius (km)", 5, 100, 30)
analyze = st.sidebar.button("🔍 Analyze")

# ==================================================
# SESSION STATE
# ==================================================
for key in ["analysis_done", "nearby", "lat", "lon", "radius_km"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ==================================================
# RUN ANALYSIS
# ==================================================
if analyze:
    df["distance_km"] = haversine_np(lat, lon, df["Latitude"].values, df["Longitude"].values)
    nearby = df[df["distance_km"] <= radius_km].copy()
    
    st.session_state.nearby = nearby
    st.session_state.lat = lat
    st.session_state.lon = lon
    st.session_state.radius_km = radius_km
    st.session_state.analysis_done = True

# ==================================================
# DISPLAY RESULTS
# ==================================================
if st.session_state.analysis_done:
    nearby = st.session_state.nearby
    lat = st.session_state.lat
    lon = st.session_state.lon
    radius_km = st.session_state.radius_km

    # ================= NETWORK PREDICTOR =================
    st.subheader("📡 Network Predictor")

    if nearby.empty:
        st.warning("❌ No network detected nearby.")

        # Find nearest site for prediction
        all_distances = haversine_np(lat, lon, df["Latitude"].values, df["Longitude"].values)
        nearest_idx = all_distances.argmin()
        nearest_site = df.iloc[nearest_idx]
        st.info(f"Nearest site is {all_distances[nearest_idx]:.2f} km away ({nearest_site['Network_Operator']}, {nearest_site['Network_Generation']})")

        # Suggested new tower location (midpoint)
        rlat = (lat + nearest_site["Latitude"]) / 2
        rlon = (lon + nearest_site["Longitude"]) / 2
        st.success(f"📍 Suggested New Tower Location: {rlat:.6f}, {rlon:.6f}")
        st.info(f"Recommended Operator: {nearest_site['Network_Operator']}")
        st.info(f"Recommended Technology: {nearest_site['Network_Generation']}")

    else:
        # Predict the strongest network in the area
        summary = nearby.groupby(
            ["Network_Operator", "Network_Generation"]
        ).size().reset_index(name="Count")
        best = summary.sort_values("Count", ascending=False).iloc[0]
        confidence = int(best["Count"] / summary["Count"].sum() * 100)
        st.success(f"Best Network: {best['Network_Operator']} ({best['Network_Generation']})")
        st.info(f"Confidence Level: {confidence}%")
        st.dataframe(summary)

    # ================= NO COVERAGE / NEW TOWER MAP =================
    st.header("🚫 No Coverage & Tower Recommendation Map")

    gap_map = folium.Map(location=[lat, lon], zoom_start=8)
    folium.GeoJson(nga, style_function=lambda x: {"fillOpacity": 0, "color": "black", "weight": 1}).add_to(gap_map)
    folium.GeoJson(states, style_function=lambda x: {"fillOpacity": 0, "color": "gray", "weight": 0.5}).add_to(gap_map)

    uncovered = []
    grid_step = 15

    for dx in range(-radius_km, radius_km + 1, grid_step):
        for dy in range(-radius_km, radius_km + 1, grid_step):
            glat = lat + dx / 111
            glon = lon + dy / (111 * cos(radians(lat)))
            distances = haversine_np(glat, glon, df["Latitude"].values, df["Longitude"].values)
            if len(distances) == 0: continue
            if distances.min() > 8:
                uncovered.append((glat, glon))
                folium.Circle([glat, glon], radius=3000, color="red", fill=True, fill_opacity=0.4).add_to(gap_map)

    # Input location
    folium.Marker([lat, lon], popup="Input Location", icon=folium.Icon(color="blue")).add_to(gap_map)

    # Suggested tower
    if uncovered:
        rlat, rlon = uncovered[0]
        folium.Marker([rlat, rlon], popup="Suggested Tower", icon=folium.Icon(color="red")).add_to(gap_map)
        st.success(f"📍 Suggested Tower Location: {rlat:.6f}, {rlon:.6f}")

    st_folium(gap_map, height=520, width=1100)

    # ================= COVERAGE STATISTICS & MAP (existing app) =================
    if not nearby.empty:
        st.header("📊 Coverage Statistics")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Sites", len(nearby))
        c2.metric("Operators", nearby["Network_Operator"].nunique())
        c3.metric("4G Sites", (nearby["Network_Generation"] == "4G").sum())
        c4.metric("3G Sites", (nearby["Network_Generation"] == "3G").sum())
        c5.metric("2G Sites", (nearby["Network_Generation"] == "2G").sum())

        st.header("📶 Coverage Map")
        m = folium.Map(location=[lat, lon], zoom_start=8)
        folium.GeoJson(nga, style_function=lambda x: {"fillOpacity": 0, "color": "black", "weight": 1}).add_to(m)
        folium.GeoJson(states, style_function=lambda x: {"fillOpacity": 0, "color": "gray", "weight": 0.5}).add_to(m)

        for _, r in nearby.iterrows():
            tech_color = TECH_COLORS.get(r["Network_Generation"], "#607D8B")
            op_color = OPERATOR_COLORS.get(r["Network_Operator"], "#1976D2")
            folium.CircleMarker(
                [r["Latitude"], r["Longitude"]],
                radius=7,
                weight=2,
                color=tech_color,
                fill=True,
                fill_color=op_color,
                fill_opacity=0.9,
                popup=f"<b>Operator:</b> {r['Network_Operator']}<br><b>Technology:</b> {r['Network_Generation']}<br><b>Distance:</b> {r['distance_km']:.2f} km"
            ).add_to(m)

        folium.Circle([lat, lon], radius=radius_km*1000, color="blue").add_to(m)

        # Legend
        legend_html = """
         <div style="position: fixed; bottom: 50px; left: 50px; width: 200px; height: 160px; 
                     border:2px solid grey; z-index:9999; font-size:14px; background-color:white; padding:10px;">
         <b>Operator (Fill):</b><br>
         <i style="background:#FFD700;color:#FFD700;">....</i> MTN Nigeria<br>
         <i style="background:#FF0000;color:#FF0000;">....</i> Airtel Nigeria<br>
         <i style="background:#008000;color:#008000;">....</i> Globacom<br>
         <i style="background:#000000;color:#000000;">....</i> 9mobile<br>
         <b>Tech (Border):</b><br>
         <i style="border:2px solid #9E9E9E;">....</i> 2G<br>
         <i style="border:2px solid #2196F3;">....</i> 3G<br>
         <i style="border:2px solid #9C27B0;">....</i> 4G<br>
         </div>
         """
        m.get_root().html.add_child(folium.Element(legend_html))
        st_folium(m, height=520, width=1100)

        # Technology Summary
        st.header("📡 Technology Summary")
        st.dataframe(
            nearby["Network_Generation"].value_counts()
            .reset_index()
            .rename(columns={"index": "Technology", "Network_Generation": "Sites"})
        )

        # Operator Summary
        st.header("🏢 Operator Operational Summary")
        st.dataframe(
            nearby.groupby("Network_Operator").agg(
                Sites=("Network_Operator", "count"),
                Avg_Distance_km=("distance_km", "mean"),
                Dominant_Tech=("Network_Generation", lambda x: x.mode()[0])
            ).reset_index()
        )

        # Coverage Density
        st.header("🗺 Coverage Density by State")
        st.dataframe(
            nearby.groupby("State").size()
            .reset_index(name="Detected_Sites")
            .sort_values("Detected_Sites", ascending=False)
        )

        # Export
        st.header("📤 Export Results")
        csv = nearby.to_csv(index=False).encode("utf-8")
        st.download_button("⬇ Download Analysis CSV", csv, "network_coverage_analysis.csv", "text/csv")

        # Operational Summary
        st.header("🧾 Operational Summary")
        st.markdown(f"""
        - **{len(nearby)} network sites** detected within **{radius_km} km**
        - **{nearby['Network_Operator'].nunique()} operators** active
        - **4G dominance** indicates moderate/high data capacity
        - Coverage gaps detected → infrastructure expansion recommended
        """)

else:
    st.info("👈 Enter coordinates and click Analyze")
