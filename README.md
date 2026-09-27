# 🚆 Predictive Intelligence System for Indian Railway Delay Cascade Analytics

An end-to-end, high-performance data engineering and machine learning platform designed to model, trace, and forecast network-wide train delay cascades across Indian Railways.

---

## 📌 Project Overview
While consumer transit apps (Ixigo, Where Is My Train) track trains linearly via GPS, they fail to model how a single delay blocks shared tracks and platforms, triggering a **cascade delay** on subsequent services. Furthermore, physical freight rakes and passenger trains compete for the same physical corridors, where localized bottlenecks rapidly compound into multi-hour gridlocks.

This system addresses that gap by:
1. Processing **1,500,000 historical journey records** locally in **~14 seconds** using **Polars** and storing them in an indexed **DuckDB** database.
2. Constructing a topological network graph of India's **16 railway zones and HDN corridors** using **NetworkX** to identify structural network chokepoints.
3. Conducting a **scientific benchmark** (Ridge vs. Random Forest vs. XGBoost vs. LightGBM) and an **ablation study** proving the value of engineered cascade features.
4. Serving real-time delay predictions and interactive simulations via an intuitive **Streamlit** dashboard featuring:
   * **Zero-Effort Passenger View:** Select Train Number only—the system automatically infers incoming rake status, seasonal weather alerts, and corridor congestion from the database.
   * **Evaluator What-If View:** Manual operational overrides for panel evaluations and extreme simulation testing.

---

## 📑 Detailed Documentation Links
* [Architecture and Workflow](docs/ARCHITECTURE_AND_WORKFLOW.md)
* [Scientific Benchmarking and Empirical Findings](docs/SCIENTIFIC_BENCHMARKING_AND_FINDINGS.md)
* [Requirements and Usage Guide](docs/USAGE_AND_REQUIREMENTS.md)

---

## 🚀 Quick Start

### 1. Prerequisites & Virtual Environment
```powershell
cd "Indian railway"
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pip install xgboost
```
###
Direct Download from Kaggle (Simplest & Best for Teammates)
Since the raw CSVs are from a public competition, your teammates can download them directly:

Share the official competition link: Kaggle - Indian Railways: Predict Train Delay
.
Tell them to download the ZIP file and place ir_train.csv and ir_test.csv inside their local Indian railway/data/ folder.
They simply run:
powershell
```
python src/etl.py
This will automatically build the db/railway.duckdb database on their machine in ~14 seconds.
```


### 2. Run Automated Verification Tests
```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\pytest.exe tests/
```
*(All 6 unit tests covering ETL, Graph Modeling, and ML Inference pass in ~2.7s).*

### 3. Launch the Interactive Dashboard
Double-click `run_app.bat` or run:
```powershell
.\.venv\Scripts\streamlit.exe run app\dashboard.py
```
Visit **`http://localhost:8501`** in your browser.

---

## 📊 Scientific Benchmark Summary

| Model | MAE (mins) | RMSE | $R^2$ | AUC-ROC | Train Time | Inference Latency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Ridge Regression** | 36.76 | 47.74 | 0.4175 | 0.9140 | 0.04s | 0.000 ms |
| **Random Forest (n=50)** | 33.95 | 46.35 | 0.4510 | 0.9068 | 3.69s | 0.002 ms |
| **XGBoost** | 33.80 | 45.87 | 0.4623 | 0.9148 | 0.88s | 0.000 ms |
| **LightGBM (Champion)** | **33.65** | **45.76** | **0.4648** | **0.9153** | **0.47s** | **0.001 ms** |

### Ablation Study Findings:
* Adding cascade features (`rake_cascade_chain_length`, `zone_delay_pressure`, `corridor_betweenness_centrality`) reduced prediction error by **0.53 minutes** and gained **+0.0059 AUC-ROC**.
* In full champion training, **`zone_delay_pressure` emerged as the #1 most important feature** across the entire dataset.

---

## 🛠️ Tech Stack
* **Storage & Analytics**: DuckDB, Polars
* **Graph Modeling**: NetworkX
* **Machine Learning**: LightGBM, XGBoost, Scikit-Learn
* **Application & Visualization**: Streamlit, Plotly
* **Testing**: PyTest
