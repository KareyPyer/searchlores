import json
import pandas as pd
import plotly.graph_objects as go
from collections import Counter
import networkx as nx

def extract_narrative_flow(data):
    """Extrait le flux narratif du prompt."""
    levels = data.get("findings", {}).get("narrative_levels", [])
    if not levels:
        return []
    return [(l.get("level", 0), l.get("voice", ""), l.get("content", "")) for l in levels]

def compute_regime_scores(data):
    """Retourne un DataFrame des scores par régime."""
    regimes = data.get("findings", {}).get("epistemic_regimes", [])
    results = []
    for r in regimes:
        if not isinstance(r, dict):
            continue
        row = {
            "Segment": r.get("segment", "")[:60],
            "Régime": r.get("regime", "unknown"),
            "Confiance": r.get("confidence", 0)
        }
        scores = r.get("regime_scores", {})
        row.update(scores)
        results.append(row)
    return pd.DataFrame(results)

def build_authority_network(data):
    """Construit un réseau d'autorités à partir des données."""
    G = nx.DiGraph()
    authorities = data.get("findings", {}).get("implicit_authorities", [])
    power_dynamics = data.get("findings", {}).get("power_dynamics", [])
    
    # Ajouter les nœuds d'autorité
    for auth in authorities:
        if isinstance(auth, dict):
            agent = auth.get("agent", "inconnu")
            G.add_node(agent, type=auth.get("authority_type", "inconnu"), 
                      confidence=auth.get("confidence", 0))
    
    # Ajouter les relations de pouvoir
    for dyn in power_dynamics:
        if dyn is None:
            continue
        if isinstance(dyn, dict):
            dom = dyn.get("dominant_agent")
            sub = dyn.get("submissive_agent")
            if dom and sub:
                G.add_edge(dom, sub, weight=dyn.get("asymmetry_score", 0.5))
    
    return G