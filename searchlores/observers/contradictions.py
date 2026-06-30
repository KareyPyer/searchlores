"""
Observer V2 : détection de contradictions sémantiques.

Réimplémentation du plugin V1 ContradictionFinder, mais produisant
des observations typées au lieu de conclusions directes.
"""
from __future__ import annotations

from typing import List

from searchlores.core.context import InvestigationContext
from searchlores.graph.knowledge_graph import (
    Evidence, KnowledgeGraph, Node, NodeType, RelationType,
)
from searchlores.observers.base import Observation, Observer


class ContradictionObserver(Observer):
    """
    Détecte les tensions sémantiques dans le texte.
    
    Paires de concepts opposés détectées :
      - unique/original vs standard/conventional
      - objective/neutral vs believe/think/feel
      - everyone/all vs some/sometimes
    
    Chaque détection produit une observation avec :
      - deux nœuds ARGUMENT (les pôles opposés)
      - une relation CONTRADICTS entre eux
      - des preuves (citations des marqueurs)
    """
    name = "contradiction_observer"

    PAIRS = [
        (["unique", "original", "novel", "innovative"],
         ["standard", "conventional", "typical", "traditional"]),
        (["objective", "neutral", "unbiased", "factual"],
         ["believe", "think", "feel", "opinion", "subjective"]),
        (["everyone", "all", "always", "never"],
         ["some", "sometimes", "exception", "rarely"]),
        (["simple", "easy", "straightforward"],
         ["complex", "complicated", "difficult", "challenging"]),
    ]

    def observe(self, text: str, graph: KnowledgeGraph,
                context: InvestigationContext) -> List[Observation]:
        """Analyse le texte et retourne les contradictions détectées."""
        text_lower = text.lower()
        observations: List[Observation] = []

        for pos, neg in self.PAIRS:
            pos_hits = [p for p in pos if p in text_lower]
            neg_hits = [n for n in neg if n in text_lower]
            
            if not (pos_hits and neg_hits):
                continue

            # Pôle positif
            pole_a = Node(
                id="",
                node_type=NodeType.ARGUMENT,
                label=f"pole_{'_'.join(pos_hits)}",
                confidence=0.8,
                evidences=[
                    Evidence(text=p, source_plugin=self.name) for p in pos_hits
                ],
                metadata={"polarity": "positive", "markers": pos_hits},
            )
            
            # Pôle négatif
            pole_b = Node(
                id="",
                node_type=NodeType.ARGUMENT,
                label=f"pole_{'_'.join(neg_hits)}",
                confidence=0.8,
                evidences=[
                    Evidence(text=n, source_plugin=self.name) for n in neg_hits
                ],
                metadata={"polarity": "negative", "markers": neg_hits},
            )
            
            observations.append(Observation(
                subject=pole_a,
                predicate=RelationType.CONTRADICTS,
                object_node=pole_b,
                confidence=0.85,
                evidences=[
                    Evidence(text=p, source_plugin=self.name) for p in pos_hits
                ] + [
                    Evidence(text=n, source_plugin=self.name) for n in neg_hits
                ],
                metadata={
                    "type": "semantic_tension",
                    "positive": pos_hits,
                    "negative": neg_hits,
                },
            ))
        
        return observations