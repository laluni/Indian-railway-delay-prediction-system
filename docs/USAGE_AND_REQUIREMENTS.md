# Requirements and Usage Guide

## 1. System Requirements

### Hardware:
* **Operating System**: Windows 10/11, macOS, or Linux (x86_64 or ARM64).
* **Processor**: Multi-core modern CPU (4+ cores recommended for parallel Polars ETL).
* **RAM**: 8 GB minimum (16 GB recommended for high-performance in-memory processing).
* **Storage**: ~2 GB free disk space (includes raw datasets, DuckDB warehouse, virtual environment, and model bundles).

### Software & Environment:
* **Python**: `3.10` to `3.13` (Tested and verified on Python 3.10 and 3.13).
* **Key Dependencies**:
  * `polars>=1.0.0` (Fast multi-threaded Rust dataframe processing)
  * `duckdb>=1.0.0` (In-process columnar SQL database engine)
  * `lightgbm>=4.3.0` (Gradient boosting engine)
  * `xgboost>=3.0.0` (Gradient boosting baseline)
  * `scikit-learn>=1.5.0` (Data preprocessing, metrics, and models)
  * `networkx>=3.2.0` (Graph topology and centrality algorithms)
  * `streamlit>=1.35.0` (Interactive web UI framework)
  * `plotly>=5.20.0` (Interactive data visualizations)
  * `pytest>=8.0.0` (Automated testing suite)
  * `joblib>=1.4.0` (Model serialization)

---

## 2. Installation & Setup

### Step 1: Clone or Navigate to Project
```powershell
cd "Indian-railway-delay-prediction-system"
```

### Step 2: Create & Activate Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

### Step 3: Install Locked Dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
pip install xgboost
```

---

## 3. Running the Complete Pipeline

### Step 1: Ingest Station Delays & Build DuckDB Warehouse
```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe src/station_etl.py
```
*Processes 1.28M station delay records (IIT Kharagpur RSTGCN Sep 2024), calculates track section kinematics, and populates `station_stops`, `section_analytics`, and `journeys` tables in `db/railway.duckdb`.*

### Step 2: Run Exploratory Data Analysis (EDA) & Heatmap Generation
```powershell
# Run full statistical EDA across 1.5M records
.\.venv\Scripts\python.exe src/run_eda.py

# Generate feature correlation matrix and save heatmap
.\.venv\Scripts\python.exe src/generate_heatmap.py
```
*Outputs `models/eda_results.json`, `models/correlation_summary.json`, and `docs/feature_correlation_heatmap.png`.*

### Step 3: Run Scientific Benchmark & Ablation Study
```powershell
.\.venv\Scripts\python.exe src/benchmark.py
```
*Evaluates Ridge, Random Forest, XGBoost, and LightGBM on 100,000 journeys and saves `models/benchmark_report.json`.*

### Step 4: Train Champion Models (LightGBM)
```powershell
.\.venv\Scripts\python.exe src/train.py
```
*Trains dual LightGBM continuous delay regressor and delay probability classifier, saving serialized models to `models/champion_models.pkl`.*

### Step 5: Run Automated Test Suite
```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe -m pytest
```
*Executes all 9 automated unit tests across ETL, Graph Modeling, ML Inference, and Station Trajectory Profiling.*

---

## 4. Launching the Interactive Dashboard

### Windows Shortcut:
Double-click `run_app.bat` or run:
```powershell
.\.venv\Scripts\streamlit.exe run app/dashboard.py
```
Open **`http://localhost:8501`** in your web browser.

---

## 5. Dashboard Walkthrough

The dashboard is designed for passengers and uses plain-language labels:

1. **Find a train**: Start typing its name or number and choose it from the list.
2. **Read the trip summary**: See the recorded route, date, distance, number of stops, and delay at the destination.
3. **Follow the delay**: The chart shows how many minutes early or late the train was at each stop. Hover over a point to see the station name.
4. **Understand time changes**: See recorded time lost between stations, extra time stopped, time made up later, and the sections where delay grew most.
5. **Open the timing table**: Expand the table to compare scheduled and recorded arrival times at each stop.

**Important:** This dashboard displays historical journeys from the local DuckDB database. It is not connected to a live railway feed and does not forecast today's arrival. Use official Indian Railways services for current running status. If the database is missing, build it using `python src/station_etl.py` before launching the dashboard.
