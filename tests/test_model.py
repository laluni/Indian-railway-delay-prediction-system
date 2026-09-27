from pathlib import Path
from src.predictor import DelayPredictor

def test_champion_model_loading_and_prediction():
    predictor = DelayPredictor()
    
    sample_on_time = {
        "zone_abbr": "SWR",
        "train_type": "Vande Bharat Express",
        "season": "Summer",
        "departure_hour": 14,
        "is_peak_hour": 0,
        "is_fog_risk": 0,
        "fog_risk_score": 0.0,
        "zone_congestion_index": 0.40,
        "is_hdn_route": 0,
        "late_incoming_rake": 0,
        "is_rake_shared": 0,
        "rake_cascade_chain_length": 0,
        "zone_delay_pressure": 5.0,
        "distance_km": 350,
        "num_scheduled_stops": 4,
        "scheduled_travel_hours": 4.5,
        "route_historical_ontime_pct": 92.0
    }
    res = predictor.predict(sample_on_time)
    assert res["predicted_delay_minutes"] >= 0.0
    assert 0.0 <= res["delay_probability_pct"] <= 100.0
    assert res["risk_category"] in ["Low (On-Time)", "Moderate Delay", "High Cascade Risk", "Severe Gridlock"]

def test_cascade_delay_elevation():
    predictor = DelayPredictor()
    
    base = {
        "zone_abbr": "NCR",
        "train_type": "Mail/Express",
        "season": "Winter/Fog",
        "departure_hour": 8,
        "is_peak_hour": 1,
        "zone_congestion_index": 0.85,
        "is_hdn_route": 1,
        "distance_km": 900,
        "route_historical_ontime_pct": 55.0,
        "late_incoming_rake": 0,
        "is_rake_shared": 0,
        "rake_cascade_chain_length": 0,
        "zone_delay_pressure": 20.0
    }
    res_base = predictor.predict(base)
    
    # Simulate cascade trigger: late incoming rake + high cascade chain length + zone congestion pressure
    cascade = base.copy()
    cascade.update({
        "late_incoming_rake": 1,
        "is_rake_shared": 1,
        "rake_cascade_chain_length": 3,
        "zone_delay_pressure": 85.0
    })
    res_cascade = predictor.predict(cascade)
    
    # Assert that cascade features produce a noticeably higher delay prediction
    assert res_cascade["predicted_delay_minutes"] > res_base["predicted_delay_minutes"], \
        "Cascade features must elevate predicted delay minutes"
    print("Model tests passed! Cascade amplification verified.")

if __name__ == "__main__":
    test_champion_model_loading_and_prediction()
    test_cascade_delay_elevation()
