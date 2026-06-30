"""
KnowledgeGraphView : explorateur interactif du Knowledge Graph.

Utilise QGraphicsScene/View pour afficher les nœuds et relations.
Le layout est calculé via networkx (spring_layout).

Fonctionnalités :
  - Affichage des nœuds avec couleurs selon le type
  - Affichage des relations avec flèches
  - Sélection de nœuds (émet node_selected sur le bus)
  - Zoom / pan
  - Filtrage par type de nœud
  - Mise en évidence des convergences/contradictions
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import networkx as nx
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QBrush, QColor, QPen, QPolygonF
from PySide6.QtWidgets import (
    QGraphicsEllipseItem, QGraphicsItem, QGraphicsLineItem,
    QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsView,
    QHBoxLayout, QComboBox, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from searchlores.graph.knowledge_graph import (
    KnowledgeGraph, Node, NodeType, Relation, RelationType,
)
from searchlores.gui.bus import InvestigationBus
from searchlores.gui.widgets.base import InvestigationWidget


# ── Palette de couleurs par type de nœud ─────────────────────
NODE_COLORS: Dict[NodeType, QColor] = {
    NodeType.CONCEPT: QColor("#4A90E2"),
    NodeType.ACTOR: QColor("#7ED321"),
    NodeType.INSTITUTION: QColor("#F5A623"),
    NodeType.AUTHOR: QColor("#BD10E0"),
    NodeType.SOURCE: QColor("#9013FE"),
    NodeType.ARGUMENT: QColor("#D0021B"),
    NodeType.HYPOTHESIS: QColor("#50E3C2"),
    NodeType.EVENT: QColor("#F8E71C"),
    NodeType.OBSERVATION: QColor("#9B9B9B"),
}

# ── Palette de couleurs par type de relation ─────────────────
RELATION_COLORS: Dict[RelationType, QColor] = {
    RelationType.SUPPORTS: QColor("#4CAF50"),
    RelationType.IMPLIES: QColor("#2196F3"),
    RelationType.CONTRADICTS: QColor("#F44336"),
    RelationType.DEPENDS_ON: QColor("#FF9800"),
    RelationType.CAUSES: QColor("#9C27B0"),
    RelationType.CITES: QColor("#607D8B"),
    RelationType.INFLUENCES: QColor("#00BCD4"),
    RelationType.REINFORCES: QColor("#8BC34A"),
    RelationType.OBSERVED_BY: QColor("#9E9E9E"),
}

NODE_RADIUS = 18.0


class _NodeItem(QGraphicsEllipseItem):
    """Item graphique représentant un nœud du graphe."""

    def __init__(self, node: Node, x: float, y: float) -> None:
        super().__init__(
            -NODE_RADIUS, -NODE_RADIUS,
            NODE_RADIUS * 2, NODE_RADIUS * 2,
        )
        self.node = node
        self.setPos(QPointF(x, y))
        self.setBrush(QBrush(NODE_COLORS.get(node.node_type, QColor("#888"))))
        self.setPen(QPen(QColor("#333"), 1.5))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setTooltip(self._build_tooltip())

        # Label
        self._label = QGraphicsSimpleTextItem(node.label[:20], self)
        label_rect = self._label.boundingRect()
        self._label.setPos(-label_rect.width() / 2, NODE_RADIUS + 4)

    def _build_tooltip(self) -> str:
        lines = [
            f"Type : {self.node.node_type.value}",
            f"Label : {self.node.label}",
            f"Confiance : {self.node.confidence:.2f}",
            f"Preuves : {len(self.node.evidences)}",
        ]
        if self.node.evidences:
            lines.append("\nPreuves :")
            for ev in self.node.evidences[:3]:
                lines.append(f"  • {ev.text[:60]} ({ev.source_plugin})")
        return "\n".join(lines)


class _RelationItem(QGraphicsLineItem):
    """Item graphique représentant une relation."""

    def __init__(self, relation: Relation,
                 source_item: _NodeItem, target_item: _NodeItem) -> None:
        super().__init__()
        self.relation = relation
        self._source_item = source_item
        self._target_item = target_item
        self._update_geometry()

        color = RELATION_COLORS.get(relation.relation_type, QColor("#888"))
        pen_width = 1.0 + relation.confidence * 2.0
        pen = QPen(color, pen_width)
        if relation.relation_type == RelationType.CONTRADICTS:
            pen.setStyle(Qt.PenStyle.DashLine)
        self.setPen(pen)
        self.setTooltip(self._build_tooltip())

    def _update_geometry(self) -> None:
        s = self._source_item.pos()
        t = self._target_item.pos()
        self.setLine(s.x(), s.y(), t.x(), t.y())

    def _build_tooltip(self) -> str:
        return (
            f"Type : {self.relation.relation_type.value}\n"
            f"Confiance : {self.relation.confidence:.2f}\n"
            f"Preuves : {len(self.relation.evidences)}"
        )


class KnowledgeGraphView(InvestigationWidget):
    """
    Explorateur interactif du Knowledge Graph.
    """

    TITLE = "Knowledge Graph"
    ICON_NAME = "view-grid"

    def __init__(self, bus: InvestigationBus,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(bus, parent)
        self._node_items: Dict[str, _NodeItem] = {}
        self._relation_items: List[_RelationItem] = []
        self._current_graph: Optional[KnowledgeGraph] = None
        self._type_filter: Optional[NodeType] = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Barre d'outils
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Filtre :"))
        
        self._type_combo = QComboBox()
        self._type_combo.addItem("Tous les types", None)
        for nt in NodeType:
            self._type_combo.addItem(nt.value, nt)
        self._type_combo.currentIndexChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self._type_combo)

        self._highlight_btn = QPushButton("Convergences")
        self._highlight_btn.setCheckable(True)
        self._highlight_btn.clicked.connect(self._on_highlight_toggled)
        toolbar.addWidget(self._highlight_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Scene + View
        self._scene = QGraphicsScene(self)
        self._view = QGraphicsView(self._scene, self)
        self._view.setRenderHint(self._view.renderHints())
        self._view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self._view.setSelectionMode(
            QGraphicsView.SelectionMode.RubberBandSelection
        )
        layout.addWidget(self._view)

        # Status bar
        self._status_label = QLabel("Aucun graphe chargé")
        layout.addWidget(self._status_label)

    # ── Cycle de vie ─────────────────────────────────────────
    def on_registered(self) -> None:
        self._bus.graph_updated.connect(self._on_graph_updated)
        self._bus.node_selected.connect(self._on_external_node_selected)
        self._scene.selectionChanged.connect(self._on_selection_changed)

    def on_unregistered(self) -> None:
        try:
            self._bus.graph_updated.disconnect(self._on_graph_updated)
            self._bus.node_selected.disconnect(self._on_external_node_selected)
            self._scene.selectionChanged.disconnect(self._on_selection_changed)
        except RuntimeError:
            pass

    # ── Handlers ─────────────────────────────────────────────
    def _on_graph_updated(self, graph: KnowledgeGraph) -> None:
        self._current_graph = graph
        self._render_graph()

    def _on_filter_changed(self, index: int) -> None:
        self._type_filter = self._type_combo.itemData(index)
        self._apply_filter()

    def _on_highlight_toggled(self, checked: bool) -> None:
        if not self._current_graph:
            return
        self._apply_highlight(checked)

    def _on_selection_changed(self) -> None:
        selected = self._scene.selectedItems()
        for item in selected:
            if isinstance(item, _NodeItem):
                self._bus.node_selected.emit(item.node.id)
                return

    def _on_external_node_selected(self, node_id: str) -> None:
        item = self._node_items.get(node_id)
        if item:
            self._scene.clearSelection()
            item.setSelected(True)
            self._view.centerOn(item)

    # ── Rendu ────────────────────────────────────────────────
    def _render_graph(self) -> None:
        self._scene.clear()
        self._node_items.clear()
        self._relation_items.clear()

        if not self._current_graph or len(self._current_graph) == 0:
            self._status_label.setText("Graphe vide")
            return

        # Layout via networkx
        nx_graph = self._current_graph.to_networkx()
        if len(nx_graph) == 0:
            return
        
        try:
            positions = nx.spring_layout(nx_graph, k=2.0, iterations=50)
        except Exception:
            positions = {n: (0, 0) for n in nx_graph.nodes}

        scale = 200.0

        # Crée les items de nœuds
        for node_id, pos in positions.items():
            node = self._current_graph.get_node(node_id)
            if not node:
                continue
            x, y = pos[0] * scale, pos[1] * scale
            item = _NodeItem(node, x, y)
            self._scene.addItem(item)
            self._node_items[node_id] = item

        # Crée les items de relations
        for u, v, data in nx_graph.edges(data=True):
            rel: Relation = data.get("relation")
            if not rel:
                continue
            source_item = self._node_items.get(u)
            target_item = self._node_items.get(v)
            if not (source_item and target_item):
                continue
            rel_item = _RelationItem(rel, source_item, target_item)
            self._scene.addItem(rel_item)
            self._relation_items.append(rel_item)

        # Ajuste la vue
        self._view.setSceneRect(self._scene.itemsBoundingRect().adjusted(
            -50, -50, 50, 50
        ))
        self._view.fitInView(self._scene.sceneRect(),
                             Qt.AspectRatioMode.KeepAspectRatio)

        # Mise à jour du statut
        n_nodes = len(self._node_items)
        n_edges = len(self._relation_items)
        self._status_label.setText(
            f"{n_nodes} nœud(s), {n_edges} relation(s)"
        )

    def _apply_filter(self) -> None:
        for node_id, item in self._node_items.items():
            if self._type_filter is None:
                item.setVisible(True)
            else:
                item.setVisible(item.node.node_type == self._type_filter)
        
        for rel_item in self._relation_items:
            s_visible = self._node_items.get(rel_item.relation.source_id)
            t_visible = self._node_items.get(rel_item.relation.target_id)
            rel_item.setVisible(
                bool(s_visible and s_visible.isVisible()
                     and t_visible and t_visible.isVisible())
            )

    def _apply_highlight(self, highlight: bool) -> None:
        if not self._current_graph:
            return
        
        if not highlight:
            # Réinitialise les couleurs
            for item in self._node_items.values():
                item.setPen(QPen(QColor("#333"), 1.5))
            return
        
        # Met en évidence les convergences
        convergences = self._current_graph.find_convergences()
        convergence_ids = {n.id for n in convergences}
        
        for node_id, item in self._node_items.items():
            if node_id in convergence_ids:
                item.setPen(QPen(QColor("#FFD700"), 3.0))
            else:
                item.setPen(QPen(QColor("#333"), 1.5))