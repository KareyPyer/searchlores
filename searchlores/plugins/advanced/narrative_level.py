"""
Strate 11 — Niveaux narratifs enchâssés.

Distingue les niveaux d'enchâssement narratif (diégèse, métadiégèse) et
cartographie les tensions entre les voix : contradictions entre narrateur
et personnage, silences narratifs (voix attendue mais absente), ruptures
de niveau.

Algorithme heuristique (Pure Python) :
  1. Segmentation par marqueurs de discours (guillemets, tirets)
  2. Attribution d'un niveau à chaque segment (0 = narrateur externe,
     1+ = discours enchâssé)
  3. Détection des tensions (contradiction, silence, rupture)

Origine : session de conception avec Qwen, testé sur le Prompt #12.
"""
from typing import List, Dict, Any
from pydantic import BaseModel, Field
import re
from enum import Enum

from .base import AdvancedPlugin


class VoiceType(str, Enum):
    """Types de voix narratives possibles."""
    EXTERNAL_NARRATOR = "narrateur externe"
    CHARACTER_SPEECH = "discours de personnage"
    QUOTED_SPEECH = "discours cité"
    INTERNAL_MONOLOGUE = "monologue intérieur"
    META_NARRATOR = "méta-narrateur"


class NarrativeLevel(BaseModel):
    level: int = Field(..., ge=0, description="Niveau d'enchâssement (0 = externe)")
    voice: VoiceType = Field(..., description="Type de voix qui s'exprime")
    content: str = Field(..., description="Contenu du segment narratif")
    start_pos: int = Field(..., description="Position de début dans le texte")
    end_pos: int = Field(..., description="Position de fin dans le texte")


class NarrativeTension(BaseModel):
    description: str = Field(..., description="Description de la tension")
    level_a: int = Field(..., description="Premier niveau impliqué")
    level_b: int = Field(..., description="Deuxième niveau impliqué")
    tension_type: str = Field(..., description="Type de tension (contradiction, silence, rupture)")


class NarrativeLevelAnalyzer(AdvancedPlugin):
    """
    Distingue les niveaux d'enchâssement narratif et cartographie les
    tensions entre les voix.
    """

    name = "narrative_level"
    dependencies: List[str] = []

    def __init__(self):
        # Verbes introducteurs de discours (français et anglais)
        self.speech_verbs = [
            "dit", "affirme", "déclare", "explique", "répond", "écrit", "pense",
            "says", "states", "declares", "explains", "responds", "writes", "thinks",
            "soutient", "prétend", "confesse", "avoue",
        ]

        # Patterns pour détecter les enchâssements
        self.quote_pattern = re.compile(r'["«»“”]([^"«»“”]*)["«»“”]', re.UNICODE)
        self.dialogue_pattern = re.compile(r"^[-–—]\s*(.+)$", re.MULTILINE)

    def analyze(self, text: str, context: Any = None) -> Dict[str, Any]:
        """Analyse le texte et retourne les niveaux narratifs et tensions."""
        segments = self._segment_text(text)
        narrative_levels = self._assign_levels(segments)
        narrative_tensions = self._detect_tensions(narrative_levels)

        return {
            "narrative_levels": [level.model_dump() for level in narrative_levels],
            "narrative_tensions": [tension.model_dump() for tension in narrative_tensions],
        }

    def _segment_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Segmente le texte en unités narratives basées sur les marqueurs.
        Retourne une liste de segments avec leur position et type.
        """
        segments = []

        quote_matches = list(self.quote_pattern.finditer(text))
        dialogue_matches = list(self.dialogue_pattern.finditer(text))

        all_matches = []
        for match in quote_matches:
            all_matches.append({
                "start": match.start(), "end": match.end(),
                "type": "quote", "content": match.group(1),
            })
        for match in dialogue_matches:
            all_matches.append({
                "start": match.start(), "end": match.end(),
                "type": "dialogue", "content": match.group(1),
            })

        all_matches.sort(key=lambda x: x["start"])

        current_pos = 0
        for match in all_matches:
            if match["start"] > current_pos:
                external_text = text[current_pos:match["start"]].strip()
                if external_text:
                    segments.append({
                        "start": current_pos, "end": match["start"],
                        "type": "external", "content": external_text,
                    })

            segments.append({
                "start": match["start"], "end": match["end"],
                "type": match["type"], "content": match["content"],
            })
            current_pos = match["end"]

        if current_pos < len(text):
            external_text = text[current_pos:].strip()
            if external_text:
                segments.append({
                    "start": current_pos, "end": len(text),
                    "type": "external", "content": external_text,
                })

        return segments

    def _assign_levels(self, segments: List[Dict[str, Any]]) -> List[NarrativeLevel]:
        """Attribue un niveau narratif à chaque segment."""
        narrative_levels = []

        for segment in segments:
            if segment["type"] == "external":
                voice = VoiceType.EXTERNAL_NARRATOR
                level = 0
            elif segment["type"] == "quote":
                level = self._count_nesting_depth(segment["content"])
                voice = VoiceType.CHARACTER_SPEECH if level == 1 else VoiceType.QUOTED_SPEECH
            elif segment["type"] == "dialogue":
                voice = VoiceType.CHARACTER_SPEECH
                level = 1
            else:
                voice = VoiceType.EXTERNAL_NARRATOR
                level = 0

            narrative_levels.append(
                NarrativeLevel(
                    level=level, voice=voice, content=segment["content"],
                    start_pos=segment["start"], end_pos=segment["end"],
                )
            )

        return narrative_levels

    def _count_nesting_depth(self, text: str) -> int:
        """Compte la profondeur d'enchâssement des guillemets."""
        quote_count = text.count('"') + text.count("«") + text.count("»")
        return (quote_count // 2) + 1

    def _detect_tensions(self, levels: List[NarrativeLevel]) -> List[NarrativeTension]:
        """Détecte les tensions narratives entre les niveaux."""
        tensions = []

        external_levels = [l for l in levels if l.level == 0]
        character_levels = [l for l in levels if l.level == 1]

        if external_levels and character_levels:
            for ext in external_levels:
                for char in character_levels:
                    if self._detect_contradiction(ext.content, char.content):
                        tensions.append(
                            NarrativeTension(
                                description=(
                                    f"Conflit entre le récit externe ('{ext.content[:50]}...') "
                                    f"et la parole du personnage ('{char.content[:50]}...')"
                                ),
                                level_a=ext.level, level_b=char.level,
                                tension_type="contradiction",
                            )
                        )

        if self._detect_narrative_silence(levels):
            tensions.append(
                NarrativeTension(
                    description="Absence de représentation directe du désir ou de la parole du sujet principal",
                    level_a=0, level_b=1, tension_type="silence",
                )
            )

        for i in range(len(levels) - 1):
            if abs(levels[i].level - levels[i + 1].level) > 1:
                tensions.append(
                    NarrativeTension(
                        description=(
                            f"Rupture de niveau entre '{levels[i].content[:30]}...' "
                            f"et '{levels[i+1].content[:30]}...'"
                        ),
                        level_a=levels[i].level, level_b=levels[i + 1].level,
                        tension_type="rupture",
                    )
                )

        return tensions

    def _detect_contradiction(self, text1: str, text2: str) -> bool:
        """Détecte si deux textes se contredisent (heuristique simple)."""
        negation_words = ["pas", "non", "aucun", "jamais", "impossible", "fiction", "illusion"]
        affirmation_words = ["vrai", "réel", "existe", "vérité", "authentique"]

        text1_lower = text1.lower()
        text2_lower = text2.lower()

        has_negation = any(word in text1_lower for word in negation_words) or \
                       any(word in text2_lower for word in negation_words)
        has_affirmation = any(word in text1_lower for word in affirmation_words) or \
                          any(word in text2_lower for word in affirmation_words)

        return has_negation and has_affirmation

    def _detect_narrative_silence(self, levels: List[NarrativeLevel]) -> bool:
        """Détecte les silences narratifs (voix absentes mais attendues)."""
        all_text = " ".join([l.content for l in levels])
        all_text_lower = all_text.lower()

        has_patient_mention = any(word in all_text_lower for word in ["patient", "sujet", "client"])
        has_patient_speech = any(l.level > 0 and "patient" in l.content.lower() for l in levels)

        return has_patient_mention and not has_patient_speech
