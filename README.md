# 🚆 Predictive Intelligence System for Indian Railway Delay Cascade Analytics

An end-to-end, high-performance data engineering and machine learning platform designed to model, trace, and forecast network-wide train delay cascades and station-level bottleneck dynamics across Indian Railways.

---

## 📌 Project Overview
While consumer transit apps (*Ixigo*, *Where Is My Train*) track trains linearly via GPS, they fail to model how a single delay blocks shared tracks and platforms, triggering a **cascade delay** on subsequent services. Furthermore, physical freight rakes and passenger trains compete for the same physical corridors, where localized bottlenecks rapidly compound into multi-hour gridlocks.

This system addresses that gap through a dual-granularity architecture:
1. **Station-Level Kinematic Localization**: Ingests **1.28 Million real station delay records** (IIT Kharagpur RSTGCN Dataset, Sep 2024) using **Polars** and an indexed **DuckDB** analytical warehouse. Computes track running deltas ($\Delta_{\text{running}}$) and platform dwell deltas ($\Delta_{\text{dwell}}$) across thousands of track sections.
2. **Network-Wide Topological Graph**: Models India's **16 railway zones and High-Density Network (HDN) corridors** using **NetworkX** to compute Betweenness Centrality and quantify structural network chokepoints.
3. **Scientific Machine Learning Benchmark**: Evaluates Ridge, Random Forest, XGBoost, and LightGBM on 100,000 journeys alongside an empirical **ablation study** proving the predictive power of engineered cascade features.
4. **Interactive 5-Tab Web Dashboard (Streamlit & Plotly)**:
   * 🎯 **Check My Train**: Commuter zero-effort mode (auto-inferred rake turnaround, weather, and congestion) & What-If simulator with real-time AI delay forecast, probability gauge, station-by-station trajectory waterfall map, and worst bottleneck localization.
   * 🗺️ **Network Hotspots**: Zone delay rankings vs. centrality and the Top 10 Chronic National Track Bottlenecks across India.
   * 📊 **AI Performance**: Multi-model comparison leaderboard and evaluation metric visualizations.
   * ⚡ **Cascade Simulator**: Shared rake turnaround simulation illustrating knock-on delay propagation and buffer recovery.
   * 🪔 **Festival Rush**: Ganesh Chaturthi (Sept 2024) surge analysis demonstrating how unscheduled special trains trigger cascade gridlocks.

---

## 📑 Documentation Index

| Document | Description |
| :--- | :--- |
| 🏗️ [Architecture and Workflow](docs/ARCHITECTURE_AND_WORKFLOW.md) | Dual-layer architecture, DuckDB schemas, kinematic equations, and sequence diagrams. |
| 🔍 [Exploratory Data Analysis (EDA)](docs/EXPLORATORY_DATA_ANALYSIS.md) | Full-scale analysis across 1.5M records, data quality, distributions, and class balance. |
| 🔬 [Scientific Benchmarking & Findings](docs/SCIENTIFIC_BENCHMARKING_AND_FINDINGS.md) | Multi-model evaluation, LightGBM champion metrics, and cascade ablation study. |
| 📊 [Model Benchmark & Comparison](docs/MODEL_BENCHMARK_AND_COMPARISON.md) | Deep comparative evaluation across Ridge, Random Forest, XGBoost, and LightGBM. |
| 📍 [Journey-Level Granularity Explained](docs/JOURNEY_LEVEL_GRANULARITY_EXPLAINED.md) | Architectural rationale for macro-journey vs. micro-station data modeling. |
| 🚀 [Usage and Requirements Guide](docs/USAGE_AND_REQUIREMENTS.md) | Complete environment setup, pipeline commands, testing, and dashboard walkthrough. |
| 🎤 [Presentation & Slide Deck Context](docs/PPT_PRESENTATION_CONTEXT.md) | Structured narrative, freight dilemma analysis, and defense talking points. |
| 🗺️ [Phased Implementation Roadmap](docs/phased_implementation_plan.md) | Step-by-step milestones, validation gates, and implementation status. |

---

## 🚀 Quick Start

### 1. Prerequisites & Virtual Environment
```powershell
# Clone or navigate to the repository
cd "Indian-railway-delay-prediction-system"

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# Install locked dependencies
pip install -r requirements.txt
pip install xgboost
```

### 2. Run Data Ingestion & Build DuckDB Warehouse
```powershell
# Ingest 1.28M station observations & build station_stops, section_analytics, journeys tables
.\.venv\Scripts\python.exe src/station_etl.py
```
*(Ingests 1.28M stops, calculates track section kinematics, and populates `db/railway.duckdb` in seconds).*

### 3. Run Automated Verification Tests
```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe -m pytest
```
*(All 9 unit tests covering ETL, Graph Centrality, ML Inference, and Station Trajectory Profiling pass seamlessly).*

### 4. Launch the Interactive Dashboard
Double-click `run_app.bat` or execute:
```powershell
.\.venv\Scripts\streamlit.exe run app/dashboard.py
```
Open **`http://localhost:8501`** in your web browser.

---

## 📊 Scientific Benchmark Summary

| Model | MAE (mins) | RMSE | $R^2$ | AUC-ROC | Train Time | Inference Latency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Ridge Regression** | 36.76 | 47.74 | 0.4175 | 0.9140 | 0.04s | < 0.001 ms |
| **Random Forest ($n=50$)** | 33.95 | 46.35 | 0.4510 | 0.9068 | 3.69s | 0.002 ms |
| **XGBoost** | 33.80 | 45.87 | 0.4623 | 0.9148 | 0.88s | < 0.001 ms |
| **LightGBM (Champion)** | **33.65** | **45.76** | **0.4648** | **0.9153** | **0.47s** | **< 0.001 ms** |

### Key Ablation & EDA Findings:
* Adding cascade features (`rake_cascade_chain_length`, `zone_delay_pressure`, `corridor_betweenness_centrality`) reduced prediction error by **0.53 minutes** and gained **+0.0059 AUC-ROC**.
* **`zone_delay_pressure` emerged as the #1 most important feature** across the entire dataset during model training.
* Section kinematic analysis reveals that **track running deceleration accounts for ~70-80% of total delay accumulation**, while platform dwell excess contributes ~20-30%.

---

## 🛠️ Tech Stack
* **Big Data & Analytics Engine**: DuckDB (Columnar SQL Warehouse), Polars (Rust-based Parallel Dataframe)
* **Graph Network Modeling**: NetworkX (Topological Centrality & Corridor Graph)
* **Machine Learning**: LightGBM, XGBoost, Scikit-Learn
* **Application & Visualizations**: Streamlit, Plotly Express & Graph Objects
* **Testing & Quality Assurance**: PyTest (9 Automated Test Suites)

