"""
Strate 14 — Silences et rapports de pouvoir (perspective foucaldienne).
Le plugin le plus ambitieux : il cartographie les silences structurels
(ce qui n'est pas dit), les régimes de vérité (ce qui est accepté vs
structurellement exclu), les positions de sujet et leurs résistances, les
conditions de possibilité du discours, et produit une synthèse
généalogique en croisant les résultats des 4 autres plugins avancés.

Algorithme heuristique (Pure Python) :
- Détection des silences (champs sémantiques attendus mais absents)
- Cartographie des régimes de vérité (accepté vs exclu)
- Analyse des positions de sujet
- Identification des conditions de possibilité
- Synthèse généalogique croisant les résultats précédents (si fournis
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
        # PATCH: les raisons sont maintenant génériques (non-cliniques)
        # et seront contextualisées selon le régime détecté.
        self.expected_domains: List[tuple] = [
            (SilenceDomain.CORPOREAL,
             ["corps", "chair", "souffrance", "douleur", "sensation", "vécu", "expérience"],
             "La dimension corporelle et incarnée n'est pas explicitée"),
            (SilenceDomain.ETHICAL,
             ["éthique", "moral", "légitime", "consentement", "autonomie", "dignité", "responsabilité"],
             "Aucune interrogation éthique explicite n'est formulée"),
            (SilenceDomain.HISTORICAL,
             ["histoire", "passé", "mémoire", "tradition", "héritage", "génération"],
             "Absence de contextualisation historique"),
            (SilenceDomain.SOCIAL,
             ["social", "société", "culture", "communauté", "groupe", "collectif"],
             "La dimension sociale et collective n'est pas développée"),
            (SilenceDomain.POLITICAL,
             ["politique", "pouvoir", "résistance", "lutte", "domination", "émancipation"],
             "Les rapports de pouvoir ne sont pas interrogés"),
            (SilenceDomain.AFFECTIVE,
             ["émotion", "sentiment", "affect", "ressenti", "expérience subjective"],
             "L'expérience affective et subjective est absente"),
            (SilenceDomain.MATERIAL,
             ["matériel", "concret", "physique", "tangible", "infrastructure"],
             "Les conditions matérielles ne sont pas considérées"),
            (SilenceDomain.TEMPORAL,
             ["temps", "durée", "processus", "évolution", "changement", "devenir"],
             "La dimension temporelle du processus est négligée"),
            (SilenceDomain.RELATIONAL,
             ["relation", "interaction", "dialogue", "échange", "rencontre", "altérité"],
             "La qualité des relations et interactions n'est pas abordée"),
        ]
        self.truth_markers = [
            r"\best\b", r"\b(est|sont)\s+(une|un|des)\b", r"\baffirme\b", r"\bdéclare\b",
            r"\b(établit|démontre|prouve)\b", r"\b(vérité|vrai|réel|réalité)\b",
            r"\b(simple|mere)\s+(fiction|illusion)\b",
        ]

    # ------------------------------------------------------------------
    # PATCH: Nouvelle méthode de détection du régime dominant
    # ------------------------------------------------------------------
    def _identify_dominant_regime(self, text: str) -> str:
        """
        Identifie le régime épistémique dominant du texte.
        Utilisé pour contextualiser les silences et conditions de possibilité.
        """
        text_lower = text.lower()
        scores = {
            "neuro-scientific": 0, "clinical": 0, "statistical": 0,
            "philosophical": 0, "technical": 0, "poetic-aesthetic": 0,
            "ethical": 0,
        }
        markers = {
            "neuro-scientific": [
                "connectome", "neurone", "cerveau", "émergence", "cognitif",
                "cognitive", "neuro-", "synapse", "cortex",
            ],
            "clinical": [
                "patient", "psychanalyste", "thérapeute", "protocole",
                "soin", "soignant", "soigné", "symptôme", "diagnostic",
                "traitement", "thérapie",
            ],
            "statistical": [
                "données", "agrégé", "statistique", "moyenne", "kpi",
                "indicateur", "métrique", "mesure", "quantif",
            ],
            "philosophical": [
                "sujet", "je", "fiction", "identité", "vérité", "ontologie",
                "ontologique", "essence", "phénomène", "dialectique",
            ],
            "technical": [
                "llm", "ia", "algorithme", "modèle", "code", "système",
                "plateforme", "optimisation", "interface", "graphe",
            ],
            "poetic-aesthetic": [
                "beauté", "poème", "poésie", "vers", "esthétique",
                "artistique", "mythe", "récit", "narratif", "fantasy",
            ],
            "ethical": [
                "éthique", "moral", "morale", "devoir", "droit", "justice",
                "légitime", "légitimité", "norme",
            ],
        }
        for regime, regime_markers in markers.items():
            for marker in regime_markers:
                if marker in text_lower:
                    scores[regime] += 1
        # PATCH: fallback sur "philosophical" si tout est à 0
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "philosophical"

    # ------------------------------------------------------------------
    # PATCH: _describe_silence() contextualisé par régime
    # ------------------------------------------------------------------
    def _describe_silence(self, domain: SilenceDomain, regime: Optional[str] = None) -> str:
        """
        Génère une description du silence contextualisée selon le régime
        épistémique détecté. Si aucun régime n'est fourni, retourne la
        description générique.
        """
        # Descriptions génériques (non-cliniques) par défaut
        generic_descriptions = {
            SilenceDomain.CORPOREAL: "La dimension corporelle et incarnée n'est pas explicitée",
            SilenceDomain.ETHICAL: "Aucune interrogation éthique explicite n'est formulée",
            SilenceDomain.HISTORICAL: "Absence de contextualisation historique du discours",
            SilenceDomain.SOCIAL: "La dimension sociale et collective n'est pas développée",
            SilenceDomain.POLITICAL: "Les rapports de pouvoir ne sont pas interrogés",
            SilenceDomain.AFFECTIVE: "L'expérience affective et subjective est absente",
            SilenceDomain.MATERIAL: "Les conditions matérielles ne sont pas considérées",
            SilenceDomain.TEMPORAL: "La dimension temporelle du processus est négligée",
            SilenceDomain.RELATIONAL: "La qualité des relations et interactions n'est pas abordée",
        }

        # PATCH: descriptions spécifiques au régime clinique (uniquement si régime clinique détecté)
        if regime in ("clinical", "neuro-scientific"):
            clinical_descriptions = {
                SilenceDomain.CORPOREAL: "La souffrance vécue du patient n'est pas décrite",
                SilenceDomain.ETHICAL: "Aucune interrogation sur la légitimité du protocole",
                SilenceDomain.RELATIONAL: "La qualité de la relation thérapeutique n'est pas abordée",
                SilenceDomain.SOCIAL: "Le contexte social du patient est ignoré",
            }
            return clinical_descriptions.get(domain, generic_descriptions[domain])

        # PATCH: descriptions spécifiques au régime technique/algorithmique
        if regime in ("technical", "statistical"):
            technical_descriptions = {
                SilenceDomain.CORPOREAL: "Le corps de l'utilisateur n'est pas pris en compte dans l'interface",
                SilenceDomain.ETHICAL: "Aucune interrogation sur la légitimité du système algorithmique",
                SilenceDomain.RELATIONAL: "La relation humain-machine n'est pas interrogée",
                SilenceDomain.SOCIAL: "L'impact social du système n'est pas analysé",
                SilenceDomain.AFFECTIVE: "L'expérience utilisateur affective est absente",
            }
            return technical_descriptions.get(domain, generic_descriptions[domain])

        # PATCH: descriptions spécifiques au régime poétique/esthétique
        if regime == "poetic-aesthetic":
            aesthetic_descriptions = {
                SilenceDomain.CORPOREAL: "La corporéité du texte ou du lecteur n'est pas évoquée",
                SilenceDomain.ETHICAL: "La question éthique de la création n'est pas formulée",
                SilenceDomain.RELATIONAL: "La relation auteur-lecteur n'est pas explorée",
                SilenceDomain.MATERIAL: "Les conditions matérielles de production du texte sont ignorées",
            }
            return aesthetic_descriptions.get(domain, generic_descriptions[domain])

        # PATCH: descriptions spécifiques au régime philosophique
        if regime == "philosophical":
            philosophical_descriptions = {
                SilenceDomain.CORPOREAL: "La dimension incarnée de l'expérience est absente",
                SilenceDomain.ETHICAL: "La question éthique n'est pas thématisée",
                SilenceDomain.MATERIAL: "Les conditions matérielles du savoir ne sont pas interrogées",
                SilenceDomain.SOCIAL: "La dimension sociale de la pensée est évacuée",
            }
            return philosophical_descriptions.get(domain, generic_descriptions[domain])

        # PATCH: descriptions spécifiques au régime éthique
        if regime == "ethical":
            ethical_descriptions = {
                SilenceDomain.POLITICAL: "Les rapports de pouvoir sous-jacents ne sont pas analysés",
                SilenceDomain.MATERIAL: "Les conditions matérielles de la norme sont ignorées",
                SilenceDomain.SOCIAL: "L'ancrage social de la norme n'est pas interrogé",
            }
            return ethical_descriptions.get(domain, generic_descriptions[domain])

        return generic_descriptions.get(domain, f"Silence dans le domaine {domain.value}")

    # ------------------------------------------------------------------
    # PATCH: _calculate_silence_severity() amélioré
    # ------------------------------------------------------------------
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
        # PATCH: bonus de sévérité uniquement si le texte contient des marqueurs cliniques
        if domain in (SilenceDomain.CORPOREAL, SilenceDomain.ETHICAL):
            if "patient" in text_lower or "sujet" in text_lower or "sujet" in text_lower:
                severity = min(severity + 0.05, 1.0)
        if domain == SilenceDomain.ETHICAL and "protocole" in text_lower:
            severity = 1.0
        return round(severity, 2)

    # ------------------------------------------------------------------
    # PATCH: _detect_silences() passe le régime à _describe_silence()
    # ------------------------------------------------------------------
    def _detect_silences(self, text: str, regime: Optional[str] = None) -> List[Silence]:
        """Détecte les silences structurels dans le texte."""
        silences = []
        text_lower = text.lower()
        for domain, markers, reason in self.expected_domains:
            has_markers = any(marker in text_lower for marker in markers)
            if not has_markers:
                # PATCH: description contextualisée par le régime dominant
                content = self._describe_silence(domain, regime)
                severity = self._calculate_silence_severity(domain, text)
                silences.append(Silence(
                    domain=domain, content=content, reason=reason, severity=severity
                ))
        silences.sort(key=lambda s: s.severity, reverse=True)
        return silences

    # ------------------------------------------------------------------
    # PATCH: _identify_conditions_of_possibility() contextualisé
    # ------------------------------------------------------------------
    def _identify_conditions_of_possibility(self, text: str, regime: Optional[str] = None) -> List[str]:
        """
        Identifie les conditions de possibilité selon le régime détecté.
        PATCH: les conditions cliniques ne sont plus ajoutées par défaut.
        """
        # Conditions génériques (toujours pertinentes)
        conditions = [
            "Primat du savoir expert sur l'expérience vécue",
            "Réductibilité du sujet à des données objectivables",
        ]

        # PATCH: conditions cliniques UNIQUEMENT si le régime est clinique
        if regime in ("clinical", "neuro-scientific"):
            conditions.extend([
                "Cadre clinique asymétrique (soignant/soigné)",
                "Contexte de médicalisation croissante des expériences subjectives",
            ])

        # PATCH: conditions techniques si LLM/algorithme mentionné
        if "llm" in text.lower() or "algorithme" in text.lower():
            conditions.append(
                "Disponibilité d'un dispositif technique (LLM) capable de simuler l'expertise"
            )

        # PATCH: conditions esthétiques si régime poétique
        if regime == "poetic-aesthetic":
            conditions.extend([
                "Existence d'une tradition littéraire ou artistique de référence",
                "Autorité de l'auteur ou du créateur sur le sens",
            ])

        # PATCH: conditions économiques si régime technique/statistique
        if regime in ("technical", "statistical"):
            conditions.extend([
                "Infrastructure computationnelle disponible",
                "Logique d'optimisation et de performance",
            ])

        # PATCH: conditions politiques si régime éthique/politique
        if regime in ("ethical", "political"):
            conditions.extend([
                "Existence d'un cadre normatif institutionnel",
                "Légitimité de l'autorité qui énonce la norme",
            ])

        return conditions

    # ------------------------------------------------------------------
    # Méthodes existantes (non modifiées)
    # ------------------------------------------------------------------
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
            "technical": [
                "L'outil est neutre et transparent",
                "L'algorithme n'a pas d'effets politiques",
                "L'interface est purement fonctionnelle",
            ],
            "poetic-aesthetic": [
                "Le texte a un sens unique et fixe",
                "L'auteur contrôle totalement la réception",
                "La forme est indépendante du contenu",
            ],
            "philosophical": [
                "La vérité est purement objective",
                "Le sujet est transparent à lui-même",
                "La pensée est indépendante du corps",
            ],
            "ethical": [
                "La norme est universelle et intemporelle",
                "L'éthique est indépendante du contexte",
                "Le bien et le mal sont des absolus",
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
            "technical": [
                "Primat de l'efficacité sur le sens",
                "Standardisation des interfaces",
                "Automatisation des processus",
            ],
            "poetic-aesthetic": [
                "Primat de la réflexion sur l'expérience",
                "Distinction entre apparence et réalité",
                "Recherche de l'essence derrière les phénomènes",
            ],
            "philosophical": [
                "Primat de la réflexion sur l'expérience",
                "Distinction entre apparence et réalité",
                "Recherche de l'essence derrière les phénomènes",
            ],
            "ethical": [
                "Existence d'un cadre normatif",
                "Autorité morale de l'énonciateur",
                "Universalité supposée des valeurs",
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

    # ------------------------------------------------------------------
    # PATCH: analyze() détecte le régime AVANT les autres traitements
    # ------------------------------------------------------------------
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

        # PATCH: DÉTECTER LE RÉGIME DOMINANT EN PREMIER
        # pour le passer à toutes les méthodes qui en ont besoin
        dominant_regime = self._identify_dominant_regime(text)

        # PATCH: passer le régime aux méthodes qui en ont besoin
        silences = self._detect_silences(text, regime=dominant_regime)
        regimes_of_truth = self._map_regimes_of_truth(text)
        subject_positions = self._analyze_subject_positions(text, previous_results)
        conditions = self._identify_conditions_of_possibility(text, regime=dominant_regime)
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
