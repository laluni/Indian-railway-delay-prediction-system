"""
Champion Model Trainer & Artifact Serializer.
Trains LightGBM Regressor (delay_minutes) and Classifier (is_delayed)
on the full scale dataset with cascade features and computes feature importance.
"""
import time
import joblib
from pathlib import Path
import numpy as np
import polars as pl
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, roc_auc_score
import lightgbm as lgb
from src.cascade_features import engineer_cascade_features

BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"

def train_champion_models(sample_size=300000):
    print("=" * 70)
    print(f"Training Champion LightGBM Models on {sample_size:,} Journeys")
    print("=" * 70)
    
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    df = engineer_cascade_features(sample_limit=sample_size)
    
    cat_cols = [
        "train_type", "season", "zone_abbr", "source_station_category", 
        "destination_station_category", "traction_type"
    ]
    
    feature_cols = [
        "year", "month", "day_of_week", "departure_hour", "is_weekend",
        "is_night_departure", "is_peak_hour", "is_festival_season",
        "distance_km", "num_scheduled_stops", "scheduled_travel_hours",
        "track_doubled", "is_hdn_route", "is_electrified", "psr_count",
        "is_circular_route", "is_monsoon_season", "is_fog_risk",
        "fog_risk_score", "zone_fog_index", "zone_congestion_index",
        "season_severity_score", "loco_age_years", "coach_age_years",
        "has_lhb_coaches", "is_rake_shared", "maintenance_score",
        "seat_utilisation_pct", "is_overloaded", "late_incoming_rake",
        "is_special_train", "route_historical_ontime_pct",
        # Cascade & Graph Features
        "rake_cascade_chain_length",
        "zone_delay_pressure",
        "corridor_betweenness_centrality",
        "corridor_degree_centrality"
    ]
    
    # Label Encoders dictionary to save for runtime inference
    label_mappings = {}
    for c in cat_cols:
        unique_vals = sorted([str(x) for x in df[c].unique().to_list() if x is not None])
        mapping = {val: idx for idx, val in enumerate(unique_vals)}
        label_mappings[c] = mapping
        df = df.with_columns(pl.col(c).cast(pl.Utf8).replace_strict(mapping, default=0).cast(pl.Int32).alias(c))
        
    all_features = feature_cols + cat_cols
    X = df.select(all_features).to_numpy()
    y_reg = df["delay_minutes"].to_numpy()
    y_cls = df["is_delayed"].to_numpy()
    
    X_train, X_test, y_train_reg, y_test_reg, y_train_cls, y_test_cls = train_test_split(
        X, y_reg, y_cls, test_size=0.2, random_state=42
    )
    
    # 1. Train Delay Regressor
    print("\n[1/3] Training LightGBM Continuous Delay Regressor...")
    t0 = time.time()
    regressor = lgb.LGBMRegressor(
        n_estimators=200,
        max_depth=8,
        learning_rate=0.08,
        num_leaves=63,
        subsample=0.8,
        colsample_bytree=0.8,
        n_jobs=-1,
        random_state=42,
        verbose=-1
    )
    regressor.fit(X_train, y_train_reg)
    t_reg = time.time() - t0
    
    y_pred_reg = regressor.predict(X_test)
    mae = mean_absolute_error(y_test_reg, y_pred_reg)
    rmse = root_mean_squared_error(y_test_reg, y_pred_reg)
    print(f"      Regressor Fit in {t_reg:.2f}s | Test MAE: {mae:.2f} mins | RMSE: {rmse:.2f}")
    
    # 2. Train Delay Classifier (Probability of > 15 mins delay)
    print("\n[2/3] Training LightGBM Delay Classifier (> 15 mins probability)...")
    t0 = time.time()
    classifier = lgb.LGBMClassifier(
        n_estimators=200,
        max_depth=8,
        learning_rate=0.08,
        num_leaves=63,
        subsample=0.8,
        colsample_bytree=0.8,
        n_jobs=-1,
        random_state=42,
        verbose=-1
    )
    classifier.fit(X_train, y_train_cls)
    t_cls = time.time() - t0
    
    y_pred_probs = classifier.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test_cls, y_pred_probs)
    print(f"      Classifier Fit in {t_cls:.2f}s | Test AUC-ROC: {auc:.4f}")
    
    # 3. Save Model Artifacts & Metadata
    print("\n[3/3] Serializing Models and Metadata...")
    model_bundle = {
        "regressor": regressor,
        "classifier": classifier,
        "feature_names": all_features,
        "label_mappings": label_mappings,
        "metrics": {
            "regressor_mae": round(float(mae), 2),
            "regressor_rmse": round(float(rmse), 2),
            "classifier_auc": round(float(auc), 4)
        }
    }
    
    artifact_path = MODELS_DIR / "champion_models.pkl"
    joblib.dump(model_bundle, artifact_path)
    print(f"      Saved model bundle to: {artifact_path}")
    
    # Feature Importance
    importance = regressor.feature_importances_
    sorted_idx = np.argsort(importance)[::-1]
    print("\nTop 7 Predictive Features (Feature Importance):")
    for i in range(7):
        feat_name = all_features[sorted_idx[i]]
        print(f"  {i+1}. {feat_name:32s} (Score: {importance[sorted_idx[i]]})")
        
    print("=" * 70)
    print("Champion Training Completed Successfully!")
    print("=" * 70)

if __name__ == "__main__":
    train_champion_models(sample_size=300000)
