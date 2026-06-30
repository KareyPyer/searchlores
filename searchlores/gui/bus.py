"""
InvestigationBus : bus de communication central entre widgets.

Tous les widgets communiquent via ce bus (pattern publish/subscribe
implémenté avec les signaux Qt). Cela évite les dépendances directes
entre widgets et garantit la modularité.

Événements émis :
  - investigation_started : début d'une investigation
  - graph_updated : le Knowledge Graph a été mis à jour
  - hypotheses_updated : nouvelles hypothèses inférées
  - verdict_updated : nouveau verdict du débat
  - synthesis_updated : nouvelle synthèse produite
  - comparison_updated : nouvelle comparaison multi-Lore
  - node_selected : un nœud du graphe a été sélectionné
  - hypothesis_selected : une hypothèse a été sélectionnée
"""
from __future__ import annotations

from typing import Any, List, Optional

from PySide6.QtCore import QObject, Signal

from searchlores.graph.knowledge_graph import KnowledgeGraph
from searchlores.reasoning.hypothesis import Hypothesis
from searchlores.reasoning.debate import Verdict
from searchlores.synthesis import Synthesis
from searchlores.lore import LoreComparison


class InvestigationBus(QObject):
    """
    Bus central de communication entre les widgets.
    
    Usage :
    
        bus = InvestigationBus()
        
        # Un widget s'abonne
        bus.node_selected.connect(my_handler)
        
        # Un autre widget émet
        bus.node_selected.emit("node_id_123")
    """

    # ── Événements d'investigation ───────────────────────────
    investigation_started = Signal(str)                    # prompt
    investigation_completed = Signal()
    
    # ── Événements de données ────────────────────────────────
    graph_updated = Signal(object)                         # KnowledgeGraph
    hypotheses_updated = Signal(list)                      # List[Hypothesis]
    verdict_updated = Signal(object)                       # Verdict
    synthesis_updated = Signal(object)                     # Synthesis
    comparison_updated = Signal(object)                    # LoreComparison
    
    # ── Événements de sélection ──────────────────────────────
    node_selected = Signal(str)                            # node_id
    hypothesis_selected = Signal(str)                      # hypothesis_label
    lore_selected = Signal(str)                            # lore_name
    
    # ── Événements de navigation ─────────────────────────────
    request_explanation = Signal(str, str)                 # (kind, id)
    request_trace = Signal(str)                            # hypothesis_label

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._current_graph: Optional[KnowledgeGraph] = None
        self._current_hypotheses: List[Hypothesis] = []
        self._current_verdict: Optional[Verdict] = None
        self._current_synthesis: Optional[Synthesis] = None
        self._current_comparison: Optional[LoreComparison] = None

    # ── Accès à l'état courant ───────────────────────────────
    @property
    def current_graph(self) -> Optional[KnowledgeGraph]:
        return self._current_graph

    @property
    def current_hypotheses(self) -> List[Hypothesis]:
        return self._current_hypotheses

    @property
    def current_verdict(self) -> Optional[Verdict]:
        return self._current_verdict

    @property
    def current_synthesis(self) -> Optional[Synthesis]:
        return self._current_synthesis

    @property
    def current_comparison(self) -> Optional[LoreComparison]:
        return self._current_comparison

    # ── Publication ──────────────────────────────────────────
    def publish_graph(self, graph: KnowledgeGraph) -> None:
        self._current_graph = graph
        self.graph_updated.emit(graph)

    def publish_hypotheses(self, hypotheses: List[Hypothesis]) -> None:
        self._current_hypotheses = list(hypotheses)
        self.hypotheses_updated.emit(hypotheses)

    def publish_verdict(self, verdict: Verdict) -> None:
        self._current_verdict = verdict
        self.verdict_updated.emit(verdict)

    def publish_synthesis(self, synthesis: Synthesis) -> None:
        self._current_synthesis = synthesis
        self.synthesis_updated.emit(synthesis)

    def publish_comparison(self, comparison: LoreComparison) -> None:
        self._current_comparison = comparison
        self.comparison_updated.emit(comparison)

    def publish_full_results(self, graph: KnowledgeGraph,
                             hypotheses: List[Hypothesis],
                             verdict: Optional[Verdict] = None,
                             synthesis: Optional[Synthesis] = None,
                             comparison: Optional[LoreComparison] = None) -> None:
        """Publie tous les résultats d'une investigation en une fois."""
        self.publish_graph(graph)
        self.publish_hypotheses(hypotheses)
        if verdict is not None:
            self.publish_verdict(verdict)
        if synthesis is not None:
            self.publish_synthesis(synthesis)
        if comparison is not None:
            self.publish_comparison(comparison)
        self.investigation_completed.emit()