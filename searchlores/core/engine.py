# searchlores/core/engine.py
# Ajoutez ces modifications pour supporter les plugins avancés

from typing import List, Optional, Any, Dict
from searchlores.core.context import InvestigationContext
from searchlores.plugins.base import Plugin

class InvestigationEngine:
    """Moteur d'investigation principal."""

    def __init__(self):
        self.plugins: List[Plugin] = []
        self.advanced_mode: bool = False
        self._advanced_plugins: List[Any] = []
        self._orchestrator = None

    def register(self, plugin: Plugin) -> None:
        """Enregistre un plugin standard."""
        if plugin not in self.plugins:
            self.plugins.append(plugin)

    def register_advanced(self, plugin: Any) -> None:
        """Enregistre un plugin avancé."""
        if hasattr(plugin, 'name'):
            self._advanced_plugins.append(plugin)

    def set_orchestrator(self, orchestrator: Any) -> None:
        """Définit l'orchestrateur pour les plugins avancés."""
        self._orchestrator = orchestrator
        self.advanced_mode = True

    def run(self, prompt: str, context: Optional[InvestigationContext] = None) -> InvestigationContext:
        """Exécute l'investigation."""
        if context is None:
            context = InvestigationContext(prompt=prompt)

        # Exécution des plugins standards
        for plugin in self.plugins:
            try:
                plugin.run(context)
            except Exception as e:
                # Gestion d'erreur silencieuse ou logging
                if not hasattr(context, 'errors'):
                    context.errors = []
                context.errors.append({
                    "plugin": getattr(plugin, 'name', 'unknown'),
                    "error": str(e)
                })

        # Exécution avancée si activée
        if self.advanced_mode and self._orchestrator:
            self._orchestrator.run_all(
                prompt,
                context=context,
                on_result=lambda name, results: self._merge_advanced_results(context, results),
                on_error=lambda name, msg: self._handle_advanced_error(context, name, msg)
            )

        return context

    def _merge_advanced_results(self, context: InvestigationContext, results: Dict[str, Any]):
        """Fusionne les résultats des plugins avancés dans le contexte."""
        for key, value in results.items():
            if key not in context.findings:
                context.findings[key] = []
            if isinstance(value, list):
                context.findings[key].extend(value)
            else:
                context.findings[key].append(value)

    def _handle_advanced_error(self, context: InvestigationContext, plugin_name: str, error_msg: str):
        """Gère les erreurs des plugins avancés."""
        if not hasattr(context, 'errors'):
            context.errors = []
        context.errors.append({
            "plugin": plugin_name,
            "error": error_msg,
            "advanced": True
        })

    @property
    def available_plugins(self) -> List[str]:
        """Retourne la liste des plugins enregistrés."""
        names = []
        for p in self.plugins:
            names.append(getattr(p, 'name', p.__class__.__name__))
        for p in self._advanced_plugins:
            names.append(getattr(p, 'name', p.__class__.__name__))
        return names
