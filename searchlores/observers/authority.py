"""
Observer V2 : détection d'autorités rhétoriques.

Réimplémentation du plugin V1 AuthorityDetector, mais produisant
des observations typées au lieu de conclusions directes.
"""
from __future__ import annotations

from typing import List

from searchlores.core.context import InvestigationContext
from searchlores.graph.knowledge_graph import (
    Evidence, KnowledgeGraph, Node, NodeType, RelationType,
)
from searchlores.observers.base import Observation, Observer


class AuthorityObserver(Observer):
    """
    Détecte les marqueurs d'autorité rhétorique.
    
    Catégories détectées :
      - institutional : "expert", "scientist", "government", etc.
      - moral : "obviously", "clearly", "everyone knows", etc.
      - technocratic : "algorithm", "data shows", "AI determined", etc.
    
    Chaque détection produit une observation avec :
      - un nœud CONCEPT (autorité_<category>)
      - une relation CITES vers le texte source
      - des preuves (citations des marqueurs)
    """
    name = "authority_observer"

    MARKERS = {
        "institutional": [
            "expert", "scientist", "researcher", "official",
            "government", "study", "peer-reviewed", "university",
            "institution", "authority", "specialist"
        ],
        "moral": [
            "obviously", "clearly", "undeniably", "everyone knows",
            "common sense", "moral duty", "ethical obligation",
            "right thing", "wrong thing"
        ],
        "technocratic": [
            "algorithm", "data shows", "metrics indicate",
            "AI determined", "model predicts", "statistically",
            "evidence-based", "data-driven", "optimization"
        ],
    }

    def observe(self, text: str, graph: KnowledgeGraph,
                context: InvestigationContext) -> List[Observation]:
        """Analyse le texte et retourne les autorités détectées."""
        text_lower = text.lower()
        observations: List[Observation] = []

        for category, markers in self.MARKERS.items():
            hits = [m for m in markers if m in text_lower]
            if not hits:
                continue

            # Nœud : l'autorité détectée
            authority_node = Node(
                id="",
                node_type=NodeType.CONCEPT,
                label=f"autorité_{category}",
                confidence=0.9,
                evidences=[
                    Evidence(text=m, source_plugin=self.name) for m in hits
                ],
                metadata={"category": category, "markers": hits},
            )
            
            # Nœud : le texte source
            source_node = Node(
                id="",
                node_type=NodeType.SOURCE,
                label="prompt_source",
                confidence=1.0,
            )
            
            observations.append(Observation(
                subject=authority_node,
                predicate=RelationType.CITES,
                object_node=source_node,
                confidence=0.9,
                evidences=[Evidence(text=h, source_plugin=self.name) for h in hits],
                metadata={"category": category, "markers": hits},
            ))
        
        return observations