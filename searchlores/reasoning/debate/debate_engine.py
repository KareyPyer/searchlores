"""
DebateEngine : orchestrateur du débat interne.

Le DebateEngine met en œuvre le processus dialectique complet :
  1. Pour chaque hypothèse, collecte les arguments via les stratégies
  2. Calcule le score dialectique
  3. Détecte les incompatibilités entre hypothèses
  4. Décide du statut de chaque hypothèse
  5. Produit un Verdict structuré et explicable

Le moteur est configurable :
  - seuils de décision (retain/eliminate)
  - stratégies activées
  - conservation multiple des conclusions
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from searchlores.graph.knowledge_graph import KnowledgeGraph
from searchlores.reasoning.debate.argument import Argument
from searchlores.reasoning.debate.debated_hypothesis import (
    DebatedHypothesis, HypothesisStatus,
)
from searchlores.reasoning.debate.strategies import (
    CompetitorStrategy, DebateStrategy, EvidenceGatheringStrategy,
)
from searchlores.reasoning.debate.verdict import Verdict
from searchlores.reasoning.hypothesis import Hypothesis


@dataclass
class DebateConfig:
    """
    Configuration du débat.
    
    Attributes:
        retain_threshold: score minimum pour RETAINED (défaut 0.3)
        eliminate_threshold: score sous lequel ELIMINATED (défaut -0.2)
        contest_margin: marge autour de 0 pour CONTESTED (défaut 0.2)
        min_arguments_to_retain: nombre minimum d'arguments pour RETAINED
        allow_multiple_conclusions: conserve plusieurs hypothèses si robustes
    """
    retain_threshold: float = 0.3
    eliminate_threshold: float = -0.2
    contest_margin: float = 0.2
    min_arguments_to_retain: int = 2
    allow_multiple_conclusions: bool = True


class DebateEngine:
    """
    Orchestrateur du processus de débat interne.
    
    Usage :
    
        engine = DebateEngine()
        
        # Configure (optionnel)
        engine.configure(DebateConfig(retain_threshold=0.4))
        
        # Ajoute des stratégies personnalisées
        engine.add_strategy(MyCustomStrategy())
        
        # Lance le débat
        verdict = engine.debate(hypotheses, graph)
        
        # Exploite le verdict
        for h in verdict.retained:
            print(f"Retenue : {h.label} (score={h.dialectical_score:.2f})")
        
        for h in verdict.eliminated:
            print(f"Éliminée : {h.label} — {h.verdict_notes}")
    """

    def __init__(self, config: Optional[DebateConfig] = None) -> None:
        self._config = config or DebateConfig()
        self._strategies: List[DebateStrategy] = [
            EvidenceGatheringStrategy(),
            CompetitorStrategy(),
        ]

    def configure(self, config: DebateConfig) -> None:
        """Remplace la configuration du débat."""
        self._config = config

    def add_strategy(self, strategy: DebateStrategy) -> None:
        """Ajoute une stratégie de débat."""
        self._strategies.append(strategy)

    def clear_strategies(self) -> None:
        """Supprime toutes les stratégies."""
        self._strategies.clear()

    def debate(self, hypotheses: List[Hypothesis],
               graph: KnowledgeGraph) -> Verdict:
        """
        Lance le débat sur une liste d'hypothèses.
        
        Pipeline :
          1. Pour chaque hypothèse : collecte des arguments
          2. Calcul du score dialectique
          3. Détection des incompatibilités
          4. Décision du statut
          5. Construction du verdict
        
        Args:
            hypotheses: hypothèses à débattre
            graph: graphe de connaissances
        
        Returns:
            Verdict structuré et explicable
        """
        if not hypotheses:
            verdict = Verdict()
            verdict.summary = "Aucune hypothèse à débattre."
            return verdict

        # 1. Débat de chaque hypothèse
        debated: List[DebatedHypothesis] = []
        for hypothesis in hypotheses:
            debated_h = self._debate_single(hypothesis, graph, hypotheses)
            debated.append(debated_h)

        # 2. Détection des incompatibilités
        self._detect_incompatibilities(debated)

        # 3. Décision des statuts
        for dh in debated:
            dh.decide_status(
                retain_threshold=self._config.retain_threshold,
                eliminate_threshold=self._config.eliminate_threshold,
                contest_margin=self._config.contest_margin,
            )
            dh.verdict_notes = self._build_verdict_note(dh)

        # 4. Construction du verdict
        verdict = Verdict(
            retained=[h for h in debated if h.status == HypothesisStatus.RETAINED],
            contested=[h for h in debated if h.status == HypothesisStatus.CONTESTED],
            weakened=[h for h in debated if h.status == HypothesisStatus.WEAKENED],
            eliminated=[h for h in debated if h.status == HypothesisStatus.ELIMINATED],
        )

        # 5. Résumé et statistiques
        verdict.build_summary()
        verdict.build_statistics()

        return verdict

    # ── Méthodes internes ────────────────────────────────────
    def _debate_single(self, hypothesis: Hypothesis,
                       graph: KnowledgeGraph,
                       all_hypotheses: List[Hypothesis]) -> DebatedHypothesis:
        """Débat d'une hypothèse unique."""
        all_arguments: List[Argument] = []

        for strategy in self._strategies:
            # Compétiteur a besoin de toutes les hypothèses
            if isinstance(strategy, CompetitorStrategy):
                args = strategy.gather_arguments(
                    hypothesis, graph, all_hypotheses
                )
            else:
                args = strategy.gather_arguments(hypothesis, graph)
            all_arguments.extend(args)

        # Construit la DebatedHypothesis
        debated = DebatedHypothesis(
            label=hypothesis.label,
            statement=hypothesis.statement,
            original_confidence=hypothesis.confidence,
            arguments=all_arguments,
            metadata={
                "original_supporting": hypothesis.supporting,
                "original_contradicting": hypothesis.contradicting,
                "original_provenance": hypothesis.provenance,
            },
        )

        # Calcule le score dialectique
        debated.compute_dialectical_score()

        return debated

    def _detect_incompatibilities(
        self, debated: List[DebatedHypothesis]
    ) -> None:
        """
        Détecte les incompatibilités entre hypothèses.
        
        Deux hypothèses sont incompatibles si :
          - elles partagent des nœuds contradictoires
          - l'une supporte ce que l'autre contredit
        """
        for i, h1 in enumerate(debated):
            nodes1 = set(h1.metadata.get("original_supporting", []))
            contra1 = set(h1.metadata.get("original_contradicting", []))

            for j, h2 in enumerate(debated):
                if i >= j:
                    continue

                nodes2 = set(h2.metadata.get("original_supporting", []))
                contra2 = set(h2.metadata.get("original_contradicting", []))

                # Incompatibilité si h1 supporte ce que h2 contredit
                if nodes1 & contra2 or nodes2 & contra1:
                    if h2.label not in h1.competitors:
                        h1.competitors.append(h2.label)
                    if h1.label not in h2.competitors:
                        h2.competitors.append(h1.label)

    def _build_verdict_note(self, dh: DebatedHypothesis) -> str:
        """Construit la note de verdict en langage naturel."""
        parts: List[str] = []

        if dh.status == HypothesisStatus.RETAINED:
            parts.append(
                f"Hypothèse retenue (score dialectique "
                f"{dh.dialectical_score:+.2f})."
            )
            parts.append(
                f"Étayée par {len(dh.supportive_arguments)} argument(s) "
                f"en faveur, contre {len(dh.hostile_arguments)} attaque(s)."
            )
        elif dh.status == HypothesisStatus.CONTESTED:
            parts.append(
                f"Débat ouvert (score {dh.dialectical_score:+.2f})."
            )
            parts.append(
                f"{len(dh.supportive_arguments)} support(s) et "
                f"{len(dh.hostile_arguments)} attaque(s) : "
                f"la balance est incertaine."
            )
        elif dh.status == HypothesisStatus.WEAKENED:
            parts.append(
                f"Hypothèse affaiblie (score {dh.dialectical_score:+.2f})."
            )
            parts.append(
                f"Les attaques ({len(dh.hostile_arguments)}) l'emportent "
                f"sur les supports ({len(dh.supportive_arguments)}), "
                f"mais sans atteindre le seuil d'élimination."
            )
        elif dh.status == HypothesisStatus.ELIMINATED:
            parts.append(
                f"Hypothèse éliminée (score {dh.dialectical_score:+.2f})."
            )
            if dh.hostile_arguments:
                top_attack = max(dh.hostile_arguments, key=lambda a: a.weight)
                parts.append(
                    f"Principale attaque : {top_attack.justification}"
                )
            else:
                parts.append("Preuves insuffisantes.")

        if dh.competitors:
            parts.append(
                f"En concurrence avec : {', '.join(dh.competitors)}."
            )

        return " ".join(parts)