"""
API des Observers (plugins V2).

Un Observer ne conclut JAMAIS. Il produit des observations
brutes, des faits, des citations et des relations, qui sont
injectés dans le Knowledge Graph avec leur provenance.

Différences avec les plugins V1 :
  - V1 : plugin.run(context) → écrit dans context.findings
  - V2 : observer.observe(text, graph, context) → retourne List[Observation]
  
Les observers V2 sont plus traçables, plus modulaires, et
permettent la coopération via le Knowledge Graph partagé.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

from searchlores.core.context import InvestigationContext
from searchlores.graph.knowledge_graph import (
    Evidence, KnowledgeGraph, Node, NodeType, Relation, RelationType,
)


@dataclass
class Observation:
    """
    Une observation atomique produite par un Observer.
    
    Une observation peut être :
      - un nœud isolé (subject seul)
      - une relation binaire (subject + predicate + object)
    
    Chaque observation porte :
      - confidence : niveau de confiance (0.0–1.0)
      - evidences : preuves (citations, spans)
      - metadata : métadonnées arbitraires
    """
    subject: Node                       # nœud principal observé
    predicate: Optional[RelationType] = None
    object_node: Optional[Node] = None  # cible si relation binaire
    confidence: float = 1.0
    evidences: List[Evidence] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class Observer(ABC):
    """
    Interface de base pour tous les observers V2.
    
    Un observer reçoit le texte + le graphe + la Lore active
    et retourne une liste d'observations. Il ne modifie JAMAIS
    directement le graphe : c'est le moteur qui s'en charge
    (cela garantit la traçabilité).
    
    Pour créer un observer personnalisé :
    
        class MyObserver(Observer):
            name = "my_observer"
            
            def observe(self, text, graph, context):
                # Analyse le texte
                # Retourne des observations
                return [
                    Observation(
                        subject=Node(...),
                        confidence=0.9,
                        evidences=[...]
                    )
                ]
    """
    name: str = "observer"
    version: str = "2.0"

    @abstractmethod
    def observe(self, text: str, graph: KnowledgeGraph,
                context: InvestigationContext) -> List[Observation]:
        """
        Analyse le texte et retourne des observations.
        
        Args:
            text: texte à analyser
            graph: graphe de connaissances (lecture seule)
            context: contexte d'investigation (Lore, metadata, etc.)
        
        Returns:
            Liste d'observations atomiques
        """
        ...