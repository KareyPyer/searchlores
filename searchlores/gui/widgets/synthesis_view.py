"""
SynthesisView : affichage de la synthèse analytique.

Affiche :
  - Le résumé en langage naturel
  - Les concepts dominants
  - Les axes de pouvoir
  - Les contradictions majeures
  - Les omissions détectées
  - La structure argumentative
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QLabel, QScrollArea, QTabWidget, QTextBrowser,
    QVBoxLayout, QWidget,
)

from searchlores.gui.bus import InvestigationBus
from searchlores.gui.widgets.base import InvestigationWidget
from searchlores.synthesis import Synthesis


class SynthesisView(InvestigationWidget):
    """
    Affichage de la synthèse analytique.
    """

    TITLE = "Synthèse analytique"
    ICON_NAME = "document-edit"

    def __init__(self, bus: InvestigationBus,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(bus, parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._header = QLabel("Aucune synthèse disponible")
        self._header.setFont(QFont(self._header.font().family(),
                                   weight=QFont.Weight.Bold))
        layout.addWidget(self._header)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self._summary_view = QTextBrowser()
        self._tabs.addTab(self._summary_view, "Résumé")

        self._concepts_view = QTextBrowser()
        self._tabs.addTab(self._concepts_view, "Concepts & pouvoir")

        self._tensions_view = QTextBrowser()
        self._tabs.addTab(self._tensions_view, "Tensions & omissions")

        self._structure_view = QTextBrowser()
        self._tabs.addTab(self._structure_view, "Structure")

    # ── Cycle de vie ─────────────────────────────────────────
    def on_registered(self) -> None:
        self._bus.synthesis_updated.connect(self._on_synthesis_updated)

    def on_unregistered(self) -> None:
        try:
            self._bus.synthesis_updated.disconnect(self._on_synthesis_updated)
        except RuntimeError:
            pass

    # ── Handlers ─────────────────────────────────────────────
    def _on_synthesis_updated(self, synthesis: Synthesis) -> None:
        self._render(synthesis)

    # ── Rendu ────────────────────────────────────────────────
    def _render(self, synthesis: Synthesis) -> None:
        self._header.setText(
            f"Synthèse — confiance {synthesis.global_confidence:.2f} "
            f"| cohérence {synthesis.coherence_score:.2f}"
        )

        # Résumé
        summary_html = [
            f"<h3>Résumé analytique</h3>",
            f"<p>{_escape(synthesis.summary)}</p>",
            "<hr>",
            f"<p><b>Concepts analysés :</b> "
            f"{synthesis.metadata.get('node_count', 0)}</p>",
            f"<p><b>Relations détectées :</b> "
            f"{synthesis.metadata.get('edge_count', 0)}</p>",
            f"<p><b>Clusters thématiques :</b> "
            f"{synthesis.metadata.get('cluster_count', 0)}</p>",
        ]
        self._summary_view.setHtml("".join(summary_html))

        # Concepts & pouvoir
        concepts_html = ["<h3>Concepts dominants</h3><ul>"]
        for c in synthesis.dominant_concepts:
            concepts_html.append(
                f"<li><b>{_escape(c['label'])}</b> "
                f"<i>({c['type']})</i><br>"
                f"Centralité : {c['centrality']:.3f} | "
                f"Confiance : {c['confidence']:.2f} | "
                f"Preuves : {c['evidence_count']}</li>"
            )
        concepts_html.append("</ul>")
        
        if synthesis.power_axes:
            concepts_html.append("<h3>Axes de pouvoir</h3><ul>")
            for a in synthesis.power_axes:
                concepts_html.append(
                    f"<li><b>{_escape(a['label'])}</b><br>"
                    f"Betweenness : {a['betweenness']:.3f} | "
                    f"Influence : {a['influence_score']:.3f} | "
                    f"Connecte {a['connected_clusters']} cluster(s)</li>"
                )
            concepts_html.append("</ul>")
        
        self._concepts_view.setHtml("".join(concepts_html))

        # Tensions & omissions
        tensions_html = []
        if synthesis.major_contradictions:
            tensions_html.append("<h3>Contradictions majeures</h3><ul>")
            for c in synthesis.major_contradictions:
                tensions_html.append(
                    f"<li><b>« {_escape(c['source'])} »</b> ↔ "
                    f"<b>« {_escape(c['target'])} »</b><br>"
                    f"Intensité : {c['tension_intensity']:.2f} | "
                    f"Plugins : {', '.join(c['provenance'])}</li>"
                )
            tensions_html.append("</ul>")
        else:
            tensions_html.append(
                "<p><i>Aucune contradiction majeure détectée.</i></p>"
            )

        if synthesis.detected_omissions:
            tensions_html.append("<h3>Angles morts</h3><ul>")
            for o in synthesis.detected_omissions:
                tensions_html.append(f"<li>{_escape(o)}</li>")
            tensions_html.append("</ul>")
        else:
            tensions_html.append(
                "<p><i>Aucune omission détectée.</i></p>"
            )
        
        self._tensions_view.setHtml("".join(tensions_html))

        # Structure argumentative
        structure_html = ["<h3>Structure argumentative</h3>"]
        if synthesis.argumentative_structure:
            structure_html.append("<ul>")
            for s in synthesis.argumentative_structure:
                structure_html.append(
                    f"<li>« {_escape(s['premise'])} » → "
                    f"« {_escape(s['conclusion'])} »</li>"
                )
            structure_html.append("</ul>")
        else:
            structure_html.append(
                "<p><i>Aucune chaîne d'implication détectée.</i></p>"
            )
        
        if synthesis.hypotheses_summary:
            structure_html.append("<h3>Top hypothèses</h3><ul>")
            for h in synthesis.hypotheses_summary:
                structure_html.append(
                    f"<li><b>{_escape(h['label'])}</b> "
                    f"(confiance={h['confidence']:.2f})<br>"
                    f"<i>{_escape(h['statement'])}</i></li>"
                )
            structure_html.append("</ul>")
        
        self._structure_view.setHtml("".join(structure_html))


def _escape(text: str) -> str:
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))