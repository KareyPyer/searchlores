"""
Structure de données pour les hypothèses inférées.

Une Hypothesis représente une conclusion produite par le moteur
d'inférence à partir du Knowledge Graph. Chaque hypothèse porte :
  - un score de confiance
  - les nœuds qui la soutiennent
  - les nœuds qui la contredisent
  - les plugins impliqués dans sa production
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Hypothesis:
    """
    Hypothèse inférée à partir du Knowledge Graph.
    
    Une hypothèse n'est pas une conclusion définitive, mais une
    proposition pondérée qui peut être comparée à d'autres
    hypothèses concurrentes.
    
    Attributes:
        label: identifiant court de l'hypothèse
        statement: énoncé complet de l'hypothèse
        confidence: niveau de confiance (0.0–1.0)
        supporting: IDs des nœuds qui soutiennent l'hypothèse
        contradicting: IDs des nœuds qui contredisent l'hypothèse
        provenance: noms des plugins/observers impliqués
        metadata: métadonnées arbitraires
    """
    label: str
    statement: str
    confidence: float
    supporting: List[str] = field(default_factory=list)
    contradicting: List[str] = field(default_factory=list)
    provenance: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0,1], got {self.confidence}")

    def to_dict(self) -> Dict[str, Any]:
        """Sérialisation pour export JSON."""
        return {
            "label": self.label,
            "statement": self.statement,
            "confidence": self.confidence,
            "supporting": self.supporting,
            "contradicting": self.contradicting,
            "provenance": self.provenance,
            "metadata": self.metadata,
        }

    def __lt__(self, other: Hypothesis) -> bool:
        """Permet le tri par confiance décroissante."""
        return self.confidence < other.confidence