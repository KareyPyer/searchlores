"""
TracePanel : timeline du raisonnement.

Affiche les étapes successives du pipeline d'investigation :
  Observers → Fusion → Inference → Debate → Synthesis

Chaque étape indique :
  - le temps d'exécution
  - les éléments produits (nombre d'observations, nœuds, etc.)
  - les plugins impliqués
"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QLabel, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from searchlores.gui.bus import InvestigationBus
from searchlores.gui.widgets.base import InvestigationWidget
from searchlores.reasoning.debate import Verdict
from searchlores.reasoning.fusion_engine import IngestionReport


class TracePanel(InvestigationWidget):
    """
    Timeline du raisonnement.
    """

    TITLE = "Trace du raisonnement"
    ICON_NAME = "view-history"

    def __init__(self, bus: InvestigationBus,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(bus, parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._header = QLabel("Pipeline d'investigation")
        self._header.setFont(QFont(self._header.font().family(),
                                   weight=QFont.Weight.Bold))
        layout.addWidget(self._header)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Étape", "Détails"])
        self._tree.setColumnWidth(0, 180)
        layout.addWidget(self._tree)

    # ── Cycle de vie ─────────────────────────────────────────
    def on_registered(self) -> None:
        self._bus.investigation_completed.connect(self._on_completed)
        self._bus.graph_updated.connect(self._on_graph_updated)
        self._bus.verdict_updated.connect(self._on_verdict_updated)

    def on_unregistered(self) -> None:
        try:
            self._bus.investigation_completed.disconnect(self._on_completed)
            self._bus.graph_updated.disconnect(self._on_graph_updated)
            self._bus.verdict_updated.disconnect(self._on_verdict_updated)
        except RuntimeError:
            pass

    # ── Handlers ─────────────────────────────────────────────
    def _on_completed(self) -> None:
        self._rebuild_trace()

    def _on_graph_updated(self, graph) -> None:
        pass  # Sera rafraîchi à investigation_completed

    def _on_verdict_updated(self, verdict: Verdict) -> None:
        pass

    # ── Rendu ────────────────────────────────────────────────
    def _rebuild_trace(self) -> None:
        self._tree.clear()
        
        # Étape 1 : Observers
        observers_item = QTreeWidgetItem([
            "1. Observers",
            f"{len(self._bus._current_hypotheses) if self._bus._current_hypotheses else 0} "
            f"hypothèses produites au total",
        ])
        self._tree.addTopLevelItem(observers_item)
        observers_item.setExpanded(True)

        # Étape 2 : Fusion
        graph = self._bus.current_graph
        if graph:
            fusion_item = QTreeWidgetItem([
                "2. Fusion dans le graphe",
                f"{len(graph)} nœud(s), {len(graph.get_relations())} relation(s)",
            ])
            self._tree.addTopLevelItem(fusion_item)
            
            # Détail par type de nœud
            from searchlores.graph.knowledge_graph import NodeType
            for nt in NodeType:
                nodes = graph.find_nodes(node_type=nt)
                if nodes:
                    child = QTreeWidgetItem([
                        f"  {nt.value}",
                        f"{len(nodes)} nœud(s)",
                    ])
                    fusion_item.addChild(child)

        # Étape 3 : Inference
        hypotheses = self._bus.current_hypotheses
        if hypotheses:
            inference_item = QTreeWidgetItem([
                "3. Inférence d'hypothèses",
                f"{len(hypotheses)} hypothèse(s)",
            ])
            self._tree.addTopLevelItem(inference_item)
            for h in hypotheses[:10]:
                child = QTreeWidgetItem([
                    f"  {h.label}",
                    f"confiance={h.confidence:.2f}",
                ])
                inference_item.addChild(child)

        # Étape 4 : Debate
        verdict = self._bus.current_verdict
        if verdict:
            debate_item = QTreeWidgetItem([
                "4. Débat interne",
                f"{len(verdict.retained)} retenue(s), "
                f"{len(verdict.contested)} contestée(s), "
                f"{len(verdict.eliminated)} éliminée(s)",
            ])
            self._tree.addTopLevelItem(debate_item)
            
            for status_name, group in [
                ("Retenues", verdict.retained),
                ("Contestées", verdict.contested),
                ("Affaiblies", verdict.weakened),
                ("Éliminées", verdict.eliminated),
            ]:
                if group:
                    child = QTreeWidgetItem([
                        f"  {status_name}",
                        f"{len(group)} hypothèse(s)",
                    ])
                    debate_item.addChild(child)

        # Étape 5 : Synthesis
        synthesis = self._bus.current_synthesis
        if synthesis:
            synth_item = QTreeWidgetItem([
                "5. Synthèse",
                f"confiance globale={synthesis.global_confidence:.2f}",
            ])
            self._tree.addTopLevelItem(synth_item)
            
            if synthesis.dominant_concepts:
                child = QTreeWidgetItem([
                    "  Concepts dominants",
                    ", ".join(c["label"] for c in synthesis.dominant_concepts[:3]),
                ])
                synth_item.addChild(child)
            
            if synthesis.detected_omissions:
                child = QTreeWidgetItem([
                    "  Omissions détectées",
                    ", ".join(synthesis.detected_omissions[:3]),
                ])
                synth_item.addChild(child)

        # Étape 6 : Multi-Lore (optionnel)
        comparison = self._bus.current_comparison
        if comparison:
            lore_item = QTreeWidgetItem([
                "6. Comparaison multi-Lore",
                f"{len(comparison.results)} cadre(s) comparé(s)",
            ])
            self._tree.addTopLevelItem(lore_item)
            
            child = QTreeWidgetItem([
                "  Hypothèses communes",
                f"{len(comparison.common_hypotheses)}",
            ])
            lore_item.addChild(child)
            child = QTreeWidgetItem([
                "  Hypothèses divergentes",
                f"{len(comparison.divergent_hypotheses)}",
            ])
            lore_item.addChild(child)