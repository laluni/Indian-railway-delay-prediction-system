"""
Exploratory Data Analysis (EDA) on the full 1.5 Million Indian Railways records in DuckDB.
Computes distributions, root-cause breakdowns, seasonal and zone disparities, and cascade statistics.
"""
import json
from pathlib import Path
import duckdb

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "db" / "railway.duckdb"

def run_full_eda():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    
    eda_data = {}
    
    # 1. High-level dataset summary
    summary = con.execute("""
        SELECT 
            count(*) as total_records,
            round(avg(delay_minutes), 2) as mean_delay,
            round(stddev(delay_minutes), 2) as std_delay,
            min(delay_minutes) as min_delay,
            approx_quantile(delay_minutes, 0.5) as median_delay,
            approx_quantile(delay_minutes, 0.75) as p75_delay,
            approx_quantile(delay_minutes, 0.90) as p90_delay,
            max(delay_minutes) as max_delay,
            round(avg(is_delayed) * 100, 2) as delayed_percentage,
            round(avg(late_incoming_rake) * 100, 2) as late_rake_percentage,
            round(avg(is_rake_shared) * 100, 2) as shared_rake_percentage
        FROM journeys;
    """).fetchall()[0]
    
    eda_data["overall_summary"] = {
        "total_records": summary[0],
        "mean_delay": summary[1],
        "std_delay": summary[2],
        "min_delay": summary[3],
        "median_delay": summary[4],
        "p75_delay": summary[5],
        "p90_delay": summary[6],
        "max_delay": summary[7],
        "delayed_pct": summary[8],
        "late_rake_pct": summary[9],
        "shared_rake_pct": summary[10]
    }
    
    # 2. Delay Distribution by Primary Root Cause
    causes = con.execute("""
        SELECT 
            primary_delay_cause,
            count(*) as count,
            round(count(*) * 100.0 / 1500000, 2) as pct_of_total,
            round(avg(delay_minutes), 1) as avg_delay_minutes,
            round(avg(is_delayed) * 100, 1) as delay_rate_pct
        FROM journeys
        GROUP BY primary_delay_cause
        ORDER BY count DESC;
    """).fetchall()
    eda_data["delay_causes"] = [
        {"cause": r[0], "count": r[1], "pct": r[2], "avg_delay": r[3], "delay_rate": r[4]}
        for r in causes
    ]
    
    # 3. Punctuality by Railway Zone (Ranked)
    zones = con.execute("""
        SELECT 
            zone_abbr,
            count(*) as trips,
            round(avg(delay_minutes), 1) as avg_delay,
            round(avg(is_delayed) * 100, 1) as delay_pct,
            round(avg(zone_congestion_index), 2) as avg_congestion,
            round(avg(late_incoming_rake) * 100, 1) as late_rake_pct
        FROM journeys
        GROUP BY zone_abbr
        ORDER BY avg_delay DESC;
    """).fetchall()
    eda_data["zone_disparity"] = [
        {"zone": r[0], "trips": r[1], "avg_delay": r[2], "delay_pct": r[3], "congestion": r[4], "late_rake_pct": r[5]}
        for r in zones
    ]
    
    # 4. Seasonal & Weather Impact
    seasons = con.execute("""
        SELECT 
            season,
            count(*) as trips,
            round(avg(delay_minutes), 1) as avg_delay,
            round(avg(is_delayed) * 100, 1) as delay_pct,
            round(avg(fog_risk_score), 2) as avg_fog,
            round(avg(season_severity_score), 2) as avg_severity
        FROM journeys
        GROUP BY season
        ORDER BY avg_delay DESC;
    """).fetchall()
    eda_data["seasonal_impact"] = [
        {"season": r[0], "trips": r[1], "avg_delay": r[2], "delay_pct": r[3], "avg_fog": r[4], "avg_severity": r[5]}
        for r in seasons
    ]
    
    # 5. Train Category Disparity (Priority Hierarchy)
    train_types = con.execute("""
        SELECT 
            train_type,
            count(*) as trips,
            round(avg(delay_minutes), 1) as avg_delay,
            round(avg(is_delayed) * 100, 1) as delay_pct,
            round(avg(has_lhb_coaches) * 100, 1) as lhb_pct,
            round(avg(scheduled_travel_hours), 1) as avg_hours
        FROM journeys
        GROUP BY train_type
        ORDER BY avg_delay ASC;
    """).fetchall()
    eda_data["train_types"] = [
        {"train_type": r[0], "trips": r[1], "avg_delay": r[2], "delay_pct": r[3], "lhb_pct": r[4], "avg_hours": r[5]}
        for r in train_types
    ]
    
    # 6. Rake Turnaround Compounding Impact
    rake_compounding = con.execute("""
        SELECT 
            late_incoming_rake,
            is_rake_shared,
            count(*) as count,
            round(avg(delay_minutes), 1) as avg_delay,
            round(avg(is_delayed) * 100, 1) as delay_pct
        FROM journeys
        GROUP BY late_incoming_rake, is_rake_shared
        ORDER BY avg_delay ASC;
    """).fetchall()
    eda_data["rake_compounding"] = [
        {"late_rake": r[0], "shared_rake": r[1], "count": r[2], "avg_delay": r[3], "delay_pct": r[4]}
        for r in rake_compounding
    ]
    
    # 7. Track Infrastructure: Single vs Doubled Track
    tracks = con.execute("""
        SELECT 
            track_doubled,
            is_hdn_route,
            count(*) as trips,
            round(avg(delay_minutes), 1) as avg_delay,
            round(avg(is_delayed) * 100, 1) as delay_pct
        FROM journeys
        GROUP BY track_doubled, is_hdn_route
        ORDER BY avg_delay ASC;
    """).fetchall()
    eda_data["infrastructure"] = [
        {"doubled": r[0], "hdn": r[1], "trips": r[2], "avg_delay": r[3], "delay_pct": r[4]}
        for r in tracks
    ]
    
    con.close()
    
    with open(BASE_DIR / "models" / "eda_results.json", "w") as f:
        json.dump(eda_data, f, indent=4)
        
    print("EDA SQL Analysis Complete! Data saved to models/eda_results.json")
    return eda_data

if __name__ == "__main__":
    run_full_eda()
