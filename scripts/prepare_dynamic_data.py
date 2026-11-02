import json
from pathlib import Path
import duckdb
from src.predictor import DelayPredictor
from src.trajectory_profiler import TrajectoryProfiler
from src.graph_builder import get_zone_centrality_metrics

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "db" / "railway.duckdb"

profiler = TrajectoryProfiler()
predictor = DelayPredictor()
zone_centrality = get_zone_centrality_metrics()

train_numbers = ['12301', '22503', '12864', '12507', '16317', '12002', '12504', '16787']
dataset = {}

for train_num in train_numbers:
    traj_df, metrics = profiler.get_route_trajectory(train_num)
    if traj_df.empty:
        continue
    
    # Train summary
    con = duckdb.connect(str(DB_PATH), read_only=True)
    row = con.execute("""
        SELECT train_number, train_name, train_type, zone_abbr, distance_km,
               late_incoming_rake, fog_risk_score, delay_minutes, is_hdn_route
        FROM journeys
        WHERE train_number = ?
        LIMIT 1
    """, [train_num]).fetchone()
    con.close()
    
    if row:
        t_num, t_name, t_type, zone, dist, late_rake, fog_score, actual_delay, is_hdn = row
    else:
        t_num, t_name, t_type, zone, dist, late_rake, fog_score, actual_delay, is_hdn = (
            train_num, metrics['origin_station'] + " Express", "Superfast Express", "NR", metrics['total_distance_km'],
            0, 0.2, metrics['final_destination_delay'], 1
        )
    
    centrality = zone_centrality.get(zone, {"corridor_betweenness_centrality": 0.05, "corridor_degree_centrality": 0.05})
    
    features = {
        "zone_abbr": zone,
        "train_type": t_type or "Superfast Express",
        "season": "Winter/Fog",
        "distance_km": int(dist or metrics['total_distance_km']),
        "num_scheduled_stops": len(traj_df),
        "scheduled_travel_hours": float((dist or metrics['total_distance_km']) / 65.0),
        "departure_hour": 8,
        "is_peak_hour": 1,
        "is_hdn_route": 1 if is_hdn else 0,
        "is_fog_risk": 1 if (fog_score or 0) > 0.4 else 0,
        "fog_risk_score": float(fog_score or 0.25),
        "zone_congestion_index": 0.82,
        "late_incoming_rake": int(late_rake or 0),
        "is_rake_shared": 1,
        "rake_cascade_chain_length": 2 if late_rake else 0,
        "zone_delay_pressure": 45.0,
        "route_historical_ontime_pct": 74.0,
        "loco_age_years": 8.0,
        "coach_age_years": 6.0,
        "maintenance_score": 8.5,
        "seat_utilisation_pct": 92.0,
        "is_overloaded": 0,
        "is_monsoon_season": 0,
        "corridor_betweenness_centrality": centrality["corridor_betweenness_centrality"],
        "corridor_degree_centrality": centrality["corridor_degree_centrality"]
    }
    
    pred = predictor.predict(features)
    pred_delay = pred["predicted_delay_minutes"]
    pred_prob = pred["delay_probability_pct"]
    risk_tier = pred.get("risk_category", "Moderate Delay")
    
    # Downstream cascade
    impacted = profiler.get_downstream_impacted_trains(train_num, date=metrics.get("journey_date"), limit=5)
    if not impacted:
        # Check any date for this train if current date had none
        con = duckdb.connect(str(DB_PATH), read_only=True)
        other_dates = [r[0] for r in con.execute(
            "SELECT DISTINCT journey_date FROM station_stops WHERE train_number = ? ORDER BY journey_date DESC",
            [train_num]
        ).fetchall()]
        con.close()
        for od in other_dates:
            imp_try = profiler.get_downstream_impacted_trains(train_num, date=str(od), limit=5)
            if imp_try:
                impacted = imp_try
                break
    
    # Clean stops for JSON serialization
    stops_list = []
    for r in traj_df.to_dict("records"):
        stops_list.append({
            "stop_sequence": int(r.get("stop_sequence", 0)),
            "station_code": str(r.get("station_code", "")),
            "station_name": str(r.get("station_name", "")),
            "distance_km": float(r.get("cumulative_distance_km", 0.0) or 0.0),
            "sch_arr_time": str(r.get("sch_arr_time", "--") or "--"),
            "act_arr_time": str(r.get("act_arr_time", "--") or "--"),
            "arr_delay_mins": float(r.get("arr_delay_mins", 0.0) or 0.0),
            "sch_dep_time": str(r.get("sch_dep_time", "--") or "--"),
            "act_dep_time": str(r.get("act_dep_time", "--") or "--"),
            "dep_delay_mins": float(r.get("dep_delay_mins", 0.0) or 0.0),
            "running_delta": float(r.get("running_delay_delta", 0.0) or 0.0),
            "dwell_delta": float(r.get("dwell_delay_delta", 0.0) or 0.0),
            "section_status": str(r.get("section_status", "Normal")),
        })
    
    # Kinematic factor splits
    track_loss = metrics.get('total_track_loss_mins', 0.0)
    dwell_loss = metrics.get('total_dwell_loss_mins', 0.0)
    total_loss = max(1.0, track_loss + dwell_loss)
    track_pct = round((track_loss / total_loss) * 100, 1)
    dwell_pct = round((dwell_loss / total_loss) * 100, 1)
    
    dataset[train_num] = {
        "train_number": str(train_num),
        "train_name": str(t_name),
        "train_type": str(t_type),
        "zone": str(zone),
        "origin": metrics.get("origin_station", "Origin"),
        "destination": metrics.get("destination_station", "Destination"),
        "total_distance_km": int(dist or metrics.get("total_distance_km", 0)),
        "stop_count": len(traj_df),
        "journey_date": metrics.get("journey_date", "2024-09-30"),
        "predicted_delay_mins": int(pred_delay),
        "delay_probability_pct": int(pred_prob),
        "risk_tier": risk_tier,
        "track_loss_mins": track_loss,
        "dwell_loss_mins": dwell_loss,
        "recovered_mins": metrics.get("total_buffer_recovered_mins", 0.0),
        "track_loss_pct": track_pct if track_pct > 0 else 72.0,
        "dwell_loss_pct": dwell_pct if dwell_pct > 0 else 28.0,
        "worst_sections": metrics.get("worst_sections", []),
        "impacted_trains": impacted,
        "stops": stops_list
    }

output_path = BASE_DIR / "UI" / "trains_backend_data.json"
with open(output_path, "w") as f:
    json.dump(dataset, f, indent=2)

print(f"Successfully generated dynamic backend dataset for {len(dataset)} trains at {output_path}")
