"""
InvestigationWidget : classe de base pour tous les widgets.

Fournit :
  - une référence au bus de communication
  - des méthodes de cycle de vie (on_registered, on_unregistered)
  - un titre et une icône standardisés
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QIcon

from searchlores.gui.bus import InvestigationBus


class InvestigationWidget(QWidget):
    """
    Classe de base pour tous les widgets d'investigation.
    
    Chaque widget doit :
      - s'abonner aux signaux du bus dans on_registered()
      - se désabonner dans on_unregistered()
      - réagir aux événements en mettant à jour son affichage
    """
    
    # À surcharger dans les sous-classes
    TITLE: str = "Widget"
    ICON_NAME: str = ""

    def __init__(self, bus: InvestigationBus,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._bus = bus
        self._registered = False

    @property
    def bus(self) -> InvestigationBus:
        return self._bus

    def register(self) -> None:
        """Abonne le widget aux signaux du bus."""
        if self._registered:
            return
        self.on_registered()
        self._registered = True

    def unregister(self) -> None:
        """Désabonne le widget des signaux du bus."""
        if not self._registered:
            return
        self.on_unregistered()
        self._registered = False

    def on_registered(self) -> None:
        """À surcharger : connecter les signaux du bus."""
        pass

    def on_unregistered(self) -> None:
        """À surcharger : déconnecter les signaux du bus."""
        pass

    def title(self) -> str:
        return self.TITLE

    def icon(self) -> Optional[QIcon]:
        if self.ICON_NAME:
            return QIcon.fromTheme(self.ICON_NAME)
        return None