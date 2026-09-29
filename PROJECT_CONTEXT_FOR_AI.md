# 🚆 PROJECT CONTEXT & AGENT COLLABORATION GUIDE
## Predictive Intelligence System for Indian Railway Delay Cascade Analytics

> **Purpose of this document:** Provide complete architectural, technical, operational, and conversational context to an AI assistant or collaborator joining this codebase.

---

## 1. Executive Summary & Problem Space

### The Problem (Why standard transit apps fail):
* Consumer apps like *Ixigo*, *Where Is My Train*, and *ConfirmTkt* track trains **linearly via GPS**. If a train is delayed, they project that same delay onto its next stops.
* **The Cascade Problem:** Trains share physical infrastructure (tracks, junctions, platforms, and trainsets/rakes). When Train A is delayed, it blocks platforms and track segments, causing subsequent trains (Train B, C, D) to accumulate **knock-on (cascade) delays**. Current apps treat trains as isolated objects and miss these ripple effects entirely.
* **The Freight & Logistics Dilemma:** Goods/freight trains share the same tracks and yield right-of-way to passenger trains. While systems like FOIS track current wagon locations via RFID, they cannot forecast delays caused by upstream passenger train gridlocks.

### Our Solution:
A **Predictive Intelligence System** running on local Big Data tooling (**Polars + DuckDB**), network graph modeling (**NetworkX**), and Machine Learning (**LightGBM**) with an interactive **Streamlit** dashboard. It transitions delay management from reactive GPS tracking to proactive, network-wide cascade forecasting and micro-level station bottleneck localization.

---

## 2. Technical Stack & Engineering Rationale

| Layer | Tool / Library | Why Chosen |
| :--- | :--- | :--- |
| **Big Data ETL & Kinematics** | **Polars** (`1.44.2`) | Fast, multi-threaded Rust dataframe engine; parsed 1.28M station stops & 1.5M journey records in seconds without memory bottlenecks. |
| **Analytical Warehouse** | **DuckDB** (`1.5.5`) | Serverless, columnar SQL database stored locally (`db/railway.duckdb`), storing `station_stops`, `section_analytics`, and `journeys` tables with sub-millisecond query latency. |
| **Graph Topology** | **NetworkX** (`3.6.1`) | 16-node graph modeling Indian Railway zones & High Density Network (HDN) corridors to compute betweenness and degree centrality. |
| **Station Kinematics & Profiling** | **TrajectoryProfiler** | Service calculating route waterfall trajectories, track running deceleration vs. platform dwell loss, and identifying the worst chronic bottleneck segments. |
| **Predictive ML** | **LightGBM** (`4.7.0`) | CPU-optimized gradient boosting; proved superior in empirical benchmarking against Ridge, Random Forest, and XGBoost. |
| **User Interface** | **Streamlit** (`1.64.0`) + **Plotly** | Clean, responsive 5-tab web dashboard featuring Commuter Zero-Effort mode, What-If simulation, Network Hotspots, AI benchmarks, Rake Turnaround simulator, and Festival Rush analytics. |

---

## 3. Dataset Specifications

The datasets are stored in `data/` and `data/station_data/`:
* **`data/station_data/train_routes_delays_Sep2024.csv`**: 1,280,000+ station-level observation records across Indian Railways (IIT Kharagpur RSTGCN Dataset, Sep 2024) containing actual and scheduled arrival/departure timestamps.
* **`data/station_data/train_routes_Sep2024.csv`**: Comprehensive route stop schedules, sequence numbers, station codes, and cumulative track distance.
* **`data/station_data/stations_zones_mapping.json`**: Station-to-Zone mapping dictionary across all 16 Indian Railway zones.
* **`data/ir_train.csv` / `ir_test.csv`**: 1,500,000 journey records (2018–2024), 45 columns, with continuous delay minutes and binary classifications.
* **DuckDB Storage Schema (`db/railway.duckdb`)**:
  * **`station_stops`**: Fine-grained stop telemetry (1.28M rows) with derived kinematic delta-delays:
    * $\text{running\_delay\_delta} = \text{arr\_delay}_i - \text{dep\_delay}_{i-1}$
    * $\text{dwell\_delay\_delta} = \text{dep\_delay}_i - \text{arr\_delay}_i$
    * $\text{section\_distance\_km} = \text{distance}_i - \text{distance}_{i-1}$
  * **`section_analytics`**: Track link aggregations (average running delay added, delay gradient per 100km, delay frequency %).
  * **`journeys`**: Journey-level aggregated training and test records with operational cascade features.

---

## 4. Key Graph & Cascade Feature Engineering (Phase 3)

The raw dataset lacks explicit network propagation metrics. We derived three key features:
1. **`rake_cascade_chain_length`**:
   * Measures consecutive delayed turnarounds for shared trainsets:
     $$\text{rake\_cascade\_chain\_length} = \sum (\text{late\_incoming\_rake} \times \text{is\_rake\_shared}) \text{ over train\_number}$$
2. **`zone_delay_pressure`**:
   * Rolling 20-period average delay per railway zone, capturing dynamic regional delay spillover.
3. **`corridor_betweenness_centrality`**:
   * Topological importance score of the railway zone derived from the 16-zone NetworkX graph.

---

## 5. Scientific Benchmark & Ablation Study Results (Phase 4)

We avoided arbitrary model selection by empirically evaluating 4 model families on 100,000 journeys under identical test splits:

| Model Family | MAE (mins) | RMSE | $R^2$ Score | AUC-ROC | Train Time | Inference Latency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Ridge Regression** | 36.76 | 47.74 | 0.4175 | 0.9140 | 0.04s | < 0.001 ms |
| **Random Forest ($n=50$)** | 33.95 | 46.35 | 0.4510 | 0.9068 | 3.69s | 0.002 ms |
| **XGBoost** | 33.80 | 45.87 | 0.4623 | 0.9148 | 0.88s | < 0.001 ms |
| **LightGBM (Champion)** | **33.65** | **45.76** | **0.4648** | **0.9153** | **0.47s** | **< 0.001 ms** |

### Scientific Ablation Study:
* **Baseline (Raw Features Only)**: MAE = 34.18m | RMSE = 46.61 | AUC = 0.9094
* **Full Model (Raw + Cascade Features)**: MAE = **33.65m** | RMSE = **45.76** | AUC = **0.9153**
* **Empirical Validation**: Adding the derived cascade features reduced prediction error by **0.53 minutes** and improved AUC by **+0.0059**.
* In full champion training (300,000 rows), **`zone_delay_pressure` emerged as the #1 most important feature** across all 41 inputs.

---

## 6. Project Architecture & Directory Layout

```
Indian-railway-delay-prediction-system/
├── data/
│   ├── ir_train.csv / ir_test.csv        # Journey-level macro datasets
│   ├── ir_data_dictionary.csv            # Macro schema definitions
│   └── station_data/                     # Micro-level IIT Kharagpur RSTGCN telemetry
│       ├── train_routes_delays_Sep2024.csv  # 1.28M real station stop delays
│       ├── train_routes_Sep2024.csv         # Route station sequences and distances
│       └── stations_zones_mapping.json      # Station to zone mappings
├── db/
│   └── railway.duckdb                    # Local DuckDB warehouse (station_stops, section_analytics, journeys)
├── models/
│   ├── champion_models.pkl               # Serialized LightGBM Regressor & Classifier bundle
│   ├── benchmark_report.json             # Multi-model benchmark & ablation metrics
│   ├── eda_results.json                  # Statistical distributions across 1.5M records
│   └── correlation_summary.json          # Correlation matrices and feature collinearity
├── src/
│   ├── __init__.py
│   ├── station_etl.py                    # Polars + DuckDB pipeline for 1.28M station stops & kinematics
│   ├── trajectory_profiler.py            # Route waterfall profiling & chokepoint localization
│   ├── etl.py                            # Journey-level macro ingestion pipeline
│   ├── graph_builder.py                  # 16-zone NetworkX topology & centrality
│   ├── cascade_features.py               # Derives rake chains & zone delay pressure
│   ├── benchmark.py                      # 4-model evaluation suite & ablation study
│   ├── train.py                          # Trains champion models on full scale
│   ├── predictor.py                      # Low-latency runtime inference class
│   ├── run_eda.py                        # Full-scale exploratory data analysis runner
│   └── generate_heatmap.py               # Generates feature correlation heatmap
├── app/
│   └── dashboard.py                      # Streamlit dashboard (Tabs 1 to 5)
├── docs/
│   ├── ARCHITECTURE_AND_WORKFLOW.md      # Dual-layer architecture & kinematic design
│   ├── EXPLORATORY_DATA_ANALYSIS.md      # 1.5M row EDA, data quality, & feature correlations
│   ├── JOURNEY_LEVEL_GRANULARITY_EXPLAINED.md # Micro vs Macro modeling rationale
│   ├── MODEL_BENCHMARK_AND_COMPARISON.md # Comprehensive 4-algorithm benchmark report
│   ├── SCIENTIFIC_BENCHMARKING_AND_FINDINGS.md # Scientific metrics and ablation findings
│   ├── USAGE_AND_REQUIREMENTS.md         # Complete installation, setup, & usage guide
│   ├── PPT_PRESENTATION_CONTEXT.md       # Slide deck blueprints & defense talking points
│   └── phased_implementation_plan.md     # Milestone tracking & status
├── tests/
│   ├── __init__.py
│   ├── test_etl.py                       # Validates DuckDB journeys table & query speed
│   ├── test_graph.py                     # Validates graph connectivity & features
│   ├── test_model.py                     # Validates ML inference & cascade elevation
│   └── test_station_etl.py               # Validates 1.28M station stops, sections, & profiler
├── run_app.bat                           # 1-click launcher for the dashboard
├── requirements.txt                      # Locked project dependencies
└── README.md                             # Comprehensive overview & quick start
```

---

## 7. Interactive Dashboard Design (`app/dashboard.py`)

1. **Tab 1: 🎯 Check My Train**:
   * **Passenger / Commuter View (Zero-Effort Default)**: Select a Train Number. The backend automatically auto-populates route specs, inspects incoming rake status, checks seasonal weather alerts, and evaluates corridor congestion pressure.
   * **What-If Mode (Advanced)**: Manual sliders for operational parameters to test custom scenarios.
   * **AI Delay Forecast**: Dual-target prediction card (estimated delay minutes + % probability of exceeding 15 min threshold + risk tier).
   * **Journey Delay Map (Station-by-Station)**: Interactive Plotly waterfall chart showing cumulative arrival delay vs. section-by-section delay additions ($\Delta_{\text{running}}$) and buffer time recoveries.
   * **Bottleneck Cards**: Highlights the top 3 worst delay-inducing track segments along the selected train's journey.
   * **Timing Log Expander**: Full tabular breakdown of scheduled vs. actual arrival/departure times and station dwells.
2. **Tab 2: 🗺️ Network Hotspots**:
   * Zone-by-zone average delays and congestion indices mapped against topological betweenness centrality.
   * **Top 10 Chronic National Track Bottlenecks**: Horizontal bar chart identifying segments across India with the highest recurring delay accumulation.
3. **Tab 3: 📊 AI Performance**:
   * Multi-model benchmark leaderboard (Ridge, Random Forest, XGBoost, LightGBM) with interactive MAE and AUC comparison charts.
4. **Tab 4: ⚡ Cascade Simulator**:
   * Sandbox modeling how an initial turnaround delay propagates across shared trainset services.
5. **Tab 5: 🪔 Festival Rush**:
   * Empirical analysis of the **Ganesh Chaturthi (Sept 2024)** festival rush, showing daily delay surges (+14.3 min network spike) caused by injection of unscheduled special trains on congested lines.

---

## 8. Verification & Quick Commands

To run tests and launch the system:

```powershell
# 1. Run full station & kinematic ETL pipeline
.\.venv\Scripts\python.exe src/station_etl.py

# 2. Run automated test suite (All 9 tests pass in ~3.3s)
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe -m pytest

# 3. Launch dashboard
.\.venv\Scripts\streamlit.exe run app/dashboard.py
```

---

## 9. Guidance for Cooperating AI Assistants

When extending or collaborating on this project, please adhere to these core principles:
1. **Preserve the Dual-Target Philosophy**: We predict both continuous `delay_minutes` (regression) and the `> 15 mins` delay probability (classification).
2. **Support Both Granularities**: Macro journey forecasting (`predictor.py`) and micro station-by-station trajectory localization (`trajectory_profiler.py`).
3. **Defend the "PoC & Research Architecture" Positioning**: Acknowledge that while live production would stream from NTES/COA APIs, our PoC validates that modeling cascade dependencies mathematically outperforms standard linear extrapolation.
4. **Keep User Mode Zero-Effort**: Never force the end-user to input technical variables (like `psr_count` or `late_incoming_rake`); always auto-infer them from the backend/database.
5. **Maintain Local Big Data Performance**: Always use **Polars** and **DuckDB** rather than converting large datasets into standard Pandas to prevent memory bottlenecks.
