"""
Moteur d'inférence.

Le InferenceEngine analyse le Knowledge Graph et produit des
hypothèses structurées à partir des patterns détectés :
  - Convergences (nœuds soutenus par plusieurs sources)
  - Contradictions (paires de relations opposées)
  - Chaînes d'implication (A → B → C)
  - Clusters (groupes de nœuds fortement connectés)

Ce moteur est extensible : de nouvelles règles d'inférence
peuvent être ajoutées sans modifier le cœur.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from searchlores.graph.knowledge_graph import (
    KnowledgeGraph, Node, NodeType, Relation, RelationType,
)
from searchlores.reasoning.hypothesis import Hypothesis


class InferenceRule(ABC):
    """
    Interface pour les règles d'inférence.
    
    Une règle d'inférence analyse le graphe et produit des
    hypothèses. Ce pattern permet d'ajouter facilement de
    nouvelles règles sans modifier InferenceEngine.
    """

    @abstractmethod
    def infer(self, graph: KnowledgeGraph,
              min_confidence: float) -> List[Hypothesis]:
        """
        Analyse le graphe et retourne des hypothèses.
        
        Args:
            graph: graphe de connaissances à analyser
            min_confidence: seuil de confiance minimum
        
        Returns:
            Liste d'hypothèses inférées
        """
        ...


class ConvergenceRule(InferenceRule):
    """
    Détecte les nœuds soutenus par plusieurs sources indépendantes.
    
    Une convergence indique un concept fortement étayé par
    plusieurs observations ou plugins, ce qui augmente sa
    crédibilité.
    """

    def infer(self, graph: KnowledgeGraph,
              min_confidence: float) -> List[Hypothesis]:
        """Produit des hypothèses pour chaque convergence détectée."""
        hypotheses: List[Hypothesis] = []

        convergences = graph.find_convergences(
            min_confidence=min_confidence,
            min_in_degree=2,
        )

        for node in convergences:
            explanation = graph.explain_node(node.id)
            
            # Collecte les plugins impliqués
            plugins = set()
            for evidence in node.evidences:
                plugins.add(evidence.source_plugin)
            for support in explanation["supports"]:
                for evidence in support.get("evidences", []):
                    plugins.add(evidence.get("source_plugin"))

            hypotheses.append(Hypothesis(
                label=f"convergence:{node.label}",
                statement=(
                    f"Le concept '{node.label}' est soutenu par "
                    f"plusieurs sources indépendantes "
                    f"(confiance={node.confidence:.2f})."
                ),
                confidence=node.confidence,
                supporting=[node.id],
                provenance=list(plugins),
                metadata={"type": "convergence", "node_id": node.id},
            ))

        return hypotheses


class ContradictionRule(InferenceRule):
    """
    Détecte les paires de relations contradictoires.
    
    Une contradiction indique une tension entre deux observations
    ou hypothèses opposées, ce qui mérite investigation.
    """

    def infer(self, graph: KnowledgeGraph,
              min_confidence: float) -> List[Hypothesis]:
        """Produit des hypothèses pour chaque contradiction détectée."""
        hypotheses: List[Hypothesis] = []

        contradictions = graph.find_contradictions(
            min_confidence=min_confidence,
        )

        for r1, r2 in contradictions:
            # Collecte les plugins impliqués
            plugins = set()
            for evidence in r1.evidences + r2.evidences:
                plugins.add(evidence.source_plugin)

            hypotheses.append(Hypothesis(
                label=f"tension:{r1.source_id}→{r1.target_id}",
                statement=(
                    f"Tension détectée entre {r1.source_id} et {r1.target_id} : "
                    f"{r1.relation_type.value} (confiance={r1.confidence:.2f}) "
                    f"est contredit par {r2.relation_type.value} "
                    f"(confiance={r2.confidence:.2f})."
                ),
                confidence=min(r1.confidence, r2.confidence),
                supporting=[r1.source_id, r1.target_id],
                contradicting=[r2.source_id, r2.target_id],
                provenance=list(plugins),
                metadata={
                    "type": "contradiction",
                    "relation_1": r1.to_dict(),
                    "relation_2": r2.to_dict(),
                },
            ))

        return hypotheses


class ImplicationChainRule(InferenceRule):
    """
    Détecte les chaînes d'implication (A → B → C).
    
    Une chaîne d'implication suggère une relation transitive
    qui peut être inférée même si non explicitement observée.
    """

    def infer(self, graph: KnowledgeGraph,
              min_confidence: float) -> List[Hypothesis]:
        """Produit des hypothèses pour chaque chaîne détectée."""
        hypotheses: List[Hypothesis] = []

        # Récupère toutes les relations IMPLIES
        implies = graph.get_relations(relation_type=RelationType.IMPLIES)

        # Cherche des chaînes de longueur 2
        for r1 in implies:
            if r1.confidence < min_confidence:
                continue
            
            for r2 in implies:
                if r2.confidence < min_confidence:
                    continue
                
                # Vérifie si r1.target == r2.source (chaîne A→B→C)
                if r1.target_id == r2.source_id:
                    # Inférence transitive : A→C
                    combined_confidence = r1.confidence * r2.confidence
                    
                    # Collecte les plugins
                    plugins = set()
                    for evidence in r1.evidences + r2.evidences:
                        plugins.add(evidence.source_plugin)

                    hypotheses.append(Hypothesis(
                        label=f"implication:{r1.source_id}→{r2.target_id}",
                        statement=(
                            f"Chaîne d'implication détectée : "
                            f"{r1.source_id} → {r1.target_id} → {r2.target_id}. "
                            f"Inférence : {r1.source_id} implique probablement "
                            f"{r2.target_id} (confiance={combined_confidence:.2f})."
                        ),
                        confidence=combined_confidence,
                        supporting=[r1.source_id, r1.target_id, r2.target_id],
                        provenance=list(plugins),
                        metadata={
                            "type": "implication_chain",
                            "chain": [r1.source_id, r1.target_id, r2.target_id],
                        },
                    ))

        return hypotheses


class InferenceEngine:
    """
    Moteur d'inférence produisant des hypothèses à partir du graphe.
    
    Le InferenceEngine applique un ensemble de règles d'inférence
    au Knowledge Graph et retourne une liste hiérarchisée
    d'hypothèses.
    
    Usage :
    
        engine = InferenceEngine()
        
        # Ajoute des règles personnalisées
        engine.add_rule(ConvergenceRule())
        engine.add_rule(ContradictionRule())
        engine.add_rule(MyCustomRule())
        
        # Produit les hypothèses
        hypotheses = engine.infer_hypotheses(graph, min_confidence=0.6)
        
        # Triées par confiance décroissante
        for h in hypotheses:
            print(f"{h.label}: {h.confidence:.2f}")
    """

    def __init__(self) -> None:
        self._rules: List[InferenceRule] = []

    def add_rule(self, rule: InferenceRule) -> None:
        """
        Ajoute une règle d'inférence au moteur.
        
        Args:
            rule: instance d'InferenceRule
        """
        self._rules.append(rule)

    def infer_hypotheses(self, graph: KnowledgeGraph,
                         min_confidence: float = 0.5) -> List[Hypothesis]:
        """
        Produit des hypothèses à partir du graphe.
        
        Applique toutes les règles d'inférence enregistrées,
        puis fusionne et trie les résultats par confiance
        décroissante.
        
        Args:
            graph: graphe de connaissances à analyser
            min_confidence: seuil de confiance minimum
        
        Returns:
            Liste d'hypothèses triées par confiance décroissante
        """
        all_hypotheses: List[Hypothesis] = []

        for rule in self._rules:
            hypotheses = rule.infer(graph, min_confidence)
            all_hypotheses.extend(hypotheses)

        # Tri par confiance décroissante
        all_hypotheses.sort(reverse=True)

        return all_hypotheses

    def get_rules(self) -> List[InferenceRule]:
        """Retourne la liste des règles d'inférence enregistrées."""
        return list(self._rules)