from src.graph_builder import build_railway_graph, get_zone_centrality_metrics
from src.cascade_features import engineer_cascade_features

def test_railway_graph_structure():
    G = build_railway_graph()
    # 1. Verify 16 IR zones exist
    assert len(G.nodes()) == 16, f"Expected 16 nodes, found {len(G.nodes())}"
    # 2. Verify graph is fully connected (no isolated zone)
    import networkx as nx
    assert nx.is_connected(G), "Railway network graph must be fully connected"
    
def test_centrality_metrics():
    metrics = get_zone_centrality_metrics()
    assert len(metrics) == 16
    for zone, m in metrics.items():
        assert 0.0 <= m["corridor_betweenness_centrality"] <= 1.0
        assert 0.0 <= m["corridor_degree_centrality"] <= 1.0

def test_cascade_feature_engineering():
    df = engineer_cascade_features(sample_limit=1000)
    assert "rake_cascade_chain_length" in df.columns
    assert "zone_delay_pressure" in df.columns
    assert "corridor_betweenness_centrality" in df.columns
    assert len(df) == 1000
    print("Graph & cascade feature engineering tests passed successfully!")

if __name__ == "__main__":
    test_railway_graph_structure()
    test_centrality_metrics()
    test_cascade_feature_engineering()
