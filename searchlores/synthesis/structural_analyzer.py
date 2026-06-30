"""
Analyseur structurel du Knowledge Graph.

Ce module extrait des métriques structurelles du graphe pour
alimenter la synthèse argumentée. Il s'appuie sur les algorithmes
de networkx (centralité, clustering, composantes connexes).

Responsabilités :
  - Identifier les concepts dominants (centralité)
  - Détecter les clusters thématiques
  - Calculer la cohérence globale du graphe
  - Produire des métriques exploitables par SynthesisEngine
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

import networkx as nx

from searchlores.graph.knowledge_graph import (
    KnowledgeGraph, Node, NodeType, RelationType,
)


@dataclass
class StructuralAnalysis:
    """
    Résultat de l'analyse structurelle du graphe.
    
    Contient toutes les métriques nécessaires à la synthèse :
      - dominant_concepts : nœuds les plus centraux
      - thematic_clusters : groupes de nœuds connectés
      - bridge_concepts : nœuds faisant le pont entre clusters
      - coherence_score : mesure de cohérence globale (0.0–1.0)
      - argumentative_structure : prémisse → conclusion détectées
    """
    dominant_concepts: List[Tuple[Node, float]] = field(default_factory=list)
    thematic_clusters: List[List[Node]] = field(default_factory=list)
    bridge_concepts: List[Tuple[Node, float]] = field(default_factory=list)
    coherence_score: float = 0.0
    argumentative_structure: List[Tuple[str, str]] = field(default_factory=list)
    global_confidence: float = 0.0
    node_count: int = 0
    edge_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "dominant_concepts": [
                {"label": n.label, "type": n.node_type.value, "centrality": c}
                for n, c in self.dominant_concepts
            ],
            "thematic_clusters": [
                [{"label": n.label, "type": n.node_type.value} for n in cluster]
                for cluster in self.thematic_clusters
            ],
            "bridge_concepts": [
                {"label": n.label, "type": n.node_type.value, "betweenness": b}
                for n, b in self.bridge_concepts
            ],
            "coherence_score": self.coherence_score,
            "argumentative_structure": self.argumentative_structure,
            "global_confidence": self.global_confidence,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
        }


class StructuralAnalyzer:
    """
    Analyse la structure du Knowledge Graph pour en extraire
    des métriques significatives.
    
    Utilise les algorithmes de networkx :
      - degree_centrality : concepts les plus connectés
      - betweenness_centrality : concepts-ponts
      - weakly_connected_components : clusters thématiques
    
    Usage :
    
        analyzer = StructuralAnalyzer()
        analysis = analyzer.analyze(graph)
        
        for node, centrality in analysis.dominant_concepts[:5]:
            print(f"{node.label}: {centrality:.3f}")
    """

    def analyze(self, graph: KnowledgeGraph,
                top_k: int = 10) -> StructuralAnalysis:
        """
        Analyse complète du graphe.
        
        Args:
            graph: graphe à analyser
            top_k: nombre de nœuds à retenir pour dominants/ponts
        
        Returns:
            StructuralAnalysis avec toutes les métriques
        """
        nx_graph = graph.to_networkx()
        analysis = StructuralAnalysis(
            node_count=len(nx_graph.nodes),
            edge_count=len(nx_graph.edges),
        )

        if analysis.node_count == 0:
            return analysis

        # 1. Concepts dominants (degree centrality)
        analysis.dominant_concepts = self._compute_dominant_concepts(
            graph, nx_graph, top_k
        )

        # 2. Clusters thématiques (weakly connected components)
        analysis.thematic_clusters = self._compute_clusters(graph, nx_graph)

        # 3. Concepts-ponts (betweenness centrality)
        analysis.bridge_concepts = self._compute_bridge_concepts(
            graph, nx_graph, top_k
        )

        # 4. Score de cohérence
        analysis.coherence_score = self._compute_coherence(graph, nx_graph)

        # 5. Structure argumentative
        analysis.argumentative_structure = self._extract_argumentative_structure(
            graph
        )

        # 6. Confiance globale
        analysis.global_confidence = self._compute_global_confidence(graph)

        return analysis

    def _compute_dominant_concepts(
        self, graph: KnowledgeGraph, nx_graph: nx.DiGraph, top_k: int
    ) -> List[Tuple[Node, float]]:
        """Nœuds avec la plus forte centralité de degré."""
        if len(nx_graph) < 2:
            return []
        
        centrality = nx.degree_centrality(nx_graph)
        sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        
        result: List[Tuple[Node, float]] = []
        for node_id, score in sorted_nodes[:top_k]:
            node = graph.get_node(node_id)
            if node and node.node_type != NodeType.OBSERVATION:
                result.append((node, score))
        return result

    def _compute_clusters(
        self, graph: KnowledgeGraph, nx_graph: nx.DiGraph
    ) -> List[List[Node]]:
        """Groupes de nœuds faiblement connectés entre eux."""
        if len(nx_graph) == 0:
            return []
        
        components = list(nx.weakly_connected_components(nx_graph))
        clusters: List[List[Node]] = []
        
        for component in components:
            if len(component) < 2:
                continue
            cluster_nodes = [
                graph.get_node(nid)
                for nid in component
                if graph.get_node(nid) is not None
            ]
            # Exclut les nœuds techniques (OBSERVATION)
            cluster_nodes = [
                n for n in cluster_nodes
                if n.node_type != NodeType.OBSERVATION
            ]
            if cluster_nodes:
                clusters.append(cluster_nodes)
        
        # Trie par taille décroissante
        clusters.sort(key=len, reverse=True)
        return clusters

    def _compute_bridge_concepts(
        self, graph: KnowledgeGraph, nx_graph: nx.DiGraph, top_k: int
    ) -> List[Tuple[Node, float]]:
        """Nœuds faisant le pont entre clusters (betweenness)."""
        if len(nx_graph) < 3:
            return []
        
        try:
            centrality = nx.betweenness_centrality(nx_graph)
        except Exception:
            return []
        
        sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        
        result: List[Tuple[Node, float]] = []
        for node_id, score in sorted_nodes[:top_k]:
            if score <= 0:
                break
            node = graph.get_node(node_id)
            if node and node.node_type != NodeType.OBSERVATION:
                result.append((node, score))
        return result

    def _compute_coherence(
        self, graph: KnowledgeGraph, nx_graph: nx.DiGraph
    ) -> float:
        """
        Score de cohérence du graphe.
        
        Mesure dans quelle mesure le graphe forme un tout connecté
        (vs. plusieurs îlots isolés). Un graphe parfaitement connecté
        a un score de 1.0 ; un graphe totalement fragmenté tend vers 0.
        """
        if len(nx_graph) < 2:
            return 1.0 if len(nx_graph) == 1 else 0.0
        
        components = list(nx.weakly_connected_components(nx_graph))
        if len(components) == 1:
            return 1.0
        
        # Ratio : taille de la plus grande composante / taille totale
        largest = max(len(c) for c in components)
        return largest / len(nx_graph)

    def _extract_argumentative_structure(
        self, graph: KnowledgeGraph
    ) -> List[Tuple[str, str]]:
        """
        Extrait les paires (prémisse, conclusion) via IMPLIES.
        
        Retourne une liste de tuples (source_label, target_label)
        pour chaque relation d'implication.
        """
        structure: List[Tuple[str, str]] = []
        implies = graph.get_relations(relation_type=RelationType.IMPLIES)
        
        for rel in implies:
            source = graph.get_node(rel.source_id)
            target = graph.get_node(rel.target_id)
            if source and target:
                structure.append((source.label, target.label))
        
        return structure

    def _compute_global_confidence(self, graph: KnowledgeGraph) -> float:
        """
        Confiance globale du graphe.
        
        Moyenne pondérée des confiances de tous les nœuds et relations.
        """
        nodes = graph.find_nodes()
        if not nodes:
            return 0.0
        
        relations = graph.get_relations()
        
        node_confidences = [n.confidence for n in nodes]
        relation_confidences = [r.confidence for r in relations]
        
        all_confidences = node_confidences + relation_confidences
        if not all_confidences:
            return 0.0
        
        return sum(all_confidences) / len(all_confidences)