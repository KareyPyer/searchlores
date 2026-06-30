"""
HeatmapView : heatmap de couverture des analyses.

Affiche une matrice (plugin × type de nœud) montrant quels
plugins ont contribué à quels types de concepts. Permet de
visualiser rapidement les angles morts de l'analyse.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, Optional, Set, Tuple

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QBrush, QPen
from PySide6.QtWidgets import (
    QGraphicsRectItem, QGraphicsScene, QGraphicsSimpleTextItem,
    QGraphicsView, QLabel, QVBoxLayout, QWidget,
)

from searchlores.graph.knowledge_graph import KnowledgeGraph, NodeType
from searchlores.gui.bus import InvestigationBus
from searchlores.gui.widgets.base import InvestigationWidget


CELL_SIZE = 40.0
LABEL_WIDTH = 120.0


class HeatmapView(InvestigationWidget):
    """
    Heatmap de couverture des analyses.
    """

    TITLE = "Heatmap de couverture"
    ICON_NAME = "view-statistics"

    def __init__(self, bus: InvestigationBus,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(bus, parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._header = QLabel("Couverture plugin × type de nœud")
        layout.addWidget(self._header)

        self._scene = QGraphicsScene(self)
        self._view = QGraphicsView(self._scene, self)
        self._view.setRenderHint(self._view.renderHints())
        layout.addWidget(self._view)

        self._legend = QLabel()
        layout.addWidget(self._legend)

    # ── Cycle de vie ─────────────────────────────────────────
    def on_registered(self) -> None:
        self._bus.graph_updated.connect(self._on_graph_updated)

    def on_unregistered(self) -> None:
        try:
            self._bus.graph_updated.disconnect(self._on_graph_updated)
        except RuntimeError:
            pass

    # ── Handlers ─────────────────────────────────────────────
    def _on_graph_updated(self, graph: KnowledgeGraph) -> None:
        self._render(graph)

    # ── Rendu ────────────────────────────────────────────────
    def _render(self, graph: KnowledgeGraph) -> None:
        self._scene.clear()

        if len(graph) == 0:
            self._legend.setText("Graphe vide")
            return

        # Construit la matrice : plugin × type de nœud
        matrix: Dict[Tuple[str, NodeType], int] = defaultdict(int)
        plugins: Set[str] = set()
        node_types: Set[NodeType] = set()

        for node in graph.find_nodes():
            if node.node_type == NodeType.OBSERVATION:
                continue
            node_types.add(node.node_type)
            for evidence in node.evidences:
                plugins.add(evidence.source_plugin)
                matrix[(evidence.source_plugin, node.node_type)] += 1

        if not plugins or not node_types:
            self._legend.setText("Aucune donnée de couverture")
            return

        plugins_list = sorted(plugins)
        types_list = sorted(node_types, key=lambda t: t.value)

        # Trouve le max pour normaliser les couleurs
        max_count = max(matrix.values()) if matrix else 1

        # Dessine les labels de colonnes (types de nœuds)
        for j, nt in enumerate(types_list):
            x = LABEL_WIDTH + j * CELL_SIZE
            text_item = QGraphicsSimpleTextItem(nt.value)
            text_item.setPos(x + 4, 4)
            self._scene.addItem(text_item)

        # Dessine les cellules
        for i, plugin in enumerate(plugins_list):
            y = 30 + i * CELL_SIZE
            
            # Label de ligne
            label = QGraphicsSimpleTextItem(plugin[:18])
            label.setPos(4, y + 12)
            self._scene.addItem(label)

            for j, nt in enumerate(types_list):
                x = LABEL_WIDTH + j * CELL_SIZE
                count = matrix.get((plugin, nt), 0)
                
                # Couleur : gradient rouge → jaune → vert
                if count == 0:
                    color = QColor("#EEEEEE")
                else:
                    ratio = count / max_count
                    color = QColor(
                        int(255 * (1 - ratio)),
                        int(200 * ratio + 55),
                        int(100 * ratio),
                    )
                
                rect = QGraphicsRectItem(
                    QRectF(x, y, CELL_SIZE - 2, CELL_SIZE - 2)
                )
                rect.setBrush(QBrush(color))
                rect.setPen(QPen(QColor("#CCC"), 0.5))
                rect.setToolTip(
                    f"{plugin} × {nt.value} : {count} occurrence(s)"
                )
                self._scene.addItem(rect)

                if count > 0:
                    count_text = QGraphicsSimpleTextItem(str(count))
                    count_text.setPos(x + CELL_SIZE / 2 - 6, y + CELL_SIZE / 2 - 8)
                    self._scene.addItem(count_text)

        # Ajuste la vue
        self._view.setSceneRect(self._scene.itemsBoundingRect())
        self._view.fitInView(self._scene.sceneRect(),
                             Qt.AspectRatioMode.KeepAspectRatio)

        self._legend.setText(
            f"{len(plugins)} plugin(s) × {len(node_types)} type(s) | "
            f"Max : {max_count}"
        )