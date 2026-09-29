import pytest
from pathlib import Path
import duckdb
from src.trajectory_profiler import TrajectoryProfiler

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "db" / "railway.duckdb"

def test_station_stops_table():
    assert DB_PATH.exists(), f"Database not found at {DB_PATH}"
    con = duckdb.connect(str(DB_PATH), read_only=True)
    count = con.execute("SELECT count(*) FROM station_stops").fetchone()[0]
    con.close()
    assert count > 1000000, f"Expected >1M station stops, found {count}"

def test_section_analytics_table():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    count = con.execute("SELECT count(*) FROM section_analytics").fetchone()[0]
    sample_bottleneck = con.execute("""
        SELECT from_station, to_station, avg_running_delay_delta 
        FROM section_analytics 
        ORDER BY avg_running_delay_delta DESC 
        LIMIT 1
    """).fetchone()
    con.close()
    assert count > 10000, f"Expected >10k section pairs, found {count}"
    assert sample_bottleneck is not None, "Failed to fetch bottleneck record"

def test_trajectory_profiler():
    profiler = TrajectoryProfiler()
    trains = profiler.get_available_trains(limit=5)
    assert not trains.empty, "Expected available express trains"
    
    first_train = trains["train_number"].iloc[0]
    traj_df, metrics = profiler.get_route_trajectory(first_train)
    
    assert not traj_df.empty, f"Expected trajectory stops for train {first_train}"
    assert "running_delay_delta" in traj_df.columns
    assert "dwell_delay_delta" in traj_df.columns
    assert "total_stops" in metrics
    assert metrics["total_stops"] >= 5
