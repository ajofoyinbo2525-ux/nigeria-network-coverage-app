import math
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Nigeria Network Coverage Intelligence",
    layout="wide"
)

st.title("📡 Nigeria Network Coverage & Planning Dashboard")

# --------------------------------------------------
# LOAD NETWORK DATA
# --------------------------------------------------
CSV_FILE = "Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv"

try:
    df_all = pd.read_csv(CSV_FILE)
except Exception as e:
    st.error(f"❌ Cannot load CSV file: {e}")
    st.stop()

required_cols = [
    "Network_Operator",
    "Network_Generation",
    "Latitude",
    "Longitude"
]

for col in required_cols:
    if col not in df_all.columns:
        st.error(f"❌ Missing required column: {col}")
        st.stop()

st.success("✅ Network dataset loaded successfully")

# --------------------------------------------------
# SIDEBAR – MASTER CONTROLLER
# --------------------------------------------------
st.sidebar.header("📍 Location Controller")

user_lat = st.sidebar.number_input("Latitude", value=6.5244, format="%.6f")
user_lon = st.sidebar.number_input("Longitude", value=3.3792, format="%.6f")

run_analysis = st.sidebar.button("▶ Run Analysis")

st.sidebar.header("⚙ Analysis Settings")

distance_mode = st.sidebar.radio(
    "Distance Mode",
    ["Unlimited", "Close Proximity"]
)

user_radius_km = st.sidebar.slider(
    "User Search Radius (km)", 1, 200, 30
)

coverage_radius_km = st.sidebar.slider(
    "Coverage Radius per Site (km)", 1, 50, 10
)

operator_filter = st.sidebar.selectbox(
    "Network Operator",
    ["All", "MTN", "Airtel", "Glo", "9mobile"]
)

generation_filter = st.sidebar.multiselect(
    "Network Generation",
    ["2G", "3G", "4G"],
    default=["2G", "3G", "4G"]
)

# --------------------------------------------------
# DISTANCE FUNCTION
# --------------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2 +
        math.cos(math.radians(lat1)) *
        math.cos(math.radians(lat2)) *
        math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))

# --------------------------------------------------
# RUN ANALYSIS
# --------------------------------------------------
if run_analysis:

    df = df_all.copy()

    # Calculate distance
    df["distance_km"] = df.apply(
        lambda r: haversine(
            user_lat, user_lon,
            r["Latitude"], r["Longitude"]
        ),
        axis=1
    )

    # Filters
    if operator_filter != "All":
        df = df[df["Network_Operator"].str.contains(
            operator_filter, case=False, na=False
        )]

    df = df[df["Network_Generation"].isin(generation_filter)]

    if distance_mode == "Close Proximity":
        df = df[df["distance_km"] <= user_radius_km]

    # Confidence score
    df["Confidence_%"] = (1 / (1 + df["distance_km"])) * 100
    df["Confidence_%"] = df["Confidence_%"].clip(0, 100)

    # Export dataframe
    export_df = df[[
        "Network_Operator",
        "Network_Generation",
        "Latitude",
        "Longitude",
        "distance_km",
        "Confidence_%"
    ]].copy()

    # --------------------------------------------------
    # TABS
    # --------------------------------------------------
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📡 Coverage Map",
        "❌ No Coverage / Gaps",
        "📍 Network Prediction",
        "🗼 New Tower Recommendation",
        "📊 Coverage Density",
        "📋 Results & Export",
        "📘 User Guide"
    ])

    # --------------------------------------------------
    # TAB 1 – COVERAGE MAP
    # --------------------------------------------------
    with tab1:
        m = folium.Map(location=[user_lat, user_lon], zoom_start=6)

        folium.Marker(
            [user_lat, user_lon],
            popup="Input Location",
            icon=folium.Icon(color="blue")
        ).add_to(m)

        for _, r in df.iterrows():
            folium.Circle(
                [r["Latitude"], r["Longitude"]],
                radius=coverage_radius_km * 1000,
                color="green",
                fill=True,
                fill_opacity=0.25,
                popup=f"{r['Network_Operator']} {r['Network_Generation']}"
            ).add_to(m)

        st_folium(m, height=520)

    # --------------------------------------------------
    # TAB 2 – NO COVERAGE
    # --------------------------------------------------
    with tab2:
        uncovered = df[df["distance_km"] > coverage_radius_km]

        if uncovered.empty:
            st.success("✅ No major coverage gaps detected")
        else:
            st.warning("⚠ Coverage gaps detected")

        st.dataframe(uncovered[[
            "Network_Operator",
            "Network_Generation",
            "distance_km"
        ]])

    # --------------------------------------------------
    # TAB 3 – NETWORK PREDICTION
    # --------------------------------------------------
    with tab3:
        st.metric("Networks Detected", len(df))

        st.dataframe(df[[
            "Network_Operator",
            "Network_Generation",
            "distance_km",
            "Confidence_%"
        ]])

    # --------------------------------------------------
    # TAB 4 – NEW TOWER RECOMMENDATION
    # --------------------------------------------------
    with tab4:
        if df.empty:
            rec_lat, rec_lon = user_lat, user_lon
            reason = "No nearby networks detected"
        else:
            far = df.sort_values("distance_km", ascending=False).iloc[0]
            rec_lat = (user_lat + far["Latitude"]) / 2
            rec_lon = (user_lon + far["Longitude"]) / 2
            reason = "Balances detected coverage gap"

        m2 = folium.Map(location=[rec_lat, rec_lon], zoom_start=7)

        folium.Marker(
            [rec_lat, rec_lon],
            popup="Recommended Tower Location",
            icon=folium.Icon(color="red")
        ).add_to(m2)

        st_folium(m2, height=500)
        st.write("📌 Recommendation Reason:", reason)

    # --------------------------------------------------
    # TAB 5 – COVERAGE DENSITY (PROXY)
    # --------------------------------------------------
    with tab5:
        density_df = df_all.copy()
        density_df["Zone"] = pd.cut(
            density_df["Latitude"],
            bins=6,
            labels=[
                "Far North",
                "North",
                "North Central",
                "South West",
                "South East",
                "South South"
            ]
        )

        density = density_df.groupby("Zone").size()
        st.bar_chart(density)

    # --------------------------------------------------
    # TAB 6 – RESULTS & EXPORT
    # --------------------------------------------------
    with tab6:
        st.download_button(
            "⬇ Export Network Results (CSV)",
            data=export_df.to_csv(index=False),
            file_name="network_prediction_results.csv",
            mime="text/csv"
        )

        st.dataframe(df)

    # --------------------------------------------------
    # TAB 7 – USER GUIDE
    # --------------------------------------------------
    with tab7:
        st.markdown("""
        ### 📘 How to Use This App

        1. Input latitude & longitude  
        2. Click *Run Analysis*  
        3. View results across all tabs  
        4. Export results if needed  

        *Use cases*
        - Network planning
        - Coverage analysis
        - New tower placement
        """)

else:
    st.info("👈 Enter coordinates and click *Run Analysis* to begin")
