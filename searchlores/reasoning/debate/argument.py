"""
Argument : preuve ou contre-preuve attachée à une hypothèse.

Un Argument est une unité élémentaire du débat : il justifie
pourquoi une hypothèse est soutenue ou affaiblie. Chaque argument
est traçable à des nœuds/relations du Knowledge Graph.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ArgumentPolarity(str, Enum):
    """Polarité d'un argument : pour ou contre une hypothèse."""
    SUPPORT = "support"           # argument en faveur
    UNDERMINE = "undermine"       # argument affaiblissant
    ATTACK = "attack"             # argument réfutant directement
    NEUTRAL = "neutral"           # information contextuelle


class ArgumentKind(str, Enum):
    """Nature de l'argument."""
    DIRECT_EVIDENCE = "direct_evidence"           # citation directe
    STRUCTURAL_SUPPORT = "structural_support"     # support structurel (centralité)
    CONVERGENCE = "convergence"                   # multiple sources
    CONTRADICTION = "contradiction"               # tension détectée
    ABSENCE = "absence"                           # omission (manque de preuve)
    COMPETITOR = "competitor"                     # hypothèse concurrente
    COHERENCE = "coherence"                       # cohérence avec le graphe


@dataclass
class Argument:
    """
    Preuve ou contre-preuve attachée à une hypothèse.
    
    Chaque argument porte :
      - polarity : pour/contre/neutre
      - kind : nature de l'argument
      - weight : poids (0.0–1.0) combinant confiance et pertinence
      - source_ids : IDs des nœuds/relations du graphe impliqués
      - justification : explication en langage naturel
      - provenance : plugins/observers à l'origine
    
    L'argument est immuable dans son intenté : il ne peut pas
    être modifié après création (garantie de traçabilité).
    """
    polarity: ArgumentPolarity
    kind: ArgumentKind
    weight: float
    justification: str
    source_ids: List[str] = field(default_factory=list)
    provenance: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(f"weight must be in [0,1], got {self.weight}")

    @property
    def is_supportive(self) -> bool:
        """True si l'argument soutient l'hypothèse."""
        return self.polarity in (ArgumentPolarity.SUPPORT,)

    @property
    def is_hostile(self) -> bool:
        """True si l'argument affaiblit ou attaque l'hypothèse."""
        return self.polarity in (
            ArgumentPolarity.UNDERMINE,
            ArgumentPolarity.ATTACK,
        )

    @property
    def signed_weight(self) -> float:
        """
        Poids signé : positif si support, négatif si hostile.
        
        Utilisé pour le calcul du score dialectique.
        """
        if self.is_supportive:
            return self.weight
        if self.is_hostile:
            return -self.weight
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "polarity": self.polarity.value,
            "kind": self.kind.value,
            "weight": self.weight,
            "signed_weight": round(self.signed_weight, 4),
            "justification": self.justification,
            "source_ids": self.source_ids,
            "provenance": self.provenance,
            "metadata": self.metadata,
        }

    @classmethod
    def support(cls, kind: ArgumentKind, weight: float,
                justification: str, **kwargs) -> Argument:
        """Factory pour un argument en faveur."""
        return cls(
            polarity=ArgumentPolarity.SUPPORT,
            kind=kind, weight=weight,
            justification=justification, **kwargs,
        )

    @classmethod
    def undermine(cls, kind: ArgumentKind, weight: float,
                  justification: str, **kwargs) -> Argument:
        """Factory pour un argument affaiblissant."""
        return cls(
            polarity=ArgumentPolarity.UNDERMINE,
            kind=kind, weight=weight,
            justification=justification, **kwargs,
        )

    @classmethod
    def attack(cls, kind: ArgumentKind, weight: float,
               justification: str, **kwargs) -> Argument:
        """Factory pour un argument réfutant."""
        return cls(
            polarity=ArgumentPolarity.ATTACK,
            kind=kind, weight=weight,
            justification=justification, **kwargs,
        )