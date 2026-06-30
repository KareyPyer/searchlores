"""
Moteur de fusion des observations.

Le FusionEngine est responsable d'injecter les observations
produites par les observers dans le Knowledge Graph.

Responsabilités :
  - Valider les observations
  - Créer les nœuds et relations dans le graphe
  - Gérer la déduplication (via KnowledgeGraph.add_node/Relation avec merge=True)
  - Reporter un résumé de l'ingestion

Ce moteur garantit que toutes les observations sont traçables
et que le graphe reste cohérent.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from searchlores.graph.knowledge_graph import (
    KnowledgeGraph, Node, NodeType, Relation, RelationType,
)
from searchlores.observers.base import Observation


@dataclass
class IngestionReport:
    """
    Résumé de l'ingestion des observations dans le graphe.
    
    Utile pour le logging et le debugging.
    """
    total_observations: int
    nodes_created: int
    nodes_merged: int
    relations_created: int
    errors: List[str]


class FusionEngine:
    """
    Injecte les observations dans le Knowledge Graph.
    
    Le FusionEngine est le pont entre les observers (qui produisent
    des observations) et le graphe (qui les accumule).
    
    Usage :
    
        fusion = FusionEngine()
        report = fusion.ingest(observations, graph)
        
        print(f"Nœuds créés: {report.nodes_created}")
        print(f"Nœuds fusionnés: {report.nodes_merged}")
        print(f"Relations créées: {report.relations_created}")
    """

    def ingest(self, observations: List[Observation],
               graph: KnowledgeGraph) -> IngestionReport:
        """
        Injecte une liste d'observations dans le graphe.
        
        Pour chaque observation :
          1. Crée ou fusionne le nœud sujet
          2. Crée ou fusionne le nœud objet (si présent)
          3. Crée ou fusionne la relation (si predicate présent)
        
        Args:
            observations: liste d'observations à ingérer
            graph: graphe de connaissances cible
        
        Returns:
            IngestionReport avec les statistiques d'ingestion
        """
        nodes_before = len(graph)
        relations_before = len(graph.get_relations())
        errors: List[str] = []
        nodes_merged = 0

        for obs in observations:
            try:
                # 1. Nœud sujet
                subj_id_before = self._find_node_id(graph, obs.subject)
                subj_id = graph.add_node(obs.subject, merge=True)
                if subj_id_before and subj_id == subj_id_before:
                    nodes_merged += 1

                # 2. Nœud objet (si relation binaire)
                obj_id: Optional[str] = None
                if obs.object_node is not None:
                    obj_id_before = self._find_node_id(graph, obs.object_node)
                    obj_id = graph.add_node(obs.object_node, merge=True)
                    if obj_id_before and obj_id == obj_id_before:
                        nodes_merged += 1

                # 3. Relation (si predicate et objet présents)
                if obs.predicate and obj_id:
                    relation = Relation(
                        source_id=subj_id,
                        target_id=obj_id,
                        relation_type=obs.predicate,
                        confidence=obs.confidence,
                        evidences=list(obs.evidences),
                        metadata=dict(obs.metadata),
                    )
                    graph.add_relation(relation)

            except Exception as e:
                errors.append(f"Error ingesting observation: {e}")

        nodes_after = len(graph)
        relations_after = len(graph.get_relations())

        return IngestionReport(
            total_observations=len(observations),
            nodes_created=nodes_after - nodes_before,
            nodes_merged=nodes_merged,
            relations_created=relations_after - relations_before,
            errors=errors,
        )

    def _find_node_id(self, graph: KnowledgeGraph, node: Node) -> Optional[str]:
        """
        Cherche si un nœud de même (type, label) existe déjà.
        
        Retourne l'ID du nœud existant, ou None.
        """
        existing = graph.find_nodes(
            node_type=node.node_type,
            label_contains=node.label,
        )
        if existing:
            # Vérifie correspondance exacte
            for n in existing:
                if n.label == node.label:
                    return n.id
        return None