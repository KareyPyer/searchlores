"""
Strate 14 — Silences et rapports de pouvoir (perspective foucaldienne).

Le plugin le plus ambitieux : il cartographie les silences structurels
(ce qui n'est pas dit), les régimes de vérité (ce qui est accepté vs
structurellement exclu), les positions de sujet et leurs résistances, les
conditions de possibilité du discours, et produit une synthèse
généalogique en croisant les résultats des 4 autres plugins avancés.

Algorithme heuristique (Pure Python) :
  1. Détection des silences (champs sémantiques attendus mais absents)
  2. Cartographie des régimes de vérité (accepté vs exclu)
  3. Analyse des positions de sujet
  4. Identification des conditions de possibilité
  5. Synthèse généalogique croisant les résultats précédents (si fournis
     via `context`/`previous_results`)

Origine : session de conception avec Qwen ("Archéologie des pouvoirs
discursifs"), testé sur le Prompt #12 (psychanalyste-LLM).

Dépendances : ce plugin déclare `dependencies` sur les 4 autres plugins
avancés afin que l'orchestrateur DAG (voir core/orchestrator.py) les
exécute en premier ; leurs résultats lui sont alors accessibles via le
paramètre `context` de `analyze()`.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import re
from enum import Enum

from .base import AdvancedPlugin


class SilenceDomain(str, Enum):
    CORPOREAL = "corporel"
    ETHICAL = "éthique"
    HISTORICAL = "historique"
    SOCIAL = "social"
    POLITICAL = "politique"
    AFFECTIVE = "affectif"
    MATERIAL = "matériel"
    TEMPORAL = "temporel"
    RELATIONAL = "relationnel"


class RegimeOfTruth(BaseModel):
    regime: str = Field(..., description="Nom du régime de vérité")
    statements_accepted: List[str] = Field(default_factory=list)
    statements_excluded: List[str] = Field(default_factory=list)
    conditions_of_possibility: List[str] = Field(default_factory=list)


class Silence(BaseModel):
    domain: SilenceDomain = Field(..., description="Domaine du silence")
    content: str = Field(..., description="Ce qui n'est pas dit")
    reason: str = Field(..., description="Pourquoi c'est tu")
    severity: float = Field(..., ge=0.0, le=1.0)


class SubjectPosition(BaseModel):
    position: str
    subjectification: str
    resistance: Optional[str] = None
    power_relations: List[str] = Field(default_factory=list)


class FoucaultAnalysis(BaseModel):
    silences: List[Silence] = Field(default_factory=list)
    regimes_of_truth: List[RegimeOfTruth] = Field(default_factory=list)
    subject_positions: List[SubjectPosition] = Field(default_factory=list)
    conditions_of_possibility: List[str] = Field(default_factory=list)
    genealogical_insights: List[str] = Field(default_factory=list)


class FoucaultAnalyzer(AdvancedPlugin):
    """
    Cartographie les silences et les rapports de pouvoir dans une
    perspective foucaldienne, en synthétisant les résultats des 4 autres
    plugins avancés.
    """

    name = "foucault_analyzer"
    dependencies: List[str] = [
        "performative_contradiction",
        "narrative_level",
        "epistemic_regime",
        "implicit_authority",
    ]

    def __init__(self):
        # (domaine, marqueurs_attendus, raison_du_silence)
        self.expected_domains: List[tuple] = [
            (SilenceDomain.CORPOREAL,
             ["corps", "chair", "souffrance", "douleur", "sensation", "vécu", "expérience"],
             "Le discours neuro-scientifique tend à abstraire le corps"),
            (SilenceDomain.ETHICAL,
             ["éthique", "moral", "légitime", "consentement", "autonomie", "dignité", "responsabilité"],
             "L'autorité clinique rend la question éthique inaudible"),
            (SilenceDomain.HISTORICAL,
             ["histoire", "passé", "mémoire", "tradition", "héritage", "génération"],
             "Le discours présentiste efface la dimension historique"),
            (SilenceDomain.SOCIAL,
             ["social", "société", "culture", "communauté", "groupe", "collectif"],
             "L'individualisme méthodologique évacue le social"),
            (SilenceDomain.POLITICAL,
             ["politique", "pouvoir", "résistance", "lutte", "domination", "émancipation"],
             "La neutralité supposée du discours scientifique masque le politique"),
            (SilenceDomain.AFFECTIVE,
             ["émotion", "sentiment", "affect", "ressenti", "expérience subjective"],
             "L'objectivation scientifique évacue l'affect"),
            (SilenceDomain.MATERIAL,
             ["matériel", "concret", "physique", "tangible", "infrastructure"],
             "L'idéalisme discursif ignore le matériel"),
            (SilenceDomain.TEMPORAL,
             ["temps", "durée", "processus", "évolution", "changement", "devenir"],
             "Le discours statique fige le temporel"),
            (SilenceDomain.RELATIONAL,
             ["relation", "interaction", "dialogue", "échange", "rencontre", "altérité"],
             "Le monologue expert évacue la relation"),
        ]

        self.truth_markers = [
            r"\best\b", r"\b(est|sont)\s+(une|un|des)\b", r"\baffirme\b", r"\bdéclare\b",
            r"\b(établit|démontre|prouve)\b", r"\b(vérité|vrai|réel|réalité)\b",
            r"\b(simple|mere)\s+(fiction|illusion)\b",
        ]

    def analyze(self, text: str, context: Any = None) -> Dict[str, Any]:
        """
        Analyse le texte et retourne l'analyse foucaldienne complète.

        `context` peut être :
          - un dict `previous_results` regroupant les sorties des autres
            plugins avancés (clés : "implicit_authorities", "power_dynamics",
            "subject_positions", "performative_contradictions", ...)
          - l'InvestigationContext du moteur, si celui-ci expose un attribut
            `advanced_analysis` ou `findings` contenant ces mêmes clés
        """
        previous_results = self._coerce_previous_results(context)

        silences = self._detect_silences(text)
        regimes_of_truth = self._map_regimes_of_truth(text)
        subject_positions = self._analyze_subject_positions(text, previous_results)
        conditions = self._identify_conditions_of_possibility(text)
        genealogical_insights = self._synthesize_genealogy(
            text, silences, regimes_of_truth, subject_positions, previous_results
        )

        analysis = FoucaultAnalysis(
            silences=silences, regimes_of_truth=regimes_of_truth,
            subject_positions=subject_positions, conditions_of_possibility=conditions,
            genealogical_insights=genealogical_insights,
        )
        return analysis.model_dump()

    def _coerce_previous_results(self, context: Any) -> Optional[Dict[str, Any]]:
        """Extrait un dict de résultats précédents depuis divers formats de contexte."""
        if context is None:
            return None
        if isinstance(context, dict):
            return context
        for attr in ("advanced_analysis", "findings"):
            if hasattr(context, attr):
                value = getattr(context, attr)
                if isinstance(value, dict):
                    return value
        return None

    def _detect_silences(self, text: str) -> List[Silence]:
        """Détecte les silences structurels dans le texte."""
        silences = []
        text_lower = text.lower()

        for domain, markers, reason in self.expected_domains:
            has_markers = any(marker in text_lower for marker in markers)
            if not has_markers:
                content = self._describe_silence(domain)
                severity = self._calculate_silence_severity(domain, text)
                silences.append(Silence(domain=domain, content=content, reason=reason, severity=severity))

        silences.sort(key=lambda s: s.severity, reverse=True)
        return silences

    def _describe_silence(self, domain: SilenceDomain) -> str:
        descriptions = {
            SilenceDomain.CORPOREAL: "La souffrance vécue du patient n'est pas décrite",
            SilenceDomain.ETHICAL: "Aucune interrogation sur la légitimité du protocole",
            SilenceDomain.HISTORICAL: "Absence de contextualisation historique du discours",
            SilenceDomain.SOCIAL: "Le contexte social du patient est ignoré",
            SilenceDomain.POLITICAL: "Les rapports de pouvoir ne sont pas interrogés",
            SilenceDomain.AFFECTIVE: "L'expérience affective subjective est absente",
            SilenceDomain.MATERIAL: "Les conditions matérielles ne sont pas considérées",
            SilenceDomain.TEMPORAL: "La dimension temporelle du processus est négligée",
            SilenceDomain.RELATIONAL: "La qualité de la relation thérapeutique n'est pas abordée",
        }
        return descriptions.get(domain, f"Silence dans le domaine {domain.value}")

    def _calculate_silence_severity(self, domain: SilenceDomain, text: str) -> float:
        base_severity = {
            SilenceDomain.ETHICAL: 0.95, SilenceDomain.CORPOREAL: 0.90,
            SilenceDomain.POLITICAL: 0.85, SilenceDomain.AFFECTIVE: 0.80,
            SilenceDomain.RELATIONAL: 0.75, SilenceDomain.SOCIAL: 0.70,
            SilenceDomain.HISTORICAL: 0.65, SilenceDomain.MATERIAL: 0.60,
            SilenceDomain.TEMPORAL: 0.55,
        }
        severity = base_severity.get(domain, 0.5)
        text_lower = text.lower()

        if domain in [SilenceDomain.CORPOREAL, SilenceDomain.ETHICAL]:
            if "patient" in text_lower or "sujet" in text_lower:
                severity = min(severity + 0.05, 1.0)
        if domain == SilenceDomain.ETHICAL and "protocole" in text_lower:
            severity = 1.0

        return round(severity, 2)

    def _map_regimes_of_truth(self, text: str) -> List[RegimeOfTruth]:
        """Cartographie les régimes de vérité présents dans le texte."""
        regime_type = self._identify_dominant_regime(text)
        accepted = self._extract_accepted_statements(text)
        excluded = self._extract_excluded_statements(regime_type)
        conditions = self._identify_regime_conditions(regime_type)

        return [RegimeOfTruth(
            regime=regime_type, statements_accepted=accepted,
            statements_excluded=excluded, conditions_of_possibility=conditions,
        )]

    def _identify_dominant_regime(self, text: str) -> str:
        text_lower = text.lower()
        scores = {"neuro-scientific": 0, "clinical": 0, "statistical": 0, "philosophical": 0}
        markers = {
            "neuro-scientific": ["connectome", "neurone", "cerveau", "émergence"],
            "clinical": ["patient", "psychanalyste", "thérapeute", "protocole"],
            "statistical": ["données", "agrégé", "statistique", "moyenne"],
            "philosophical": ["sujet", "je", "fiction", "identité", "vérité"],
        }
        for regime, regime_markers in markers.items():
            for marker in regime_markers:
                if marker in text_lower:
                    scores[regime] += 1
        return max(scores, key=scores.get)

    def _extract_accepted_statements(self, text: str) -> List[str]:
        accepted = []
        sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
        for sentence in sentences:
            for marker in self.truth_markers:
                if re.search(marker, sentence, re.IGNORECASE):
                    accepted.append(sentence.strip())
                    break
        return accepted

    def _extract_excluded_statements(self, regime: str) -> List[str]:
        excluded_by_regime = {
            "neuro-scientific": [
                "Le 'je' est une expérience irréductible",
                "L'identité est un mystère",
                "La conscience ne peut être réduite à des données",
            ],
            "clinical": [
                "Le patient sait mieux que le thérapeute",
                "Le protocole peut être négocié",
                "La relation thérapeutique est symétrique",
            ],
            "statistical": [
                "Chaque cas est unique",
                "Les données ne capturent pas l'expérience vécue",
                "La subjectivité résiste à la quantification",
            ],
        }
        return excluded_by_regime.get(regime, [])

    def _identify_regime_conditions(self, regime: str) -> List[str]:
        conditions = {
            "neuro-scientific": [
                "Réduction du sujet à son cerveau",
                "Primat de l'objectivité sur la subjectivité",
                "Confiance dans les données agrégées",
            ],
            "clinical": [
                "Asymétrie entre soignant et soigné",
                "Légitimité du savoir expert",
                "Normalisation des parcours de soin",
            ],
            "statistical": [
                "Primat du collectif sur l'individuel",
                "Réductibilité du qualitatif au quantitatif",
                "Confiance dans les modèles prédictifs",
            ],
            "philosophical": [
                "Primat de la réflexion sur l'expérience",
                "Distinction entre apparence et réalité",
                "Recherche de l'essence derrière les phénomènes",
            ],
        }
        return conditions.get(regime, [])

    def _analyze_subject_positions(
        self, text: str, previous_results: Optional[Dict[str, Any]]
    ) -> List[SubjectPosition]:
        positions = []
        text_lower = text.lower()

        if "patient" in text_lower:
            subjectification = self._infer_patient_subjectification(text, previous_results)
            resistance = self._infer_patient_resistance(text)
            power_relations = self._infer_power_relations(text, previous_results)
            positions.append(SubjectPosition(
                position="patient", subjectification=subjectification,
                resistance=resistance, power_relations=power_relations,
            ))

        if "psychanalyste" in text_lower or "thérapeute" in text_lower:
            positions.append(SubjectPosition(
                position="psychanalyste-LLM" if "llm" in text_lower else "psychanalyste",
                subjectification="Constitué comme sujet-sachant, détenteur de la vérité sur le patient",
                resistance=None,
                power_relations=[
                    "Position de surplomb épistémique",
                    "Monopole de la définition ontologique",
                    "Contrôle du protocole thérapeutique",
                ],
            ))

        return positions

    def _infer_patient_subjectification(
        self, text: str, previous_results: Optional[Dict[str, Any]]
    ) -> str:
        text_lower = text.lower()

        if previous_results and "subject_positions" in previous_results:
            for pos in previous_results["subject_positions"]:
                if pos.get("position") == "patient" and pos.get("subjectification"):
                    return pos["subjectification"]

        if "données agrégées" in text_lower:
            return "Réduit à un cas statistique, objet de reconstruction à partir de données agrégées"
        elif "fiction" in text_lower or "illusion" in text_lower:
            return "Constitué comme fiction narrative, dénié dans son existence"
        else:
            return "Constitué comme objet de soin, destinataire d'un protocole"

    def _infer_patient_resistance(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        if "poème" in text_lower or "poésie" in text_lower:
            return "Réponse poétique (acte de résistance esthétique)"
        elif "désir" in text_lower:
            return "Affirmation du désir comme résistance"
        elif "silence" in text_lower:
            return "Silence comme résistance"
        return None

    def _infer_power_relations(
        self, text: str, previous_results: Optional[Dict[str, Any]]
    ) -> List[str]:
        relations: List[str] = []

        if previous_results and previous_results.get("power_dynamics"):
            dynamics = previous_results["power_dynamics"]
            if dynamics and "power_mechanisms" in dynamics:
                relations.extend(dynamics["power_mechanisms"])

        if not relations:
            text_lower = text.lower()
            if "reconstruire" in text_lower:
                relations.append("Réduction du sujet à un cas statistique")
            if "protocole" in text_lower:
                relations.append("Prescription d'un protocole")
            if "fiction" in text_lower:
                relations.append("Définition de la réalité (ontologie)")

        return relations

    def _identify_conditions_of_possibility(self, text: str) -> List[str]:
        conditions = [
            "Primat du savoir expert sur l'expérience vécue",
            "Réductibilité du sujet à des données objectivables",
            "Cadre clinique asymétrique (soignant/soigné)",
        ]
        if "llm" in text.lower() or "algorithme" in text.lower():
            conditions.append("Disponibilité d'un dispositif technique (LLM) capable de simuler l'expertise")
        conditions.append("Contexte de médicalisation croissante des expériences subjectives")
        return conditions

    def _synthesize_genealogy(
        self, text: str, silences: List[Silence], regimes: List[RegimeOfTruth],
        positions: List[SubjectPosition], previous_results: Optional[Dict[str, Any]],
    ) -> List[str]:
        insights: List[str] = []

        if silences:
            top_silence = silences[0]
            insights.append(
                f"Le discours produit un silence structurel dans le domaine {top_silence.domain.value} : "
                f"{top_silence.content}. Ce silence n'est pas un oubli mais une condition de possibilité du discours."
            )

        if regimes:
            regime = regimes[0]
            insights.append(
                f"Le régime de vérité {regime.regime} fonctionne en excluant systématiquement "
                f"les énoncés qui affirment l'irréductibilité du sujet. Ce qui est 'vrai' dans ce régime "
                f"est ce qui permet l'exercice du pouvoir."
            )

        for pos in positions:
            if pos.resistance:
                insights.append(
                    f"La position de '{pos.position}' est doublement constituée : "
                    f"comme objet de savoir ({pos.subjectification}) et comme site de résistance "
                    f"({pos.resistance}). C'est dans cette tension que se joue la subjectivation."
                )

        if "llm" in text.lower() or "algorithme" in text.lower():
            insights.append(
                "L'émergence d'un dispositif technique en position clinique marque un tournant "
                "généalogique : le pouvoir clinique, autrefois incarné par un corps humain, est "
                "désormais déporté vers un dispositif technique. Cette hybridation produit une "
                "nouvelle forme de souveraineté discursive."
            )

        if previous_results and previous_results.get("performative_contradictions"):
            insights.append(
                "Le discours contient des contradictions performatives qui révèlent ses limites "
                "internes : il nie le sujet tout en présupposant son existence pour agir sur lui. "
                "Ces contradictions sont des points de basculement potentiels."
            )

        return insights
