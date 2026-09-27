"""
Graph Builder for Indian Railway Zones & Corridors.
Constructs a topological network of the 16 IR zones and computes network centrality metrics.
"""
import networkx as nx

def build_railway_graph():
    """
    Builds a network graph of the 16 Indian Railway zones based on geographical adjacency
    and major High-Density Network (HDN) connecting corridors (Golden Quadrilateral & Diagonals).
    """
    G = nx.Graph()
    
    # 16 Indian Railway Zones (Abbreviations & HQ Locations)
    zones = [
        ("NR", {"name": "Northern Railway", "hq": "New Delhi"}),
        ("NCR", {"name": "North Central Railway", "hq": "Prayagraj"}),
        ("NER", {"name": "North Eastern Railway", "hq": "Gorakhpur"}),
        ("NWR", {"name": "North Western Railway", "hq": "Jaipur"}),
        ("ER", {"name": "Eastern Railway", "hq": "Kolkata"}),
        ("ECR", {"name": "East Central Railway", "hq": "Hajipur"}),
        ("ECoR", {"name": "East Coast Railway", "hq": "Bhubaneswar"}),
        ("CR", {"name": "Central Railway", "hq": "Mumbai CSMT"}),
        ("WR", {"name": "Western Railway", "hq": "Mumbai Churchgate"}),
        ("WCR", {"name": "West Central Railway", "hq": "Jabalpur"}),
        ("SR", {"name": "Southern Railway", "hq": "Chennai"}),
        ("SCR", {"name": "South Central Railway", "hq": "Secunderabad"}),
        ("SWR", {"name": "South Western Railway", "hq": "Hubballi"}),
        ("SER", {"name": "South Eastern Railway", "hq": "Kolkata"}),
        ("SECR", {"name": "South East Central Railway", "hq": "Bilaspur"}),
        ("NFR", {"name": "Northeast Frontier Railway", "hq": "Guwahati"}),
    ]
    
    for code, attrs in zones:
        G.add_node(code, **attrs)
        
    # Inter-Zone HDN & Trunk Corridors
    corridors = [
        ("NR", "NCR"), ("NR", "NWR"), ("NR", "NER"),
        ("NCR", "ECR"), ("NCR", "WCR"), ("NCR", "NER"),
        ("ECR", "ER"), ("ECR", "SER"),
        ("ER", "SER"), ("ER", "NFR"),
        ("NWR", "WR"), ("NWR", "WCR"),
        ("WCR", "CR"), ("WCR", "SECR"),
        ("WR", "CR"),
        ("CR", "SCR"), ("CR", "SECR"),
        ("SCR", "SWR"), ("SCR", "SR"), ("SCR", "ECoR"),
        ("SER", "SECR"), ("SER", "ECoR"),
        ("SECR", "ECoR"),
        ("ECoR", "SR"),
        ("SWR", "SR")
    ]
    
    G.add_edges_from(corridors)
    return G

def get_zone_centrality_metrics():
    """
    Computes betweenness centrality and degree centrality for each zone.
    Betweenness centrality quantifies how often a zone acts as a critical transit chokepoint.
    """
    G = build_railway_graph()
    betweenness = nx.betweenness_centrality(G, normalized=True)
    degree = nx.degree_centrality(G)
    
    metrics = {}
    for node in G.nodes():
        metrics[node] = {
            "corridor_betweenness_centrality": round(betweenness[node], 4),
            "corridor_degree_centrality": round(degree[node], 4)
        }
    return metrics

if __name__ == "__main__":
    metrics = get_zone_centrality_metrics()
    print("Zone Centrality Metrics (Top Chokepoints):")
    sorted_metrics = sorted(metrics.items(), key=lambda x: x[1]["corridor_betweenness_centrality"], reverse=True)
    for zone, m in sorted_metrics[:5]:
        print(f"  Zone: {zone:5s} | Betweenness: {m['corridor_betweenness_centrality']:.4f} | Degree: {m['corridor_degree_centrality']:.4f}")
