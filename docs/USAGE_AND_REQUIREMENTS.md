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

## 5. Dashboard Walkthrough & Features

### 🎯 Tab 1: Check My Train
* **👤 Commuter Mode (Zero-Effort Default)**:
  * Select a train from the dropdown (e.g. express train 12441).
  * The backend automatically auto-populates route specs, inspects whether the incoming trainset was delayed on its prior run (`late_incoming_rake`), evaluates seasonal fog/weather alerts, and queries DuckDB for rolling corridor congestion.
  * Displays automatic diagnostic badges (Rake status, Weather risk, Corridor delay pressure).
* **🔬 What-If Simulator (Advanced)**:
  * Provides manual sliders for zone, distance, stop count, scheduled travel time, departure hour, HDN status, fog conditions, rake sharing, and active zone delay pressure to simulate extreme edge cases.
* **🔮 AI Delay Forecast**:
  * Predicts continuous arrival delay in minutes, probability of exceeding the 15-minute IRCTC threshold, and risk tier (LOW, MEDIUM, HIGH).
* **🚉 Journey Delay Waterfall Map**:
  * Interactive Plotly chart showing cumulative arrival delay curve alongside section-by-section delay additions ($\Delta_{\text{running}}$) and buffer time recoveries across the entire route.
* **🚨 Worst Sections on Route**:
  * Highlights the top 3 worst delay-accumulating track segments on the chosen train's journey.
* **📋 Full Timing Log**:
  * Expandable table containing scheduled vs. actual arrival/departure times, section distance, and station dwell deltas.

### 🗺️ Tab 2: Network Hotspots
* **Zone Delay Rankings**: Interactive bar chart comparing average delay across all 16 railway zones, color-coded by congestion index.
* **Network Centrality Table**: Ranks railway zones by topological Betweenness Centrality computed from the 16-zone NetworkX graph.
* **Top 10 Chronic National Track Bottlenecks**: Horizontal bar chart identifying segments across India where trains chronically lose time, with delay frequency and delay gradient metrics.

### 📊 Tab 3: AI Performance
* Multi-model benchmark leaderboard comparing **Ridge Regression vs. Random Forest vs. XGBoost vs. LightGBM** across MAE, RMSE, $R^2$, AUC-ROC, Training Time, and Inference Latency.
* Interactive Plotly charts visualizing prediction error (MAE) and delay detection accuracy (AUC-ROC).

### ⚡ Tab 4: Cascade Simulator
* Interactive what-if sandbox simulating how a delay on an incoming trainset ripples across consecutive turnaround services.
* Configurable incoming delay (0–180 mins), maintenance buffer time (30–180 mins), and number of turnaround services.

### 🪔 Tab 5: Festival Rush
* Empirical analysis of the **Ganesh Chaturthi (Sept 2024)** festival rush.
* Visualizes daily average network delays, highlighting the +14.3 minute delay surge during festival peak dates (Sept 7–17, 2024) caused by unscheduled special trains and loop siding cascade gridlocks.
