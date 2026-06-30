"""
Adaptateur permettant aux plugins V1 de fonctionner dans le moteur V2.

Les plugins V1 écrivent directement dans context.findings, ce qui
viole le principe de séparation observation/interprétation.

Le V1PluginWrapper exécute le plugin V1 sur un contexte isolé,
puis traduit ses findings en observations injectées dans le
Knowledge Graph.

Usage :
    
    from searchlores.plugins.builtin.authority import AuthorityDetector
    from searchlores.compat import V1PluginWrapper
    
    legacy_plugin = AuthorityDetector()
    observer = V1PluginWrapper(legacy_plugin)
    
    # Maintenant observer peut être utilisé comme un Observer V2
    observations = observer.observe(text, graph, context)
"""
from __future__ import annotations

from copy import deepcopy
from typing import List

from searchlores.core.context import InvestigationContext
from searchlores.core.engine import Plugin
from searchlores.graph.knowledge_graph import (
    Evidence, KnowledgeGraph, Node, NodeType, Relation, RelationType,
)
from searchlores.observers.base import Observation, Observer


class V1PluginWrapper(Observer):
    """
    Adapte un plugin V1 en Observer V2.
    
    Stratégie :
      1. Exécuter le plugin V1 sur un contexte isolé
      2. Traduire les findings en observations typées
      3. Retourner la liste d'observations
    
    Les plugins V1 continuent ainsi de fonctionner sans modification,
    tout en participant au graphe de connaissances V2.
    """
    version = "1.0-compat"

    def __init__(self, legacy_plugin: Plugin) -> None:
        """
        Initialise l'adaptateur avec un plugin V1.
        
        Args:
            legacy_plugin: instance d'un plugin V1 (hérite de Plugin)
        """
        self._legacy = legacy_plugin
        self.name = f"v1_{legacy_plugin.name}"

    def observe(self, text: str, graph: KnowledgeGraph,
                context: InvestigationContext) -> List[Observation]:
        """
        Exécute le plugin V1 et traduit ses findings en observations.
        
        Args:
            text: texte à analyser
            graph: graphe de connaissances (non utilisé ici)
            context: contexte d'investigation
        
        Returns:
            Liste d'observations traduites depuis les findings V1
        """
        # Contexte isolé pour ne pas polluer l'état global
        isolated_ctx = deepcopy(context)
        isolated_ctx.prompt = text
        
        # Exécution du plugin V1
        self._legacy.run(isolated_ctx)

        observations: List[Observation] = []

        # Traduction générique des findings en nœuds d'observation
        for key, value in isolated_ctx.findings.items():
            obs_node = Node(
                id="",
                node_type=NodeType.OBSERVATION,
                label=f"{self._legacy.name}:{key}",
                confidence=0.7,
                evidences=[Evidence(
                    text=str(value)[:500],  # tronquer si trop long
                    source_plugin=self.name,
                )],
                metadata={
                    "legacy_key": key,
                    "legacy_value": value,
                },
            )
            observations.append(Observation(
                subject=obs_node,
                confidence=0.7,
                metadata={
                    "legacy_plugin": self._legacy.name,
                    "finding_key": key,
                },
            ))

        # Traduction spécifique des contradictions V1
        for c in getattr(isolated_ctx, "contradictions", []):
            tension = c.get("tension", "tension")
            node = Node(
                id="",
                node_type=NodeType.ARGUMENT,
                label=f"contradiction:{tension}",
                confidence=0.8,
                evidences=[Evidence(
                    text=c.get("description", ""),
                    source_plugin=self.name,
                )],
            )
            observations.append(Observation(
                subject=node,
                predicate=RelationType.CONTRADICTS,
                confidence=0.8,
                metadata={"legacy_contradiction": c},
            ))

        return observations