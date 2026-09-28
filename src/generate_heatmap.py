"""
Generates a Feature Correlation Heatmap for the Indian Railways Delay Analytics project.
Computes Pearson correlation across all numerical operational, weather, cascade, and target features.
Saves:
1. High-resolution PNG image: docs/feature_correlation_heatmap.png
2. JSON summary of top correlated pairs: models/correlation_summary.json
"""
import json
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import polars as pl
from src.cascade_features import engineer_cascade_features

BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "docs"
MODELS_DIR = BASE_DIR / "models"
OUTPUT_IMAGE = DOCS_DIR / "feature_correlation_heatmap.png"
OUTPUT_JSON = MODELS_DIR / "correlation_summary.json"

def generate_correlation_matrix(sample_size=100000):
    print("=" * 70)
    print(f"Generating Correlation Heatmap on {sample_size:,} Journeys")
    print("=" * 70)
    
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    df = engineer_cascade_features(sample_limit=sample_size)
    
    # Key numerical features representing all domains:
    # 1. Target & Delay: delay_minutes, is_delayed
    # 2. Engineered Cascade: zone_delay_pressure, rake_cascade_chain_length, corridor_betweenness_centrality
    # 3. Weather & Environment: fog_risk_score, zone_fog_index, season_severity_score, is_monsoon_season
    # 4. Route & Track: distance_km, num_scheduled_stops, scheduled_travel_hours, psr_count, is_hdn_route, track_doubled
    # 5. Assets & Operations: loco_age_years, coach_age_years, maintenance_score, seat_utilisation_pct, late_incoming_rake, is_rake_shared, route_historical_ontime_pct, zone_congestion_index
    
    corr_columns = [
        "delay_minutes",
        "is_delayed",
        "zone_delay_pressure",
        "rake_cascade_chain_length",
        "corridor_betweenness_centrality",
        "route_historical_ontime_pct",
        "zone_congestion_index",
        "late_incoming_rake",
        "is_rake_shared",
        "fog_risk_score",
        "zone_fog_index",
        "season_severity_score",
        "is_hdn_route",
        "track_doubled",
        "distance_km",
        "num_scheduled_stops",
        "scheduled_travel_hours",
        "psr_count",
        "loco_age_years",
        "coach_age_years",
        "maintenance_score",
        "seat_utilisation_pct"
    ]
    
    # Filter and convert to pandas for seaborn
    sub_df = df.select(corr_columns).to_pandas()
    corr_matrix = sub_df.corr(method="pearson").round(2)
    
    # Set up matplotlib figure
    plt.figure(figsize=(18, 14))
    sns.set_theme(style="white")
    
    # Mask upper triangle for aesthetic readability
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
    
    cmap = sns.diverging_palette(230, 20, as_cmap=True)
    
    heatmap = sns.heatmap(
        corr_matrix,
        mask=mask,
        cmap=cmap,
        vmax=1.0,
        vmin=-1.0,
        center=0,
        square=True,
        linewidths=.5,
        cbar_kws={"shrink": .8, "label": "Pearson Correlation Coefficient (r)"},
        annot=True,
        fmt=".2f",
        annot_kws={"size": 9}
    )
    
    plt.title("Indian Railway Delay Cascade Analytics: Feature Correlation Matrix", fontsize=18, pad=20, fontweight="bold")
    plt.tight_layout()
    plt.savefig(str(OUTPUT_IMAGE), dpi=300)
    plt.close()
    print(f"Heatmap successfully saved to: {OUTPUT_IMAGE}")
    
    # Identify top positive and negative correlations with delay_minutes
    target_corr = corr_matrix["delay_minutes"].drop(["delay_minutes", "is_delayed"]).sort_values(ascending=False)
    
    top_positive = target_corr.head(5).to_dict()
    top_negative = target_corr.tail(5).to_dict()
    
    summary = {
        "top_positive_correlations_with_delay": top_positive,
        "top_negative_correlations_with_delay": top_negative,
        "full_matrix": corr_matrix.to_dict()
    }
    
    with open(OUTPUT_JSON, "w") as f:
        json.dump(summary, f, indent=4)
        
    print("\nTop Positive Correlates with Arrival Delay (delay_minutes):")
    for k, v in top_positive.items():
        print(f"  + {k:32s} : r = {v:+.2f}")
        
    print("\nTop Negative Correlates with Arrival Delay (delay_minutes):")
    for k, v in top_negative.items():
        print(f"  - {k:32s} : r = {v:+.2f}")
        
    return summary

if __name__ == "__main__":
    generate_correlation_matrix()
