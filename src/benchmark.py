"""
Model Comparison Benchmark and Ablation Study Suite.
Evaluates:
1. Linear Regression Baseline
2. Random Forest Regressor
3. XGBoost Regressor
4. LightGBM Regressor
Also conducts an Ablation Study: Baseline Features vs. Baseline + Cascade/Graph Features.
"""
import time
import json
from pathlib import Path
import numpy as np
import polars as pl
from sklearn.model_selection import train_test_split
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score, roc_auc_score
import xgboost as xgb
import lightgbm as lgb
from src.cascade_features import engineer_cascade_features

BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"

def prepare_benchmark_data(sample_size=100000):
    """
    Prepares train and test matrices for the benchmark.
    Returns: X_train_raw, X_test_raw, X_train_full, X_test_full, y_train, y_test, y_train_cls, y_test_cls
    """
    print(f"Loading {sample_size:,} records for scientific benchmark...")
    df = engineer_cascade_features(sample_limit=sample_size)
    
    # Categorical columns to encode numerically
    cat_cols = [
        "train_type", "season", "zone_abbr", "source_station_category", 
        "destination_station_category", "traction_type"
    ]
    
    # Raw baseline feature set
    raw_feature_cols = [
        "year", "month", "day_of_week", "departure_hour", "is_weekend",
        "is_night_departure", "is_peak_hour", "is_festival_season",
        "distance_km", "num_scheduled_stops", "scheduled_travel_hours",
        "track_doubled", "is_hdn_route", "is_electrified", "psr_count",
        "is_circular_route", "is_monsoon_season", "is_fog_risk",
        "fog_risk_score", "zone_fog_index", "zone_congestion_index",
        "season_severity_score", "loco_age_years", "coach_age_years",
        "has_lhb_coaches", "is_rake_shared", "maintenance_score",
        "seat_utilisation_pct", "is_overloaded", "late_incoming_rake",
        "is_special_train", "route_historical_ontime_pct"
    ]
    
    # Cascade and graph features derived in Phase 3
    cascade_feature_cols = [
        "rake_cascade_chain_length",
        "zone_delay_pressure",
        "corridor_betweenness_centrality",
        "corridor_degree_centrality"
    ]
    
    # Convert categoricals to integers
    for c in cat_cols:
        df = df.with_columns(pl.col(c).cast(pl.Categorical).to_physical().alias(c))
        
    full_feature_cols = raw_feature_cols + cat_cols + cascade_feature_cols
    baseline_feature_cols = raw_feature_cols + cat_cols
    
    # Extract numpy arrays
    X_full = df.select(full_feature_cols).to_numpy()
    X_raw = df.select(baseline_feature_cols).to_numpy()
    y_reg = df["delay_minutes"].to_numpy()
    y_cls = df["is_delayed"].to_numpy()
    
    # Train / test split (80 / 20)
    idx_train, idx_test = train_test_split(np.arange(len(df)), test_size=0.2, random_state=42)
    
    data = {
        "X_train_full": X_full[idx_train],
        "X_test_full": X_full[idx_test],
        "X_train_raw": X_raw[idx_train],
        "X_test_raw": X_raw[idx_test],
        "y_train_reg": y_reg[idx_train],
        "y_test_reg": y_reg[idx_test],
        "y_train_cls": y_cls[idx_train],
        "y_test_cls": y_cls[idx_test],
        "feature_names_full": full_feature_cols,
        "feature_names_raw": baseline_feature_cols
    }
    return data

def run_benchmark():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    data = prepare_benchmark_data(sample_size=100000)
    
    X_tr_f = data["X_train_full"]
    X_te_f = data["X_test_full"]
    y_tr_r = data["y_train_reg"]
    y_te_r = data["y_test_reg"]
    y_te_c = data["y_test_cls"]
    
    models = {
        "Ridge Linear Regression": Ridge(alpha=1.0),
        "Random Forest (n=50)": RandomForestRegressor(n_estimators=50, max_depth=12, n_jobs=-1, random_state=42),
        "XGBoost": xgb.XGBRegressor(n_estimators=150, max_depth=6, learning_rate=0.08, n_jobs=-1, random_state=42),
        "LightGBM": lgb.LGBMRegressor(n_estimators=150, max_depth=8, learning_rate=0.08, n_jobs=-1, random_state=42, verbose=-1)
    }
    
    benchmark_results = {}
    
    print("\n" + "=" * 80)
    print(f"{'MODEL COMPARISON BENCHMARK (100,000 Journeys)':^80}")
    print("=" * 80)
    print(f"{'Model':<26} | {'MAE (mins)':<10} | {'RMSE':<10} | {'R2':<8} | {'AUC-ROC':<8} | {'Train(s)':<8} | {'Latency(ms)'}")
    print("-" * 80)
    
    for name, model in models.items():
        # Measure training time
        t_start = time.time()
        model.fit(X_tr_f, y_tr_r)
        t_train = time.time() - t_start
        
        # Measure inference latency (avg per 1,000 samples)
        t_pred_start = time.time()
        y_pred = model.predict(X_te_f)
        t_pred = (time.time() - t_pred_start) / len(X_te_f) * 1000.0  # ms per record
        
        # Metrics
        mae = mean_absolute_error(y_te_r, y_pred)
        rmse = root_mean_squared_error(y_te_r, y_pred)
        r2 = r2_score(y_te_r, y_pred)
        
        # Convert continuous predictions to probability estimate for AUC-ROC
        y_pred_clipped = np.clip(y_pred, 0, None)
        pred_probs = 1 / (1 + np.exp(-(y_pred_clipped - 15) / 10.0))
        auc = roc_auc_score(y_te_c, pred_probs)
        
        benchmark_results[name] = {
            "mae": round(float(mae), 2),
            "rmse": round(float(rmse), 2),
            "r2": round(float(r2), 4),
            "auc_roc": round(float(auc), 4),
            "train_time_sec": round(float(t_train), 2),
            "latency_ms": round(float(t_pred), 3)
        }
        
        print(f"{name:<26} | {mae:<10.2f} | {rmse:<10.2f} | {r2:<8.4f} | {auc:<8.4f} | {t_train:<8.2f} | {t_pred:.3f} ms")
        
    print("=" * 80)
    
    # -------------------------------------------------------------
    # ABLATION STUDY: LightGBM Baseline vs. Baseline + Cascade
    # -------------------------------------------------------------
    print("\n" + "=" * 80)
    print(f"{'SCIENTIFIC ABLATION STUDY (Marginal Impact of Cascade Features)':^80}")
    print("=" * 80)
    
    # Model 1: Baseline Features Only
    m_base = lgb.LGBMRegressor(n_estimators=150, max_depth=8, learning_rate=0.08, n_jobs=-1, random_state=42, verbose=-1)
    m_base.fit(data["X_train_raw"], y_tr_r)
    p_base = m_base.predict(data["X_test_raw"])
    mae_base = mean_absolute_error(y_te_r, p_base)
    rmse_base = root_mean_squared_error(y_te_r, p_base)
    r2_base = r2_score(y_te_r, p_base)
    auc_base = roc_auc_score(y_te_c, 1 / (1 + np.exp(-(np.clip(p_base, 0, None) - 15) / 10.0)))
    
    # Model 2: Baseline + Cascade Features (already evaluated as LightGBM above)
    lgb_res = benchmark_results["LightGBM"]
    mae_cascade = lgb_res["mae"]
    rmse_cascade = lgb_res["rmse"]
    r2_cascade = lgb_res["r2"]
    auc_cascade = lgb_res["auc_roc"]
    
    mae_delta = mae_base - mae_cascade
    rmse_delta = rmse_base - rmse_cascade
    auc_delta = auc_cascade - auc_base
    
    ablation_results = {
        "Baseline (Raw Features Only)": {
            "mae": round(float(mae_base), 2),
            "rmse": round(float(rmse_base), 2),
            "r2": round(float(r2_base), 4),
            "auc_roc": round(float(auc_base), 4)
        },
        "Full Model (Raw + Cascade Features)": {
            "mae": mae_cascade,
            "rmse": rmse_cascade,
            "r2": r2_cascade,
            "auc_roc": auc_cascade
        },
        "Improvement_Delta": {
            "mae_reduction_minutes": round(float(mae_delta), 2),
            "rmse_reduction": round(float(rmse_delta), 2),
            "auc_gain": round(float(auc_delta), 4)
        }
    }
    
    print(f"1. Baseline Features Only       : MAE = {mae_base:.2f} mins | RMSE = {rmse_base:.2f} | AUC = {auc_base:.4f}")
    print(f"2. Baseline + Cascade Features  : MAE = {mae_cascade:.2f} mins | RMSE = {rmse_cascade:.2f} | AUC = {auc_cascade:.4f}")
    print(f"-> IMPACT DELTA                 : Error Reduced by {mae_delta:.2f} mins | AUC Increased by {auc_delta:.4f}")
    print("=" * 80)
    
    # Save benchmark report to JSON for the Streamlit dashboard
    report = {
        "benchmark_comparison": benchmark_results,
        "ablation_study": ablation_results
    }
    with open(MODELS_DIR / "benchmark_report.json", "w") as f:
        json.dump(report, f, indent=4)
        
    print(f"\nReport successfully saved to: {MODELS_DIR / 'benchmark_report.json'}")
    return report

if __name__ == "__main__":
    run_benchmark()
