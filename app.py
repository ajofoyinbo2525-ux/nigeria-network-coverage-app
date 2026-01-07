# app.py
# FINAL – Nigeria Mobile Network Coverage, Density & Site Selection Web App
# Author: Ajo Fx Project

import streamlit as st
import pandas as pd
import numpy as np
from sklearn.neighbors import BallTree
import folium
from streamlit_folium import st_folium

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Nigeria Network Coverage & Planning App",
    page_icon="📡",
    layout="wide"
)

# ---------------- LOAD DATA ----------------
@st.cache_data
def load_data():
    return pd.read_csv("Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv")

df = load_data()

# Safety checks
required_cols = ["Latitude", "Longitude", "Network_Provider", "Technology"]
for col in required_cols:
    if col not in df.columns:
        st.error(f"Missing required column: {col}")
        st.stop()

# Spatial index (no distance limit)
coords_rad = np.radians(df[["Latitude", "Longitude"]])
tree = BallTree(coords_rad, metric="haversine")

# ---------------- SIDEBAR CONTROLS ----------------
st.sidebar.title("📍 Analysis Controls")

lat = st.sidebar.number_input("Latitude", value=6.5244, format="%.6f")
lon = st.sidebar.number_input("Longitude", value=3.3792, format="%.6f")

k = st.sidebar.slider("Nearby sites to analyze", 1, 25, 5)
buffer_km = st.sidebar.slider("Coverage buffer (km)", 1, 20, 5)

show_density_grid = st.sidebar.checkbox("Show coverage density grid", True)
show_site_selection = st.sidebar.checkbox("Show site selection map", True)
show_state_density = st.sidebar.checkbox("Show coverage density per state")

predict_btn = st.sidebar.button("📡 Predict Network Coverage")

# ---------------- USER GUIDE ----------------
with st.expander("📘 User Guide"):
    st.markdown(
        """
        **How to use this app**
        1. Enter coordinates OR click on the map
        2. Choose number of nearby sites
        3. Adjust coverage buffer
        4. Click *Predict Network Coverage*
        5. Green = covered | Red = no coverage
        6. Export results for ArcGIS / QGIS
        """
    )

# ---------------- MAIN TITLE ----------------
st.title("📡 Nigeria Mobile Network Coverage & Planning System")

# ---------------- MAP INITIALIZATION ----------------
base_map = folium.Map(location=[lat, lon], zoom_start=6, tiles="CartoDB positron")

click_data = st_folium(base_map, height=350, width=1100)

if click_data and click_data.get("last_clicked"):
    lat = click_data["last_clicked"]["lat"]
    lon = click_data["last_clicked"]["lng"]

# ---------------- ANALYSIS ----------------
if predict_btn:

    # Nearest sites
    point = np.radians([[lat, lon]])
    dist, idx = tree.query(point, k=k)
    nearby = df.iloc[idx[0]].copy()

    # User marker
    folium.Marker(
        [lat, lon],
        popup="Analysis Location",
        icon=folium.Icon(color="blue", icon="signal")
    ).add_to(base_map)

    # Operator colors
    operator_colors = {
        "MTN": "orange",
        "Airtel": "red",
        "Glo": "green",
        "9mobile": "darkgreen"
    }

    # ---------------- BUFFERS & SITES ----------------
    for _, row in nearby.iterrows():
        color = operator_colors.get(row["Network_Provider"], "gray")

        folium.Marker(
            [row["Latitude"], row["Longitude"]],
            popup=f"{row['Network_Provider']} | {row['Technology']}",
            icon=folium.Icon(color=color)
        ).add_to(base_map)

        folium.Circle(
            [row["Latitude"], row["Longitude"]],
            radius=buffer_km * 1000,
            color=color,
            fill=True,
            fill_opacity=0.25
        ).add_to(base_map)

    # ---------------- GRID-BASED COVERAGE ----------------
    if show_density_grid:
        st.subheader("🟩 Covered vs 🟥 No-Coverage Areas")

        grid_step = 0.05  # approx 5km
        lat_range = np.arange(lat - 0.3, lat + 0.3, grid_step)
        lon_range = np.arange(lon - 0.3, lon + 0.3, grid_step)

        covered_cells = []
        uncovered_cells = []

        for la in lat_range:
            for lo in lon_range:
                d, _ = tree.query(np.radians([[la, lo]]), k=1)
                if d[0][0] * 6371 <= buffer_km:
                    covered_cells.append((la, lo))
                else:
                    uncovered_cells.append((la, lo))

        for la, lo in covered_cells:
            folium.Circle(
                [la, lo],
                radius=2000,
                color="green",
                fill=True,
                fill_opacity=0.15
            ).add_to(base_map)

        for la, lo in uncovered_cells:
            folium.Circle(
                [la, lo],
                radius=2000,
                color="red",
                fill=True,
                fill_opacity=0.05
            ).add_to(base_map)

        # Export grid
        export_grid = pd.DataFrame(
            covered_cells + uncovered_cells,
            columns=["Latitude", "Longitude"]
        )
        export_grid["Coverage_Status"] = (
            ["Covered"] * len(covered_cells) + ["No Coverage"] * len(uncovered_cells)
        )

        st.download_button(
            "⬇️ Download Coverage Grid (CSV)",
            export_grid.to_csv(index=False),
            file_name="coverage_grid.csv",
            mime="text/csv"
        )

    # ---------------- SITE SELECTION ----------------
    if show_site_selection:
        st.subheader("🟦 Site Selection Insight")
        st.markdown(
            "Areas marked red are priority zones for new network deployment due to lack of coverage."
        )

    # ---------------- STATE DENSITY ----------------
    if show_state_density:
        st.subheader("🗺️ Coverage Density per State")

        if "State" in df.columns:
            state_density = df.groupby("State").size().reset_index(name="Total_Sites")
            st.dataframe(state_density)

            st.download_button(
                "⬇️ Download State Coverage Density",
                state_density.to_csv(index=False),
                file_name="state_coverage_density.csv",
                mime="text/csv"
            )
        else:
            st.warning("State column not found in dataset.")

# ---------------- FINAL MAP ----------------
st_folium(base_map, height=550, width=1100)

