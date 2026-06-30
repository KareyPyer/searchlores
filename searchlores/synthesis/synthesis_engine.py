"""
Moteur de synthèse argumentée.

Le SynthesisEngine produit un résumé analytique structuré à partir
du Knowledge Graph et de son analyse structurelle.

Contrairement à une simple concaténation des résultats de plugins,
la synthèse est produite par analyse du graphe : elle identifie
les concepts dominants, les axes de pouvoir, les contradictions
majeures, les omissions détectées, et le niveau global de confiance.

La synthèse est entièrement explicable : chaque affirmation est
rattachée à des nœuds/relations du graphe avec leur provenance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from searchlores.graph.knowledge_graph import (
    KnowledgeGraph, Node, NodeType, RelationType,
)
from searchlores.reasoning.hypothesis import Hypothesis
from searchlores.synthesis.structural_analyzer import (
    StructuralAnalysis, StructuralAnalyzer,
)


@dataclass
class Synthesis:
    """
    Synthèse analytique complète produite par le moteur.
    
    Une synthèse n'est pas un simple résumé : c'est une analyse
    argumentée qui identifie :
      - les concepts dominants
      - les axes de pouvoir/influence
      - les contradictions majeures
      - les omissions détectées
      - la structure argumentative
      - le niveau global de confiance
    """
    summary: str                                    # résumé en langage naturel
    dominant_concepts: List[Dict[str, Any]]         # concepts les plus centraux
    power_axes: List[Dict[str, Any]]                # axes d'influence détectés
    major_contradictions: List[Dict[str, Any]]      # tensions principales
    detected_omissions: List[str]                   # ce qui manque
    argumentative_structure: List[Dict[str, Any]]   # prémisse → conclusion
    global_confidence: float                        # confiance globale
    coherence_score: float                          # cohérence du graphe
    hypotheses_summary: List[Dict[str, Any]]        # top hypothèses
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "dominant_concepts": self.dominant_concepts,
            "power_axes": self.power_axes,
            "major_contradictions": self.major_contradictions,
            "detected_omissions": self.detected_omissions,
            "argumentative_structure": self.argumentative_structure,
            "global_confidence": self.global_confidence,
            "coherence_score": self.coherence_score,
            "hypotheses_summary": self.hypotheses_summary,
            "metadata": self.metadata,
        }


class SynthesisEngine:
    """
    Produit une synthèse analytique argumentée à partir du graphe.
    
    La synthèse est construite en 6 étapes :
      1. Analyse structurelle du graphe
      2. Identification des concepts dominants
      3. Détection des axes de pouvoir
      4. Extraction des contradictions majeures
      5. Détection des omissions
      6. Production du résumé en langage naturel
    
    Usage :
    
        engine = SynthesisEngine()
        synthesis = engine.synthesize(graph, hypotheses)
        
        print(synthesis.summary)
        print(f"Confiance globale: {synthesis.global_confidence:.2f}")
    """

    def __init__(self) -> None:
        self._analyzer = StructuralAnalyzer()

    def synthesize(self, graph: KnowledgeGraph,
                   hypotheses: Optional[List[Hypothesis]] = None,
                   expected_topics: Optional[List[str]] = None) -> Synthesis:
        """
        Produit la synthèse complète.
        
        Args:
            graph: graphe de connaissances à synthétiser
            hypotheses: liste d'hypothèses inférées (optionnel)
            expected_topics: topics attendus pour détecter les omissions
        
        Returns:
            Synthesis complète et argumentée
        """
        # 1. Analyse structurelle
        analysis = self._analyzer.analyze(graph)

        # 2. Concepts dominants
        dominant_concepts = self._extract_dominant_concepts(analysis)

        # 3. Axes de pouvoir
        power_axes = self._extract_power_axes(graph, analysis)

        # 4. Contradictions majeures
        major_contradictions = self._extract_major_contradictions(graph)

        # 5. Omissions détectées
        detected_omissions = self._detect_omissions(
            graph, expected_topics or []
        )

        # 6. Structure argumentative
        argumentative_structure = self._format_argumentative_structure(analysis)

        # 7. Hypothèses (top 5)
        hypotheses_summary = self._summarize_hypotheses(hypotheses or [])

        # 8. Résumé en langage naturel
        summary = self._build_summary(
            analysis=analysis,
            dominant_concepts=dominant_concepts,
            power_axes=power_axes,
            major_contradictions=major_contradictions,
            detected_omissions=detected_omissions,
        )

        return Synthesis(
            summary=summary,
            dominant_concepts=dominant_concepts,
            power_axes=power_axes,
            major_contradictions=major_contradictions,
            detected_omissions=detected_omissions,
            argumentative_structure=argumentative_structure,
            global_confidence=analysis.global_confidence,
            coherence_score=analysis.coherence_score,
            hypotheses_summary=hypotheses_summary,
            metadata={
                "node_count": analysis.node_count,
                "edge_count": analysis.edge_count,
                "cluster_count": len(analysis.thematic_clusters),
            },
        )

    # ── Extracteurs ──────────────────────────────────────────
    def _extract_dominant_concepts(
        self, analysis: StructuralAnalysis
    ) -> List[Dict[str, Any]]:
        """Top concepts par centralité."""
        return [
            {
                "label": node.label,
                "type": node.node_type.value,
                "centrality": round(centrality, 4),
                "confidence": node.confidence,
                "evidence_count": len(node.evidences),
            }
            for node, centrality in analysis.dominant_concepts[:5]
        ]

    def _extract_power_axes(
        self, graph: KnowledgeGraph, analysis: StructuralAnalysis
    ) -> List[Dict[str, Any]]:
        """
        Axes de pouvoir = concepts-ponts entre clusters.
        
        Un concept-pont est un nœud qui connecte plusieurs clusters
        thématiques : il exerce une forme d'influence structurelle.
        """
        axes: List[Dict[str, Any]] = []
        
        for node, betweenness in analysis.bridge_concepts[:5]:
            # Identifie les clusters connectés
            connected_clusters: List[int] = []
            for idx, cluster in enumerate(analysis.thematic_clusters):
                cluster_ids = {n.id for n in cluster}
                # Vérifie si le nœud est adjacent à ce cluster
                relations = graph.get_relations(node.id)
                for rel in relations:
                    other_id = (rel.target_id if rel.source_id == node.id
                                else rel.source_id)
                    if other_id in cluster_ids:
                        connected_clusters.append(idx)
                        break
            
            axes.append({
                "label": node.label,
                "type": node.node_type.value,
                "betweenness": round(betweenness, 4),
                "connected_clusters": len(set(connected_clusters)),
                "influence_score": round(
                    betweenness * node.confidence, 4
                ),
            })
        
        return axes

    def _extract_major_contradictions(
        self, graph: KnowledgeGraph
    ) -> List[Dict[str, Any]]:
        """Contradictions les plus significatives."""
        pairs = graph.find_contradictions(min_confidence=0.4)
        
        results: List[Dict[str, Any]] = []
        for r1, r2 in pairs:
            source = graph.get_node(r1.source_id)
            target = graph.get_node(r1.target_id)
            if not (source and target):
                continue
            
            results.append({
                "source": source.label,
                "target": target.label,
                "support_confidence": r1.confidence,
                "contradict_confidence": r2.confidence,
                "tension_intensity": round(
                    min(r1.confidence, r2.confidence), 4
                ),
                "provenance": list({
                    e.source_plugin
                    for e in r1.evidences + r2.evidences
                }),
            })
        
        # Trie par intensité décroissante
        results.sort(key=lambda x: x["tension_intensity"], reverse=True)
        return results[:5]

    def _detect_omissions(
        self, graph: KnowledgeGraph, expected_topics: List[str]
    ) -> List[str]:
        """
        Détecte les topics attendus mais absents du graphe.
        
        Utile pour identifier les angles morts de l'analyse.
        """
        if not expected_topics:
            return []
        
        # Collecte tous les labels du graphe
        all_labels = {
            n.label.lower()
            for n in graph.find_nodes()
        }
        # Ajoute aussi les textes des preuves
        for node in graph.find_nodes():
            for evidence in node.evidences:
                all_labels.add(evidence.text.lower())
        
        ommissions: List[str] = []
        for topic in expected_topics:
            topic_lower = topic.lower()
            # Vérifie si le topic (ou une partie) est couvert
            covered = any(
                topic_lower in label or label in topic_lower
                for label in all_labels
            )
            if not covered:
                ommissions.append(topic)
        
        return ommissions

    def _format_argumentative_structure(
        self, analysis: StructuralAnalysis
    ) -> List[Dict[str, Any]]:
        """Formate la structure argumentative pour export."""
        return [
            {
                "premise": premise,
                "conclusion": conclusion,
            }
            for premise, conclusion in analysis.argumentative_structure
        ]

    def _summarize_hypotheses(
        self, hypotheses: List[Hypothesis]
    ) -> List[Dict[str, Any]]:
        """Top 5 hypothèses par confiance."""
        sorted_h = sorted(hypotheses, reverse=True)[:5]
        return [
            {
                "label": h.label,
                "statement": h.statement,
                "confidence": h.confidence,
                "provenance": h.provenance,
            }
            for h in sorted_h
        ]

    # ── Résumé en langage naturel ────────────────────────────
    def _build_summary(
        self,
        analysis: StructuralAnalysis,
        dominant_concepts: List[Dict[str, Any]],
        power_axes: List[Dict[str, Any]],
        major_contradictions: List[Dict[str, Any]],
        detected_omissions: List[str],
    ) -> str:
        """
        Construit le résumé en langage naturel.
        
        Le résumé est généré par templates à partir des métriques
        structurelles. Chaque phrase est traçable aux nœuds du graphe.
        """
        parts: List[str] = []

        # 1. Vue d'ensemble
        parts.append(
            f"Analyse portant sur {analysis.node_count} concepts "
            f"et {analysis.edge_count} relations. "
            f"Cohérence globale : {analysis.coherence_score:.2f}. "
            f"Confiance moyenne : {analysis.global_confidence:.2f}."
        )

        # 2. Concepts dominants
        if dominant_concepts:
            top_labels = ", ".join(
                f"« {c['label']} »" for c in dominant_concepts[:3]
            )
            parts.append(f"Concepts centraux identifiés : {top_labels}.")

        # 3. Axes de pouvoir
        if power_axes:
            axis_labels = ", ".join(
                f"« {a['label']} »" for a in power_axes[:2]
            )
            parts.append(
                f"Axes d'influence structurelle détectés : {axis_labels}."
            )

        # 4. Contradictions
        if major_contradictions:
            tensions = ", ".join(
                f"« {c['source']} » / « {c['target']} »"
                for c in major_contradictions[:2]
            )
            parts.append(f"Tensions majeures : {tensions}.")

        # 5. Omissions
        if detected_omissions:
            parts.append(
                f"Angles morts (topics attendus non couverts) : "
                f"{', '.join(detected_omissions[:3])}."
            )

        # 6. Clusters
        cluster_count = len(analysis.thematic_clusters)
        if cluster_count > 1:
            parts.append(
                f"L'analyse révèle {cluster_count} clusters thématiques "
                f"distincts, suggérant une structure fragmentée."
            )
        elif cluster_count == 1:
            parts.append(
                "L'analyse forme un cluster thématique cohérent."
            )

        return " ".join(parts)