"""
Module de débat interne.

Le débat est un processus dialectique qui :
  - collecte des preuves et contre-preuves pour chaque hypothèse
  - calcule un score dialectique
  - décide du statut de chaque hypothèse
  - produit un verdict explicable
"""
from searchlores.reasoning.debate.argument import (
    Argument, ArgumentKind, ArgumentPolarity,
)
from searchlores.reasoning.debate.debated_hypothesis import (
    DebatedHypothesis, HypothesisStatus,
)
from searchlores.reasoning.debate.debate_engine import (
    DebateConfig, DebateEngine,
)
from searchlores.reasoning.debate.strategies import (
    AbsenceStrategy, CompetitorStrategy, ConvergenceStrategy,
    DebateStrategy, EvidenceGatheringStrategy,
)
from searchlores.reasoning.debate.verdict import Verdict

__all__ = [
    "Argument",
    "ArgumentKind",
    "ArgumentPolarity",
    "DebatedHypothesis",
    "HypothesisStatus",
    "DebateConfig",
    "DebateEngine",
    "AbsenceStrategy",
    "CompetitorStrategy",
    "ConvergenceStrategy",
    "DebateStrategy",
    "EvidenceGatheringStrategy",
    "Verdict",
]