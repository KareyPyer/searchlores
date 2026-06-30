"""
LoreFrame : cadre interprétatif actif.

Une LoreFrame n'est plus un simple référentiel statique : c'est
un cadre qui module activement l'analyse en :
  - pondérant certains types de nœuds (weights)
  - activant/désactivant des règles d'inférence (active_rules)
  - filtrant certaines observations (filters)
  - ajoutant des règles d'inférence spécifiques (custom_rules)

Le même texte peut être analysé sous plusieurs LoreFrames
différentes, produisant des hypothèses et synthèses distinctes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from searchlores.graph.knowledge_graph import NodeType
from searchlores.observers.base import Observation
from searchlores.reasoning.inference_engine import InferenceRule


# Type pour les filtres d'observations
ObservationFilter = Callable[[Observation], bool]


@dataclass
class LoreFrame:
    """
    Cadre interprétatif actif.
    
    Une LoreFrame module l'analyse en :
      - pondérant certains types de nœuds (weights)
      - activant/désactivant des règles d'inférence (active_rules)
      - filtrant certaines observations (filters)
      - ajoutant des règles spécifiques (custom_rules)
    
    Attributes:
        name: identifiant de la Lore
        description: description en langage naturel
        weights: pondération par type de nœud (défaut=1.0)
        active_rules: noms des règles activées (None = toutes)
        filters: filtres appliqués aux observations
        custom_rules: règles d'inférence spécifiques à cette Lore
        expected_topics: topics attendus (pour détection d'omissions)
        metadata: métadonnées arbitraires
    
    Exemple :
    
        # Lore "critique des autorités"
        lore = LoreFrame(
            name="authority_skeptic",
            description="Scepticisme systématique envers les autorités",
            weights={
                NodeType.CONCEPT: 1.2,      # concepts surpondérés
                NodeType.INSTITUTION: 0.5,  # institutions sous-pondérées
            },
            filters=[
                lambda obs: obs.confidence >= 0.7,  # seuil élevé
            ],
        )
    """
    name: str
    description: str = ""
    weights: Dict[NodeType, float] = field(default_factory=dict)
    active_rules: Optional[List[str]] = None  # None = toutes
    filters: List[ObservationFilter] = field(default_factory=list)
    custom_rules: List[InferenceRule] = field(default_factory=list)
    expected_topics: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_weight(self, node_type: NodeType) -> float:
        """Retourne le poids d'un type de nœud (défaut=1.0)."""
        return self.weights.get(node_type, 1.0)

    def apply_filters(self, observations: List[Observation]) -> List[Observation]:
        """
        Applique tous les filtres aux observations.
        
        Une observation doit passer TOUS les filtres pour être retenue.
        """
        if not self.filters:
            return observations
        
        filtered: List[Observation] = []
        for obs in observations:
            if all(f(obs) for f in self.filters):
                filtered.append(obs)
        return filtered

    def is_rule_active(self, rule_name: str) -> bool:
        """Vérifie si une règle est activée par cette Lore."""
        if self.active_rules is None:
            return True  # toutes activées par défaut
        return rule_name in self.active_rules

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "weights": {k.value: v for k, v in self.weights.items()},
            "active_rules": self.active_rules,
            "expected_topics": self.expected_topics,
            "custom_rules_count": len(self.custom_rules),
            "filters_count": len(self.filters),
            "metadata": self.metadata,
        }

    @classmethod
    def default(cls) -> LoreFrame:
        """LoreFrame par défaut (neutre, aucun filtre)."""
        return cls(
            name="default",
            description="Cadre interprétatif neutre par défaut.",
        )

    @classmethod
    def skeptic(cls) -> LoreFrame:
        """LoreFrame sceptique : seuil de confiance élevé."""
        return cls(
            name="skeptic",
            description="Scepticisme méthodique : seules les observations "
                        "fortement étayées sont retenues.",
            weights={
                NodeType.HYPOTHESIS: 0.7,
                NodeType.ARGUMENT: 1.2,
            },
            filters=[lambda obs: obs.confidence >= 0.8],
        )

    @classmethod
    def institutional_critical(cls) -> LoreFrame:
        """LoreFrame critique envers les institutions."""
        return cls(
            name="institutional_critical",
            description="Analyse critique des discours institutionnels : "
                        "les marqueurs d'autorité sont surpondérés.",
            weights={
                NodeType.INSTITUTION: 1.5,
                NodeType.AUTHOR: 1.3,
                NodeType.CONCEPT: 1.1,
            },
            expected_topics=[
                "autorité", "institution", "pouvoir", "légitimité",
            ],
        )

    @classmethod
    def narrative_focus(cls) -> LoreFrame:
        """LoreFrame focalisée sur la structure narrative."""
        return cls(
            name="narrative_focus",
            description="Analyse focalisée sur la structure argumentative "
                        "et narrative du texte.",
            weights={
                NodeType.ARGUMENT: 1.5,
                NodeType.HYPOTHESIS: 1.3,
                NodeType.EVENT: 1.2,
            },
            active_rules=[
                "ConvergenceRule",
                "ContradictionRule",
                "ImplicationChainRule",
            ],
        )