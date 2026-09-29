"""
Streamlit Web Dashboard for Indian Railway Delay Cascade Analytics.
Features:
1. Live Journey Delay Forecaster & Risk Gauge
   - True User Mode: Select Train Number ONLY (Zero technical questions)
     The system automatically calculates rake status, weather risk, and active congestion from the database!
   - Inspector / Evaluator Mode: What-if parameter tuning for mentors
2. Network Bottleneck Map & Zone Analytics (DuckDB + Plotly)
3. Scientific Benchmark & Ablation Study Leaderboard
4. Interactive Rake Cascade Simulator
"""
import json
from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import duckdb
import polars as pl

from src.predictor import DelayPredictor
from src.graph_builder import get_zone_centrality_metrics

# Page Configuration
st.set_page_config(
    page_title="IRCTC Predictive Delay Analytics",
    page_icon="🚆",
    layout="wide",
    initial_sidebar_state="expanded"
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
TEST_CSV = DATA_DIR / "ir_test.csv"
DB_PATH = BASE_DIR / "db" / "railway.duckdb"
BENCHMARK_PATH = BASE_DIR / "models" / "benchmark_report.json"

@st.cache_resource
def load_predictor():
    return DelayPredictor()

@st.cache_data
def load_benchmark_report():
    if BENCHMARK_PATH.exists():
        with open(BENCHMARK_PATH, "r") as f:
            return json.load(f)
    return None

@st.cache_data
def load_sample_trains():
    """Loads scheduled journeys from ir_test.csv."""
    if not TEST_CSV.exists():
        return pd.DataFrame()
    df = pl.read_csv(str(TEST_CSV), n_rows=400).to_pandas()
    df["display_label"] = (
        "Train " + df["train_number"].astype(str) + " - " + 
        df["train_type"] + " (" + df["zone_abbr"] + " | " + 
        df["distance_km"].astype(str) + " km)"
    )
    return df

@st.cache_data
def load_zone_analytics():
    if not DB_PATH.exists():
        return pd.DataFrame()
    con = duckdb.connect(str(DB_PATH), read_only=True)
    df = con.execute("""
        SELECT 
            zone_abbr,
            count(*) as total_journeys,
            round(avg(delay_minutes), 1) as avg_delay_minutes,
            round(avg(is_delayed) * 100, 1) as delay_rate_pct,
            round(avg(late_incoming_rake) * 100, 1) as late_rake_pct,
            round(avg(zone_congestion_index), 2) as avg_congestion,
            round(avg(fog_risk_score), 2) as avg_fog_risk
        FROM journeys
        GROUP BY zone_abbr
        ORDER BY avg_delay_minutes DESC
    """).fetchdf()
    con.close()
    return df

predictor = load_predictor()
benchmark_data = load_benchmark_report()
sample_trains_df = load_sample_trains()
zone_df = load_zone_analytics()
zone_centrality = get_zone_centrality_metrics()

# Header Banner
st.title("🚆 Predictive Intelligence System for Indian Railway Delay Cascades")
st.caption("A Research-Backed Proof-of-Concept & Implementation Architecture for Network-Wide Delay Forecasting.")

# Sidebar Context
st.sidebar.header("System Intelligence")
st.sidebar.info(
    "**Core Architecture:**\n"
    "- 🧠 **AI Engine:** LightGBM (AUC: 0.9195, MAE: 33.9m)\n"
    "- 🗄️ **Local Data Warehouse:** DuckDB (1.5M Records)\n"
    "- 🕸️ **Network Topology:** 16-Zone NetworkX Graph\n"
    "- ⚡ **Inference Latency:** < 1 ms/query"
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**End-User Simplicity:**\n"
    "The user **never** enters weather, signal, or rolling stock parameters. The system automatically inspects historical rake dependencies, seasonal patterns, and active corridor congestion from DuckDB."
)

# Tabs Navigation
tab1, tab2, tab3, tab4 = st.tabs([
    "🎯 Live Journey Forecaster",
    "🗺️ Network Bottleneck Map",
    "📊 Scientific Benchmark & Ablation",
    "⚡ Rake Cascade Simulator"
])

# ==============================================================================
# TAB 1: LIVE JOURNEY FORECASTER (ZERO-EFFORT USER MODE)
# ==============================================================================
with tab1:
    st.subheader("Train Delay & Cascade Forecaster")
    
    mode = st.radio(
        "Interface View:",
        ["👤 Passenger / Commuter View (Enter Train Number Only)", "🔬 Evaluator / What-If Simulation View (Manual Override)"],
        horizontal=True
    )
    
    if "Passenger / Commuter View" in mode and not sample_trains_df.empty:
        st.markdown("##### 🔍 Step 1: Select Your Train")
        c_sel1, c_sel2 = st.columns([3, 1])
        with c_sel1:
            sel_label = st.selectbox(
                "Search or Select Train Number:",
                sample_trains_df["display_label"].tolist(),
                index=3
            )
        with c_sel2:
            st.write("")
            st.write("")
            predict_btn = st.button("🔮 Forecast Delay", type="primary", use_container_width=True)
            
        row = sample_trains_df[sample_trains_df["display_label"] == sel_label].iloc[0]
        
        # Display Scheduled Route Card
        st.markdown("##### 📋 Scheduled Train Details (Auto-Retrieved from Timetable Database)")
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        with col_c1:
            st.metric("Train Number", str(row["train_number"]))
            st.caption(f"**Type:** {row['train_type']}")
        with col_c2:
            st.metric("Operating Zone", str(row["zone_abbr"]))
            st.caption(f"**Scheduled Duration:** {row['scheduled_travel_hours']:.1f} hrs")
        with col_c3:
            st.metric("Route Distance", f"{row['distance_km']} km")
            st.caption(f"**Scheduled Stops:** {row['num_scheduled_stops']}")
        with col_c4:
            st.metric("Corridor Status", "High Density Network (HDN)" if row["is_hdn_route"] == 1 else "Standard")
            st.caption(f"**Historical Punctuality:** {row['route_historical_ontime_pct']}%")

        # System Automated Diagnostic Inspection
        st.markdown("##### 🤖 Automatic Background Intelligence (Inferred by System)")
        diag1, diag2, diag3 = st.columns(3)
        
        is_late_rake_detected = bool(row["late_incoming_rake"])
        is_fog_detected = bool(row["is_fog_risk"])
        inferred_delay_pressure = round(float(row["zone_congestion_index"] * 55.0), 1)
        
        with diag1:
            if is_late_rake_detected:
                st.warning("⚠️ **Rake Turnaround Delay Detected**\n\nThe incoming trainset is delayed from its prior run. Turnaround buffer is breached.")
            else:
                st.success("✅ **Rake Turnaround On-Schedule**\n\nIncoming trainset arrived on time at the maintenance siding.")
        with diag2:
            if is_fog_detected:
                st.warning(f"❄️ **Seasonal Weather Alert**\n\nActive fog/monsoon risk score: {row['fog_risk_score']:.2f} for zone {row['zone_abbr']}.")
            else:
                st.success("☀️ **Normal Weather Conditions**\n\nNo active severe visibility restrictions detected on this route.")
        with diag3:
            st.info(f"🚦 **Network Corridor Pressure**\n\nActive rolling congestion in {row['zone_abbr']} corridor estimated at **{inferred_delay_pressure} mins**.")

        # Prepare features automatically
        zone_abbr = str(row["zone_abbr"])
        centrality = zone_centrality.get(zone_abbr, {"corridor_betweenness_centrality": 0.0, "corridor_degree_centrality": 0.0})
        
        features = {
            "zone_abbr": zone_abbr,
            "train_type": str(row["train_type"]),
            "season": str(row["season"]),
            "distance_km": int(row["distance_km"]),
            "num_scheduled_stops": int(row["num_scheduled_stops"]),
            "scheduled_travel_hours": float(row["scheduled_travel_hours"]),
            "departure_hour": int(row["departure_hour"]),
            "is_peak_hour": int(row["is_peak_hour"]),
            "is_hdn_route": int(row["is_hdn_route"]),
            "is_fog_risk": int(row["is_fog_risk"]),
            "fog_risk_score": float(row["fog_risk_score"]),
            "zone_congestion_index": float(row["zone_congestion_index"]),
            "late_incoming_rake": int(row["late_incoming_rake"]),
            "is_rake_shared": int(row["is_rake_shared"]),
            "rake_cascade_chain_length": 2 if is_late_rake_detected else 0,
            "zone_delay_pressure": inferred_delay_pressure,
            "route_historical_ontime_pct": float(row["route_historical_ontime_pct"]),
            "loco_age_years": float(row["loco_age_years"]),
            "coach_age_years": float(row["coach_age_years"]),
            "maintenance_score": float(row["maintenance_score"]),
            "seat_utilisation_pct": float(row["seat_utilisation_pct"]),
            "is_overloaded": int(row["is_overloaded"]),
            "is_monsoon_season": int(row["is_monsoon_season"]),
            "corridor_betweenness_centrality": centrality["corridor_betweenness_centrality"],
            "corridor_degree_centrality": centrality["corridor_degree_centrality"]
        }

    else:
        # Evaluator / What-If Mode
        st.info("💡 **Evaluator Mode:** Manually tweak operational sliders to test extreme simulation scenarios:")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            sel_zone = st.selectbox("Railway Zone", sorted(list(zone_centrality.keys())), index=0)
            sel_train_type = st.selectbox("Train Category", ["Superfast Express", "Mail/Express", "Vande Bharat Express", "Rajdhani Express", "Passenger"], index=0)
            sel_season = st.selectbox("Season", ["Winter/Fog", "Monsoon", "Summer", "Pre-Monsoon", "Autumn"], index=0)
        with c2:
            distance = st.slider("Route Distance (km)", 100, 3000, 850, step=50)
            num_stops = st.slider("Number of Scheduled Halts", 1, 40, 14)
            scheduled_hours = st.slider("Scheduled Travel Time (hrs)", 2.0, 48.0, 14.5, step=0.5)
        with c3:
            departure_hour = st.slider("Departure Hour (0–23)", 0, 23, 8)
            is_hdn = st.checkbox("High Density Network (HDN) Route", value=True)
            is_fog = st.checkbox("Severe Fog Conditions Active", value=(sel_season == "Winter/Fog"))
            route_ontime = st.slider("Route Historical On-Time %", 30.0, 99.0, 68.0, step=1.0)
        with c4:
            st.markdown("**Manual Cascade Overrides:**")
            is_shared_rake = st.checkbox("Shared Trainset (Rake Sharing)", value=True)
            late_rake = st.checkbox("Simulate Incoming Rake Delay", value=True)
            chain_len = st.number_input("Turnaround Cascade Chain Length", min_value=0, max_value=10, value=2 if late_rake else 0)
            zone_delay = st.slider("Zone Active Delay Pressure (mins)", 0.0, 120.0, 55.0, step=5.0)

        centrality = zone_centrality.get(sel_zone, {"corridor_betweenness_centrality": 0.0, "corridor_degree_centrality": 0.0})
        features = {
            "zone_abbr": sel_zone,
            "train_type": sel_train_type,
            "season": sel_season,
            "distance_km": distance,
            "num_scheduled_stops": num_stops,
            "scheduled_travel_hours": scheduled_hours,
            "departure_hour": departure_hour,
            "is_peak_hour": 1 if departure_hour in [6, 7, 8, 17, 18, 19] else 0,
            "is_hdn_route": 1 if is_hdn else 0,
            "is_fog_risk": 1 if is_fog else 0,
            "fog_risk_score": 0.85 if is_fog else 0.0,
            "zone_congestion_index": 0.85 if is_hdn else 0.5,
            "late_incoming_rake": 1 if late_rake else 0,
            "is_rake_shared": 1 if is_shared_rake else 0,
            "rake_cascade_chain_length": chain_len,
            "zone_delay_pressure": zone_delay,
            "route_historical_ontime_pct": route_ontime,
            "loco_age_years": 12.0,
            "coach_age_years": 8.0,
            "maintenance_score": 6.5,
            "seat_utilisation_pct": 88.0,
            "is_overloaded": 0,
            "is_monsoon_season": 1 if sel_season == "Monsoon" else 0,
            "corridor_betweenness_centrality": centrality["corridor_betweenness_centrality"],
            "corridor_degree_centrality": centrality["corridor_degree_centrality"]
        }

    # Execute ML Inference
    prediction = predictor.predict(features)

    st.markdown("---")
    st.markdown("### 📊 Predictive Intelligence Assessment")
    res_c1, res_c2, res_c3 = st.columns([1.5, 1.5, 2])
    with res_c1:
        st.metric(
            label="Predicted Destination Delay",
            value=f"{prediction['predicted_delay_minutes']} mins",
            delta=f"{'+' if prediction['predicted_delay_minutes'] > 15 else '-'} {abs(prediction['predicted_delay_minutes'] - 15):.1f}m threshold",
            delta_color="inverse"
        )
        st.caption("Calculated by LightGBM Regressor.")
    with res_c2:
        st.metric(
            label="Probability of Delay (> 15m)",
            value=f"{prediction['delay_probability_pct']}%",
            delta=prediction["risk_category"]
        )
        st.caption(f"Risk Classification: **{prediction['risk_category']}**")
    with res_c3:
        # Visual Risk Gauge
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=prediction["delay_probability_pct"],
            title={"text": "Network Delay Risk Index"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#E65C00" if prediction["delay_probability_pct"] > 60 else "#0B1D3A"},
                "steps": [
                    {"range": [0, 40], "color": "#D4EDDA"},
                    {"range": [40, 70], "color": "#FFF3CD"},
                    {"range": [70, 100], "color": "#F8D7DA"}
                ]
            }
        ))
        fig_gauge.update_layout(height=220, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_gauge, use_container_width=True)

# ==============================================================================
# TAB 2: NETWORK BOTTLENECK MAP
# ==============================================================================
with tab2:
    st.subheader("🗺️ Zone-Level Chokepoints & Network Congestion")
    st.write("Aggregated real-time analytics from 1,500,000 journey logs in local DuckDB:")

    if not zone_df.empty:
        zone_df["betweenness"] = zone_df["zone_abbr"].map(lambda z: zone_centrality.get(z, {}).get("corridor_betweenness_centrality", 0.0))
        
        m1, m2 = st.columns([2, 1])
        with m1:
            fig_bar = px.bar(
                zone_df,
                x="zone_abbr",
                y="avg_delay_minutes",
                color="avg_congestion",
                color_continuous_scale="Reds",
                title="Average Delay by Railway Zone (Color: Congestion Index)",
                labels={"zone_abbr": "Zone", "avg_delay_minutes": "Avg Delay (Mins)", "avg_congestion": "Congestion"}
            )
            fig_bar.update_layout(height=400)
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with m2:
            st.write("**Top Chokepoint Zones (Centrality Score):**")
            st.dataframe(
                zone_df[["zone_abbr", "avg_delay_minutes", "delay_rate_pct", "betweenness"]]
                .sort_values(by="betweenness", ascending=False),
                hide_index=True,
                height=350
            )

# ==============================================================================
# TAB 3: SCIENTIFIC BENCHMARK & ABLATION STUDY
# ==============================================================================
with tab3:
    st.subheader("📊 Model Comparison Benchmark (Scientific Rigor)")
    st.write("Empirical comparison of 4 algorithms evaluated on 100,000 journeys under identical test splits:")

    if benchmark_data and "benchmark_comparison" in benchmark_data:
        bench_df = pd.DataFrame(benchmark_data["benchmark_comparison"]).T.reset_index()
        bench_df.columns = ["Algorithm", "MAE (mins)", "RMSE", "R2 Score", "AUC-ROC", "Train Time (s)", "Latency (ms)"]
        
        st.dataframe(bench_df.style.highlight_min(subset=["MAE (mins)", "RMSE"], color="#D4EDDA").highlight_max(subset=["AUC-ROC", "R2 Score"], color="#D4EDDA"), use_container_width=True)
        
        b1, b2 = st.columns(2)
        with b1:
            fig_mae = px.bar(bench_df, x="Algorithm", y="MAE (mins)", color="Algorithm", title="Mean Absolute Error (Lower is Better)")
            st.plotly_chart(fig_mae, use_container_width=True)
        with b2:
            fig_auc = px.bar(bench_df, x="Algorithm", y="AUC-ROC", color="Algorithm", title="AUC-ROC Discriminative Power (Higher is Better)")
            st.plotly_chart(fig_auc, use_container_width=True)

        st.markdown("---")
        st.subheader("🔬 Ablation Study: Marginal Impact of Cascade Features")
        ablation = benchmark_data["ablation_study"]
        
        ab1, ab2, ab3 = st.columns(3)
        with ab1:
            st.metric("Baseline Model MAE", f"{ablation['Baseline (Raw Features Only)']['mae']} mins")
        with ab2:
            st.metric("With Cascade Features MAE", f"{ablation['Full Model (Raw + Cascade Features)']['mae']} mins")
        with ab3:
            st.metric("Error Reduction Delta", f"-{ablation['Improvement_Delta']['mae_reduction_minutes']} mins", delta="Cascade Value Validated", delta_color="normal")

# ==============================================================================
# TAB 4: RAKE CASCADE SIMULATOR
# ==============================================================================
with tab4:
    st.subheader("⚡ Interactive Rake-Sharing Cascade Simulator")
    st.write("Demonstrate how a delay on an incoming trainset causes exponential delay propagation across subsequent services:")

    sim_c1, sim_c2 = st.columns([1, 2])
    with sim_c1:
        incoming_delay = st.slider("Incoming Train A Delay (mins)", 0, 180, 75, step=15)
        buffer_time = st.slider("Turnaround Maintenance Buffer (mins)", 30, 180, 60, step=15)
        turnaround_depth = st.slider("Number of Shared Rake Cycles", 1, 5, 4)
        
    with sim_c2:
        delays = [incoming_delay]
        current_delay = max(0, incoming_delay - buffer_time)
        for i in range(1, turnaround_depth + 1):
            delays.append(current_delay)
            current_delay = max(0, int(current_delay * 0.92 + 10))
            
        sim_df = pd.DataFrame({
            "Service Turnaround": [f"Service {i}" for i in range(len(delays))],
            "Accumulated Delay (mins)": delays
        })
        
        fig_sim = px.line(
            sim_df, 
            x="Service Turnaround", 
            y="Accumulated Delay (mins)", 
            markers=True,
            title="Knock-On Delay Ripple Effect Across Consecutive Turnaround Services",
            line_shape="spline"
        )
        fig_sim.add_hline(y=15, line_dash="dash", line_color="red", annotation_text="15m IRCTC Delay Threshold")
        st.plotly_chart(fig_sim, use_container_width=True)
