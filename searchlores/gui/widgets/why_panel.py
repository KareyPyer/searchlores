"""
WhyPanel : panneau d'explication des conclusions.

Affiche la traçabilité complète d'un nœud ou d'une hypothèse :
  - Pour un nœud : quels plugins, quelles preuves, quels supports
  - Pour une hypothèse : arguments pour/contre, score dialectique

Répond aux questions :
  - Pourquoi cette conclusion ?
  - Quels plugins ?
  - Quelles observations ?
  - Quel niveau de confiance ?
  - Existe-t-il une hypothèse concurrente ?
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea, QTabWidget,
    QTextBrowser, QVBoxLayout, QWidget,
)

from searchlores.graph.knowledge_graph import KnowledgeGraph
from searchlores.gui.bus import InvestigationBus
from searchlores.gui.widgets.base import InvestigationWidget
from searchlores.reasoning.debate import DebatedHypothesis, Verdict


class WhyPanel(InvestigationWidget):
    """
    Panneau d'explication des conclusions.
    """

    TITLE = "Pourquoi cette conclusion ?"
    ICON_NAME = "help-about"

    def __init__(self, bus: InvestigationBus,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(bus, parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._header = QLabel("Sélectionnez un nœud ou une hypothèse")
        self._header.setStyleSheet("font-weight: bold; padding: 4px;")
        layout.addWidget(self._header)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        # Onglet "Nœud"
        self._node_view = QTextBrowser()
        self._node_view.setOpenExternalLinks(False)
        self._tabs.addTab(self._node_view, "Nœud")

        # Onglet "Hypothèse"
        self._hypothesis_view = QTextBrowser()
        self._tabs.addTab(self._hypothesis_view, "Hypothèse")

        # Onglet "Arguments"
        self._arguments_view = QTextBrowser()
        self._tabs.addTab(self._arguments_view, "Arguments du débat")

        self._clear_all()

    # ── Cycle de vie ─────────────────────────────────────────
    def on_registered(self) -> None:
        self._bus.node_selected.connect(self._on_node_selected)
        self._bus.hypothesis_selected.connect(self._on_hypothesis_selected)
        self._bus.verdict_updated.connect(self._on_verdict_updated)

    def on_unregistered(self) -> None:
        try:
            self._bus.node_selected.disconnect(self._on_node_selected)
            self._bus.hypothesis_selected.disconnect(self._on_hypothesis_selected)
            self._bus.verdict_updated.disconnect(self._on_verdict_updated)
        except RuntimeError:
            pass

    # ── Handlers ─────────────────────────────────────────────
    def _on_node_selected(self, node_id: str) -> None:
        graph = self._bus.current_graph
        if not graph:
            return
        node = graph.get_node(node_id)
        if not node:
            return
        
        self._tabs.setCurrentIndex(0)
        self._render_node_explanation(graph, node_id)

    def _on_hypothesis_selected(self, label: str) -> None:
        verdict = self._bus.current_verdict
        if not verdict:
            return
        
        for dh in verdict.all_debated:
            if dh.label == label:
                self._tabs.setCurrentIndex(1)
                self._render_hypothesis_explanation(dh)
                self._render_arguments(dh)
                return

    def _on_verdict_updated(self, verdict: Verdict) -> None:
        # Pré-remplit l'onglet hypothèse si une hypothèse est sélectionnée
        pass

    # ── Rendu ────────────────────────────────────────────────
    def _render_node_explanation(self, graph: KnowledgeGraph,
                                 node_id: str) -> None:
        try:
            explanation = graph.explain_node(node_id)
        except KeyError:
            self._node_view.setHtml("<i>Nœud introuvable.</i>")
            return
        
        node = explanation["node"]
        
        html = [
            f"<h3>{_escape(node['label'])}</h3>",
            f"<p><b>Type :</b> {_escape(node['type'])}</p>",
            f"<p><b>Confiance :</b> {node['confidence']:.2f}</p>",
            "<hr>",
            "<h4>Plugins impliqués</h4>",
            "<ul>",
        ]
        for plugin in explanation["plugins_involved"]:
            html.append(f"<li>{_escape(plugin)}</li>")
        html.append("</ul>")

        if explanation["supports"]:
            html.append("<h4>Supports</h4><ul>")
            for s in explanation["supports"]:
                html.append(
                    f"<li>{_escape(s.get('source', '?'))} → "
                    f"{_escape(s.get('target', '?'))} "
                    f"(confiance={s['confidence']:.2f})</li>"
                )
            html.append("</ul>")

        if explanation["contradicts"]:
            html.append("<h4 style='color:#D0021B'>Contradictions</h4><ul>")
            for c in explanation["contradicts"]:
                html.append(
                    f"<li>{_escape(c.get('source', '?'))} ↔ "
                    f"{_escape(c.get('target', '?'))} "
                    f"(confiance={c['confidence']:.2f})</li>"
                )
            html.append("</ul>")

        if node["evidences"]:
            html.append("<h4>Preuves</h4><ul>")
            for ev in node["evidences"][:10]:
                html.append(
                    f"<li>« {_escape(ev['text'][:80])} » "
                    f"<i>(source : {_escape(ev['source_plugin'])})</i></li>"
                )
            html.append("</ul>")

        self._node_view.setHtml("".join(html))
        self._header.setText(f"Nœud : {node['label']}")

    def _render_hypothesis_explanation(self, dh: DebatedHypothesis) -> None:
        status_colors = {
            "retained": "#4CAF50",
            "contested": "#FF9800",
            "weakened": "#FFC107",
            "eliminated": "#F44336",
        }
        color = status_colors.get(dh.status.value, "#888")
        
        html = [
            f"<h3>{_escape(dh.label)}</h3>",
            f"<p><i>{_escape(dh.statement)}</i></p>",
            "<hr>",
            f"<p><b>Statut :</b> <span style='color:{color}'>"
            f"<b>{dh.status.value.upper()}</b></span></p>",
            f"<p><b>Score dialectique :</b> {dh.dialectical_score:+.2f}</p>",
            f"<p><b>Confiance originale :</b> {dh.original_confidence:.2f}</p>",
            f"<p><b>Supports :</b> {len(dh.supportive_arguments)} "
            f"(poids total = {dh.support_weight:.2f})</p>",
            f"<p><b>Attaques :</b> {len(dh.hostile_arguments)} "
            f"(poids total = {dh.hostility_weight:.2f})</p>",
        ]

        if dh.competitors:
            html.append("<h4>Hypothèses concurrentes</h4><ul>")
            for c in dh.competitors:
                html.append(f"<li>{_escape(c)}</li>")
            html.append("</ul>")

        if dh.verdict_notes:
            html.append(f"<h4>Verdict</h4><p>{_escape(dh.verdict_notes)}</p>")

        self._hypothesis_view.setHtml("".join(html))
        self._header.setText(f"Hypothèse : {dh.label}")

    def _render_arguments(self, dh: DebatedHypothesis) -> None:
        if not dh.arguments:
            self._arguments_view.setHtml(
                "<i>Aucun argument collecté pour cette hypothèse.</i>"
            )
            return
        
        html = ["<h4>Arguments du débat</h4>"]
        
        # Groupe par polarité
        for polarity_name, args in [
            ("En faveur", dh.supportive_arguments),
            ("Contre", dh.hostile_arguments),
        ]:
            if not args:
                continue
            color = "#4CAF50" if polarity_name == "En faveur" else "#F44336"
            html.append(f"<h4 style='color:{color}'>{polarity_name}</h4><ul>")
            for arg in sorted(args, key=lambda a: a.weight, reverse=True):
                html.append(
                    f"<li><b>[{arg.kind.value}]</b> "
                    f"(poids={arg.weight:.2f})<br>"
                    f"<i>{_escape(arg.justification)}</i></li>"
                )
            html.append("</ul>")
        
        self._arguments_view.setHtml("".join(html))

    def _clear_all(self) -> None:
        placeholder = "<i>Aucune sélection.</i>"
        self._node_view.setHtml(placeholder)
        self._hypothesis_view.setHtml(placeholder)
        self._arguments_view.setHtml(placeholder)


def _escape(text: str) -> str:
    """Échappe les caractères HTML."""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))