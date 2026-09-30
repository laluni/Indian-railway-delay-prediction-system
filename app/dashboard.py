"""
RailPulse - Will my train be late?
Simple, plain-language delay forecasts for Indian Railways passengers.
"""
import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import duckdb
import polars as pl

from src.predictor import DelayPredictor
from src.graph_builder import get_zone_centrality_metrics
from src.trajectory_profiler import TrajectoryProfiler

st.set_page_config(page_title="RailPulse - Will my train be late?", page_icon="🚆",
                   layout="centered", initial_sidebar_state="collapsed")

# ─── Colours & style: light, high contrast, big text ─────────────────────────
GREEN, AMBER, RED, BLUE = "#1f7a4d", "#b45309", "#b42318", "#1d4ed8"
INK, MUTED = "#14213d", "#4b5563"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&display=swap');
html, body, [class*="css"], .stApp {{ font-family:'Atkinson Hyperlegible', Arial, sans-serif; }}
.stApp {{ background:#f6f7f9; color:{INK}; }}
#MainMenu, footer, header {{ visibility:hidden; }}
.block-container {{ padding-top:1.5rem; max-width:860px; }}
h1 {{ font-size:2.2rem !important; margin-bottom:0 !important; color:{INK}; }}
.stApp .sub {{ font-size:1.1rem; margin:.2rem 0 1.2rem; }}
.step {{ font-size:1.25rem; font-weight:700; margin:1.6rem 0 .6rem; color:{INK}; }}
.verdict {{ border-radius:14px; padding:1.5rem 1.6rem; background:#fff; border:2px solid var(--c); }}
.verdict .big {{ font-size:2.4rem; font-weight:700; color:var(--c); line-height:1.15; }}
.verdict .txt {{ font-size:1.1rem; margin-top:.5rem; color:{INK}; }}
.tip {{ background:#fff; border-left:5px solid var(--c); border-radius:8px; padding:.8rem 1rem;
        margin:.5rem 0; font-size:1.02rem; }}
[data-testid="stTabs"] [role="tab"] {{ font-size:1.05rem; font-weight:700; padding:.7rem 1rem; }}
[data-testid="metric-container"] {{ background:#fff; border:1px solid #e5e7eb; border-radius:10px; padding:.7rem 1rem; }}

.stApp, .stApp p, .stApp label, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
[data-testid="stMarkdownContainer"] {{ color:{INK}; }}
.stApp .sub, [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{ color:{MUTED}; }}
[data-baseweb="select"] > div, [data-baseweb="input"], input, textarea {{ background:#fff !important; color:{INK} !important; border-color:#cbd5e1 !important; }}
[data-baseweb="select"] * {{ color:{INK} !important; }}
[data-baseweb="popover"] ul, [data-baseweb="popover"] li, [data-baseweb="menu"] {{ background:#fff !important; color:{INK} !important; }}
[data-baseweb="popover"] li:hover {{ background:#e8effc !important; }}
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * {{ color:{INK} !important; }}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * {{ color:{MUTED} !important; }}
[data-testid="stExpander"] details {{ background:#fff; border:1px solid #e5e7eb; border-radius:10px; }}
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary * {{ color:{INK} !important; }}
[data-testid="stAlert"] {{ background:#fff !important; border:1px solid #d1d5db; border-left:5px solid {BLUE}; }}
[data-testid="stAlert"] * {{ color:{INK} !important; }}
[data-testid="stTabs"] [role="tab"] {{ color:{MUTED}; }}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {{ color:{BLUE}; }}
[data-testid="stTickBarMin"], [data-testid="stTickBarMax"] {{ color:{MUTED} !important; }}
[data-testid="stToggle"] p, [data-testid="stCheckbox"] p {{ color:{INK} !important; }}
.legend {{ display:flex; gap:1.2rem; flex-wrap:wrap; font-size:.95rem; margin:.3rem 0 .6rem; color:{INK}; }}
.legend i {{ display:inline-block; width:12px; height:12px; border-radius:50%; margin-right:.35rem; vertical-align:-1px; }}
.route {{ max-height:560px; overflow-y:auto; background:#fff; border:1px solid #d1d5db; border-radius:12px; padding:.4rem 1rem; }}
.stop {{ display:flex; gap:.9rem; }}
.rail {{ position:relative; width:22px; flex:none; }}
.rail:before {{ content:""; position:absolute; left:9px; top:0; bottom:0; width:4px; background:#cbd5e1; }}
.stop:first-child .rail:before {{ top:26px; }}
.stop:last-child .rail:before {{ bottom:calc(100% - 26px); }}
.dot {{ position:absolute; left:2px; top:17px; width:18px; height:18px; border-radius:50%; background:var(--c); border:3px solid #fff; box-shadow:0 0 0 2px var(--c); }}
.info {{ flex:1; display:flex; justify-content:space-between; align-items:center; gap:1rem; padding:.6rem 0; border-bottom:1px solid #eef0f3; }}
.sname {{ font-weight:700; color:{INK}; font-size:1.02rem; }}
.stime {{ color:{MUTED}; font-size:.9rem; }}
.lost {{ font-size:.9rem; font-weight:700; }}
.badge {{ background:var(--c); color:#fff; border-radius:999px; padding:.2rem .8rem; font-weight:700; font-size:.92rem; white-space:nowrap; }}
</style>
""", unsafe_allow_html=True)

DATA_DIR = BASE_DIR / "data"
TEST_CSV = DATA_DIR / "ir_test.csv"
DB_PATH = BASE_DIR / "db" / "railway.duckdb"
BENCHMARK_PATH = BASE_DIR / "models" / "benchmark_report.json"


def note(text, color):
    st.markdown(f'<div class="tip" style="--c:{color}">{text}</div>', unsafe_allow_html=True)


def style_fig(fig, height=380):
    fig.update_layout(template="plotly_white", height=height, font=dict(size=14, color=INK),
                      margin=dict(l=10, r=10, t=50, b=10), paper_bgcolor="#ffffff", plot_bgcolor="#ffffff")
    return fig


# ─── Data loading (unchanged logic) ──────────────────────────────────────────
@st.cache_resource
def load_services():
    return DelayPredictor(), TrajectoryProfiler()


@st.cache_data
def load_benchmark_report():
    if BENCHMARK_PATH.exists():
        with open(BENCHMARK_PATH, "r") as f:
            return json.load(f)
    return None


@st.cache_data
def load_sample_trains():
    if DB_PATH.exists():
        df = TrajectoryProfiler().get_available_trains(limit=500)
        if not df.empty:
            return df
    if TEST_CSV.exists():
        df = pl.read_csv(str(TEST_CSV), n_rows=400).to_pandas()
        df["display_label"] = ("Train " + df["train_number"].astype(str) + " - " + df["train_type"]
                               + " (" + df["zone_abbr"] + " | " + df["distance_km"].astype(str) + " km)")
        return df
    return pd.DataFrame()


@st.cache_data
def load_zone_analytics():
    if not DB_PATH.exists():
        return pd.DataFrame()
    con = duckdb.connect(str(DB_PATH), read_only=True)
    df = con.execute("""
        SELECT zone_abbr, count(*) as total_journeys,
               round(avg(delay_minutes), 1) as avg_delay_minutes,
               round(avg(is_delayed) * 100, 1) as delay_rate_pct,
               round(avg(zone_congestion_index), 2) as avg_congestion
        FROM journeys GROUP BY zone_abbr ORDER BY avg_delay_minutes DESC
    """).fetchdf()
    con.close()
    return df


predictor, profiler = load_services()
benchmark_data = load_benchmark_report()
sample_trains_df = load_sample_trains()
zone_df = load_zone_analytics()
zone_centrality = get_zone_centrality_metrics()

# ─── Header ──────────────────────────────────────────────────────────────────
st.markdown("# 🚆 RailPulse")
st.markdown('<p class="sub">Will your train be late? Pick a train and find out.</p>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["Check my train", "Trouble spots", "Coach chain reaction", "Festival rush"])

# ==============================================================================
# TAB 1: CHECK MY TRAIN
# ==============================================================================
with tab1:
    st.markdown('<div class="step">1. Choose your train</div>', unsafe_allow_html=True)
    selected_train_num = None
    advanced = st.toggle("I want to try my own what-if settings", value=False)

    if not advanced and not sample_trains_df.empty:
        sel_label = st.selectbox("Train", sample_trains_df["display_label"].tolist(),
                                 index=min(3, len(sample_trains_df) - 1), label_visibility="collapsed")
        row = sample_trains_df[sample_trains_df["display_label"] == sel_label].iloc[0]
        selected_train_num = str(row["train_number"])
        zone_abbr = str(row.get("zone_abbr", "NR"))
        st.caption(f"{row.get('train_type', 'Express')} · {row.get('distance_km', '—')} km · {zone_abbr} zone")

        late_rake = bool(row.get("late_incoming_rake", 0) == 1)
        fog = bool(row.get("fog_risk_score", 0.0) > 0.5)
        pressure = float(row.get("avg_delay_mins", 42.0))

        st.markdown('<div class="step">2. What could affect it today?</div>', unsafe_allow_html=True)
        if late_rake:
            note("⚠️ <b>Coaches ran late on their last trip.</b> This train may leave late.", AMBER)
        else:
            note("✅ <b>Coaches arrived on time.</b> Departure looks normal.", GREEN)
        if fog:
            note("🌫️ <b>Fog is likely</b> on this route. Trains may run slower.", AMBER)
        else:
            note("☀️ <b>Weather looks clear</b> on this route.", GREEN)
        note(f"🚦 <b>Busy tracks:</b> trains in this zone are running about {pressure:.0f} min late on average.",
             RED if pressure >= 45 else BLUE)

        centrality = zone_centrality.get(zone_abbr, {"corridor_betweenness_centrality": 0.0,
                                                     "corridor_degree_centrality": 0.0})
        dist = int(row.get("distance_km", 850))
        features = {
            "zone_abbr": zone_abbr, "train_type": str(row.get("train_type", "Superfast Express")),
            "season": str(row.get("season", "Winter/Fog")), "distance_km": dist,
            "num_scheduled_stops": int(row.get("stop_count", 14)),
            "scheduled_travel_hours": float(dist / 60.0), "departure_hour": 8, "is_peak_hour": 1,
            "is_hdn_route": 1 if zone_abbr in ["NR", "NCR", "ECR"] else 0,
            "is_fog_risk": 1 if fog else 0,
            "fog_risk_score": float(row.get("fog_risk_score", 0.65)) if fog else 0.15,
            "zone_congestion_index": 0.85, "late_incoming_rake": 1 if late_rake else 0,
            "is_rake_shared": 1, "rake_cascade_chain_length": 2 if late_rake else 0,
            "zone_delay_pressure": pressure, "route_historical_ontime_pct": 72.0,
            "loco_age_years": 10.0, "coach_age_years": 7.0, "maintenance_score": 8.0,
            "seat_utilisation_pct": 88.0, "is_overloaded": 0, "is_monsoon_season": 0,
            "corridor_betweenness_centrality": centrality["corridor_betweenness_centrality"],
            "corridor_degree_centrality": centrality["corridor_degree_centrality"],
        }
    else:
        st.caption("Change any setting below. The forecast updates right away.")
        c1, c2 = st.columns(2)
        with c1:
            sel_zone = st.selectbox("Railway zone", sorted(list(zone_centrality.keys())))
            sel_train_type = st.selectbox("Type of train", ["Superfast Express", "Mail/Express",
                                          "Vande Bharat Express", "Rajdhani Express", "Passenger"])
            sel_season = st.selectbox("Season", ["Winter/Fog", "Monsoon", "Summer", "Pre-Monsoon", "Autumn"])
            distance = st.slider("Journey length (km)", 100, 3000, 850, step=50)
            num_stops = st.slider("Number of stops", 1, 40, 14)
            scheduled_hours = st.slider("Scheduled journey time (hours)", 2.0, 48.0, 14.5, step=0.5)
        with c2:
            departure_hour = st.slider("Departure hour (0–23)", 0, 23, 8)
            route_ontime = st.slider("How often this route is on time (%)", 30.0, 99.0, 68.0, step=1.0)
            zone_delay = st.slider("Current delays in this zone (min)", 0.0, 120.0, 55.0, step=5.0)
            is_hdn = st.checkbox("Very busy route", value=True)
            is_fog = st.checkbox("Heavy fog today", value=(sel_season == "Winter/Fog"))
            is_shared_rake = st.checkbox("Coaches are reused by other trains", value=True)
            late_rake = st.checkbox("Coaches are arriving late", value=True)
            chain_len = st.number_input("How many trains use these coaches after this one",
                                        min_value=0, max_value=10, value=2 if late_rake else 0)
        centrality = zone_centrality.get(sel_zone, {"corridor_betweenness_centrality": 0.0,
                                                    "corridor_degree_centrality": 0.0})
        features = {
            "zone_abbr": sel_zone, "train_type": sel_train_type, "season": sel_season,
            "distance_km": distance, "num_scheduled_stops": num_stops,
            "scheduled_travel_hours": scheduled_hours, "departure_hour": departure_hour,
            "is_peak_hour": 1 if departure_hour in [6, 7, 8, 17, 18, 19] else 0,
            "is_hdn_route": 1 if is_hdn else 0, "is_fog_risk": 1 if is_fog else 0,
            "fog_risk_score": 0.85 if is_fog else 0.0,
            "zone_congestion_index": 0.85 if is_hdn else 0.5,
            "late_incoming_rake": 1 if late_rake else 0, "is_rake_shared": 1 if is_shared_rake else 0,
            "rake_cascade_chain_length": chain_len, "zone_delay_pressure": zone_delay,
            "route_historical_ontime_pct": route_ontime, "loco_age_years": 12.0,
            "coach_age_years": 8.0, "maintenance_score": 6.5, "seat_utilisation_pct": 88.0,
            "is_overloaded": 0, "is_monsoon_season": 1 if sel_season == "Monsoon" else 0,
            "corridor_betweenness_centrality": centrality["corridor_betweenness_centrality"],
            "corridor_degree_centrality": centrality["corridor_degree_centrality"],
        }
        selected_train_num = "22503"

    # ── Forecast ───────────────────────────────────────────────────────────────
    prediction = predictor.predict(features)
    delay_mins = prediction["predicted_delay_minutes"]
    delay_prob = prediction["delay_probability_pct"]

    if delay_mins >= 60:
        color, headline, advice = RED, "Expect a long delay", "Plan extra time and check the station board before you leave."
    elif delay_mins >= 20:
        color, headline, advice = AMBER, "Expect some delay", "Leave a little extra time, especially if you have a connection."
    else:
        color, headline, advice = GREEN, "Should be on time", "No big delay expected. Arrive at the usual time."

    st.markdown('<div class="step">3. Your forecast</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="verdict" style="--c:{color}">
      <div class="big">{headline}</div>
      <div class="txt">About <b>{delay_mins} minutes late</b> at the destination.
      There is a <b>{delay_prob}% chance</b> it will be more than 15 minutes late.</div>
      <div class="txt" style="color:{MUTED}">{advice}</div>
    </div>""", unsafe_allow_html=True)
    st.caption("This is an estimate from past train data, not an official announcement.")

    # ── Where delay builds up ──────────────────────────────────────────────────
    if selected_train_num:
        st.markdown('<div class="step">4. Where does the delay happen?</div>', unsafe_allow_html=True)
        traj_df, m = profiler.get_route_trajectory(selected_train_num)

        if not traj_df.empty:
            a, b, c = st.columns(3)
            a.metric("Lost while moving", f"{m['total_track_loss_mins']} min",
                     help="Time added between stations")
            b.metric("Lost at platforms", f"{m['total_dwell_loss_mins']} min",
                     help="Extra time standing at stations")
            c.metric("Made up", f"{m['total_buffer_recovered_mins']} min",
                     help="Time recovered by running faster")

            st.markdown("**Delay along the route**")
            x_labels = traj_df["station_name"]
            fig = go.Figure(go.Scatter(
                x=x_labels, y=traj_df["arr_delay_mins"], mode="lines", line=dict(color=BLUE, width=3, shape="spline"),
                fill="tozeroy", fillcolor="rgba(29,78,216,.10)",
                hovertemplate="<b>%{x}</b><br>%{y:.0f} min late<extra></extra>"))
            fig.add_hline(y=15, line_dash="dot", line_color=AMBER, annotation_text="15 min = officially late",
                          annotation_font_color=AMBER)
            style_fig(fig, 260).update_layout(xaxis=dict(showticklabels=False, title="Start  →  End of journey"),
                                              yaxis_title="Minutes late", showlegend=False,
                                              margin=dict(l=10, r=10, t=20, b=40))
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("**Station by station**")
            st.markdown(f'<div class="legend"><span><i style="background:{GREEN}"></i>On time (0–5 min)</span>'
                        f'<span><i style="background:{AMBER}"></i>Late (6–30 min)</span>'
                        f'<span><i style="background:{RED}"></i>Very late (over 30 min)</span></div>',
                        unsafe_allow_html=True)

            def num(v):
                try:
                    v = float(v)
                    return 0.0 if v != v else v
                except Exception:
                    return 0.0

            rows = []
            for r in traj_df.to_dict("records"):
                d = num(r.get("arr_delay_mins"))
                c = GREEN if d <= 5 else (AMBER if d <= 30 else RED)
                badge = "On time" if d <= 5 else f"{d:.0f} min late"
                step = num(r.get("running_delay_delta")) + num(r.get("dwell_delay_delta"))
                if step >= 5:
                    extra = f'<div class="lost" style="color:{RED}">Lost {step:.0f} min getting here</div>'
                elif step <= -3:
                    extra = f'<div class="lost" style="color:{GREEN}">Made up {abs(step):.0f} min</div>'
                else:
                    extra = ""
                due, act = r.get("sch_arr_time"), r.get("act_arr_time")
                times = f'<div class="stime">Due {due} · Actual {act}</div>' if due is not None and act is not None else ""
                rows.append(f'<div class="stop"><div class="rail"><div class="dot" style="--c:{c}"></div></div>'
                            f'<div class="info"><div><div class="sname">{r.get("station_name")} '
                            f'<span class="stime">({r.get("station_code")})</span></div>{times}{extra}</div>'
                            f'<div class="badge" style="--c:{c}">{badge}</div></div></div>')
            st.markdown('<div class="route">' + "".join(rows) + '</div>', unsafe_allow_html=True)

            if m.get("worst_sections"):
                st.markdown("**Slowest parts of this journey**")
                for i, w in enumerate(m["worst_sections"], 1):
                    note(f"<b>{i}. {w['section_name']}</b> ({w['section']}): "
                         f"adds <b>{w['delay_added']}</b> over {w['distance']}. {w['status']}", RED)

            with st.expander("See every station"):
                cols = [c for c in ["stop_sequence", "station_name", "sch_arr_time", "act_arr_time",
                                    "arr_delay_mins"] if c in traj_df.columns]
                st.dataframe(traj_df[cols].rename(columns={
                    "stop_sequence": "Stop", "station_name": "Station", "sch_arr_time": "Due",
                    "act_arr_time": "Actual", "arr_delay_mins": "Minutes late"}),
                    use_container_width=True, hide_index=True)
        else:
            st.info("No station-by-station data for this train. Try another train from the list.")

# ==============================================================================
# TAB 2: TROUBLE SPOTS
# ==============================================================================
with tab2:
    st.markdown('<div class="step">Which railway zones run latest?</div>', unsafe_allow_html=True)
    st.caption("Based on 1.28 million real train stops in September 2024. Shorter bars are better.")
    if not zone_df.empty:
        fig = px.bar(zone_df, x="zone_abbr", y="avg_delay_minutes", color="avg_delay_minutes",
                     color_continuous_scale=["#93c5fd", "#f59e0b", "#b42318"],
                     labels={"zone_abbr": "Zone", "avg_delay_minutes": "Average delay (min)"})
        style_fig(fig).update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
        worst = zone_df.iloc[0]
        st.info(f"**{worst['zone_abbr']}** has the longest average delay: {worst['avg_delay_minutes']} min. "
                f"{worst['delay_rate_pct']}% of its trains were late.")

    st.markdown('<div class="step">Track sections where trains lose the most time</div>', unsafe_allow_html=True)
    cp = profiler.get_national_chokepoints(limit=10)
    if not cp.empty:
        fig = px.bar(cp.head(10), x="avg_minutes_lost", y="section", orientation="h",
                     color="avg_minutes_lost", color_continuous_scale=["#f59e0b", "#b42318"],
                     labels={"section": "", "avg_minutes_lost": "Average minutes lost"})
        style_fig(fig, 420).update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
        with st.expander("See the full table"):
            st.dataframe(cp.rename(columns={
                "section": "Track section", "distance_km": "Length (km)", "sample_runs": "Trains observed",
                "avg_minutes_lost": "Avg minutes lost", "delay_frequency_pct": "% of trains late (>5 min)"}),
                use_container_width=True, hide_index=True)

# ==============================================================================
# TAB 3: COACH CHAIN REACTION
# ==============================================================================
with tab3:
    st.markdown('<div class="step">One late train can make the next ones late</div>', unsafe_allow_html=True)
    st.write("The same set of coaches (called a rake) is often used for several trips a day. "
             "If the first trip is late, the next trip may start late too.")
    incoming = st.slider("First train arrives this many minutes late", 0, 180, 75, step=15)
    buffer = st.slider("Time allowed for cleaning and checks (min)", 30, 180, 60, step=15)
    depth = st.slider("Number of trips using these coaches", 1, 5, 4)

    delays, cur = [incoming], max(0, incoming - buffer)
    for _ in range(depth):
        delays.append(cur)
        cur = max(0, int(cur * 0.92 + 10))
    colors = [GREEN if d <= 15 else (AMBER if d <= 60 else RED) for d in delays]
    fig = go.Figure(go.Bar(x=["Trip 1"] + [f"Trip {i + 1}" for i in range(1, len(delays))], y=delays,
                           marker_color=colors, hovertemplate="%{x}: %{y} min late<extra></extra>"))
    fig.add_hline(y=15, line_dash="dot", line_color=AMBER, annotation_text="15 min = late")
    style_fig(fig, 340).update_layout(yaxis_title="Minutes late")
    st.plotly_chart(fig, use_container_width=True)
    if delays[-1] > 15:
        st.error(f"The last trip still starts **{delays[-1]} minutes late**. The delay never fully clears.")
    else:
        st.success("The delay fades away. Later trips should leave close to on time.")

# ==============================================================================
# TAB 4: FESTIVAL RUSH
# ==============================================================================
with tab4:
    st.markdown('<div class="step">Do festivals make trains later?</div>', unsafe_allow_html=True)
    st.write("During Ganesh Chaturthi 2024, many extra trains were added to busy routes. Here is what happened.")
    try:
        con = duckdb.connect(str(DB_PATH), read_only=True)
        fdf = con.execute("""
            SELECT departure_date as journey_date, round(avg(delay_minutes), 1) as avg_network_delay
            FROM journeys GROUP BY departure_date ORDER BY departure_date ASC
        """).fetchdf()
        con.close()
    except Exception:
        fdf = pd.DataFrame()

    if not fdf.empty:
        d = fdf["journey_date"].astype(str)
        pre = fdf[d < "2024-09-07"]["avg_network_delay"].mean()
        during = fdf[(d >= "2024-09-07") & (d <= "2024-09-17")]["avg_network_delay"].mean()
        m1, m2 = st.columns(2)
        m1.metric("Normal days (Sept 1–6)", f"{pre:.1f} min late")
        m2.metric("Festival days (Sept 7–17)", f"{during:.1f} min late",
                  delta=f"+{during - pre:.1f} min", delta_color="inverse")
        fig = px.bar(fdf, x="journey_date", y="avg_network_delay", color_discrete_sequence=[BLUE],
                     labels={"journey_date": "Date", "avg_network_delay": "Average delay (min)"})
        fig.add_vrect(x0="2024-09-07", x1="2024-09-17", fillcolor="#f59e0b", opacity=0.2,
                      annotation_text="Festival", annotation_position="top left")
        style_fig(fig).update_layout(title="Average delay across India, September 2024")
        st.plotly_chart(fig, use_container_width=True)
        st.info("**Why?** Extra special trains share the same tracks. Regular trains get priority, so "
                "specials wait in side tracks, and one blocked track can hold up several trains in a row.")
    else:
        st.info("Festival data is not available yet.")

# ─── About the AI (kept out of the way) ──────────────────────────────────────
with st.expander("How accurate is this forecast?"):
    if benchmark_data and "ablation_study" in benchmark_data:
        ab = benchmark_data["ablation_study"]
        basic = ab["Baseline (Raw Features Only)"]["mae"]
        full = ab["Full Model (Raw + Cascade Features)"]["mae"]
        st.write(f"On 100,000 journeys the model had never seen, its forecast was off by about "
                 f"**{full} minutes** on average. Without knowing about coach reuse, fog and busy tracks, "
                 f"it was off by {basic} minutes.")
    else:
        st.write("Accuracy report not found. Run `python src/benchmark.py` to create it.")

st.caption("RailPulse · Data: Indian Railways, Sep 2024 (IIT Kharagpur RSTGCN dataset) · "
           "Not affiliated with IRCTC or Indian Railways")