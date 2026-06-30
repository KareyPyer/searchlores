"""
Knowledge Graph central de SearchLores v2.

Le graphe est le cœur du framework : toutes les observations,
inférences et synthèses s'y accumulent avec leur provenance
et leur niveau de confiance.

Ce module définit :
  - L'ontologie du graphe (types de nœuds et relations)
  - Les structures de données (Node, Relation, Evidence)
  - La classe KnowledgeGraph avec ses opérations
  - Les requêtes d'investigation (convergences, contradictions)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import networkx as nx


# ─────────────────────────────────────────────────────────────
# Ontologie du graphe
# ─────────────────────────────────────────────────────────────
class NodeType(str, Enum):
    """Types de nœuds du graphe de connaissances."""
    CONCEPT = "concept"
    ACTOR = "actor"
    INSTITUTION = "institution"
    AUTHOR = "author"
    SOURCE = "source"
    ARGUMENT = "argument"
    HYPOTHESIS = "hypothesis"
    EVENT = "event"
    OBSERVATION = "observation"   # nœud technique : trace d'un observer


class RelationType(str, Enum):
    """Types de relations entre nœuds."""
    SUPPORTS = "supporte"
    IMPLIES = "implique"
    CONTRADICTS = "contredit"
    DEPENDS_ON = "depend_de"
    CAUSES = "provoque"
    CITES = "cite"
    INFLUENCES = "influence"
    REINFORCES = "renforce"
    OBSERVED_BY = "observe_par"   # relation technique observation→observer


# ─────────────────────────────────────────────────────────────
# Structures de données
# ─────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Evidence:
    """
    Preuve élémentaire attachée à une relation ou un nœud.
    
    Une Evidence est immuable (frozen=True) pour garantir
    l'intégrité de la traçabilité.
    """
    text: str                              # citation ou extrait
    source_plugin: str                     # nom de l'observer
    source_span: Optional[Tuple[int, int]] = None  # (start, end) dans le texte
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Sérialisation pour export JSON."""
        return {
            "text": self.text,
            "source_plugin": self.source_plugin,
            "source_span": self.source_span,
            "timestamp": self.timestamp,
        }


@dataclass
class Node:
    """
    Représentation typée d'un nœud du graphe.
    
    Chaque nœud possède :
      - un ID unique (généré si vide)
      - un type (NodeType)
      - un label (texte affiché)
      - un niveau de confiance (0.0–1.0)
      - des métadonnées arbitraires
      - des preuves (Evidence)
    """
    id: str
    node_type: NodeType
    label: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    evidences: List[Evidence] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0,1], got {self.confidence}")

    def to_dict(self) -> Dict[str, Any]:
        """Sérialisation pour export JSON."""
        return {
            "id": self.id,
            "type": self.node_type.value,
            "label": self.label,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "evidences": [e.to_dict() for e in self.evidences],
        }


@dataclass
class Relation:
    """
    Arête typée avec provenance et confiance.
    
    Chaque relation conserve :
      - source et cible (IDs de nœuds)
      - type de relation (RelationType)
      - niveau de confiance (0.0–1.0)
      - preuves (Evidence)
      - métadonnées arbitraires
    """
    source_id: str
    target_id: str
    relation_type: RelationType
    confidence: float = 1.0
    evidences: List[Evidence] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0,1], got {self.confidence}")

    def to_dict(self) -> Dict[str, Any]:
        """Sérialisation pour export JSON."""
        return {
            "source": self.source_id,
            "target": self.target_id,
            "type": self.relation_type.value,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "evidences": [e.to_dict() for e in self.evidences],
        }


# ─────────────────────────────────────────────────────────────
# Knowledge Graph
# ─────────────────────────────────────────────────────────────
class KnowledgeGraph:
    """
    Graphe de connaissances dirigé, pondéré et annoté.
    
    Chaque nœud et chaque arête conserve :
      - son origine (plugin/observer)
      - son niveau de confiance
      - ses preuves (citations, spans)
    
    Le graphe est le cœur du framework : il est le seul état
    partagé entre observers, fusion, inférence et synthèse.
    
    Exemple d'utilisation :
    
        graph = KnowledgeGraph()
        
        # Ajouter un nœud
        node = Node(
            id="",
            node_type=NodeType.CONCEPT,
            label="autorité_institutionnelle",
            confidence=0.9,
            evidences=[Evidence(text="expert", source_plugin="authority_observer")]
        )
        node_id = graph.add_node(node)
        
        # Ajouter une relation
        relation = Relation(
            source_id=node_id,
            target_id=other_node_id,
            relation_type=RelationType.CITES,
            confidence=0.8
        )
        graph.add_relation(relation)
        
        # Requêtes
        convergences = graph.find_convergences(min_confidence=0.6)
        contradictions = graph.find_contradictions()
    """

    def __init__(self) -> None:
        self._g: nx.DiGraph = nx.DiGraph()
        self._node_index: Dict[str, Node] = {}       # id → Node
        self._label_index: Dict[Tuple[NodeType, str], str] = {}  # (type,label) → id

    # ── Nœuds ────────────────────────────────────────────────
    def add_node(self, node: Node, *, merge: bool = True) -> str:
        """
        Ajoute un nœud au graphe.
        
        Si un nœud de même (type, label) existe déjà et merge=True,
        les preuves et confiances sont fusionnées (probabiliste).
        
        Retourne l'ID du nœud (existant ou nouveau).
        """
        key = (node.node_type, node.label)
        existing_id = self._label_index.get(key)

        if existing_id and merge:
            # Fusion avec nœud existant
            existing = self._node_index[existing_id]
            existing.evidences.extend(node.evidences)
            # Confiance fusionnée : 1 - Π(1 - c_i) (probabiliste)
            combined = 1.0 - (1.0 - existing.confidence) * (1.0 - node.confidence)
            existing.confidence = min(combined, 1.0)
            existing.metadata.update(node.metadata)
            self._g.nodes[existing_id].update(existing.to_dict())
            return existing_id

        # Nouveau nœud
        new_id = node.id or f"{node.node_type.value}_{uuid4().hex[:8]}"
        node.id = new_id
        self._node_index[new_id] = node
        self._label_index[key] = new_id
        self._g.add_node(new_id, **node.to_dict())
        return new_id

    def get_node(self, node_id: str) -> Optional[Node]:
        """Récupère un nœud par son ID."""
        return self._node_index.get(node_id)

    def find_nodes(self, node_type: Optional[NodeType] = None,
                   label_contains: Optional[str] = None) -> List[Node]:
        """
        Recherche de nœuds avec filtres optionnels.
        
        Args:
            node_type: filtre par type de nœud
            label_contains: filtre par substring dans le label (case-insensitive)
        
        Returns:
            Liste de nœuds correspondant aux critères
        """
        nodes = list(self._node_index.values())
        if node_type is not None:
            nodes = [n for n in nodes if n.node_type == node_type]
        if label_contains:
            q = label_contains.lower()
            nodes = [n for n in nodes if q in n.label.lower()]
        return nodes

    # ── Arêtes ───────────────────────────────────────────────
    def add_relation(self, relation: Relation) -> None:
        """
        Ajoute une relation au graphe.
        
        Si une relation de même (source, target, type) existe déjà,
        les preuves et confiances sont fusionnées.
        
        Lève KeyError si source ou target n'existe pas dans le graphe.
        """
        if relation.source_id not in self._node_index:
            raise KeyError(f"Source node {relation.source_id!r} not in graph")
        if relation.target_id not in self._node_index:
            raise KeyError(f"Target node {relation.target_id!r} not in graph")

        # Clé d'arête unique par (src, tgt, type)
        key = (relation.source_id, relation.target_id, relation.relation_type.value)
        existing = self._g.get_edge_data(*key)
        
        if existing:
            # Fusion avec relation existante
            rel_obj: Relation = existing["relation"]
            rel_obj.evidences.extend(relation.evidences)
            combined = 1.0 - (1.0 - rel_obj.confidence) * (1.0 - relation.confidence)
            rel_obj.confidence = min(combined, 1.0)
            self._g.edges[key]["relation"] = rel_obj
            self._g.edges[key]["confidence"] = rel_obj.confidence
        else:
            # Nouvelle relation
            self._g.add_edge(
                relation.source_id,
                relation.target_id,
                key=relation.relation_type.value,
                relation=relation,
                confidence=relation.confidence,
                **relation.to_dict(),
            )

    def get_relations(self, node_id: Optional[str] = None,
                      relation_type: Optional[RelationType] = None) -> List[Relation]:
        """
        Récupère les relations avec filtres optionnels.
        
        Args:
            node_id: filtre par nœud (source ou cible)
            relation_type: filtre par type de relation
        
        Returns:
            Liste de relations correspondant aux critères
        """
        out: List[Relation] = []
        for u, v, data in self._g.edges(data=True):
            rel: Relation = data["relation"]
            if node_id and node_id not in (u, v):
                continue
            if relation_type and rel.relation_type != relation_type:
                continue
            out.append(rel)
        return out

    # ── Requêtes d'investigation ─────────────────────────────
    def find_convergences(self, min_confidence: float = 0.6,
                          min_in_degree: int = 2) -> List[Node]:
        """
        Détecte les nœuds soutenus par plusieurs sources indépendantes.
        
        Une convergence indique un concept fortement étayé par
        plusieurs observations ou plugins.
        
        Args:
            min_confidence: seuil de confiance minimum
            min_in_degree: nombre minimum de relations SUPPORTS entrantes
        
        Returns:
            Liste de nœuds convergents
        """
        results: List[Node] = []
        for node_id, node in self._node_index.items():
            if node.confidence < min_confidence:
                continue
            supporting = [
                r for r in self.get_relations(node_id, RelationType.SUPPORTS)
                if r.target_id == node_id
            ]
            if len(supporting) >= min_in_degree:
                results.append(node)
        return results

    def find_contradictions(self, min_confidence: float = 0.4) -> List[Tuple[Relation, Relation]]:
        """
        Détecte les paires d'arêtes contradictoires entre mêmes concepts.
        
        Une contradiction indique une tension entre deux observations
        ou hypothèses opposées.
        
        Args:
            min_confidence: seuil de confiance minimum
        
        Returns:
            Liste de paires (relation_support, relation_contradict)
        """
        pairs: List[Tuple[Relation, Relation]] = []
        for u, v, data in self._g.edges(data=True):
            r1: Relation = data["relation"]
            if r1.confidence < min_confidence:
                continue
            if r1.relation_type != RelationType.SUPPORTS:
                continue
            # Cherche une CONTRADICTS entre u et v
            for r2 in self.get_relations(u):
                if (r2.target_id == v
                        and r2.relation_type == RelationType.CONTRADICTS
                        and r2.confidence >= min_confidence):
                    pairs.append((r1, r2))
        return pairs

    def explain_node(self, node_id: str) -> Dict[str, Any]:
        """
        Retourne l'explication complète d'un nœud (traçabilité).
        
        Cette méthode est cruciale pour la GUI : elle permet
        d'afficher "Pourquoi cette conclusion ?" en montrant
        tous les plugins, observations et preuves impliqués.
        
        Args:
            node_id: ID du nœud à expliquer
        
        Returns:
            Dict avec node, supports, contradicts, implies, plugins_involved
        
        Raises:
            KeyError: si le nœud n'existe pas
        """
        node = self._node_index.get(node_id)
        if not node:
            raise KeyError(node_id)
        
        incoming = [r for r in self.get_relations(node_id) if r.target_id == node_id]
        outgoing = [r for r in self.get_relations(node_id) if r.source_id == node_id]
        
        return {
            "node": node.to_dict(),
            "supports": [r.to_dict() for r in incoming if r.relation_type == RelationType.SUPPORTS],
            "contradicts": [r.to_dict() for r in incoming if r.relation_type == RelationType.CONTRADICTS],
            "implies": [r.to_dict() for r in outgoing if r.relation_type == RelationType.IMPLIES],
            "plugins_involved": list({
                e.source_plugin
                for r in incoming + outgoing
                for e in r.evidences
            }),
        }

    # ── Exports ──────────────────────────────────────────────
    def to_networkx(self) -> nx.DiGraph:
        """Retourne une copie du graphe networkx sous-jacent."""
        return self._g.copy()

    def to_dict(self) -> Dict[str, Any]:
        """Sérialisation complète pour export JSON."""
        return {
            "nodes": [n.to_dict() for n in self._node_index.values()],
            "edges": [data["relation"].to_dict()
                      for _, _, data in self._g.edges(data=True)],
        }

    def __len__(self) -> int:
        """Nombre de nœuds dans le graphe."""
        return len(self._node_index)