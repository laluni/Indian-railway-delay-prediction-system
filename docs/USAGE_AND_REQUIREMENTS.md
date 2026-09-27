# Requirements and Usage Guide

## 1. System Requirements

### Hardware:
* **Operating System**: Windows 10/11, macOS, or Linux.
* **Processor**: Multi-core modern CPU (x86_64 or ARM64).
* **RAM**: 8 GB minimum (16 GB recommended for 1.5M row processing).
* **Storage**: ~1.5 GB free disk space (includes dataset, virtual environment, and DuckDB storage).

### Software & Environment:
* **Python**: `3.10` to `3.13` (Developed & verified on Python 3.13.3).
* **Core Libraries**:
  * `polars>=1.0.0`
  * `duckdb>=1.0.0`
  * `lightgbm>=4.3.0`
  * `xgboost>=3.0.0`
  * `scikit-learn>=1.5.0`
  * `networkx>=3.2.0`
  * `streamlit>=1.35.0`
  * `plotly>=5.20.0`
  * `joblib>=1.4.0`
  * `pytest>=8.0.0`

---

## 2. Installation & Setup

### Step 1: Clone or Navigate to Project
```powershell
cd "Indian railway"
```

### Step 2: Create Virtual Environment
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

## 3. Running the Pipeline

### Step 1: Run Big Data ETL (Loads into DuckDB)
```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe src\etl.py
```

### Step 2: Run Scientific Benchmark & Ablation Study
```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe src\benchmark.py
```

### Step 3: Train Champion Models (LightGBM)
```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe src\train.py
```

### Step 4: Run Automated Test Suite
```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\pytest.exe tests/
```

---

## 4. Launching the Web Dashboard

### Windows Shortcut:
Simply double-click `run_app.bat` or run in terminal:
```powershell
.\.venv\Scripts\streamlit.exe run app\dashboard.py
```
Open your browser at: **`http://localhost:8501`**

---

## 5. Dashboard Features & User Interaction Modes

### Tab 1: Live Journey Forecaster (Dual-Mode Design)
* **👤 Passenger / Commuter View (Zero-Effort Default)**:
  * Users **never** enter operational parameters like speed restrictions, rake turnarounds, or active corridor delay pressure.
  * The user simply selects a **Train Number**.
  * The system automatically looks up timetable specs, inspects whether the incoming trainset was delayed on its prior run, evaluates seasonal fog alerts, and calculates rolling corridor congestion.
  * Clicking **"🔮 Forecast Delay"** delivers the predicted delay minutes, delay probability gauge, and risk tier in < 1 ms.
* **🔬 Evaluator / What-If View**:
  * Provides manual sliders and overrides for academic evaluators, mentors, or panel judges to test extreme synthetic edge cases.

### Tab 2: Network Bottleneck Map
* Direct SQL connection to local DuckDB (1.5M rows) rendering:
  * Zone-level average delay rankings color-coded by congestion index.
  * Topological Betweenness Centrality table highlighting structural chokepoint hubs.

### Tab 3: Scientific Benchmark & Ablation
* Interactive leaderboard comparing **Ridge Regression vs. Random Forest vs. XGBoost vs. LightGBM**.
* Ablation study quantifying the exact error reduction (-0.53 mins) and AUC gain (+0.0059) from the engineered cascade features.

### Tab 4: Rake Cascade Simulator
* Interactive what-if sandbox demonstrating how a turnaround buffer deficit causes exponential delay propagation across consecutive services.
