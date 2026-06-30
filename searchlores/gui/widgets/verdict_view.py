"""
VerdictView : affichage du verdict du débat interne.

Affiche :
  - Le résumé du verdict
  - Les hypothèses retenues / contestées / affaiblies / éliminées
  - Les statistiques globales
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QLabel, QTextBrowser, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

from searchlores.gui.bus import InvestigationBus
from searchlores.gui.widgets.base import InvestigationWidget
from searchlores.reasoning.debate import DebatedHypothesis, Verdict


STATUS_COLORS = {
    "retained": "#4CAF50",
    "contested": "#FF9800",
    "weakened": "#FFC107",
    "eliminated": "#F44336",
}


class VerdictView(InvestigationWidget):
    """
    Affichage du verdict du débat.
    """

    TITLE = "Verdict du débat"
    ICON_NAME = "dialog-ok"

    def __init__(self, bus: InvestigationBus,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(bus, parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._summary = QTextBrowser()
        self._summary.setMaximumHeight(120)
        layout.addWidget(self._summary)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Hypothèse", "Score", "Statut"])
        self._tree.setColumnWidth(0, 300)
        self._tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._tree)

        self._stats_label = QLabel()
        layout.addWidget(self._stats_label)

    # ── Cycle de vie ─────────────────────────────────────────
    def on_registered(self) -> None:
        self._bus.verdict_updated.connect(self._on_verdict_updated)

    def on_unregistered(self) -> None:
        try:
            self._bus.verdict_updated.disconnect(self._on_verdict_updated)
        except RuntimeError:
            pass

    # ── Handlers ─────────────────────────────────────────────
    def _on_verdict_updated(self, verdict: Verdict) -> None:
        self._render(verdict)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        label = item.data(0, Qt.ItemDataRole.UserRole)
        if label:
            self._bus.hypothesis_selected.emit(label)

    # ── Rendu ────────────────────────────────────────────────
    def _render(self, verdict: Verdict) -> None:
        self._tree.clear()

        # Résumé
        self._summary.setHtml(
            f"<h4>{_escape(verdict.summary)}</h4>"
        )

        # Hypothèses groupées par statut
        groups = [
            ("Retenues", verdict.retained, "#4CAF50"),
            ("Contestées", verdict.contested, "#FF9800"),
            ("Affaiblies", verdict.weakened, "#FFC107"),
            ("Éliminées", verdict.eliminated, "#F44336"),
        ]

        for group_name, group_list, color in groups:
            if not group_list:
                continue
            
            parent_item = QTreeWidgetItem([
                f"{group_name} ({len(group_list)})",
                "",
                group_name.upper(),
            ])
            parent_item.setForeground(2, QColor(color))
            font = parent_item.font(0)
            font.setBold(True)
            parent_item.setFont(0, font)
            self._tree.addTopLevelItem(parent_item)
            parent_item.setExpanded(True)

            for dh in sorted(group_list, key=lambda h: h.dialectical_score,
                             reverse=True):
                child = QTreeWidgetItem([
                    dh.label,
                    f"{dh.dialectical_score:+.2f}",
                    dh.status.value,
                ])
                child.setData(0, Qt.ItemDataRole.UserRole, dh.label)
                child.setForeground(1, QColor(color))
                parent_item.addChild(child)

        # Statistiques
        stats = verdict.statistics
        if stats:
            self._stats_label.setText(
                f"Total : {stats.get('total_hypotheses', 0)} hypothèse(s) | "
                f"Arguments : {stats.get('total_arguments', 0)} | "
                f"Score moyen : {stats.get('avg_dialectical_score', 0):+.2f}"
            )


def _escape(text: str) -> str:
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))