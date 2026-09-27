"""
ETL pipeline for Indian Railways Delay Analytics.
Processes 1.5M records using Polars and loads into a local persistent DuckDB database.
"""
import os
import time
from pathlib import Path
import duckdb
import polars as pl

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_DIR = BASE_DIR / "db"
TRAIN_CSV = DATA_DIR / "ir_train.csv"
DB_PATH = DB_DIR / "railway.duckdb"

def run_etl():
    print("=" * 60)
    print("Starting ETL Pipeline: Polars + DuckDB")
    print("=" * 60)
    
    start_time = time.time()
    DB_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"[1/4] Scanning raw dataset from: {TRAIN_CSV}")
    if not TRAIN_CSV.exists():
        raise FileNotFoundError(f"Dataset not found at {TRAIN_CSV}")
        
    lazy_df = pl.scan_csv(
        str(TRAIN_CSV),
        schema_overrides={
            "journey_id": pl.Utf8,
            "train_number": pl.Utf8,
            "train_type": pl.Categorical,
            "departure_date": pl.Utf8,
            "season": pl.Categorical,
            "zone": pl.Categorical,
            "zone_abbr": pl.Categorical,
            "source_station_category": pl.Categorical,
            "destination_station_category": pl.Categorical,
            "traction_type": pl.Categorical,
            "primary_delay_cause": pl.Categorical,
        }
    )
    
    print("[2/4] Applying data cleansing & standardizations via Polars...")
    cleaned_df = (
        lazy_df
        .with_columns([
            pl.col("departure_date").str.to_date("%Y-%m-%d"),
            pl.col("delay_minutes").fill_null(0).cast(pl.Int32),
            pl.col("is_delayed").fill_null(0).cast(pl.Int8),
            pl.col("late_incoming_rake").fill_null(0).cast(pl.Int8),
            pl.col("is_rake_shared").fill_null(0).cast(pl.Int8),
            pl.col("is_hdn_route").fill_null(0).cast(pl.Int8),
            pl.col("fog_risk_score").fill_null(0.0).cast(pl.Float32),
            pl.col("zone_congestion_index").fill_null(0.5).cast(pl.Float32),
            pl.col("season_severity_score").fill_null(0.5).cast(pl.Float32),
            pl.col("distance_km").cast(pl.Int32),
            pl.col("num_scheduled_stops").cast(pl.Int32),
            pl.col("scheduled_travel_hours").cast(pl.Float32),
        ])
        .collect(streaming=True)
    )
    
    row_count = len(cleaned_df)
    print(f"      Successfully processed {row_count:,} rows across {len(cleaned_df.columns)} columns.")
    
    print(f"[3/4] Ingesting into persistent DuckDB warehouse at: {DB_PATH}")
    if DB_PATH.exists():
        try:
            DB_PATH.unlink()
        except Exception:
            pass
            
    con = duckdb.connect(str(DB_PATH))
    con.register("cleaned_view", cleaned_df)
    con.execute("""
        CREATE TABLE journeys AS 
        SELECT * FROM cleaned_view;
    """)
    
    print("[4/4] Creating optimized analytical indexes...")
    con.execute("CREATE INDEX idx_train_num ON journeys (train_number);")
    con.execute("CREATE INDEX idx_zone ON journeys (zone_abbr);")
    con.execute("CREATE INDEX idx_dep_date ON journeys (departure_date);")
    con.execute("CREATE INDEX idx_hdn ON journeys (is_hdn_route);")
    
    db_count = con.execute("SELECT count(*) FROM journeys").fetchone()[0]
    con.close()
    
    elapsed = time.time() - start_time
    print("=" * 60)
    print(f"ETL Completed Successfully in {elapsed:.2f} seconds!")
    print(f"Total records stored in DuckDB: {db_count:,}")
    print("=" * 60)
    return db_count

if __name__ == "__main__":
    run_etl()
