"""
Feature engineering pipeline for delay cascades.
Computes:
1. Rake cascade chain length (consecutive delayed runs on shared rakes)
2. Zone delay pressure (rolling average delay per zone)
3. Graph centrality features (from graph_builder)
"""
import time
from pathlib import Path
import duckdb
import polars as pl
from src.graph_builder import get_zone_centrality_metrics

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "db" / "railway.duckdb"

def engineer_cascade_features(sample_limit=None):
    """
    Reads data from DuckDB, computes cascade propagation features, and returns
    an enriched Polars DataFrame ready for model training.
    """
    print("=" * 60)
    print("Deriving Cascade & Network Features")
    print("=" * 60)
    t0 = time.time()
    
    # 1. Fetch zone centrality scores
    zone_metrics = get_zone_centrality_metrics()
    
    # Connect to DuckDB
    con = duckdb.connect(str(DB_PATH), read_only=True)
    
    limit_clause = f"LIMIT {sample_limit}" if sample_limit else ""
    
    # Extract data sorted by train and schedule for sequential cascade tracing
    query = f"""
        SELECT 
            journey_id,
            train_number,
            train_type,
            departure_date,
            year,
            month,
            day_of_week,
            departure_hour,
            is_weekend,
            is_night_departure,
            is_peak_hour,
            is_festival_season,
            season,
            zone_abbr,
            source_station_category,
            destination_station_category,
            distance_km,
            num_scheduled_stops,
            scheduled_travel_hours,
            track_doubled,
            is_hdn_route,
            traction_type,
            is_electrified,
            psr_count,
            is_circular_route,
            is_monsoon_season,
            is_fog_risk,
            fog_risk_score,
            zone_fog_index,
            zone_congestion_index,
            season_severity_score,
            loco_age_years,
            coach_age_years,
            has_lhb_coaches,
            is_rake_shared,
            maintenance_score,
            seat_utilisation_pct,
            is_overloaded,
            late_incoming_rake,
            is_special_train,
            route_historical_ontime_pct,
            delay_minutes,
            is_delayed
        FROM journeys
        ORDER BY train_number, departure_date, departure_hour
        {limit_clause};
    """
    
    print("[1/3] Fetching sorted journey records from DuckDB...")
    arrow_table = con.execute(query).arrow()
    df = pl.from_arrow(arrow_table)
    con.close()
    
    print(f"[2/3] Computing Rake Cascade chains and Zone Delay Pressure on {len(df):,} rows...")
    
    # Feature A: Rake Cascade Chain Length
    # When a rake is shared and incoming rake is late, delay risk compounds
    df = df.with_columns(
        (pl.col("late_incoming_rake") * pl.col("is_rake_shared"))
        .cum_sum()
        .over("train_number")
        .cast(pl.Int32)
        .alias("rake_cascade_chain_length")
    )
    
    # Feature B: Zone Delay Pressure (Rolling average delay across zone journeys)
    df = df.with_columns(
        pl.col("delay_minutes")
        .rolling_mean(window_size=20, min_samples=1)
        .over("zone_abbr")
        .fill_null(0.0)
        .cast(pl.Float32)
        .alias("zone_delay_pressure")
    )
    
    # Feature C: Map Graph Betweenness & Degree Centrality from NetworkX
    betweenness_map = {z: m["corridor_betweenness_centrality"] for z, m in zone_metrics.items()}
    degree_map = {z: m["corridor_degree_centrality"] for z, m in zone_metrics.items()}
    
    df = df.with_columns([
        pl.col("zone_abbr").replace_strict(betweenness_map, default=0.0).cast(pl.Float32).alias("corridor_betweenness_centrality"),
        pl.col("zone_abbr").replace_strict(degree_map, default=0.0).cast(pl.Float32).alias("corridor_degree_centrality")
    ])
    
    elapsed = time.time() - t0
    print(f"[3/3] Feature extraction completed in {elapsed:.2f}s! Enriched dataset has {len(df.columns)} columns.")
    return df

if __name__ == "__main__":
    enriched_df = engineer_cascade_features(sample_limit=100000)
    print("\nSample engineered features:")
    print(enriched_df.select([
        "train_number", "zone_abbr", "is_rake_shared", "late_incoming_rake", 
        "rake_cascade_chain_length", "zone_delay_pressure", "corridor_betweenness_centrality"
    ]).head(5))
