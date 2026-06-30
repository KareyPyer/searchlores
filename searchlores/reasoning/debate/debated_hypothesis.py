"""
DebatedHypothesis : hypothèse enrichie par le débat.

Une DebatedHypothesis est une Hypothesis à laquelle ont été
attachés des arguments (pour/contre). Elle possède un score
dialectique calculé à partir de ses arguments, et un statut
(retained/eliminated/contested).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from searchlores.reasoning.debate.argument import Argument


class HypothesisStatus(str, Enum):
    """Statut d'une hypothèse après le débat."""
    RETAINED = "retained"           # solidement étayée
    CONTESTED = "contested"         # débat ouvert (preuves ET contre-preuves)
    WEAKENED = "weakened"           # affaiblie mais non éliminée
    ELIMINATED = "eliminated"       # rejetée (trop peu de preuves)
    SUPERSEDED = "superseded"       # remplacée par une hypothèse plus forte


@dataclass
class DebatedHypothesis:
    """
    Hypothèse ayant subi le processus de débat.
    
    Enrichit l'Hypothesis originale avec :
      - arguments : liste de preuves/contre-preuves
      - dialectical_score : score issu du débat (-1.0 à +1.0)
      - status : statut après le débat
      - competitors : hypothèses concurrentes incompatibles
      - verdict_notes : explication du verdict
    
    Le dialectical_score est calculé ainsi :
      score = Σ(signed_weight) / (Σ|weight| + ε)
    
    Un score proche de +1.0 = hypothèse fortement étayée.
    Un score proche de -1.0 = hypothèse fortement réfutée.
    Un score proche de 0.0 = débat ouvert / incertain.
    """
    label: str
    statement: str
    original_confidence: float
    arguments: List[Argument] = field(default_factory=list)
    dialectical_score: float = 0.0
    status: HypothesisStatus = HypothesisStatus.CONTESTED
    competitors: List[str] = field(default_factory=list)
    verdict_notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ── Calcul du score dialectique ──────────────────────────
    def compute_dialectical_score(self, epsilon: float = 0.1) -> float:
        """
        Calcule le score dialectique à partir des arguments.
        
        Formule : Σ(signed_weight) / (Σ|weight| + ε)
        
        Args:
            epsilon: terme de lissage pour éviter division par zéro
        
        Returns:
            Score dans [-1.0, +1.0]
        """
        if not self.arguments:
            self.dialectical_score = 0.0
            return 0.0
        
        signed_sum = sum(a.signed_weight for a in self.arguments)
        abs_sum = sum(abs(a.weight) for a in self.arguments)
        
        if abs_sum == 0:
            self.dialectical_score = 0.0
            return 0.0
        
        self.dialectical_score = signed_sum / (abs_sum + epsilon)
        return self.dialectical_score

    # ── Agrégats ─────────────────────────────────────────────
    @property
    def supportive_arguments(self) -> List[Argument]:
        """Arguments en faveur de l'hypothèse."""
        return [a for a in self.arguments if a.is_supportive]

    @property
    def hostile_arguments(self) -> List[Argument]:
        """Arguments contre l'hypothèse."""
        return [a for a in self.arguments if a.is_hostile]

    @property
    def support_weight(self) -> float:
        """Poids total des arguments en faveur."""
        return sum(a.weight for a in self.supportive_arguments)

    @property
    def hostility_weight(self) -> float:
        """Poids total des arguments contre."""
        return sum(a.weight for a in self.hostile_arguments)

    @property
    def argument_count(self) -> int:
        return len(self.arguments)

    @property
    def is_robust(self) -> bool:
        """True si l'hypothèse a plus de supports que d'attaques."""
        return self.support_weight > self.hostility_weight

    # ── Mutation de statut ───────────────────────────────────
    def decide_status(self, retain_threshold: float = 0.3,
                      eliminate_threshold: float = -0.2,
                      contest_margin: float = 0.2) -> HypothesisStatus:
        """
        Détermine le statut de l'hypothèse selon son score.
        
        Args:
            retain_threshold: score minimum pour RETAINED
            eliminate_threshold: score en-dessous duquel ELIMINATED
            contest_margin: marge autour de 0 pour CONTESTED
        
        Returns:
            Statut décidé
        """
        score = self.dialectical_score
        
        if score >= retain_threshold:
            self.status = HypothesisStatus.RETAINED
        elif score <= eliminate_threshold:
            self.status = HypothesisStatus.ELIMINATED
        elif abs(score) < contest_margin:
            self.status = HypothesisStatus.CONTESTED
        else:
            self.status = HypothesisStatus.WEAKENED
        
        return self.status

    # ── Explication ──────────────────────────────────────────
    def explain(self) -> Dict[str, Any]:
        """
        Retourne l'explication complète du débat autour de cette hypothèse.
        
        Utilisé par la GUI pour le panneau "Pourquoi cette conclusion ?".
        """
        return {
            "label": self.label,
            "statement": self.statement,
            "original_confidence": self.original_confidence,
            "dialectical_score": round(self.dialectical_score, 4),
            "status": self.status.value,
            "support_count": len(self.supportive_arguments),
            "hostile_count": len(self.hostile_arguments),
            "support_weight": round(self.support_weight, 4),
            "hostility_weight": round(self.hostility_weight, 4),
            "arguments": [a.to_dict() for a in self.arguments],
            "competitors": self.competitors,
            "verdict_notes": self.verdict_notes,
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.explain()