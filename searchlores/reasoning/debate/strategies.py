"""
Stratégies de débat.

Une DebateStrategy définit comment collecter les arguments
(pour/contre) d'une hypothèse à partir du Knowledge Graph.

Le pattern Strategy permet d'ajouter facilement de nouvelles
façons de débattre sans modifier le DebateEngine.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from searchlores.graph.knowledge_graph import (
    KnowledgeGraph, Node, NodeType, Relation, RelationType,
)
from searchlores.reasoning.debate.argument import Argument, ArgumentKind
from searchlores.reasoning.hypothesis import Hypothesis


class DebateStrategy(ABC):
    """
    Interface pour les stratégies de débat.
    
    Une stratégie reçoit une hypothèse et le graphe, et retourne
    une liste d'arguments (pour/contre).
    """

    @abstractmethod
    def gather_arguments(self, hypothesis: Hypothesis,
                         graph: KnowledgeGraph) -> List[Argument]:
        """
        Collecte les arguments pour/contre une hypothèse.
        
        Args:
            hypothesis: hypothèse à débattre
            graph: graphe de connaissances
        
        Returns:
            Liste d'arguments (supports et attaques)
        """
        ...


class EvidenceGatheringStrategy(DebateStrategy):
    """
    Stratégie de base : collecte les preuves structurelles.
    
    Pour chaque nœud référencé par l'hypothèse :
      - SUPPORTS entrants → arguments en faveur
      - CONTRADICTS entrants → arguments contre
      - CITES / REINFORCES → arguments de convergence
    """

    def gather_arguments(self, hypothesis: Hypothesis,
                         graph: KnowledgeGraph) -> List[Argument]:
        arguments: List[Argument] = []

        for node_id in hypothesis.supporting:
            node = graph.get_node(node_id)
            if not node:
                continue

            # 1. Preuves directes (evidences du nœud)
            for evidence in node.evidences:
                arguments.append(Argument.support(
                    kind=ArgumentKind.DIRECT_EVIDENCE,
                    weight=min(node.confidence, 0.9),
                    justification=(
                        f"Preuve directe pour « {node.label} » : "
                        f"« {evidence.text[:80]} » "
                        f"(source : {evidence.source_plugin})."
                    ),
                    source_ids=[node_id],
                    provenance=[evidence.source_plugin],
                ))

            # 2. Supports structurels (relations SUPPORTS entrantes)
            incoming_supports = [
                r for r in graph.get_relations(node_id, RelationType.SUPPORTS)
                if r.target_id == node_id
            ]
            for rel in incoming_supports:
                source = graph.get_node(rel.source_id)
                source_label = source.label if source else rel.source_id
                arguments.append(Argument.support(
                    kind=ArgumentKind.STRUCTURAL_SUPPORT,
                    weight=rel.confidence,
                    justification=(
                        f"« {source_label} » soutient « {node.label} » "
                        f"(confiance={rel.confidence:.2f})."
                    ),
                    source_ids=[rel.source_id, node_id],
                    provenance=[e.source_plugin for e in rel.evidences],
                ))

            # 3. Contradictions (relations CONTRADICTS)
            contradictions = [
                r for r in graph.get_relations(node_id, RelationType.CONTRADICTS)
                if r.target_id == node_id or r.source_id == node_id
            ]
            for rel in contradictions:
                other_id = (rel.source_id if rel.target_id == node_id
                            else rel.target_id)
                other = graph.get_node(other_id)
                other_label = other.label if other else other_id
                arguments.append(Argument.undermine(
                    kind=ArgumentKind.CONTRADICTION,
                    weight=rel.confidence,
                    justification=(
                        f"« {other_label} » contredit « {node.label} » "
                        f"(confiance={rel.confidence:.2f})."
                    ),
                    source_ids=[other_id, node_id],
                    provenance=[e.source_plugin for e in rel.evidences],
                ))

        # 4. Nœuds en contradiction directe (hypothesis.contradicting)
        for node_id in hypothesis.contradicting:
            node = graph.get_node(node_id)
            if not node:
                continue
            arguments.append(Argument.attack(
                kind=ArgumentKind.CONTRADICTION,
                weight=node.confidence,
                justification=(
                    f"Le nœud « {node.label} » contredit directement "
                    f"l'hypothèse (confiance={node.confidence:.2f})."
                ),
                source_ids=[node_id],
                provenance=[e.source_plugin for e in node.evidences],
            ))

        return arguments


class ConvergenceStrategy(DebateStrategy):
    """
    Stratégie de convergence : valorise les hypothèses étayées
    par plusieurs sources indépendantes.
    
    Si un nœud de l'hypothèse a été fusionné depuis plusieurs
    observations (plusieurs plugins), c'est un signal fort.
    """

    def gather_arguments(self, hypothesis: Hypothesis,
                         graph: KnowledgeGraph) -> List[Argument]:
        arguments: List[Argument] = []

        for node_id in hypothesis.supporting:
            node = graph.get_node(node_id)
            if not node:
                continue

            # Compte les plugins distincts ayant contribué
            plugins = {e.source_plugin for e in node.evidences}
            
            if len(plugins) >= 2:
                # Convergence : plusieurs sources indépendantes
                arguments.append(Argument.support(
                    kind=ArgumentKind.CONVERGENCE,
                    weight=min(0.5 + 0.1 * len(plugins), 1.0),
                    justification=(
                        f"Convergence forte sur « {node.label} » : "
                        f"{len(plugins)} sources indépendantes "
                        f"({', '.join(sorted(plugins))})."
                    ),
                    source_ids=[node_id],
                    provenance=list(plugins),
                ))
            elif len(plugins) == 1:
                # Source unique : signal plus faible
                arguments.append(Argument(
                    polarity=__import__("searchlores.reasoning.debate.argument",
                                        fromlist=["ArgumentPolarity"]).ArgumentPolarity.NEUTRAL,
                    kind=ArgumentKind.DIRECT_EVIDENCE,
                    weight=0.3,
                    justification=(
                        f"Source unique sur « {node.label} » : "
                        f"un seul plugin ({next(iter(plugins))})."
                    ),
                    source_ids=[node_id],
                    provenance=list(plugins),
                ))

        return arguments


class CompetitorStrategy(DebateStrategy):
    """
    Stratégie compétitive : identifie les hypothèses rivales.
    
    Deux hypothèses sont rivales si elles partagent des nœuds
    mais avec des polarités opposées (l'une supporte ce que
    l'autre contredit).
    """

    def gather_arguments(self, hypothesis: Hypothesis,
                         graph: KnowledgeGraph,
                         all_hypotheses: List[Hypothesis] = None) -> List[Argument]:
        arguments: List[Argument] = []
        
        if not all_hypotheses:
            return arguments

        hypothesis_nodes = set(hypothesis.supporting) | set(hypothesis.contradicting)

        for other in all_hypotheses:
            if other.label == hypothesis.label:
                continue

            other_nodes = set(other.supporting) | set(other.contradicting)
            overlap = hypothesis_nodes & other_nodes

            if overlap and (
                hypothesis_nodes & set(other.contradicting)
                or other_nodes & set(hypothesis.contradicting)
            ):
                # Hypothèse concurrente détectée
                arguments.append(Argument.undermine(
                    kind=ArgumentKind.COMPETITOR,
                    weight=other.confidence * 0.7,
                    justification=(
                        f"Hypothèse concurrente : « {other.label} » "
                        f"(confiance={other.confidence:.2f}) partage "
                        f"{len(overlap)} nœud(s) avec polarité opposée."
                    ),
                    source_ids=list(overlap),
                    provenance=other.provenance,
                    metadata={"competitor_label": other.label},
                ))

        return arguments


class AbsenceStrategy(DebateStrategy):
    """
    Stratégie d'absence : détecte les omissions.
    
    Si une hypothèse porte sur un concept qui n'apparaît nulle
    part ailleurs dans le graphe, c'est un signal d'isolement
    (potentiellement un angle mort ou une spéculation).
    """

    def gather_arguments(self, hypothesis: Hypothesis,
                         graph: KnowledgeGraph) -> List[Argument]:
        arguments: List[Argument] = []

        for node_id in hypothesis.supporting:
            node = graph.get_node(node_id)
            if not node:
                continue

            # Compte les connexions du nœud
            relations = graph.get_relations(node_id)
            
            if len(relations) == 0:
                # Nœud isolé : signal d'absence
                arguments.append(Argument.undermine(
                    kind=ArgumentKind.ABSENCE,
                    weight=0.4,
                    justification=(
                        f"« {node.label} » est isolé dans le graphe : "
                        f"aucune relation ne le connecte à d'autres concepts. "
                        f"Signal d'absence de corroboration."
                    ),
                    source_ids=[node_id],
                ))
            elif len(relations) == 1:
                # Faiblement connecté
                arguments.append(Argument(
                    polarity=__import__("searchlores.reasoning.debate.argument",
                                        fromlist=["ArgumentPolarity"]).ArgumentPolarity.NEUTRAL,
                    kind=ArgumentKind.ABSENCE,
                    weight=0.2,
                    justification=(
                        f"« {node.label} » est faiblement connecté "
                        f"(1 seule relation)."
                    ),
                    source_ids=[node_id],
                ))

        return arguments