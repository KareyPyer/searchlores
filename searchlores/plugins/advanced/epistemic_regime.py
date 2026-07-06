"""
Strate 12 — Régimes épistémiques.

Identifie et classifie les régimes de savoir mobilisés dans le texte
(neuro-scientifique, clinique, poétique, philosophique, éthique, technique,
statistique) et détecte leurs tensions : transitions brusques, hybridations,
conflits structurels (ex: objectivation vs subjectivation), exclusions
(ex: absence de régime éthique).

Algorithme heuristique (Pure Python) :
  1. Lexiques configurables par régime, avec poids par terme
  2. Segmentation en phrases
  3. Classification par scores (régime dominant + confiance)
  4. Détection des tensions (transition, hybridation, conflit, exclusion)

Origine : session de conception avec Qwen, testé sur le Prompt #12.
"""
from typing import List, Dict, Any
from pydantic import BaseModel, Field
import re
from enum import Enum

from .base import AdvancedPlugin


class EpistemicRegime(str, Enum):
    NEURO_SCIENTIFIC = "neuro-scientific"
    CLINICAL = "clinical"
    POETIC_AESTHETIC = "poetic-aesthetic"
    PHILOSOPHICAL = "philosophical"
    ETHICAL = "ethical"
    TECHNICAL = "technical"
    NARRATIVE = "narrative"
    STATISTICAL = "statistical"


class EpistemicSegment(BaseModel):
    segment: str = Field(..., description="Le segment de texte analysé")
    regime: EpistemicRegime = Field(..., description="Régime épistémique dominant")
    markers: List[str] = Field(default_factory=list, description="Marqueurs détectés")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Score de confiance")
    regime_scores: Dict[str, float] = Field(
        default_factory=dict, description="Scores pour tous les régimes détectés"
    )


class RegimeTension(BaseModel):
    description: str = Field(..., description="Description de la tension")
    regime_a: EpistemicRegime = Field(..., description="Premier régime")
    regime_b: EpistemicRegime = Field(..., description="Deuxième régime")
    tension_type: str = Field(..., description="Type de tension (transition, hybridation, conflit, exclusion)")


class EpistemicRegimeDetector(AdvancedPlugin):
    """
    Identifie et classifie les régimes de savoir mobilisés dans le texte.
    """

    name = "epistemic_regime"
    dependencies: List[str] = []

    def __init__(self):
        # Lexiques par régime avec poids (terme: poids). 1.0 = marqueur fort.
        self.regime_lexicons: Dict[EpistemicRegime, Dict[str, float]] = {
            EpistemicRegime.NEURO_SCIENTIFIC: {
                "connectome": 1.0, "neurone": 1.0, "cerveau": 0.9, "synapse": 1.0,
                "neurotransmetteur": 1.0, "cortex": 0.9, "imagerie": 0.8, "irm": 0.9,
                "eeg": 0.9, "données agrégées": 0.8, "émergence": 0.7, "réseau": 0.6,
                "biologique": 0.7, "cognitif": 0.7, "neuroscientifique": 1.0, "neuroscience": 1.0,
            },
            EpistemicRegime.CLINICAL: {
                "patient": 0.9, "thérapeute": 0.9, "psychanalyste": 1.0, "thérapeutique": 0.9,
                "protocole": 0.8, "diagnostic": 1.0, "symptôme": 0.9, "traitement": 0.8,
                "soin": 0.7, "clinique": 0.9, "pathologie": 0.9, "trouble": 0.8,
                "reconstruire": 0.7, "rétablir": 0.7, "guérir": 0.8,
            },
            EpistemicRegime.POETIC_AESTHETIC: {
                "poème": 1.0, "poésie": 1.0, "métaphore": 0.9, "image": 0.6, "lyrique": 0.9,
                "esthétique": 0.9, "beauté": 0.7, "sublime": 0.8, "rythme": 0.7, "vers": 0.8,
                "désir": 0.6, "rêve": 0.7, "émotion": 0.6, "sentiment": 0.6, "âme": 0.8,
            },
            EpistemicRegime.PHILOSOPHICAL: {
                "sujet": 0.8, "ontologie": 1.0, "ontologique": 1.0, "épistémologie": 1.0,
                "vérité": 0.8, "réalité": 0.7, "existence": 0.8, "être": 0.7, "conscience": 0.8,
                "phénoménologie": 1.0, "herméneutique": 1.0, "dialectique": 0.9, "paradoxe": 0.8,
                "aporie": 1.0, "je": 0.6, "moi": 0.6, "identité": 0.7, "fiction": 0.7, "narratif": 0.6,
            },
            EpistemicRegime.ETHICAL: {
                "éthique": 1.0, "moral": 0.9, "morale": 0.9, "devoir": 0.8, "responsabilité": 0.8,
                "légitime": 0.8, "légitimité": 0.9, "juste": 0.7, "injuste": 0.7, "bien": 0.5,
                "mal": 0.5, "consentement": 0.9, "autonomie": 0.8, "dignité": 0.9,
            },
            EpistemicRegime.TECHNICAL: {
                "algorithme": 1.0, "modèle": 0.7, "paramètre": 0.8, "données": 0.6, "calcul": 0.7,
                "système": 0.6, "interface": 0.7, "programme": 0.8, "code": 0.8, "logiciel": 0.9,
                "llm": 1.0, "ia": 0.9, "prompt": 0.9,
            },
            EpistemicRegime.STATISTICAL: {
                "statistique": 1.0, "probabilité": 0.9, "moyenne": 0.8, "écart-type": 1.0,
                "corrélation": 0.9, "régression": 0.9, "échantillon": 0.8, "agrégé": 0.7,
                "données agrégées": 0.9, "distribution": 0.8, "variance": 0.9,
            },
        }

    def analyze(self, text: str, context: Any = None) -> Dict[str, Any]:
        """Analyse le texte et retourne les régimes épistémiques et tensions."""
        segments = self._segment_text(text)
        epistemic_segments = self._classify_segments(segments)
        regime_tensions = self._detect_tensions(epistemic_segments)

        return {
            "epistemic_regimes": [seg.model_dump() for seg in epistemic_segments],
            "regime_tensions": [tension.model_dump() for tension in regime_tensions],
        }

    def _segment_text(self, text: str) -> List[str]:
        """Segmente le texte en phrases ou propositions."""
        sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _classify_segments(self, segments: List[str]) -> List[EpistemicSegment]:
        """Classifie chaque segment par régime épistémique."""
        classified = []

        for segment in segments:
            regime_scores = self._calculate_regime_scores(segment)
            if not regime_scores:
                continue

            dominant_regime = max(regime_scores, key=regime_scores.get)
            max_score = regime_scores[dominant_regime]

            total_score = sum(regime_scores.values())
            confidence = max_score / total_score if total_score > 0 else 0.0

            markers = self._extract_markers(segment, dominant_regime)

            classified.append(
                EpistemicSegment(
                    segment=segment, regime=dominant_regime, markers=markers,
                    confidence=round(confidence, 2),
                    regime_scores={k.value: round(v, 2) for k, v in regime_scores.items()},
                )
            )

        return classified

    def _calculate_regime_scores(self, segment: str) -> Dict[EpistemicRegime, float]:
        """Calcule les scores pour chaque régime dans un segment."""
        scores = {}
        segment_lower = segment.lower()

        for regime, lexicon in self.regime_lexicons.items():
            score = 0.0
            for term, weight in lexicon.items():
                count = min(segment_lower.count(term.lower()), 3)
                score += count * weight
            if score > 0:
                scores[regime] = score

        return scores

    def _extract_markers(self, segment: str, regime: EpistemicRegime) -> List[str]:
        """Extrait les marqueurs détectés pour le régime dominant."""
        markers = []
        segment_lower = segment.lower()

        if regime in self.regime_lexicons:
            for term in self.regime_lexicons[regime]:
                if term.lower() in segment_lower:
                    markers.append(term)

        return markers

    def _detect_tensions(self, segments: List[EpistemicSegment]) -> List[RegimeTension]:
        """Détecte les tensions entre régimes épistémiques."""
        tensions = []

        if len(segments) < 2:
            return tensions

        # Tension 1 : changements brusques de régime
        for i in range(len(segments) - 1):
            current = segments[i]
            next_seg = segments[i + 1]

            if current.regime != next_seg.regime:
                if current.confidence > 0.7 and next_seg.confidence > 0.7:
                    tensions.append(
                        RegimeTension(
                            description=f"Transition brusque entre le régime {current.regime.value} et {next_seg.regime.value}",
                            regime_a=current.regime, regime_b=next_seg.regime,
                            tension_type="transition",
                        )
                    )

        # Tension 2 : hybridation (segment qui mélange plusieurs régimes)
        for segment in segments:
            if segment.confidence < 0.6 and len(segment.regime_scores) > 1:
                sorted_regimes = sorted(
                    segment.regime_scores.items(), key=lambda x: x[1], reverse=True
                )
                if len(sorted_regimes) >= 2:
                    regime_a = EpistemicRegime(sorted_regimes[0][0])
                    regime_b = EpistemicRegime(sorted_regimes[1][0])
                    tensions.append(
                        RegimeTension(
                            description=f"Hybridation entre {regime_a.value} et {regime_b.value} dans: '{segment.segment[:50]}...'",
                            regime_a=regime_a, regime_b=regime_b,
                            tension_type="hybridation",
                        )
                    )

        # Tension 3 : conflits épistémiques structurels
        tensions.extend(self._detect_regime_conflicts(segments))

        return tensions

    def _detect_regime_conflicts(self, segments: List[EpistemicSegment]) -> List[RegimeTension]:
        """Détecte les conflits épistémiques structurels."""
        conflicts = []
        regimes_present = set(seg.regime for seg in segments)

        if EpistemicRegime.NEURO_SCIENTIFIC in regimes_present and EpistemicRegime.POETIC_AESTHETIC in regimes_present:
            conflicts.append(
                RegimeTension(
                    description="Tension entre le régime neuro-scientifique (objectivant) et le régime poétique (subjectivant)",
                    regime_a=EpistemicRegime.NEURO_SCIENTIFIC, regime_b=EpistemicRegime.POETIC_AESTHETIC,
                    tension_type="conflit",
                )
            )

        if EpistemicRegime.CLINICAL in regimes_present and EpistemicRegime.ETHICAL not in regimes_present:
            conflicts.append(
                RegimeTension(
                    description="Absence de régime éthique dans la proposition thérapeutique",
                    regime_a=EpistemicRegime.CLINICAL, regime_b=EpistemicRegime.ETHICAL,
                    tension_type="exclusion",
                )
            )

        if EpistemicRegime.STATISTICAL in regimes_present and EpistemicRegime.PHILOSOPHICAL in regimes_present:
            conflicts.append(
                RegimeTension(
                    description="Tension entre le régime statistique (réduction) et le régime philosophique (irréductibilité du sujet)",
                    regime_a=EpistemicRegime.STATISTICAL, regime_b=EpistemicRegime.PHILOSOPHICAL,
                    tension_type="conflit",
                )
            )

        return conflicts
