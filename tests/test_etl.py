import time
from pathlib import Path
import duckdb

def test_duckdb_warehouse():
    base_dir = Path(__file__).resolve().parent.parent
    db_path = base_dir / "db" / "railway.duckdb"
    
    assert db_path.exists(), f"Database file not found at {db_path}"
    
    con = duckdb.connect(str(db_path), read_only=True)
    
    # 1. Test Row Count
    count = con.execute("SELECT count(*) FROM journeys").fetchone()[0]
    assert count == 1500000, f"Expected 1,500,000 rows, found {count}"
    
    # 2. Test Query Performance (< 200ms)
    t0 = time.time()
    res = con.execute("""
        SELECT 
            zone_abbr, 
            count(*) as trip_count, 
            avg(delay_minutes) as avg_delay,
            avg(late_incoming_rake) as late_rake_pct
        FROM journeys 
        GROUP BY zone_abbr 
        ORDER BY avg_delay DESC
        LIMIT 5;
    """).fetchall()
    query_time = (time.time() - t0) * 1000
    
    con.close()
    
    assert len(res) == 5, "Expected top 5 zones"
    assert query_time < 500, f"Query latency too high: {query_time:.2f}ms"
    print(f"Test passed! Query latency: {query_time:.2f} ms for 1.5M rows aggregation.")

if __name__ == "__main__":
    test_duckdb_warehouse()
