"""
Runtime Service for Station-by-Station Delay Localization & Trajectory Profiling.
Queries DuckDB (station_stops & section_analytics) to generate:
1. Route Waterfall profiles (Running Delays vs Buffer Recoveries)
2. Platform Dwell vs Track Deceleration breakdown (Root-cause kinematics)
3. Identification of the worst structural bottleneck sections along any train's path.
"""
from pathlib import Path
import duckdb
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "db" / "railway.duckdb"

class TrajectoryProfiler:
    def __init__(self, db_path=DB_PATH):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"DuckDB database not found at {self.db_path}. Run station_etl.py first.")

    def get_available_trains(self, limit=300):
        """
        Returns a DataFrame of popular express trains with station stops in the database.
        """
        con = duckdb.connect(str(self.db_path), read_only=True)
        query = f"""
            SELECT 
                s.train_number,
                s.train_name,
                count(DISTINCT s.station_code) as stop_count,
                max(s.cumulative_distance_km) as distance_km,
                FIRST(s.zone_abbr) as zone_abbr,
                round(avg(s.arr_delay_mins), 1) as avg_delay_mins,
                COALESCE(round(avg(j.late_incoming_rake)), 0) as late_incoming_rake,
                COALESCE(round(avg(j.fog_risk_score), 2), 0.15) as fog_risk_score
            FROM station_stops s
            LEFT JOIN journeys j ON CAST(s.train_number AS VARCHAR) = CAST(j.train_number AS VARCHAR)
            GROUP BY s.train_number, s.train_name
            HAVING stop_count >= 5
            ORDER BY distance_km DESC
            LIMIT {limit};
        """
        df = con.execute(query).fetchdf()
        con.close()
        
        df["display_label"] = (
            "Train " + df["train_number"].astype(str) + " - " + 
            df["train_name"].astype(str) + " (" + df["zone_abbr"].astype(str) + " | " + 
            df["distance_km"].astype(str) + " km | " + df["stop_count"].astype(str) + " stops)"
        )
        return df

    def get_route_trajectory(self, train_number, date=None):
        """
        Extracts the full station-by-station trajectory for a given train.
        Returns:
            trajectory_df: pandas DataFrame of stops with running and dwell deltas
            metrics: summary dictionary of running loss vs dwell loss and worst bottleneck
        """
        con = duckdb.connect(str(self.db_path), read_only=True)
        
        train_str = str(train_number)
        
        # If no date specified, select the date with the most complete run
        if not date:
            date_query = """
                SELECT journey_date, count(*) as stops
                FROM station_stops
                WHERE train_number = ?
                GROUP BY journey_date
                ORDER BY stops DESC, journey_date DESC
                LIMIT 1;
            """
            best_date_row = con.execute(date_query, [train_str]).fetchone()
            if not best_date_row:
                con.close()
                return pd.DataFrame(), {}
            date = str(best_date_row[0])
            
        stops_query = """
            SELECT 
                stop_sequence,
                station_code,
                station_name,
                zone_abbr,
                cumulative_distance_km,
                section_distance_km,
                prev_station_code,
                sch_arr_time,
                act_arr_time,
                arr_delay_mins,
                sch_dep_time,
                act_dep_time,
                dep_delay_mins,
                running_delay_delta,
                dwell_delay_delta
            FROM station_stops
            WHERE train_number = ? AND journey_date = ?
            ORDER BY stop_sequence ASC;
        """
        df = con.execute(stops_query, [train_str, date]).fetchdf()
        con.close()
        
        if df.empty:
            return pd.DataFrame(), {}
            
        # Classify section types:
        # 'Bottleneck' (running_delay_delta >= 5m)
        # 'Buffer Recovery' (running_delay_delta <= -2m)
        # 'Normal'
        def classify_section(delta):
            if delta >= 10:
                return "Severe Bottleneck (Track Jam)"
            elif delta >= 4:
                return "Moderate Delay Accumulation"
            elif delta <= -3:
                return "Buffer Slack Recovery (Made Up Time)"
            else:
                return "On Schedule"
                
        df["section_status"] = df["running_delay_delta"].apply(classify_section)
        
        # Color coding for Plotly visualizations
        def get_delta_color(delta):
            if delta >= 8:
                return "#E63946"  # Bright Red
            elif delta >= 3:
                return "#F4A261"  # Orange
            elif delta <= -3:
                return "#2A9D8F"  # Teal / Green
            else:
                return "#A8DADC"  # Soft blue/gray
                
        df["waterfall_color"] = df["running_delay_delta"].apply(get_delta_color)
        
        # Compute kinematic breakdown:
        total_running_loss = float(df[df["running_delay_delta"] > 0]["running_delay_delta"].sum())
        total_running_recovery = float(abs(df[df["running_delay_delta"] < 0]["running_delay_delta"].sum()))
        total_dwell_loss = float(df[df["dwell_delay_delta"] > 0]["dwell_delay_delta"].sum())
        final_arr_delay = float(df["arr_delay_mins"].iloc[-1])
        initial_dep_delay = float(df["dep_delay_mins"].iloc[0])
        
        # Worst 3 bottleneck sections
        worst_sections = (
            df[df["section_distance_km"] > 0]
            .sort_values(by="running_delay_delta", ascending=False)
            .head(3)
        )
        worst_list = []
        for _, r in worst_sections.iterrows():
            if r["running_delay_delta"] > 1:
                worst_list.append({
                    "section": f"{r['prev_station_code']} -> {r['station_code']}",
                    "section_name": f"{r['station_name']}",
                    "delay_added": f"+{r['running_delay_delta']:.1f} mins",
                    "distance": f"{r['section_distance_km']} km",
                    "status": r["section_status"]
                })
                
        metrics = {
            "journey_date": date,
            "origin_station": f"{df['station_name'].iloc[0]} ({df['station_code'].iloc[0]})",
            "destination_station": f"{df['station_name'].iloc[-1]} ({df['station_code'].iloc[-1]})",
            "total_stops": len(df),
            "total_distance_km": int(df["cumulative_distance_km"].iloc[-1]),
            "initial_origin_delay": round(initial_dep_delay, 1),
            "final_destination_delay": round(final_arr_delay, 1),
            "total_track_loss_mins": round(total_running_loss, 1),
            "total_dwell_loss_mins": round(total_dwell_loss, 1),
            "total_buffer_recovered_mins": round(total_running_recovery, 1),
            "running_loss_pct": round(total_running_loss / max(1.0, (total_running_loss + total_dwell_loss)) * 100, 1),
            "dwell_loss_pct": round(total_dwell_loss / max(1.0, (total_running_loss + total_dwell_loss)) * 100, 1),
            "worst_sections": worst_list
        }
        
        return df, metrics

    def get_national_chokepoints(self, limit=10):
        """
        Returns the top nationwide track sections where trains chronically lose time.
        """
        con = duckdb.connect(str(self.db_path), read_only=True)
        query = f"""
            SELECT 
                from_station || ' -> ' || to_station as section,
                distance_km,
                sample_runs,
                avg_running_delay_delta as avg_minutes_lost,
                pct_runs_delayed as delay_frequency_pct,
                delay_gradient_per_100km
            FROM section_analytics
            WHERE sample_runs >= 20 AND distance_km >= 10
            ORDER BY avg_running_delay_delta DESC
            LIMIT {limit};
        """
        df = con.execute(query).fetchdf()
        con.close()
        return df

if __name__ == "__main__":
    profiler = TrajectoryProfiler()
    trains = profiler.get_available_trains(limit=5)
    print("Available Sample Trains:")
    print(trains[["train_number", "train_name", "distance_km", "stop_count"]])
    
    if not trains.empty:
        t_num = trains["train_number"].iloc[0]
        traj_df, met = profiler.get_route_trajectory(t_num)
        print(f"\nRoute Trajectory for Train {t_num}:")
        print(f"  Origin: {met['origin_station']} -> Destination: {met['destination_station']}")
        print(f"  Final Delay: {met['final_destination_delay']} mins")
        print(f"  Track Running Loss: {met['total_track_loss_mins']} mins ({met['running_loss_pct']}%)")
        print(f"  Platform Dwell Loss: {met['total_dwell_loss_mins']} mins ({met['dwell_loss_pct']}%)")
        print("\nTop Bottlenecks on Route:")
        for w in met['worst_sections']:
            print(f"   {w['section']} ({w['section_name']}): {w['delay_added']} over {w['distance']}")
