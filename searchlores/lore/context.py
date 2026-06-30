"""
LoreContext : contexte d'investigation enrichi par une LoreFrame.

Le LoreContext encapsule le contexte d'investigation standard
et y ajoute la LoreFrame active. Il est transmis aux observers
et aux moteurs pour qu'ils puissent adapter leur comportement.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from searchlores.core.context import InvestigationContext
from searchlores.lore.frame import LoreFrame


@dataclass
class LoreContext:
    """
    Contexte d'investigation enrichi par une LoreFrame.
    
    Attributes:
        base_context: contexte d'investigation sous-jacent
        lore: LoreFrame active
        lore_metadata: métadonnées spécifiques à l'exécution Lore
    """
    base_context: InvestigationContext
    lore: LoreFrame
    lore_metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def prompt(self) -> str:
        return self.base_context.prompt

    @property
    def findings(self) -> Dict[str, Any]:
        return self.base_context.findings

    def to_investigation_context(self) -> InvestigationContext:
        """
        Retourne le contexte sous-jacent, enrichi des métadonnées Lore.
        
        Utile pour maintenir la compatibilité avec l'API existante.
        """
        self.base_context.findings["_lore"] = self.lore.to_dict()
        self.base_context.findings["_lore_metadata"] = self.lore_metadata
        return self.base_context

    @classmethod
    def from_context(cls, context: InvestigationContext,
                     lore: Optional[LoreFrame] = None) -> LoreContext:
        """Construit un LoreContext depuis un contexte existant."""
        return cls(
            base_context=context,
            lore=lore or LoreFrame.default(),
        )