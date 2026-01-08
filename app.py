import streamlit as st
import pandas as pd
import numpy as np
import folium
import json
from math import radians, cos, sin, asin, sqrt
from shapely.geometry import Point, shape
from shapely.ops import unary_union
from streamlit_folium import st_folium

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="Nigeria Network Coverage & Planning",
    layout="wide",
    page_icon="📡"
)

st.title("📡 Nigeria Mobile Network Coverage & Planning System")
st.caption("2G | 3G | 4G • Coverage • Gaps • Site Recommendation")

# =====================================================
# LOAD NETWORK DATA
# =====================================================
@st.cache_data
def load_sites():
    return pd.read_csv("Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv")

df = load_sites()

# =====================================================
# VALIDATE CSV COLUMNS
# =====================================================
required_cols = [
    "Country",
    "Network_Operator",
    "Radio_Technology",
    "Network_Generation",
    "Latitude",
    "Longitude"
]

missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"Missing required column(s) in CSV: {missing}")
    st.stop()

# =====================================================
# LOAD GEOJSON FILES
# =====================================================
try:
    with open("gadm41_NGA_0.geojson", "r", encoding="utf-8") as f:
        nigeria_geo = json.load(f)

    with open("gadm41_NGA_1.geojson", "r", encoding="utf-8") as f:
        states_geo = json.load(f)
except Exception as e:
    st.error(f"Error loading GeoJSON files: {e}")
    st.stop()

# =====================================================
# HELPER FUNCTIONS
# =====================================================
def haversine(lat1, lon1, lat2, lon2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)*2 + cos(lat1)*cos(lat2)*sin(dlon/2)*2
    c = 2 * asin(sqrt(a))
    return 6371 * c

def confidence(dist):
    if dist <= 5:
        return "High"
    elif dist <= 15:
        return "Medium"
    return "Low"

def nearest_distance(lat, lon):
    return df.apply(
        lambda r: haversine(lat, lon, r["Latitude"], r["Longitude"]),
        axis=1
    ).min()

# =====================================================
# SIDEBAR CONTROLS
# =====================================================
st.sidebar.header("📍 Location Analysis")

lat = st.sidebar.number_input("Latitude", value=6.5244, format="%.6f")
lon = st.sidebar.number_input("Longitude", value=3.3792, format="%.6f")

nearby_n = st.sidebar.slider("Nearby Sites to Analyze", 1, 10, 3)
buffer_km = st.sidebar.slider("Coverage Buffer Radius (km)", 1, 50, 10)

run = st.sidebar.button("🔍 Predict Network")

# =====================================================
# TABS
# =====================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📡 Network Prediction",
    "🟦 Location Buffer",
    "🗺️ Coverage Density",
    "🟢 Coverage Areas",
    "🚫 No Coverage Areas",
    "📍 Recommended New Towers"
])

# =====================================================
# TAB 1 — NETWORK PREDICTION
# =====================================================
with tab1:
    st.subheader("Select Location")

    base_map = folium.Map(location=[lat, lon], zoom_start=6)
    click = st_folium(base_map, height=400, width=1100)

    if click and click.get("last_clicked"):
        lat = click["last_clicked"]["lat"]
        lon = click["last_clicked"]["lng"]
        st.success(f"Selected: {lat:.6f}, {lon:.6f}")

    if run:
        df["Distance_km"] = df.apply(
            lambda r: haversine(lat, lon, r["Latitude"], r["Longitude"]),
            axis=1
        )

        nearby = df.sort_values("Distance_km").head(nearby_n)
        nearest = nearby.iloc[0]

        c1, c2, c3 = st.columns(3)
        c1.metric("Nearest Operator", nearest["Network_Operator"])
        c2.metric("Network Generation", nearest["Network_Generation"])
        c3.metric("Distance (km)", f"{nearest['Distance_km']:.2f}")

        st.info(f"Confidence Level: {confidence(nearest['Distance_km'])}")

        st.subheader("Operator Probability (%)")
        st.bar_chart(
            nearby["Network_Operator"]
            .value_counts(normalize=True) * 100
        )

        st.subheader("Nearby Network Sites")
        st.dataframe(
            nearby[[
                "Network_Operator",
                "Network_Generation",
                "Radio_Technology",
                "Distance_km"
            ]],
            use_container_width=True
        )

# =====================================================
# TAB 2 — BUFFER AROUND LOCATION
# =====================================================
with tab2:
    st.subheader("Coverage Buffer")

    buf_map = folium.Map(location=[lat, lon], zoom_start=10)

    folium.Marker([lat, lon], popup="Selected Location").add_to(buf_map)

    folium.Circle(
        [lat, lon],
        radius=buffer_km * 1000,
        color="blue",
        fill=True,
        fill_opacity=0.3
    ).add_to(buf_map)

    st_folium(buf_map, height=500, width=1100)

# =====================================================
# TAB 3 — COVERAGE DENSITY (SAFE VERSION)
# =====================================================
with tab3:
    st.subheader("Coverage Density (National Overview)")

    density_map = folium.Map(location=[9, 8.5], zoom_start=6)

    folium.GeoJson(
        states_geo,
        style_function=lambda x: {
            "fillColor": "#ffeecc",
            "color": "black",
            "weight": 0.5,
            "fillOpacity": 0.4
        }
    ).add_to(density_map)

    st.info(
        "Per-state density requires spatial join. "
        "This view shows national distribution safely."
    )

    st_folium(density_map, height=500, width=1100)

# =====================================================
# PREPARE COVERAGE BUFFERS
# =====================================================
nigeria_polygon = shape(nigeria_geo["features"][0]["geometry"])

buffers = []
sample_df = df.sample(min(800, len(df)))

for _, r in sample_df.iterrows():
    p = Point(r["Longitude"], r["Latitude"])
    buffers.append(p.buffer((buffer_km * 1000) / 111320))

coverage_area = unary_union(buffers)
no_coverage_area = nigeria_polygon.difference(coverage_area)

# =====================================================
# TAB 4 — COVERAGE AREAS
# =====================================================
with tab4:
    st.subheader("Network Coverage Areas")

    cov_map = folium.Map(location=[9, 8.5], zoom_start=6)

    folium.GeoJson(
        coverage_area._geo_interface_,
        style_function=lambda x: {
            "fillColor": "green",
            "color": "green",
            "fillOpacity": 0.45
        }
    ).add_to(cov_map)

    st_folium(cov_map, height=550, width=1100)

# =====================================================
# TAB 5 — NO COVERAGE AREAS
# =====================================================
with tab5:
    st.subheader("Areas With No Network Coverage")

    no_cov_map = folium.Map(location=[9, 8.5], zoom_start=6)

    folium.GeoJson(
        no_coverage_area._geo_interface_,
        style_function=lambda x: {
            "fillColor": "red",
            "color": "red",
            "fillOpacity": 0.45
        }
    ).add_to(no_cov_map)

    st_folium(no_cov_map, height=550, width=1100)

# =====================================================
# TAB 6 — RECOMMENDED NEW TOWERS
# =====================================================
with tab6:
    st.subheader("Recommended New Tower Locations")

    if no_coverage_area.is_empty:
        st.success("Coverage is sufficient nationwide.")
    else:
        polys = (
            [no_coverage_area]
            if no_coverage_area.geom_type == "Polygon"
            else list(no_coverage_area.geoms)
        )

        sites = []

        for poly in polys:
            if poly.area > 0.05:
                c = poly.centroid
                dist = nearest_distance(c.y, c.x)
                score = (poly.area * 0.6) + (dist * 0.4)

                sites.append({
                    "Latitude": c.y,
                    "Longitude": c.x,
                    "Uncovered_Area": round(poly.area, 4),
                    "Distance_To_Nearest_Site_km": round(dist, 2),
                    "Population_Proxy_Score": round(score, 2)
                })

        sites_df = pd.DataFrame(sites).sort_values(
            "Population_Proxy_Score",
            ascending=False
        ).reset_index(drop=True)

        sites_df["Priority_Rank"] = sites_df.index + 1

        st.dataframe(sites_df, use_container_width=True)

        rec_map = folium.Map(location=[9, 8.5], zoom_start=6)

        for _, r in sites_df.iterrows():
            folium.Marker(
                [r["Latitude"], r["Longitude"]],
                popup=f"Rank {r['Priority_Rank']} | Score {r['Population_Proxy_Score']}",
                icon=folium.Icon(color="blue", icon="signal")
            ).add_to(rec_map)

        st_folium(rec_map, height=550, width=1100)

        st.download_button(
            "⬇️ Download Recommended Sites (CSV)",
            sites_df.to_csv(index=False),
            "recommended_sites.csv",
            "text/csv"

        )
