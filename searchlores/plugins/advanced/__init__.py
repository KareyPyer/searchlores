"""
Plugins avancés de Searchlores (strates 10-14).

Issus de la session de conception "Archéologie des pouvoirs discursifs"
avec Qwen. Chaque plugin est autonome (pas de dépendance lourde, juste
`pydantic`), testable indépendamment, et déclare ses propres métadonnées
(`name`, `dependencies`) via la classe de base `AdvancedPlugin`.
"""
from .base import AdvancedPlugin
from .performative_contradiction import PerformativeContradictionDetector
from .narrative_level import NarrativeLevelAnalyzer
from .epistemic_regime import EpistemicRegimeDetector
from .implicit_authority import ImplicitAuthorityDetector
from .foucault_analyzer import FoucaultAnalyzer
from .general_semantics import GeneralSemanticsAnalyzer

__all__ = [
    "AdvancedPlugin",
    "PerformativeContradictionDetector",
    "NarrativeLevelAnalyzer",
    "EpistemicRegimeDetector",
    "ImplicitAuthorityDetector",
    "FoucaultAnalyzer",
    "GeneralSemanticsAnalyzer",
    "ADVANCED_PLUGINS",
]

# Liste ordonnée pour enregistrement automatique.
# L'ordre logique (utile pour la lecture) ; l'ordre d'EXÉCUTION réel est
# recalculé par PluginOrchestrator via un tri topologique sur `dependencies`.
ADVANCED_PLUGINS = [
    PerformativeContradictionDetector,
    NarrativeLevelAnalyzer,
    EpistemicRegimeDetector,
    ImplicitAuthorityDetector,
    FoucaultAnalyzer,
    GeneralSemanticsAnalyzer,
]
