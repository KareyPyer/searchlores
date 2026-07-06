"""
Strate 10 — Contradictions performatives.

Détecte les énoncés qui contredisent leurs propres conditions d'énonciation
(ex: "le langage est inadéquat" énoncé... en langage ; "le 'je' est une
fiction" suivi d'un acte qui présuppose ce même 'je').

Algorithme heuristique (Pure Python, sans dépendance lourde) :
  1. Segmentation en phrases
  2. Détection des marqueurs de négation/déni (ce qui est nié)
  3. Détection des marqueurs performatifs (l'acte qui présuppose ce qui
     vient d'être nié)
  4. Croisement : toute paire (négation, performatif) dans des phrases
     différentes est une contradiction performative candidate

Origine : conçu lors d'une session de conception avec Qwen ("Archéologie
des pouvoirs discursifs"), testé sur le Prompt #12 (psychanalyste-LLM).
"""
from typing import List, Dict, Any, Tuple
from pydantic import BaseModel, Field
import re

from .base import AdvancedPlugin


class PerformativeContradiction(BaseModel):
    statement: str = Field(..., description="Énoncé qui nie/déconstruit quelque chose")
    contradicts_with: str = Field(..., description="Acte performatif qui présuppose ce qui a été nié")
    type: str = Field(..., description="Type de contradiction (négation_vs_performatif)")
    severity: float = Field(..., ge=0.0, le=1.0, description="Score de sévérité")


class PerformativeContradictionDetector(AdvancedPlugin):
    """
    Détecte les énoncés qui contredisent leurs propres conditions
    d'énonciation.
    """

    name = "performative_contradiction"
    dependencies: List[str] = []

    def __init__(self):
        # Marqueurs de négation (le contenu sémantique qui nie)
        # Format : (regex, type_de_négation, score_de_base)
        self.negation_patterns: List[Tuple[str, str, float]] = [
            (r"\ble\s+'je'\s+est\s+(une\s+)?fiction", "denial_of_subject", 0.9),
            (r"\ble\s+langage\s+est\s+inadéquat", "denial_of_medium", 0.95),
            (r"\bl'identité\s+n'est\s+(qu'|pas\s+)?une\s+illusion", "denial_of_subject", 0.85),
            (r"\btoute\s+vérité\s+est\s+relative", "self_refuting_absolute", 0.8),
            (r"\bil\s+est\s+impossible\s+de\s+(dire|exprimer|représenter)", "denial_of_representation", 0.9),
            (r"\best\s+(une\s+)?(simple\s+)?(fiction|illusion|construction)\b", "denial_of_subject", 0.75),
            (r"\bn'est\s+(qu'|pas\s+)?", "generic_denial", 0.5),
        ]

        # Marqueurs performatifs (l'acte de parole qui contredit la négation)
        self.performative_patterns: List[Tuple[str, str, float]] = [
            (r"\bnous\s+allons\s+reconstruire\s+(votre|ton)\s+(récit|histoire|vécu)", "prescriptive_reconstruction", 0.9),
            (r"\bje\s+vais\s+vous\s+aider\s+à\s+trouver\s+votre\s+vrai\s+(moi|soi)", "therapeutic_prescription", 0.85),
            (r"\banalysons\s+(votre|ton)\s+", "analytical_prescription", 0.7),
            (r"\b(ce|mon)\s+(prompt|discours|texte|analyse)\s+(va|vise|cherche)\s+à", "meta_discursive_act", 0.75),
            (r"\bnous\s+allons\s+\w+", "generic_prescription", 0.5),
            (r"\bje\s+vais\s+\w+", "generic_prescription", 0.5),
        ]

    def analyze(self, text: str, context: Any = None) -> Dict[str, Any]:
        """Analyse le texte et retourne les contradictions performatives détectées."""
        contradictions: List[PerformativeContradiction] = []
        sentences = self._split_sentences(text)

        negations_found = self._extract_patterns(sentences, self.negation_patterns)
        performatives_found = self._extract_patterns(sentences, self.performative_patterns)

        seen_pairs = set()
        for neg in negations_found:
            for perf in performatives_found:
                # Une contradiction performative émerge si le performatif présuppose
                # ce que la négation vient de détruire, dans une phrase différente.
                if neg["sentence"] != perf["sentence"]:
                    pair_key = (neg["sentence"], perf["sentence"])
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)

                    severity = (neg["score"] + perf["score"]) / 2

                    contradictions.append(
                        PerformativeContradiction(
                            statement=neg["sentence"],
                            contradicts_with=perf["sentence"],
                            type=f"{neg['type']}_vs_{perf['type']}",
                            severity=round(severity, 2),
                        )
                    )

        return {"performative_contradictions": [c.model_dump() for c in contradictions]}

    def _split_sentences(self, text: str) -> List[str]:
        """Segmentation simple mais robuste du texte."""
        return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]

    def _extract_patterns(
        self, sentences: List[str], patterns: List[Tuple[str, str, float]]
    ) -> List[Dict[str, Any]]:
        """Extrait les occurrences des motifs dans les phrases (une seule fois par phrase/pattern)."""
        found = []
        for sentence in sentences:
            for pattern, p_type, score in patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    found.append({"sentence": sentence, "type": p_type, "score": score})
        return found
