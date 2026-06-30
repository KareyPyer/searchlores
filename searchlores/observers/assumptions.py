"""
Observer V2 : extraction d'hypothèses implicites.

Réimplémentation du plugin V1 AssumptionExtractor, mais produisant
des observations typées au lieu de conclusions directes.
"""
from __future__ import annotations

import re
from typing import List

from searchlores.core.context import InvestigationContext
from searchlores.graph.knowledge_graph import (
    Evidence, KnowledgeGraph, Node, NodeType, RelationType,
)
from searchlores.observers.base import Observation, Observer


class AssumptionObserver(Observer):
    """
    Identifie les hypothèses implicites dans le texte.
    
    Marqueurs détectés :
      - conditionnels : "if", "when", "assuming"
      - généralisations : "everyone", "always", "never"
      - présuppositions : "obviously", "clearly", "naturally"
    
    Chaque détection produit une observation avec :
      - un nœud HYPOTHESIS (l'hypothèse extraite)
      - une relation SUPPORTS vers le texte source
      - des preuves (citations des marqueurs)
    """
    name = "assumption_observer"

    PATTERNS = {
        "conditional": [
            r"\bif\b.*\bthen\b",
            r"\bwhen\b.*\bwill\b",
            r"\bassuming\b",
            r"\bprovided\b",
        ],
        "generalization": [
            r"\beveryone\b",
            r"\ball\b.*\bwill\b",
            r"\bnever\b",
            r"\balways\b",
        ],
        "presupposition": [
            r"\bobviously\b",
            r"\bclearly\b",
            r"\bnaturally\b",
            r"\bof course\b",
        ],
    }

    def observe(self, text: str, graph: KnowledgeGraph,
                context: InvestigationContext) -> List[Observation]:
        """Analyse le texte et retourne les hypothèses détectées."""
        text_lower = text.lower()
        observations: List[Observation] = []

        for category, patterns in self.PATTERNS.items():
            hits: List[str] = []
            for pattern in patterns:
                matches = re.findall(pattern, text_lower)
                hits.extend(matches)
            
            if not hits:
                continue

            # Nœud : l'hypothèse détectée
            hypothesis_node = Node(
                id="",
                node_type=NodeType.HYPOTHESIS,
                label=f"hypothèse_{category}",
                confidence=0.75,
                evidences=[
                    Evidence(text=h, source_plugin=self.name) for h in hits
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
                subject=hypothesis_node,
                predicate=RelationType.SUPPORTS,
                object_node=source_node,
                confidence=0.75,
                evidences=[Evidence(text=h, source_plugin=self.name) for h in hits],
                metadata={"category": category, "markers": hits},
            ))
        
        return observations