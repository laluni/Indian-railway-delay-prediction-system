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
A **Predictive Intelligence System** running on local Big Data tooling (**Polars + DuckDB**), network graph modeling (**NetworkX**), and Machine Learning (**LightGBM**) with an interactive **Streamlit** dashboard. It transitions delay management from reactive GPS tracking to proactive, network-wide cascade forecasting.

---

## 2. Technical Stack & Engineering Rationale

| Layer | Tool / Library | Why Chosen |
| :--- | :--- | :--- |
| **Big Data ETL** | **Polars** (`1.44.2`) | Fast, multi-threaded Rust dataframe engine; parsed 1.5M rows in 14.4s without memory crashes. |
| **Analytical Warehouse** | **DuckDB** (`1.5.5`) | Serverless, columnar SQL database stored locally (`db/railway.duckdb`), zero cloud costs, sub-millisecond query latency. |
| **Graph Topology** | **NetworkX** (`3.6.1`) | 16-node graph modeling Indian Railway zones & High Density Network (HDN) corridors to compute betweenness centrality. |
| **Predictive ML** | **LightGBM** (`4.7.0`) | CPU-optimized gradient boosting; proved superior in empirical benchmarking against Ridge, Random Forest, and XGBoost. |
| **User Interface** | **Streamlit** (`1.64.0`) + **Plotly** | Clean web application with dual modes (Commuter zero-effort view vs. Evaluator simulation view). |

---

## 3. Dataset Specifications

The dataset is located in `data/` (originating from the Kaggle competition *Indian Railways: Predict Train Delay*):
* **`ir_train.csv`**: 1,500,000 historical journey records (2018–2024), 45 columns, ~337 MB.
* **`ir_test.csv`**: 375,000 journey records without target labels, used for test inference.
* **`ir_data_dictionary.csv`**: Feature schemas, units, and descriptions.
* **Target Columns:**
  * `delay_minutes` (Continuous regression target: actual arrival delay in minutes).
  * `is_delayed` (Binary classification target: 1 if delayed > 15 mins, 0 otherwise).

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
| **Ridge Regression** | 36.76 | 47.74 | 0.4175 | 0.9140 | 0.04s | 0.000 ms |
| **Random Forest (n=50)** | 33.95 | 46.35 | 0.4510 | 0.9068 | 3.69s | 0.002 ms |
| **XGBoost** | 33.80 | 45.87 | 0.4623 | 0.9148 | 0.88s | 0.000 ms |
| **LightGBM (Champion)** | **33.65** | **45.76** | **0.4648** | **0.9153** | **0.47s** | **0.001 ms** |

### Scientific Ablation Study:
* **Baseline (Raw Features Only)**: MAE = 34.18m | RMSE = 46.61 | AUC = 0.9094
* **Full Model (Raw + Cascade Features)**: MAE = **33.65m** | RMSE = **45.76** | AUC = **0.9153**
* **Empirical Validation**: Adding the derived cascade features reduced prediction error by **0.53 minutes** and improved AUC by **+0.0059**.
* In full champion training (300,000 rows), **`zone_delay_pressure` emerged as the #1 most important feature** across all 41 inputs.

---

## 6. Project Architecture & Directory Layout

```
Indian railway/
├── data/                         # Datasets (ir_train.csv, ir_test.csv, etc.)
├── db/
│   └── railway.duckdb            # Local DuckDB database (table: journeys, 1.5M rows)
├── models/
│   ├── champion_models.pkl       # Serialized LightGBM Regressor & Classifier bundle
│   └── benchmark_report.json     # Multi-model benchmark & ablation metrics
├── src/
│   ├── __init__.py
│   ├── etl.py                    # Polars -> DuckDB pipeline
│   ├── graph_builder.py          # 16-zone NetworkX topology & centrality
│   ├── cascade_features.py       # Derives rake chains & zone delay pressure
│   ├── benchmark.py              # 4-model evaluation suite & ablation study
│   ├── train.py                  # Trains champion models on full scale
│   └── predictor.py              # Low-latency runtime inference class
├── app/
│   └── dashboard.py              # Streamlit dashboard (Tabs 1 to 4)
├── docs/
│   ├── ARCHITECTURE_AND_WORKFLOW.md
│   ├── SCIENTIFIC_BENCHMARKING_AND_FINDINGS.md
│   └── USAGE_AND_REQUIREMENTS.md
├── tests/
│   ├── __init__.py
│   ├── test_etl.py               # Validates DuckDB 1.5M rows & query speed
│   ├── test_graph.py             # Validates graph connectivity & features
│   └── test_model.py             # Validates inference & cascade elevation
├── run_app.bat                   # 1-click launcher for the dashboard
├── requirements.txt              # Locked project dependencies
├── README.md                     # High-level overview
└── PROJECT_CONTEXT_FOR_AI.md     # THIS COMPLETE CONTEXT FILE
```

---

## 7. Interactive Dashboard Design (`app/dashboard.py`)

1. **Tab 1: Live Journey Forecaster**:
   * **Passenger View (Zero-Effort)**: The user only selects a **Train Number**. The backend automatically auto-populates timetable specs, evaluates incoming rake status, checks seasonal fog risk, and calculates active corridor pressure. Clicking *"Forecast Delay"* yields predicted delay minutes, risk probability gauge, and classification tier in < 1 ms.
   * **Evaluator View**: Manual sliders for professors, mentors, and panel judges to test custom edge cases.
2. **Tab 2: Network Bottleneck Map**:
   * Queries DuckDB to display zone-by-zone average delays, congestion indexes, and topological betweenness centrality.
3. **Tab 3: Scientific Benchmark & Ablation**:
   * Displays the comparative leaderboard (Ridge vs. RF vs. XGBoost vs. LightGBM) and ablation study delta.
4. **Tab 4: Rake Cascade Simulator**:
   * What-if sandbox simulating how an initial turnaround deficit cascades across consecutive service cycles.

---

## 8. Verification & Quick Commands

To collaborate and run the project:

```powershell
# 1. Activate environment
cd "Indian railway"
.\.venv\Scripts\activate

# 2. Run automated test suite (All 6 tests pass in ~2.7s)
$env:PYTHONPATH="."
.\.venv\Scripts\pytest.exe tests/

# 3. Launch dashboard
.\.venv\Scripts\streamlit.exe run app\dashboard.py
```

---

## 9. Guidance for Cooperating AI Assistants

When extending or collaborating on this project, please adhere to these core principles:
1. **Preserve the Dual-Target Philosophy**: We predict both continuous `delay_minutes` (regression) and the `> 15 mins` delay probability (classification).
2. **Defend the "PoC & Research Architecture" Positioning**: Acknowledge that while live production would stream from NTES/COA APIs, our PoC validates that modeling cascade dependencies mathematically outperforms standard linear extrapolation.
3. **Keep User Mode Zero-Effort**: Never force the end-user to input technical variables (like `psr_count` or `late_incoming_rake`); always auto-infer them from the backend/database.
4. **Maintain Local Big Data Performance**: Always use **Polars** and **DuckDB** rather than converting large datasets into standard Pandas to prevent memory bottlenecks.
