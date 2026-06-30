"""
Verdict : résultat final du débat.

Le Verdict synthétise les décisions prises par le DebateEngine :
quelles hypothèses sont retenues, lesquelles sont éliminées,
et pourquoi. Il est entièrement explicable et traçable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from searchlores.reasoning.debate.debated_hypothesis import (
    DebatedHypothesis, HypothesisStatus,
)


@dataclass
class Verdict:
    """
    Résultat structuré du débat.
    
    Contient :
      - retained : hypothèses solidement étayées
      - contested : hypothèses avec débat ouvert
      - weakened : hypothèses affaiblies
      - eliminated : hypothèses rejetées
      - summary : résumé en langage naturel
      - statistics : métriques du débat
    
    Le verdict est l'entrée principale pour la synthèse finale
    et pour la GUI (panneau "Trace du raisonnement").
    """
    retained: List[DebatedHypothesis] = field(default_factory=list)
    contested: List[DebatedHypothesis] = field(default_factory=list)
    weakened: List[DebatedHypothesis] = field(default_factory=list)
    eliminated: List[DebatedHypothesis] = field(default_factory=list)
    summary: str = ""
    statistics: Dict[str, Any] = field(default_factory=dict)

    @property
    def all_debated(self) -> List[DebatedHypothesis]:
        """Toutes les hypothèses débattues (tout statut confondu)."""
        return self.retained + self.contested + self.weakened + self.eliminated

    @property
    def final_conclusions(self) -> List[DebatedHypothesis]:
        """
        Conclusions finales : hypothèses retenues ET contestées.
        
        Les contestées sont conservées car le débat n'est pas tranché :
        c'est un signal d'incertitude légitime, pas un échec.
        """
        return self.retained + self.contested

    @property
    def robust_conclusions(self) -> List[DebatedHypothesis]:
        """Uniquement les hypothèses solidement étayées."""
        return list(self.retained)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "retained": [h.to_dict() for h in self.retained],
            "contested": [h.to_dict() for h in self.contested],
            "weakened": [h.to_dict() for h in self.weakened],
            "eliminated": [h.to_dict() for h in self.eliminated],
            "summary": self.summary,
            "statistics": self.statistics,
        }

    def build_summary(self) -> str:
        """
        Construit le résumé en langage naturel du verdict.
        
        Chaque phrase est traçable aux hypothèses et arguments.
        """
        parts: List[str] = []

        total = len(self.all_debated)
        parts.append(f"Débat portant sur {total} hypothèse(s).")

        if self.retained:
            labels = ", ".join(f"« {h.label} »" for h in self.retained[:3])
            parts.append(
                f"{len(self.retained)} hypothèse(s) retenue(s) : {labels}."
            )

        if self.contested:
            labels = ", ".join(f"« {h.label} »" for h in self.contested[:3])
            parts.append(
                f"{len(self.contested)} hypothèse(s) en débat ouvert : {labels}."
            )

        if self.weakened:
            parts.append(
                f"{len(self.weakened)} hypothèse(s) affaiblie(s) "
                f"mais non éliminée(s)."
            )

        if self.eliminated:
            parts.append(
                f"{len(self.eliminated)} hypothèse(s) éliminée(s) "
                f"(preuves insuffisantes ou contradictions trop fortes)."
            )

        # Signal d'incertitude globale
        if self.contested and not self.retained:
            parts.append(
                "Aucune hypothèse solidement étayée : l'investigation "
                "nécessite davantage de données."
            )
        elif len(self.retained) >= 2:
            parts.append(
                f"Plusieurs conclusions coexistent : le raisonnement "
                f"n'est pas univoque, ce qui reflète la complexité du texte."
            )

        self.summary = " ".join(parts)
        return self.summary

    def build_statistics(self) -> Dict[str, Any]:
        """Construit les statistiques du débat."""
        all_h = self.all_debated
        if not all_h:
            self.statistics = {}
            return self.statistics

        scores = [h.dialectical_score for h in all_h]
        self.statistics = {
            "total_hypotheses": len(all_h),
            "retained_count": len(self.retained),
            "contested_count": len(self.contested),
            "weakened_count": len(self.weakened),
            "eliminated_count": len(self.eliminated),
            "avg_dialectical_score": (
                sum(scores) / len(scores) if scores else 0.0
            ),
            "max_dialectical_score": max(scores) if scores else 0.0,
            "min_dialectical_score": min(scores) if scores else 0.0,
            "total_arguments": sum(h.argument_count for h in all_h),
            "total_support_weight": sum(
                h.support_weight for h in all_h
            ),
            "total_hostility_weight": sum(
                h.hostility_weight for h in all_h
            ),
        }
        return self.statistics