"""
MultiLoreView : comparaison visuelle des Lores.

Affiche :
  - Le résumé comparatif
  - Les hypothèses communes
  - Les hypothèses divergentes
  - Les divergences de confiance
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QLabel, QTabWidget, QTextBrowser, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

from searchlores.gui.bus import InvestigationBus
from searchlores.gui.widgets.base import InvestigationWidget
from searchlores.lore import LoreComparison


class MultiLoreView(InvestigationWidget):
    """
    Comparaison visuelle des Lores.
    """

    TITLE = "Comparaison multi-Lore"
    ICON_NAME = "view-split-left-right"

    def __init__(self, bus: InvestigationBus,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(bus, parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._header = QLabel("Aucune comparaison disponible")
        self._header.setFont(QFont(self._header.font().family(),
                                   weight=QFont.Weight.Bold))
        layout.addWidget(self._header)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self._summary_view = QTextBrowser()
        self._tabs.addTab(self._summary_view, "Résumé")

        self._common_view = QTreeWidget()
        self._common_view.setHeaderLabels([
            "Hypothèse", "Confiance moy.", "Min", "Max",
        ])
        self._tabs.addTab(self._common_view, "Communes")

        self._divergent_view = QTreeWidget()
        self._divergent_view.setHeaderLabels([
            "Hypothèse", "Présente dans", "Confiance",
        ])
        self._tabs.addTab(self._divergent_view, "Divergentes")

        self._divergence_view = QTreeWidget()
        self._divergence_view.setHeaderLabels([
            "Hypothèse", "Écart", "Min", "Max",
        ])
        self._tabs.addTab(self._divergence_view, "Écarts de confiance")

    # ── Cycle de vie ─────────────────────────────────────────
    def on_registered(self) -> None:
        self._bus.comparison_updated.connect(self._on_comparison_updated)

    def on_unregistered(self) -> None:
        try:
            self._bus.comparison_updated.disconnect(self._on_comparison_updated)
        except RuntimeError:
            pass

    # ── Handlers ─────────────────────────────────────────────
    def _on_comparison_updated(self, comparison: LoreComparison) -> None:
        self._render(comparison)

    # ── Rendu ────────────────────────────────────────────────
    def _render(self, comparison: LoreComparison) -> None:
        lore_names = [r.lore.name for r in comparison.results]
        self._header.setText(
            f"Comparaison : {', '.join(lore_names)}"
        )

        # Résumé
        self._summary_view.setHtml(
            f"<p>{_escape(comparison.comparative_summary)}</p>"
        )

        # Hypothèses communes
        self._common_view.clear()
        for h in comparison.common_hypotheses:
            item = QTreeWidgetItem([
                h["label"],
                f"{h['avg_confidence']:.2f}",
                f"{h['min_confidence']:.2f}",
                f"{h['max_confidence']:.2f}",
            ])
            self._common_view.addTopLevelItem(item)

        # Hypothèses divergentes
        self._divergent_view.clear()
        for h in comparison.divergent_hypotheses:
            item = QTreeWidgetItem([
                h["label"],
                ", ".join(h["present_in"]),
                f"{h['confidence']:.2f}",
            ])
            self._divergent_view.addTopLevelItem(item)

        # Divergences de confiance
        self._divergence_view.clear()
        for d in comparison.confidence_divergences:
            item = QTreeWidgetItem([
                d["hypothesis"],
                f"{d['divergence']:.2f}",
                f"{d['min_confidence']:.2f}",
                f"{d['max_confidence']:.2f}",
            ])
            self._divergence_view.addTopLevelItem(item)


def _escape(text: str) -> str:
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))