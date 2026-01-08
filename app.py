import os
import math
import json
import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from fpdf import FPDF

# =====================================================
# APP CONFIG
# =====================================================
st.set_page_config(
    page_title="Nigeria Mobile Network Coverage",
    layout="wide"
)

st.title("🇳🇬 Nigeria Mobile Network Coverage Planning System")
st.caption("2G | 3G | 4G • Operator Detection • Gap Analysis • Reports")

# =====================================================
# UTILITIES
# =====================================================
def find_file(name):
    for root, _, files in os.walk("."):
        if name in files:
            return os.path.join(root, name)
    return None

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

# =====================================================
# LOAD FILES
# =====================================================
nga0 = find_file("gadm41_NGA_0.geojson")
nga1 = find_file("gadm41_NGA_1.geojson")
csv_file = find_file("Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv")

if not nga0 or not nga1:
    st.error("Nigeria GeoJSON files missing")
    st.stop()

nigeria = gpd.read_file(nga0)
states = gpd.read_file(nga1)

network_df = None
if csv_file:
    network_df = pd.read_csv(csv_file)

# =====================================================
# USER GUIDE
# =====================================================
with st.expander("📘 User Guide"):
    st.markdown("""
    *Features*
    - Network operator detection
    - 2G / 3G / 4G confidence scoring
    - Coverage gap identification
    - PDF planning reports

    *How it works*
    - Enter coordinates
    - Predict nearby networks
    - Analyze coverage gaps
    - Export report
    """)

# =====================================================
# BASE MAP
# =====================================================
def base_map():
    m = folium.Map([9.1, 8.7], zoom_start=6, tiles="CartoDB positron")
    folium.GeoJson(nigeria, style_function=lambda x: {"color": "black", "weight": 2}).add_to(m)
    folium.GeoJson(states, style_function=lambda x: {"color": "gray", "weight": 1}).add_to(m)
    return m

# =====================================================
# TABS
# =====================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "🗺 Coverage Map",
    "📍 Network Prediction",
    "⚠ Coverage Gaps",
    "📄 PDF Report"
])

# =====================================================
# TAB 1 – MAP
# =====================================================
with tab1:
    m = base_map()

    if network_df is not None:
        lat_col = next(c for c in network_df.columns if "lat" in c.lower())
        lon_col = next(c for c in network_df.columns if "lon" in c.lower())
        op_col = next(c for c in network_df.columns if "operator" in c.lower())

        for _, r in network_df.sample(min(800, len(network_df))).iterrows():
            folium.CircleMarker(
                [r[lat_col], r[lon_col]],
                radius=2,
                color="blue",
                fill=True
            ).add_to(m)

    st_folium(m, height=600)

# =====================================================
# TAB 2 – NETWORK PREDICTION
# =====================================================
with tab2:
    col1, col2 = st.columns(2)
    lat = col1.number_input("Latitude", value=6.5244, format="%.6f")
    lon = col2.number_input("Longitude", value=3.3792, format="%.6f")

    if st.button("🔮 Predict Network"):
        if network_df is None:
            st.warning("Network CSV not loaded")
        else:
            network_df["distance"] = network_df.apply(
                lambda r: haversine(lat, lon, r[lat_col], r[lon_col]), axis=1
            )

            nearest = network_df.sort_values("distance").head(30)

            operators = nearest[op_col].value_counts()
            tech_conf = {
                "2G": min(100, 100 - nearest["distance"].mean() * 10),
                "3G": min(100, 100 - nearest["distance"].mean() * 8),
                "4G": min(100, 100 - nearest["distance"].mean() * 6),
            }

            st.success("📡 Network Detected")

            st.subheader("Available Operators")
            st.write(operators)

            st.subheader("Technology Confidence")
            st.progress(int(tech_conf["2G"]))
            st.write("2G:", f"{tech_conf['2G']:.1f}%")

            st.progress(int(tech_conf["3G"]))
            st.write("3G:", f"{tech_conf['3G']:.1f}%")

            st.progress(int(tech_conf["4G"]))
            st.write("4G:", f"{tech_conf['4G']:.1f}%")

            m = base_map()
            folium.Marker([lat, lon], icon=folium.Icon(color="green")).add_to(m)

            for _, r in nearest.head(6).iterrows():
                folium.CircleMarker([r[lat_col], r[lon_col]], radius=4, color="blue").add_to(m)

            st_folium(m, height=500)

# =====================================================
# TAB 3 – COVERAGE GAP DETECTION
# =====================================================
with tab3:
    st.subheader("Coverage Gap Zones")

    if network_df is None:
        st.warning("CSV missing")
    else:
        sparse = network_df.groupby(op_col).filter(lambda x: len(x) < 200)

        m = base_map()
        for _, r in sparse.iterrows():
            folium.CircleMarker(
                [r[lat_col], r[lon_col]],
                radius=5,
                color="red",
                fill=True
            ).add_to(m)

        st_folium(m, height=600)
        st.info("Red zones indicate potential coverage gaps")

# =====================================================
# TAB 4 – PDF REPORT
# =====================================================
with tab4:
    st.subheader("Generate Planning Report")

    report_lat = st.number_input("Report Latitude", value=6.5244)
    report_lon = st.number_input("Report Longitude", value=3.3792)

    if st.button("📄 Generate PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        pdf.cell(0, 10, "Nigeria Network Coverage Report", ln=True)
        pdf.cell(0, 10, f"Location: {report_lat}, {report_lon}", ln=True)
        pdf.cell(0, 10, "Technologies: 2G / 3G / 4G", ln=True)
        pdf.cell(0, 10, "Operators: MTN, Airtel, Glo, 9mobile", ln=True)
        pdf.cell(0, 10, "Generated via Streamlit App", ln=True)

        path = "network_report.pdf"
        pdf.output(path)

        with open(path, "rb") as f:
            st.download_button(
                "⬇ Download PDF Report",
                f,
                file_name="Nigeria_Network_Report.pdf",
                mime="application/pdf"
            )

        st.success("Report generated successfully")
