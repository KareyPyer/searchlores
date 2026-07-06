"""
Orchestrateur de plugins avancés basé sur un graphe acyclique orienté (DAG).
Résout automatiquement l'ordre d'exécution à partir des `dependencies`
déclarées par chaque plugin (voir plugins/advanced/base.py).

Autonome : n'importe aucun module du reste de Searchlores, afin de pouvoir
être testé et utilisé indépendamment de l'architecture exacte de
core/engine.py et core/context.py existants.
"""
from typing import List, Dict, Any, Protocol, Set
from dataclasses import dataclass, field


class AdvancedPluginProtocol(Protocol):
    """Interface structurelle attendue (duck-typing, pas d'héritage requis)."""

    name: str
    dependencies: List[str]

    def analyze(self, text: str, context: Any = None) -> Dict[str, Any]:
        ...


@dataclass
class PluginNode:
    plugin: AdvancedPluginProtocol
    dependencies: Set[str] = field(default_factory=set)
    executed: bool = False


class PluginOrchestrator:
    """
    Orchestre l'exécution des plugins avancés en respectant leurs
    dépendances déclarées.

    Algorithme : tri topologique de Kahn. Si un plugin échoue, les plugins
    qui en dépendent sont sautés (avec une erreur tracée), mais les autres
    branches indépendantes du DAG continuent normalement.
    """

    def __init__(self):
        self._plugins: Dict[str, PluginNode] = {}

    def get_plugin(self, name: str) -> AdvancedPluginProtocol:
        """Accès public à une instance de plugin enregistrée, par son nom."""
        return self._plugins[name].plugin

    def register(self, plugin: AdvancedPluginProtocol) -> None:
        """Enregistre un plugin. Lève ValueError en cas de nom dupliqué."""
        if plugin.name in self._plugins:
            raise ValueError(f"Un plugin nommé '{plugin.name}' est déjà enregistré")
        self._plugins[plugin.name] = PluginNode(
            plugin=plugin, dependencies=set(getattr(plugin, "dependencies", []) or [])
        )

    def _topological_sort(self) -> List[str]:
        """
        Tri topologique (Kahn). Lève ValueError si une dépendance est
        inconnue ou si un cycle est détecté.
        """
        for node in self._plugins.values():
            for dep in node.dependencies:
                if dep not in self._plugins:
                    raise ValueError(
                        f"Plugin '{node.plugin.name}' dépend de '{dep}' qui n'est pas enregistré"
                    )

        # in_degree[name] = nombre de dépendances non résolues pour ce plugin
        in_degree: Dict[str, int] = {
            name: len(node.dependencies) for name, node in self._plugins.items()
        }

        queue = [name for name, degree in in_degree.items() if degree == 0]
        order: List[str] = []

        while queue:
            current = queue.pop(0)
            order.append(current)
            # Décrémenter les plugins qui dépendaient de 'current'
            for name, node in self._plugins.items():
                if current in node.dependencies and name not in order:
                    in_degree[name] -= 1
                    if in_degree[name] == 0:
                        queue.append(name)

        if len(order) != len(self._plugins):
            remaining = set(self._plugins) - set(order)
            raise ValueError(f"Cycle détecté dans les dépendances des plugins : {remaining}")

        return order

    def run_all(self, text: str, context: Any = None, on_result=None, on_error=None) -> Dict[str, Any]:
        """
        Exécute tous les plugins enregistrés dans l'ordre topologique.

        `context` est transmis tel quel à chaque `plugin.analyze(text, context)`.
        `on_result(plugin_name, results)` et `on_error(plugin_name, message)`
        sont des callbacks optionnels (utiles pour brancher sur
        InvestigationContext.register_plugin()/record_error() sans que cet
        orchestrateur ait besoin de connaître leur forme exacte).

        Retourne un dict {plugin_name: results} pour les plugins ayant réussi.
        """
        execution_order = self._topological_sort()
        failed_plugins: Set[str] = set()
        all_results: Dict[str, Any] = {}

        for plugin_name in execution_order:
            node = self._plugins[plugin_name]

            missing_deps = node.dependencies & failed_plugins
            if missing_deps:
                message = f"Sauté car dépendances échouées : {sorted(missing_deps)}"
                if on_error:
                    on_error(plugin_name, message)
                failed_plugins.add(plugin_name)
                continue

            try:
                results = node.plugin.analyze(text, context)
                all_results[plugin_name] = results
                node.executed = True
                if on_result:
                    on_result(plugin_name, results)
            except Exception as e:  # noqa: BLE001 - on isole volontairement toute exception plugin
                message = f"{type(e).__name__}: {e}"
                if on_error:
                    on_error(plugin_name, message)
                failed_plugins.add(plugin_name)

        return all_results
