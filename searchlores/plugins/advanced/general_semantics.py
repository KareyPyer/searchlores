"""
Strate 15 — Sémantique générale (hommage à A.E. Van Vogt / Alfred Korzybski).

Là où Fravia inspirait l'archéologie du prompt, ce plugin rend hommage au
"Monde des Non-A" : Gilbert Gosseyn n'a d'accès à son "extra-cerveau" qu'en
s'étant libéré des réflexes de la logique aristotélicienne à deux valeurs.
Ce plugin traque, dans le texte, les violations les plus classiques de la
Sémantique Générale de Korzybski — la discipline qui a directement inspiré
Van Vogt :

  - Identification        : confondre la carte et le territoire
                             ("le mot n'est pas la chose")
  - Allness                : totalisation illégitime ("tous", "toujours",
                             "jamais", "tout le monde")
  - Orientation à 2 valeurs : logique du tiers exclu, faux dilemme
  - Élémentalisme          : scinder verbalement ce qui est uni dans les
                             faits ("corps et esprit", "raison contre
                             émotion")
  - Absence d'indexation   : traiter tous les membres d'une classe comme
                             identiques (Smith_1 n'est pas Smith_2)
  - Réaction-signal        : réflexe sémantique non différé (emphase et
                             ponctuation compulsives, court-circuitant
                             l'évaluation)

Le plugin calcule aussi un **indice Non-A** (0 = discours pleinement
aristotélicien/absolutiste, 1 = discours nuancé, indexé, multi-valué) —
clin d'œil direct au roman.

Algorithme heuristique (Pure Python) : lexiques pondérés + regex, dans le
même esprit que les autres plugins avancés. Aucune dépendance lourde.
"""
from typing import List, Dict, Any, Tuple, Optional
from pydantic import BaseModel, Field
import re
from enum import Enum

from .base import AdvancedPlugin


class GSPrinciple(str, Enum):
    IDENTIFICATION = "identification (carte confondue avec le territoire)"
    ALLNESS = "allness (totalisation illégitime)"
    TWO_VALUED = "orientation à deux valeurs (logique aristotélicienne)"
    ELEMENTALISM = "élémentalisme (scission verbale d'un tout)"
    MISSING_INDEXING = "absence d'indexation (Smith1 ≠ Smith2)"
    SIGNAL_REACTION = "réaction-signal (réflexe sémantique non différé)"


class GSViolation(BaseModel):
    excerpt: str = Field(..., description="Extrait du texte concerné")
    principle: GSPrinciple = Field(..., description="Principe de sémantique générale violé")
    explanation: str = Field(..., description="Explication de la violation")
    korzybski_note: str = Field(..., description="Rappel du principe korzybskien concerné")
    severity: float = Field(..., ge=0.0, le=1.0)


class GeneralSemanticsProfile(BaseModel):
    violations: List[GSViolation] = Field(default_factory=list)
    null_a_index: float = Field(..., ge=0.0, le=1.0, description="1 = non-aristotélicien/nuancé, 0 = aristotélicien/absolu")
    dominant_principle: Optional[GSPrinciple] = Field(default=None)
    gosseyn_note: str = Field(..., description="Verdict façon 'entraînement non-A', pour le clin d'œil")


class GeneralSemanticsAnalyzer(AdvancedPlugin):
    """
    Détecte les violations des principes de la Sémantique Générale de
    Korzybski et calcule un indice Non-A du texte.
    """

    name = "general_semantics"
    dependencies: List[str] = []

    def __init__(self):
        # Allness : marqueurs de totalisation, avec poids
        self.allness_markers: List[Tuple[str, float]] = [
            (r"\btous\b", 0.5), (r"\btoutes\b", 0.5),
            (r"\btoujours\b", 0.6), (r"\bjamais\b", 0.6),
            (r"\baucun\b", 0.5), (r"\baucune\b", 0.5),
            (r"\bpersonne\s+ne\b", 0.6), (r"\btout\s+le\s+monde\b", 0.65),
            (r"\babsolument\b", 0.5), (r"\btotalement\b", 0.5),
            (r"\bsans\s+exception\b", 0.8), (r"\bchaque\s+fois\b", 0.5),
            (r"\bn['’]importe\s+quel\b", 0.4), (r"\buniversellement\b", 0.6),
            (r"\bpartout\b", 0.4), (r"\ben\s+tout\s+temps\b", 0.6),
        ]

        # Identification : verbe être + label évaluatif figé (confond
        # évaluation et description, fige l'objet dans une catégorie)
        self.evaluative_labels = [
            "un génie", "un idiot", "un imbécile", "un traître", "un lâche",
            "un héros", "un monstre", "un raciste", "un menteur", "un fou",
            "une folle", "une ordure", "un raté", "un loser", "un salaud",
            "stupide", "génial", "nul", "brillant", "pathétique",
            "méprisable", "admirable", "lamentable", "grotesque", "abject",
        ]
        self.identity_verb_pattern = re.compile(
            r"\b(est|sont|était|étaient|reste|restent)\s+(?:vraiment\s+|juste\s+|simplement\s+)?"
            r"(" + "|".join(re.escape(lbl) for lbl in self.evaluative_labels) + r")\b",
            re.IGNORECASE,
        )

        # Orientation à deux valeurs : faux dilemme, tiers exclu
        self.two_valued_patterns: List[Tuple[str, float]] = [
            (r"\bsoit\b.*\bsoit\b", 0.6),
            (r"\bou\s+bien\b.*\bou\s+bien\b", 0.6),
            (r"\bil\s+n['’]y\s+a\s+que\s+deux\b", 0.7),
            (r"\bavec\s+(nous|moi)\s+ou\s+contre\b", 0.8),
            (r"\bpas\s+de\s+(juste\s+)?milieu\b", 0.7),
            (r"\bc['’]est\s+(tout\s+)?(blanc\s+ou\s+(tout\s+)?noir)\b", 0.75),
            (r"\bsoit\s+vous\b.*\bsoit\b", 0.6),
        ]

        # Élémentalisme : paires de termes verbalement scindés que la
        # sémantique générale considère comme un tout non-élémentaliste
        self.elementalist_pairs: List[Tuple[str, str]] = [
            ("corps", "esprit"), ("raison", "émotion"), ("théorie", "pratique"),
            ("nature", "culture"), ("individu", "société"), ("forme", "fond"),
            ("objectif", "subjectif"), ("pensée", "action"), ("intellect", "instinct"),
        ]
        self.elementalist_connectors = r"(et|ou|contre|opposé[e]?\s+à|versus|vs\.?|face\s+à)"

        # Absence d'indexation : généralisation catégorielle sans nuance
        self.indexing_hedges = [
            "certains", "certaines", "quelques", "parfois", "souvent",
            "généralement", "en général", "la plupart", "beaucoup de",
            "dans certains cas", "typiquement",
        ]
        self.category_generalization_pattern = re.compile(
            r"\bles\s+(\w+s)\s+(sont|font|veulent|pensent|croient|agissent)\b",
            re.IGNORECASE,
        )

    def analyze(self, text: str, context: Any = None) -> Dict[str, Any]:
        """Analyse le texte et retourne le profil de sémantique générale."""
        sentences = self._split_sentences(text)

        violations: List[GSViolation] = []
        violations.extend(self._detect_allness(sentences))
        violations.extend(self._detect_identification(sentences))
        violations.extend(self._detect_two_valued(sentences))
        violations.extend(self._detect_elementalism(sentences))
        violations.extend(self._detect_missing_indexing(sentences))
        violations.extend(self._detect_signal_reaction(sentences))

        violations.sort(key=lambda v: v.severity, reverse=True)

        null_a_index = self._compute_null_a_index(violations, sentences)
        dominant = self._dominant_principle(violations)
        gosseyn_note = self._gosseyn_note(null_a_index, dominant)

        profile = GeneralSemanticsProfile(
            violations=violations, null_a_index=null_a_index,
            dominant_principle=dominant, gosseyn_note=gosseyn_note,
        )
        return profile.model_dump()

    # ---------------------------------------------------------- helpers

    def _split_sentences(self, text: str) -> List[str]:
        return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]

    def _detect_allness(self, sentences: List[str]) -> List[GSViolation]:
        found = []
        for sentence in sentences:
            for pattern, weight in self.allness_markers:
                m = re.search(pattern, sentence, re.IGNORECASE)
                if m:
                    found.append(GSViolation(
                        excerpt=sentence,
                        principle=GSPrinciple.ALLNESS,
                        explanation=(
                            f"Le marqueur '{m.group(0)}' totalise sans qualification — "
                            "Korzybski rappelle qu'aucune affirmation ne peut légitimement "
                            "couvrir 'tous les cas, en tout temps, sans exception'."
                        ),
                        korzybski_note="\"Whatever you say something is, it is not\" — et ce n'est jamais 'tout'.",
                        severity=weight,
                    ))
                    break  # une seule violation d'allness par phrase, la plus tôt trouvée
        return found

    def _detect_identification(self, sentences: List[str]) -> List[GSViolation]:
        found = []
        for sentence in sentences:
            m = self.identity_verb_pattern.search(sentence)
            if m:
                found.append(GSViolation(
                    excerpt=sentence,
                    principle=GSPrinciple.IDENTIFICATION,
                    explanation=(
                        f"Le 'est' d'identité ('{m.group(0)}') fige un jugement de valeur en "
                        "description d'essence, comme si l'étiquette était la chose elle-même."
                    ),
                    korzybski_note="\"The map is not the territory\" — l'étiquette n'épuise jamais l'objet.",
                    severity=0.65,
                ))
        return found

    def _detect_two_valued(self, sentences: List[str]) -> List[GSViolation]:
        found = []
        for sentence in sentences:
            for pattern, weight in self.two_valued_patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    found.append(GSViolation(
                        excerpt=sentence,
                        principle=GSPrinciple.TWO_VALUED,
                        explanation=(
                            "Le texte impose une logique du tiers exclu là où une "
                            "orientation multi-valuée (degrés, nuances, positions "
                            "intermédiaires) serait plus fidèle à la structure des faits."
                        ),
                        korzybski_note="La logique à deux valeurs ('A ou non-A, rien entre les deux') "
                                       "est précisément ce dont Gosseyn doit se libérer.",
                        severity=weight,
                    ))
                    break
        return found

    def _detect_elementalism(self, sentences: List[str]) -> List[GSViolation]:
        found = []
        for sentence in sentences:
            sentence_lower = sentence.lower()
            for term_a, term_b in self.elementalist_pairs:
                det = r"(?:l['’]|le\s+|la\s+|les\s+)?"
                pattern = rf"\b{re.escape(term_a)}\b\s*{self.elementalist_connectors}\s*{det}\b{re.escape(term_b)}\b"
                reverse_pattern = rf"\b{re.escape(term_b)}\b\s*{self.elementalist_connectors}\s*{det}\b{re.escape(term_a)}\b"
                if re.search(pattern, sentence_lower) or re.search(reverse_pattern, sentence_lower):
                    found.append(GSViolation(
                        excerpt=sentence,
                        principle=GSPrinciple.ELEMENTALISM,
                        explanation=(
                            f"'{term_a}' et '{term_b}' sont verbalement opposés ou séparés, "
                            "alors qu'ils constituent un processus unifié dans les faits — "
                            "la scission n'existe que dans le langage."
                        ),
                        korzybski_note="L'élémentalisme est la survivance verbale de dichotomies "
                                       "que la structure non-aristotélicienne du monde ne connaît pas.",
                        severity=0.55,
                    ))
        return found

    def _detect_missing_indexing(self, sentences: List[str]) -> List[GSViolation]:
        found = []
        for sentence in sentences:
            m = self.category_generalization_pattern.search(sentence)
            if m:
                sentence_lower = sentence.lower()
                has_hedge = any(hedge in sentence_lower for hedge in self.indexing_hedges)
                if not has_hedge:
                    found.append(GSViolation(
                        excerpt=sentence,
                        principle=GSPrinciple.MISSING_INDEXING,
                        explanation=(
                            f"'{m.group(0)}' traite les membres de la catégorie '{m.group(1)}' "
                            "comme interchangeables, sans indexation — Korzybski : "
                            "'Smith1 n'est pas Smith2', chaque instance diffère de la classe."
                        ),
                        korzybski_note="L'indexation (Smith1, Smith2, ...) est l'antidote structurel "
                                       "à la confusion entre une classe et ses membres.",
                        severity=0.5,
                    ))
        return found

    def _detect_signal_reaction(self, sentences: List[str]) -> List[GSViolation]:
        """Réflexe sémantique non différé : emphase/ponctuation compulsive
        (majuscules, points d'exclamation répétés) qui court-circuite
        l'évaluation au profit d'une réaction immédiate."""
        found = []
        for sentence in sentences:
            exclamations = sentence.count("!")
            words = re.findall(r"[A-Za-zÀ-ÿ]+", sentence)
            caps_words = [w for w in words if len(w) > 2 and w.isupper()]
            caps_ratio = len(caps_words) / len(words) if words else 0

            if exclamations >= 2 or caps_ratio > 0.3:
                found.append(GSViolation(
                    excerpt=sentence,
                    principle=GSPrinciple.SIGNAL_REACTION,
                    explanation=(
                        "L'emphase typographique (majuscules/exclamations répétées) signale "
                        "une réaction-signal — une réponse automatique et non différée — "
                        "plutôt qu'une réaction-symbole évaluée."
                    ),
                    korzybski_note="Le 'délai sémantique' (semantic delay/pause) est ce qui "
                                   "distingue la réaction-symbole humaine de la réaction-signal animale.",
                    severity=min(0.3 + 0.15 * exclamations, 0.9),
                ))
        return found

    def _compute_null_a_index(self, violations: List[GSViolation], sentences: List[str]) -> float:
        """
        Indice Non-A : 1.0 = discours nuancé/indexé/multi-valué (l'idéal
        non-aristotélicien de Korzybski/Van Vogt), 0.0 = discours
        pleinement absolutiste/à deux valeurs.
        """
        if not sentences:
            return 1.0
        total_severity = sum(v.severity for v in violations)
        density = total_severity / len(sentences)
        return round(max(0.0, min(1.0, 1.0 - density)), 2)

    def _dominant_principle(self, violations: List[GSViolation]) -> Optional[GSPrinciple]:
        if not violations:
            return None
        counts: Dict[GSPrinciple, float] = {}
        for v in violations:
            counts[v.principle] = counts.get(v.principle, 0.0) + v.severity
        return max(counts, key=counts.get)

    def _gosseyn_note(self, null_a_index: float, dominant: Optional[GSPrinciple]) -> str:
        if null_a_index >= 0.85:
            return (
                "Entraînement non-A réussi : ce discours résiste à l'identification, "
                "indexe ses affirmations et laisse place au degré. Gosseyn approuverait."
            )
        if null_a_index >= 0.6:
            return (
                "Cortex thalamique encore partiellement aristotélicien : quelques réflexes "
                "de langage à deux valeurs subsistent, mais le texte garde des nuances."
            )
        if null_a_index >= 0.35:
            return (
                f"Réactions-signal fréquentes (dominante : {dominant.value if dominant else 'diffuse'}) — "
                "ce discours n'a pas encore franchi le seuil de l'entraînement non-aristotélicien."
            )
        return (
            "Orientation aristotélicienne massive : allness, identification et logique à deux "
            "valeurs saturent le texte. Loin, très loin, de l'Institut de Sémantique Générale."
        )
