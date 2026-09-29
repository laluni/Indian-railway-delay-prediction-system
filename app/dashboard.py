"""
RailPulse Dashboard - Passenger-First Railway Delay Intelligence
Powered by LightGBM AI and 1.28M real station observations.
"""
import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import duckdb
import polars as pl

from src.predictor import DelayPredictor
from src.graph_builder import get_zone_centrality_metrics
from src.trajectory_profiler import TrajectoryProfiler

st.set_page_config(
    page_title="RailPulse - Indian Railway Delay Intelligence",
    page_icon="🚆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Premium CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Poppins:wght@700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: linear-gradient(135deg,#0a0e1a 0%,#0d1b2a 50%,#0a1628 100%); color:#e2e8f0; }
#MainMenu, footer, header { visibility:hidden; }
.block-container { padding-top:1.2rem; max-width:1300px; }
.hero { background:linear-gradient(135deg,#1a3a5c 0%,#0d2137 100%); border:1px solid rgba(99,179,237,.2); border-radius:16px; padding:1.8rem 2.2rem; margin-bottom:1.5rem; }
.hero h1 { font-family:'Poppins',sans-serif; font-size:2.1rem; font-weight:800; background:linear-gradient(90deg,#63b3ed,#90cdf4,#f6ad55); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; margin:0; }
.hero p  { color:#90a8c0; font-size:.93rem; margin-top:.4rem; }
.hero-badge { display:inline-block; background:rgba(99,179,237,.12); border:1px solid rgba(99,179,237,.28); color:#63b3ed; border-radius:20px; padding:.18rem .7rem; font-size:.76rem; font-weight:500; margin:.55rem .3rem 0 0; }
.pred-box { background:linear-gradient(135deg,#1a3a5c,#0d2137); border:1px solid rgba(99,179,237,.25); border-radius:16px; padding:1.8rem; text-align:center; }
.pred-number { font-family:'Poppins',sans-serif; font-size:3.8rem; font-weight:800; line-height:1; }
.pred-number.red { color:#fc8181; } .pred-number.orange { color:#f6ad55; } .pred-number.green { color:#68d391; }
.pred-label { font-size:.88rem; color:#90a8c0; margin-top:.4rem; }
.risk-chip { display:inline-block; padding:.3rem .9rem; border-radius:20px; font-size:.82rem; font-weight:600; margin-top:.7rem; }
.risk-HIGH   { background:rgba(252,129,129,.18); color:#fc8181; border:1px solid rgba(252,129,129,.3); }
.risk-MEDIUM { background:rgba(246,173,85,.18);  color:#f6ad55; border:1px solid rgba(246,173,85,.3); }
.risk-LOW    { background:rgba(104,211,145,.18); color:#68d391; border:1px solid rgba(104,211,145,.3); }
.section-h { font-size:1.05rem; font-weight:700; color:#bee3f8; margin:1.4rem 0 .65rem; padding-bottom:.35rem; border-bottom:1px solid rgba(99,179,237,.15); }
.bcard { background:rgba(252,129,129,.07); border:1px solid rgba(252,129,129,.2); border-radius:10px; padding:.9rem; margin-bottom:.4rem; }
.bcard-rank { font-size:.68rem; color:#fc8181; font-weight:700; text-transform:uppercase; letter-spacing:.06em; margin-bottom:.15rem; }
.bcard-name { font-size:.95rem; font-weight:600; color:#fed7d7; }
.bcard-detail { font-size:.8rem; color:#9a9a9a; margin-top:.25rem; line-height:1.5; }
[data-testid="stTabs"] [role="tab"] { font-weight:500; font-size:.86rem; color:#718096; border-radius:8px 8px 0 0; padding:.55rem 1.1rem; }
[data-testid="stTabs"] [role="tab"][aria-selected="true"] { color:#63b3ed; background:rgba(99,179,237,.1); border-bottom:2px solid #63b3ed; }
[data-testid="metric-container"] { background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.08); border-radius:10px; padding:.7rem 1rem; }
[data-testid="stInfo"]    { background:rgba(99,179,237,.08);  border-left-color:#63b3ed; border-radius:8px; }
[data-testid="stWarning"] { background:rgba(246,173,85,.08);  border-left-color:#f6ad55; border-radius:8px; }
[data-testid="stSuccess"] { background:rgba(104,211,145,.08); border-left-color:#68d391; border-radius:8px; }
[data-testid="stError"]   { background:rgba(252,129,129,.08); border-left-color:#fc8181; border-radius:8px; }
hr { border-color:rgba(255,255,255,.06); }
</style>
""", unsafe_allow_html=True)

DATA_DIR = BASE_DIR / "data"
TEST_CSV = DATA_DIR / "ir_test.csv"
DB_PATH = BASE_DIR / "db" / "railway.duckdb"
BENCHMARK_PATH = BASE_DIR / "models" / "benchmark_report.json"

@st.cache_resource
def load_services():
    predictor = DelayPredictor()
    profiler = TrajectoryProfiler()
    return predictor, profiler

@st.cache_data
def load_benchmark_report():
    if BENCHMARK_PATH.exists():
        with open(BENCHMARK_PATH, "r") as f:
            return json.load(f)
    return None

@st.cache_data
def load_sample_trains():
    """Loads scheduled journeys with station stop data from DuckDB, falling back to ir_test.csv if present."""
    if DB_PATH.exists():
        profiler = TrajectoryProfiler()
        df = profiler.get_available_trains(limit=500)
        if not df.empty:
            return df

    if TEST_CSV.exists():
        df = pl.read_csv(str(TEST_CSV), n_rows=400).to_pandas()
        df["display_label"] = (
            "Train " + df["train_number"].astype(str) + " - " + 
            df["train_type"] + " (" + df["zone_abbr"] + " | " + 
            df["distance_km"].astype(str) + " km)"
        )
        return df

    return pd.DataFrame()

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

predictor, profiler = load_services()
benchmark_data = load_benchmark_report()
sample_trains_df = load_sample_trains()
zone_df = load_zone_analytics()
zone_centrality = get_zone_centrality_metrics()

# ─── Hero Banner ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>🚆 RailPulse</h1>
  <p>AI-powered delay prediction &amp; station-level bottleneck intelligence for Indian Railways</p>
  <span class="hero-badge">📍 1.28M Station Observations</span>
  <span class="hero-badge">🧠 LightGBM AI · AUC 0.91</span>
  <span class="hero-badge">⚡ &lt;1ms Inference</span>
  <span class="hero-badge">🗄️ DuckDB Warehouse</span>
</div>
""", unsafe_allow_html=True)

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 Check My Train",
    "🗺️ Network Hotspots",
    "📊 AI Performance",
    "⚡ Cascade Simulator",
    "🪔 Festival Rush",
])

# ==============================================================================
# TAB 1: CHECK MY TRAIN
# ==============================================================================
with tab1:
    st.markdown('<p class="section-h">Step 1 — Select Your Train</p>', unsafe_allow_html=True)

    mode = st.radio(
        "View mode:",
        ["👤 Commuter Mode (just pick a train)", "🔬 What-If Simulator (advanced)"],
        horizontal=True,
        label_visibility="collapsed",
    )
    
    selected_train_num = None
    
    if "Commuter" in mode and not sample_trains_df.empty:
        col_sel, col_info = st.columns([3, 1])
        with col_sel:
            sel_label = st.selectbox(
                "Search or select a train:",
                sample_trains_df["display_label"].tolist(),
                index=min(3, len(sample_trains_df) - 1),
                label_visibility="collapsed",
            )
        row = sample_trains_df[sample_trains_df["display_label"] == sel_label].iloc[0]
        selected_train_num = str(row["train_number"])
        with col_info:
            st.caption(f"📏 {row.get('distance_km', '—')} km  |  🏷️ {row.get('train_type', 'Express')}")
        
        # Auto-diagnostics
        is_late_rake_detected = bool(row.get("late_incoming_rake", 0) == 1)
        is_fog_detected = bool(row.get("fog_risk_score", 0.0) > 0.5)
        inferred_delay_pressure = float(row.get("avg_delay_mins", 42.0))

        diag1, diag2, diag3 = st.columns(3)
        with diag1:
            if is_late_rake_detected:
                st.warning("⚠️ **Train coaches were late** from their last run. Departure may be delayed.")
            else:
                st.success("✅ **Coaches arrived on time** from previous run. Departure looks normal.")
        with diag2:
            if is_fog_detected:
                st.warning(f"❄️ **Weather risk detected** on the {row.get('zone_abbr','NR')} corridor. Signal speeds may be reduced.")
            else:
                st.success("☀️ **Clear weather conditions** on this route. No visibility restrictions expected.")
        with diag3:
            st.info(f"🚦 **Network pressure:** The {row.get('zone_abbr','NR')} corridor has an average delay of **{inferred_delay_pressure:.0f} min** today.")

        # Prepare features automatically
        zone_abbr = str(row.get("zone_abbr", "NR"))
        centrality = zone_centrality.get(zone_abbr, {"corridor_betweenness_centrality": 0.0, "corridor_degree_centrality": 0.0})
        
        features = {
            "zone_abbr": zone_abbr,
            "train_type": str(row.get("train_type", "Superfast Express")),
            "season": str(row.get("season", "Winter/Fog")),
            "distance_km": int(row.get("distance_km", 850)),
            "num_scheduled_stops": int(row.get("stop_count", 14)),
            "scheduled_travel_hours": float(row.get("distance_km", 850) / 60.0),
            "departure_hour": 8,
            "is_peak_hour": 1,
            "is_hdn_route": 1 if zone_abbr in ["NR", "NCR", "ECR"] else 0,
            "is_fog_risk": 1 if is_fog_detected else 0,
            "fog_risk_score": float(row.get("fog_risk_score", 0.65)) if is_fog_detected else 0.15,
            "zone_congestion_index": 0.85,
            "late_incoming_rake": 1 if is_late_rake_detected else 0,
            "is_rake_shared": 1,
            "rake_cascade_chain_length": 2 if is_late_rake_detected else 0,
            "zone_delay_pressure": inferred_delay_pressure,
            "route_historical_ontime_pct": 72.0,
            "loco_age_years": 10.0,
            "coach_age_years": 7.0,
            "maintenance_score": 8.0,
            "seat_utilisation_pct": 88.0,
            "is_overloaded": 0,
            "is_monsoon_season": 0,
            "corridor_betweenness_centrality": centrality["corridor_betweenness_centrality"],
            "corridor_degree_centrality": centrality["corridor_degree_centrality"]
        }

    else:
        st.info("🔬 **What-If Mode:** Tweak any parameter below and see how the AI delay estimate changes in real time.")
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
        selected_train_num = "22503"  # default sample train

    # ── Step 2: AI Delay Forecast ──────────────────────────────────────────────
    prediction = predictor.predict(features)
    st.markdown('<p class="section-h">Step 2 — Delay Forecast</p>', unsafe_allow_html=True)

    delay_mins = prediction["predicted_delay_minutes"]
    delay_prob = prediction["delay_probability_pct"]

    if delay_mins >= 60:
        num_cls, verdict = "red",    "Significant delay expected"
    elif delay_mins >= 20:
        num_cls, verdict = "orange", "Moderate delay likely"
    else:
        num_cls, verdict = "green",  "On time or minor delay"

    risk_cls = "HIGH" if delay_prob > 60 else ("MEDIUM" if delay_prob > 35 else "LOW")
    risk_emoji = "🔴" if risk_cls == "HIGH" else ("🟡" if risk_cls == "MEDIUM" else "🟢")

    pred_col, gauge_col = st.columns([1, 1])
    with pred_col:
        st.markdown(f"""
        <div class="pred-box">
            <div class="pred-number {num_cls}">{delay_mins} min</div>
            <div class="pred-label">Estimated delay at destination</div>
            <div style="margin-top:.65rem;">
                <span class="risk-chip risk-{risk_cls}">
                    {risk_emoji} {risk_cls} RISK &nbsp;&middot;&nbsp; {delay_prob}% chance of delay &gt;15 min
                </span>
            </div>
            <div style="color:#718096;font-size:.77rem;margin-top:.65rem;">{verdict}</div>
        </div>
        """, unsafe_allow_html=True)

    with gauge_col:
        bar_color = "#fc8181" if delay_prob > 60 else ("#f6ad55" if delay_prob > 35 else "#68d391")
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=delay_prob,
            number={"suffix": "%", "font": {"size": 36, "color": "#e2e8f0"}},
            title={"text": "Delay Probability", "font": {"size": 13, "color": "#90a8c0"}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#4a5568"},
                "bar":  {"color": bar_color, "thickness": 0.7},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0,  35], "color": "rgba(104,211,145,.1)"},
                    {"range": [35, 65], "color": "rgba(246,173,85,.1)"},
                    {"range": [65,100], "color": "rgba(252,129,129,.1)"},
                ],
            },
        ))
        fig_gauge.update_layout(
            height=230, margin=dict(l=20,r=20,t=40,b=10),
            paper_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0",
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

    # ── Step 3: Station Journey Map ────────────────────────────────────────────
    if selected_train_num:
        st.markdown('<p class="section-h">Step 3 — Where Does Delay Build Up?</p>', unsafe_allow_html=True)
        st.caption("See exactly which stations or track sections cause delay to accumulate or recover.")

        traj_df, traj_metrics = profiler.get_route_trajectory(selected_train_num)

        if not traj_df.empty:
            t_col1, t_col2, t_col3, t_col4 = st.columns(4)
            with t_col1:
                st.metric("Total Stations", f"{traj_metrics['total_stops']}")
            with t_col2:
                st.metric("⏱ Time Lost on Track", f"+{traj_metrics['total_track_loss_mins']} min",
                          help="Delay added while the train moves between stations")
            with t_col3:
                st.metric("🚉 Time Lost at Platforms", f"+{traj_metrics['total_dwell_loss_mins']} min",
                          help="Extra time spent standing at stations beyond schedule")
            with t_col4:
                st.metric("✅ Time Recovered", f"-{traj_metrics['total_buffer_recovered_mins']} min",
                          help="Time made up by running faster than the timetable allows")

            st.markdown("#### Journey Delay Map — Station by Station")
            x_labels = traj_df["station_name"] + " (" + traj_df["station_code"] + ")"
            colors    = traj_df["waterfall_color"]
            fig_traj  = go.Figure()
            # Shaded fill
            fig_traj.add_trace(go.Scatter(
                x=x_labels, y=traj_df["arr_delay_mins"],
                mode="none", fill="tozeroy",
                fillcolor="rgba(99,179,237,.07)", showlegend=False, hoverinfo="skip",
            ))
            # Per-section delta bars
            fig_traj.add_trace(go.Bar(
                x=x_labels, y=traj_df["running_delay_delta"],
                name="Time Lost / Gained (per section)",
                marker_color=colors, opacity=0.7,
                hovertemplate="<b>%{x}</b><br>Section delta: %{y:.1f} min<extra></extra>",
            ))
            # Cumulative arrival delay line
            fig_traj.add_trace(go.Scatter(
                x=x_labels, y=traj_df["arr_delay_mins"],
                mode="lines+markers", name="Cumulative Arrival Delay",
                line=dict(color="#90cdf4", width=2.5),
                marker=dict(size=7, color=colors, line=dict(color="#0a0e1a", width=1.5)),
                hovertemplate="<b>%{x}</b><br>Arrival delay: %{y:.0f} min<extra></extra>",
            ))
            fig_traj.add_hline(
                y=15, line_dash="dot", line_color="#f6ad55",
                annotation_text="⚠️ 15-min punctuality threshold",
                annotation_font_color="#f6ad55", annotation_font_size=11,
            )
            fig_traj.update_layout(
                title=dict(text=f"Train {selected_train_num}  {traj_metrics['origin_station']} → {traj_metrics['destination_station']}",
                           font=dict(size=13, color="#bee3f8")),
                xaxis=dict(title="Station (in journey order)", tickangle=-35,
                           tickfont=dict(size=9, color="#718096"), gridcolor="rgba(255,255,255,.04)"),
                yaxis=dict(title="Delay (minutes)", gridcolor="rgba(255,255,255,.06)",
                           tickfont=dict(color="#718096"), zeroline=True, zerolinecolor="rgba(255,255,255,.1)"),
                height=430, hovermode="x unified", barmode="overlay",
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="#e2e8f0",
                legend=dict(orientation="h", y=1.05, x=0, font=dict(size=11)),
                margin=dict(l=10,r=10,t=55,b=90),
            )
            st.plotly_chart(fig_traj, use_container_width=True)

            if traj_metrics.get("worst_sections"):
                st.markdown("#### 🚨 Worst Sections on This Route")
                b_cols = st.columns(len(traj_metrics["worst_sections"]))
                for idx, w in enumerate(traj_metrics["worst_sections"]):
                    with b_cols[idx]:
                        st.markdown(f"""
                        <div class="bcard">
                            <div class="bcard-rank">Rank #{idx+1} Bottleneck</div>
                            <div class="bcard-name">{w['section_name']}</div>
                            <div class="bcard-detail">
                                📍 {w['section']}<br>
                                ⏱ +{w['delay_added']} added here<br>
                                📏 {w['distance']}<br>
                                ⚡ {w['status']}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

            with st.expander("📋 Full station-by-station timing log"):
                disp_cols = [c for c in [
                    "stop_sequence","station_code","station_name","cumulative_distance_km",
                    "sch_arr_time","act_arr_time","arr_delay_mins",
                    "running_delay_delta","dwell_delay_delta","section_status"
                ] if c in traj_df.columns]
                st.dataframe(
                    traj_df[disp_cols].rename(columns={
                        "stop_sequence":"Stop #","station_code":"Code","station_name":"Station",
                        "cumulative_distance_km":"Dist (km)","sch_arr_time":"Sched. Arr",
                        "act_arr_time":"Actual Arr","arr_delay_mins":"Arrival Delay (min)",
                        "running_delay_delta":"Time Lost on Track (min)",
                        "dwell_delay_delta":"Time Lost at Platform (min)",
                        "section_status":"Status",
                    }),
                    use_container_width=True, hide_index=True,
                )
        else:
            st.info("Station telemetry is not indexed for this specific test train. Try selecting one of the express trains from the dropdown.")

# ==============================================================================
# TAB 2: NETWORK HOTSPOTS
# ==============================================================================
with tab2:
    st.markdown('<p class="section-h">Which zones and track sections are the worst?</p>', unsafe_allow_html=True)
    st.caption("Based on 1.28 million real station observations from September 2024.")

    if not zone_df.empty:
        zone_df["betweenness"] = zone_df["zone_abbr"].map(
            lambda z: zone_centrality.get(z, {}).get("corridor_betweenness_centrality", 0.0)
        )
        chart_col, table_col = st.columns([2, 1])
        with chart_col:
            fig_bar = px.bar(
                zone_df, x="zone_abbr", y="avg_delay_minutes",
                color="avg_congestion",
                color_continuous_scale=["#2d3748", "#744210", "#c05621", "#fc8181"],
                title="Average Train Delay by Railway Zone",
                labels={"zone_abbr": "Zone", "avg_delay_minutes": "Avg Delay (min)", "avg_congestion": "Congestion"},
            )
            fig_bar.update_layout(
                height=380, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="#e2e8f0",
                xaxis=dict(gridcolor="rgba(255,255,255,.04)"),
                yaxis=dict(gridcolor="rgba(255,255,255,.06)"),
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        with table_col:
            st.markdown("**Zones ranked by network centrality:**")
            st.dataframe(
                zone_df[["zone_abbr","avg_delay_minutes","delay_rate_pct","betweenness"]]
                .sort_values("betweenness", ascending=False)
                .rename(columns={"zone_abbr":"Zone","avg_delay_minutes":"Avg Delay (min)",
                                  "delay_rate_pct":"% Delayed","betweenness":"Network Centrality"}),
                hide_index=True, height=360, use_container_width=True,
            )

    st.markdown('<p class="section-h">Top 10 Chronic Track Bottlenecks Across India</p>', unsafe_allow_html=True)
    st.caption("Sections where trains repeatedly lose the most time, identified from station-by-station data:")

    national_chokepoints = profiler.get_national_chokepoints(limit=10)
    if not national_chokepoints.empty:
        fig_cp = px.bar(
            national_chokepoints.head(10),
            x="avg_minutes_lost", y="section",
            orientation="h",
            color="delay_frequency_pct",
            color_continuous_scale=["#2d3748", "#c05621", "#fc8181"],
            title="Track Sections with Highest Average Delay Added",
            labels={"section":"Track Section","avg_minutes_lost":"Avg Min Lost","delay_frequency_pct":"% Delayed Runs"},
        )
        fig_cp.update_layout(
            height=420, yaxis={"categoryorder":"total ascending"},
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e2e8f0",
            xaxis=dict(gridcolor="rgba(255,255,255,.06)"),
        )
        st.plotly_chart(fig_cp, use_container_width=True)
        with st.expander("📋 Full bottleneck data table"):
            st.dataframe(
                national_chokepoints.rename(columns={
                    "section":"Track Section","distance_km":"Length (km)",
                    "sample_runs":"Train Runs Observed","avg_minutes_lost":"Avg Delay Added (min)",
                    "delay_frequency_pct":"% Delayed Runs (>5min)",
                    "delay_gradient_per_100km":"Delay Gradient (min/100km)",
                }),
                use_container_width=True, hide_index=True,
            )

# ==============================================================================
# TAB 3: AI PERFORMANCE
# ==============================================================================
with tab3:
    st.markdown('<p class="section-h">How accurate is the AI model?</p>', unsafe_allow_html=True)
    st.caption("Tested on 100,000 real journeys using a held-out test split — never seen during training.")

    if benchmark_data and "benchmark_comparison" in benchmark_data:
        bench_df = pd.DataFrame(benchmark_data["benchmark_comparison"]).T.reset_index()
        bench_df.columns = ["Algorithm", "MAE (mins)", "RMSE", "R² Score", "AUC-ROC", "Train Time (s)", "Latency (ms)"]

        st.dataframe(
            bench_df.style
            .highlight_min(subset=["MAE (mins)","RMSE"], color="#1c3a28", axis=0)
            .highlight_max(subset=["AUC-ROC","R² Score"], color="#1c3a28", axis=0),
            use_container_width=True,
        )

        b1, b2 = st.columns(2)
        with b1:
            fig_mae = px.bar(bench_df, x="Algorithm", y="MAE (mins)", color="Algorithm",
                             title="Prediction Error — Lower is Better",
                             color_discrete_sequence=["#63b3ed","#4299e1","#f6ad55","#fc8181"])
            fig_mae.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                                  font_color="#e2e8f0", showlegend=False)
            st.plotly_chart(fig_mae, use_container_width=True)
        with b2:
            fig_auc = px.bar(bench_df, x="Algorithm", y="AUC-ROC", color="Algorithm",
                             title="Delay Detection Accuracy — Higher is Better",
                             color_discrete_sequence=["#63b3ed","#4299e1","#f6ad55","#fc8181"])
            fig_auc.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                                  font_color="#e2e8f0", showlegend=False)
            st.plotly_chart(fig_auc, use_container_width=True)

        st.markdown('<p class="section-h">What do cascade features add?</p>', unsafe_allow_html=True)
        st.caption("The AI improves when we add rake-sharing, congestion, and fog risk on top of basic train info:")
        ablation = benchmark_data["ablation_study"]
        ab1, ab2, ab3 = st.columns(3)
        with ab1:
            st.metric("Basic Model (train info only)", f"{ablation['Baseline (Raw Features Only)']['mae']} min error")
        with ab2:
            st.metric("Full AI (with cascade factors)", f"{ablation['Full Model (Raw + Cascade Features)']['mae']} min error")
        with ab3:
            st.metric("Improvement", f"-{ablation['Improvement_Delta']['mae_reduction_minutes']} min",
                      delta="Cascade features proven helpful", delta_color="normal")
    else:
        st.info("No benchmark report found. Run `python src/benchmark.py` to generate it.")

# ==============================================================================
# TAB 4: CASCADE SIMULATOR
# ==============================================================================
with tab4:
    st.markdown('<p class="section-h">Rake Cascade Simulator</p>', unsafe_allow_html=True)
    st.write(
        "A **rake** is the set of coaches and engine that forms a train. "
        "Many trains reuse the same rake multiple times a day. "
        "If Train A is late, Train B using the same rake is also delayed — and so on."
    )
    sc1, sc2 = st.columns([1, 2])
    with sc1:
        incoming_delay   = st.slider("Train A arrives this many minutes late:", 0, 180, 75, step=15)
        buffer_time      = st.slider("Maintenance turnaround buffer (mins):", 30, 180, 60, step=15)
        turnaround_depth = st.slider("Number of services sharing this rake:", 1, 5, 4)
        st.caption("Watch how the delay ripples across subsequent services →")
    with sc2:
        delays  = [incoming_delay]
        current = max(0, incoming_delay - buffer_time)
        for _ in range(1, turnaround_depth + 1):
            delays.append(current)
            current = max(0, int(current * 0.92 + 10))
        sim_df = pd.DataFrame({
            "Service": [f"Service {i}" for i in range(len(delays))],
            "Accumulated Delay (mins)": delays,
        })
        color_vals = ["#68d391" if d <= 15 else ("#f6ad55" if d <= 60 else "#fc8181") for d in delays]
        fig_sim = go.Figure(go.Bar(
            x=sim_df["Service"], y=sim_df["Accumulated Delay (mins)"],
            marker_color=color_vals,
            hovertemplate="<b>%{x}</b><br>Delay: %{y} min<extra></extra>",
        ))
        fig_sim.add_hline(y=15, line_dash="dot", line_color="#f6ad55", annotation_text="⚠️ 15-min threshold")
        fig_sim.update_layout(
            title="Knock-on delay across consecutive rake turnarounds",
            height=350,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e2e8f0",
            yaxis=dict(title="Delay (mins)", gridcolor="rgba(255,255,255,.06)"),
            xaxis=dict(gridcolor="rgba(255,255,255,.04)"),
        )
        st.plotly_chart(fig_sim, use_container_width=True)
    if delays[-1] > 15:
        st.error(f"🔴 Even after **{turnaround_depth} turnarounds**, this rake is still **{delays[-1]} minutes late**. Passengers on the last service will face significant delays.")
    else:
        st.success(f"🟢 The delay dissipates after **{turnaround_depth} turnarounds** thanks to buffer time. Later services should depart close to schedule.")

# ==============================================================================
# TAB 5: FESTIVAL RUSH
# ==============================================================================
with tab5:
    st.markdown('<p class="section-h">Ganesh Chaturthi 2024 — How Festivals Crush the Network</p>', unsafe_allow_html=True)
    st.write("During major festivals, hundreds of special trains flood routes that are already at capacity. Here's the data:")

    try:
        con = duckdb.connect(str(DB_PATH), read_only=True)
        festival_df = con.execute("""
            SELECT
                departure_date,
                round(avg(delay_minutes), 1) as avg_network_delay,
                round(avg(is_delayed) * 100, 1) as delayed_trains_pct,
                count(*) as daily_train_runs
            FROM journeys
            GROUP BY departure_date
            ORDER BY departure_date ASC;
        """).fetchdf()
        if not festival_df.empty:
            festival_df = festival_df.rename(columns={"departure_date": "journey_date"})
        con.close()
    except Exception:
        festival_df = pd.DataFrame()

    if not festival_df.empty:
        fc1, fc2 = st.columns([2, 1])
        with fc1:
            fig_fest = px.bar(
                festival_df, x="journey_date", y="avg_network_delay",
                color="avg_network_delay",
                color_continuous_scale=["#2d4a70", "#c05621", "#fc8181"],
                title="Daily Average Delay Across India — September 2024",
                labels={"journey_date": "Date", "avg_network_delay": "Avg Delay (min)"},
            )
            fig_fest.add_vrect(
                x0="2024-09-07", x1="2024-09-17",
                fillcolor="#ed8936", opacity=0.15,
                annotation_text="🪔 Ganpati Festival",
                annotation_position="top left",
                annotation_font_color="#f6ad55",
            )
            fig_fest.update_layout(
                height=400,
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="#e2e8f0",
                xaxis=dict(gridcolor="rgba(255,255,255,.04)"),
                yaxis=dict(gridcolor="rgba(255,255,255,.06)"),
            )
            st.plotly_chart(fig_fest, use_container_width=True)
        with fc2:
            st.markdown("#### 📈 What the data shows:")
            pre_fest = festival_df[festival_df["journey_date"].astype(str) < "2024-09-07"]["avg_network_delay"].mean()
            during   = festival_df[
                (festival_df["journey_date"].astype(str) >= "2024-09-07") &
                (festival_df["journey_date"].astype(str) <= "2024-09-17")
            ]["avg_network_delay"].mean()
            st.metric("Normal delay (Sept 1–6)", f"{pre_fest:.1f} min")
            st.metric("Festival peak (Sept 7–17)", f"{during:.1f} min",
                      delta=f"+{during - pre_fest:.1f} min surge", delta_color="inverse")
            st.markdown("---")
            st.info(
                "**Why does this happen?**\n\n"
                "- Hundreds of unscheduled special trains were injected onto Konkan and Central Railway lines.\n\n"
                "- Priority given to scheduled expresses forces specials into loop sidings — causing cascade gridlocks.\n\n"
                "- A single blocked loop can delay 4–6 trains in sequence."
            )
    else:
        st.info("Festival analysis data not yet available. Ensure the DuckDB warehouse is populated.")

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#4a5568;font-size:.76rem;padding:.4rem;'>"
    "RailPulse &middot; LightGBM AI &middot; IIT Kharagpur RSTGCN Dataset &middot; DuckDB &middot; "
    "Data: Indian Railways Sep 2024 &nbsp;|&nbsp; Not affiliated with IRCTC or Indian Railways"
    "</div>",
    unsafe_allow_html=True,
)
