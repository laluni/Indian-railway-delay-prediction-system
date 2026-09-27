"""
Runtime Inference Service for Delay Forecasting.
Loads trained champion LightGBM bundle and provides instant predictions.
"""
from pathlib import Path
import joblib
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "champion_models.pkl"

class DelayPredictor:
    def __init__(self, model_path=MODEL_PATH):
        if not Path(model_path).exists():
            raise FileNotFoundError(f"Model file not found at {model_path}. Run train.py first.")
        self.bundle = joblib.load(model_path)
        self.regressor = self.bundle["regressor"]
        self.classifier = self.bundle["classifier"]
        self.feature_names = self.bundle["feature_names"]
        self.label_mappings = self.bundle["label_mappings"]
        self.metrics = self.bundle["metrics"]

    def predict(self, feature_dict):
        """
        Takes a raw dictionary of journey features and outputs:
        - predicted_delay_minutes
        - delay_probability_pct
        - risk_category ('Low', 'Moderate', 'High', 'Severe')
        """
        vector = []
        for name in self.feature_names:
            val = feature_dict.get(name, 0)
            if name in self.label_mappings:
                val_mapped = self.label_mappings[name].get(str(val), 0)
                vector.append(val_mapped)
            else:
                try:
                    vector.append(float(val))
                except (ValueError, TypeError):
                    vector.append(0.0)
                    
        X = np.array([vector])
        pred_minutes = max(0.0, float(self.regressor.predict(X)[0]))
        pred_prob = float(self.classifier.predict_proba(X)[0, 1]) * 100.0
        
        if pred_minutes < 15:
            risk = "Low (On-Time)"
            color = "green"
        elif pred_minutes < 45:
            risk = "Moderate Delay"
            color = "yellow"
        elif pred_minutes < 90:
            risk = "High Cascade Risk"
            color = "orange"
        else:
            risk = "Severe Gridlock"
            color = "red"
            
        return {
            "predicted_delay_minutes": round(pred_minutes, 1),
            "delay_probability_pct": round(pred_prob, 1),
            "risk_category": risk,
            "risk_color": color
        }

if __name__ == "__main__":
    predictor = DelayPredictor()
    sample_journey = {
        "zone_abbr": "NR",
        "train_type": "Superfast Express",
        "season": "Winter/Fog",
        "departure_hour": 7,
        "is_peak_hour": 1,
        "is_fog_risk": 1,
        "fog_risk_score": 0.85,
        "zone_congestion_index": 0.88,
        "is_hdn_route": 1,
        "late_incoming_rake": 1,
        "is_rake_shared": 1,
        "rake_cascade_chain_length": 2,
        "zone_delay_pressure": 65.0,
        "distance_km": 850,
        "num_scheduled_stops": 12,
        "scheduled_travel_hours": 14.5,
        "route_historical_ontime_pct": 60.0
    }
    res = predictor.predict(sample_journey)
    print("Inference Test:")
    print(f"  Predicted Delay : {res['predicted_delay_minutes']} mins")
    print(f"  Delay Prob      : {res['delay_probability_pct']}%")
    print(f"  Risk Category   : {res['risk_category']}")
