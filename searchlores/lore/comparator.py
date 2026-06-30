"""
Comparateur multi-Lore.

Le MultiLoreComparator exécute le pipeline d'investigation complet
sur le même texte avec plusieurs LoreFrames, puis compare les
résultats pour identifier :
  - les hypothèses communes à toutes les Lores
  - les hypothèses spécifiques à chaque Lore
  - les divergences de confiance
  - un rapport comparatif structuré

C'est l'outil central de l'investigation multi-perspective.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from searchlores.core.context import InvestigationContext
from searchlores.graph.knowledge_graph import KnowledgeGraph
from searchlores.lore.frame import LoreFrame
from searchlores.reasoning.hypothesis import Hypothesis
from searchlores.synthesis.synthesis_engine import Synthesis, SynthesisEngine


@dataclass
class LoreResult:
    """Résultat d'une investigation avec une LoreFrame spécifique."""
    lore: LoreFrame
    graph: KnowledgeGraph
    hypotheses: List[Hypothesis]
    synthesis: Synthesis
    context: InvestigationContext

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lore": self.lore.to_dict(),
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "synthesis": self.synthesis.to_dict(),
            "graph_stats": {
                "nodes": len(self.graph),
                "relations": len(self.graph.get_relations()),
            },
        }


@dataclass
class LoreComparison:
    """
    Résultat de la comparaison multi-Lore.
    
    Identifie :
      - common_hypotheses : hypothèses présentes dans toutes les Lores
      - divergent_hypotheses : hypothèses spécifiques à certaines Lores
      - confidence_divergences : écarts de confiance entre Lores
      - comparative_summary : résumé comparatif
    """
    results: List[LoreResult]
    common_hypotheses: List[Dict[str, Any]] = field(default_factory=list)
    divergent_hypotheses: List[Dict[str, Any]] = field(default_factory=list)
    confidence_divergences: List[Dict[str, Any]] = field(default_factory=list)
    comparative_summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "results": [r.to_dict() for r in self.results],
            "common_hypotheses": self.common_hypotheses,
            "divergent_hypotheses": self.divergent_hypotheses,
            "confidence_divergences": self.confidence_divergences,
            "comparative_summary": self.comparative_summary,
            "metadata": self.metadata,
        }


class MultiLoreComparator:
    """
    Compare les résultats de plusieurs LoreFrames sur un même texte.
    
    Usage :
    
        comparator = MultiLoreComparator(engine)
        
        lores = [
            LoreFrame.default(),
            LoreFrame.skeptic(),
            LoreFrame.institutional_critical(),
        ]
        
        comparison = comparator.compare(text, lores)
        
        print(comparison.comparative_summary)
        for div in comparison.confidence_divergences:
            print(f"{div['hypothesis']}: {div['divergence']:.2f}")
    """

    def __init__(self, engine) -> None:
        """
        Args:
            engine: InvestigationEngine utilisé pour exécuter chaque Lore
        """
        self._engine = engine
        self._synthesis_engine = SynthesisEngine()

    def compare(self, text: str, lores: List[LoreFrame],
                expected_topics: Optional[List[str]] = None) -> LoreComparison:
        """
        Exécute l'investigation avec chaque Lore et compare les résultats.
        
        Args:
            text: texte à analyser
            lores: liste de LoreFrames à comparer
            expected_topics: topics attendus (optionnel)
        
        Returns:
            LoreComparison avec analyse comparative
        """
        results: List[LoreResult] = []

        for lore in lores:
            result = self._run_with_lore(text, lore, expected_topics)
            results.append(result)

        # Analyse comparative
        common = self._find_common_hypotheses(results)
        divergent = self._find_divergent_hypotheses(results)
        divergences = self._compute_confidence_divergences(results)
        summary = self._build_comparative_summary(results, common, divergent)

        return LoreComparison(
            results=results,
            common_hypotheses=common,
            divergent_hypotheses=divergent,
            confidence_divergences=divergences,
            comparative_summary=summary,
            metadata={
                "lore_count": len(lores),
                "text_length": len(text),
            },
        )

    def _run_with_lore(self, text: str, lore: LoreFrame,
                       expected_topics: Optional[List[str]]) -> LoreResult:
        """Exécute l'investigation complète avec une LoreFrame."""
        # Crée un graphe isolé pour cette Lore
        graph = KnowledgeGraph()
        context = InvestigationContext(prompt=text)

        # Exécute le moteur (avec application des filtres Lore)
        self._engine.run_with_lore(text, graph, context, lore)

        # Produit la synthèse
        topics = expected_topics or lore.expected_topics
        synthesis = self._synthesis_engine.synthesize(
            graph,
            hypotheses=context.hypotheses,
            expected_topics=topics,
        )

        return LoreResult(
            lore=lore,
            graph=graph,
            hypotheses=list(context.hypotheses),
            synthesis=synthesis,
            context=context,
        )

    def _find_common_hypotheses(
        self, results: List[LoreResult]
    ) -> List[Dict[str, Any]]:
        """Hypothèses présentes dans toutes les Lores."""
        if not results:
            return []
        
        # Labels par Lore
        labels_per_lore: List[Set[str]] = [
            {h.label for h in r.hypotheses}
            for r in results
        ]
        
        # Intersection
        common_labels: Set[str] = labels_per_lore[0]
        for labels in labels_per_lore[1:]:
            common_labels &= labels
        
        if not common_labels:
            return []
        
        # Construit le résultat avec confiances moyennes
        common: List[Dict[str, Any]] = []
        for label in common_labels:
            confidences = []
            statement = ""
            for result in results:
                for h in result.hypotheses:
                    if h.label == label:
                        confidences.append(h.confidence)
                        if not statement:
                            statement = h.statement
            
            common.append({
                "label": label,
                "statement": statement,
                "avg_confidence": sum(confidences) / len(confidences),
                "min_confidence": min(confidences),
                "max_confidence": max(confidences),
                "present_in_all": True,
            })
        
        common.sort(key=lambda x: x["avg_confidence"], reverse=True)
        return common

    def _find_divergent_hypotheses(
        self, results: List[LoreResult]
    ) -> List[Dict[str, Any]]:
        """Hypothèses spécifiques à certaines Lores."""
        if not results:
            return []
        
        # Toutes les labels
        all_labels: Set[str] = set()
        for result in results:
            all_labels.update(h.label for h in result.hypotheses)
        
        # Labels communes
        common_labels = {h["label"] for h in self._find_common_hypotheses(results)}
        
        # Labels divergentes = toutes - communes
        divergent_labels = all_labels - common_labels
        
        divergent: List[Dict[str, Any]] = []
        for label in divergent_labels:
            present_in: List[str] = []
            statement = ""
            confidence = 0.0
            
            for result in results:
                for h in result.hypotheses:
                    if h.label == label:
                        present_in.append(result.lore.name)
                        if not statement:
                            statement = h.statement
                            confidence = h.confidence
            
            divergent.append({
                "label": label,
                "statement": statement,
                "confidence": confidence,
                "present_in": present_in,
            })
        
        divergent.sort(key=lambda x: x["confidence"], reverse=True)
        return divergent

    def _compute_confidence_divergences(
        self, results: List[LoreResult]
    ) -> List[Dict[str, Any]]:
        """Écarts de confiance pour les hypothèses communes."""
        common = self._find_common_hypotheses(results)
        
        divergences: List[Dict[str, Any]] = []
        for h in common:
            divergence = h["max_confidence"] - h["min_confidence"]
            if divergence > 0.1:  # seuil significatif
                divergences.append({
                    "hypothesis": h["label"],
                    "statement": h["statement"],
                    "divergence": round(divergence, 4),
                    "min_confidence": h["min_confidence"],
                    "max_confidence": h["max_confidence"],
                    "avg_confidence": h["avg_confidence"],
                })
        
        divergences.sort(key=lambda x: x["divergence"], reverse=True)
        return divergences

    def _build_comparative_summary(
        self,
        results: List[LoreResult],
        common: List[Dict[str, Any]],
        divergent: List[Dict[str, Any]],
    ) -> str:
        """Construit le résumé comparatif en langage naturel."""
        if not results:
            return "Aucune Lore à comparer."
        
        parts: List[str] = []
        
        # 1. Vue d'ensemble
        lore_names = ", ".join(f"« {r.lore.name} »" for r in results)
        parts.append(
            f"Comparaison de {len(results)} cadres interprétatifs : {lore_names}."
        )
        
        # 2. Hypothèses communes
        if common:
            parts.append(
                f"{len(common)} hypothèse(s) commune(s) à tous les cadres, "
                f"indiquant des points de convergence robustes."
            )
            top_common = common[0]
            parts.append(
                f"La plus solide : « {top_common['label']} » "
                f"(confiance moyenne {top_common['avg_confidence']:.2f})."
            )
        else:
            parts.append(
                "Aucune hypothèse commune : les cadres produisent "
                "des analyses radicalement différentes."
            )
        
        # 3. Hypothèses divergentes
        if divergent:
            parts.append(
                f"{len(divergent)} hypothèse(s) spécifique(s) à certains cadres, "
                f"révélant des angles d'analyse distincts."
            )
        
        # 4. Divergences de confiance
        divergences = self._compute_confidence_divergences(results)
        if divergences:
            top_div = divergences[0]
            parts.append(
                f"Divergence maximale sur « {top_div['hypothesis']} » : "
                f"écart de {top_div['divergence']:.2f} entre les cadres."
            )
        
        return " ".join(parts)