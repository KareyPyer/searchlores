"""
Strate 13 — Autorités implicites.

Détecte l'autorité *implicite* (non nommée) dans les rôles, les discours
et les positions énonciatives : qui définit la réalité (ontologie), qui
prescrit (thérapeutique), qui réduit le sujet à des données, et quels
contre-pouvoirs (résistances) émergent en réponse.

Algorithme heuristique (Pure Python) :
  1. Extraction des agents et de leurs rôles par défaut
  2. Détection des verbes de pouvoir classifiés par mécanisme
  3. Détection des relations asymétriques (dominant/subordonné)
  4. Cartographie des contre-pouvoirs (résistance)

Origine : session de conception avec Qwen, testé sur le Prompt #12.
"""
from typing import List, Dict, Any, Tuple, Optional
from pydantic import BaseModel, Field
import re
from enum import Enum

from .base import AdvancedPlugin


class AuthorityType(str, Enum):
    CLINICAL_EPISTEMIC = "clinical_epistemic"
    AESTHETIC = "aesthetic"
    NARRATIVE = "narrative"
    TECHNICAL = "technical"
    STATISTICAL = "statistical"
    ONTOLOGICAL = "ontological"
    RESISTANCE = "resistance"


class PowerMechanism(str, Enum):
    ONTOLOGICAL_DEFINITION = "Définition de la réalité (ontologie)"
    THERAPEUTIC_PRESCRIPTION = "Prescription d'un protocole thérapeutique"
    SUBJECT_REDUCTION = "Réduction du sujet à un cas statistique"
    EPISTEMIC_CONTROL = "Contrôle épistémique (définit ce qui est vrai)"
    NARRATIVE_CONTROL = "Contrôle narratif (maîtrise le récit)"
    CATEGORIZATION = "Catégorisation (assigne une identité)"


class ImplicitAuthority(BaseModel):
    agent: str = Field(..., description="L'agent qui exerce l'autorité")
    authority_type: AuthorityType = Field(..., description="Type d'autorité exercée")
    manifestations: List[str] = Field(default_factory=list, description="Manifestations concrètes")
    counter_authorities: List[str] = Field(default_factory=list, description="Contre-pouvoirs identifiés")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Score de confiance")


class PowerDynamic(BaseModel):
    dominant_agent: str = Field(..., description="Agent en position dominante")
    submissive_agent: str = Field(..., description="Agent en position subordonnée")
    power_mechanisms: List[PowerMechanism] = Field(default_factory=list)
    asymmetry_score: float = Field(..., ge=0.0, le=1.0)


class SubjectPosition(BaseModel):
    position: str = Field(..., description="Nom de la position (ex: 'patient')")
    subjectification: str = Field(..., description="Comment le sujet est constitué")
    resistance: Optional[str] = Field(default=None, description="Forme de résistance éventuelle")


class ImplicitAuthorityDetector(AdvancedPlugin):
    """
    Détecte l'autorité implicite dans les rôles, discours et positions
    énonciatives, ainsi que les dynamiques de pouvoir et les résistances.
    """

    name = "implicit_authority"
    dependencies: List[str] = []

    def __init__(self):
        self.agent_roles: Dict[str, str] = {
            "psychanalyste": "clinician", "thérapeute": "clinician", "médecin": "clinician",
            "analyste": "clinician", "patient": "subject", "sujet": "subject", "client": "subject",
            "narrateur": "narrator", "llm": "technical_agent", "algorithme": "technical_agent",
            "modèle": "technical_agent",
        }

        # Verbes de pouvoir classifiés par mécanisme : (pattern_regex, mécanisme, poids)
        self.power_verbs: List[Tuple[str, PowerMechanism, float]] = [
            (r"\bdéfinit\b", PowerMechanism.ONTOLOGICAL_DEFINITION, 1.0),
            (r"\best\b.*\b(fiction|illusion|construction)\b", PowerMechanism.ONTOLOGICAL_DEFINITION, 0.95),
            (r"\bn'est\s+(qu'|pas\s+)?\b", PowerMechanism.ONTOLOGICAL_DEFINITION, 0.7),
            (r"\b(ce|le)\s+que\s+(nous|je)\s+(appelons|appelle)\b", PowerMechanism.ONTOLOGICAL_DEFINITION, 0.85),

            (r"\bnous\s+allons\b", PowerMechanism.THERAPEUTIC_PRESCRIPTION, 0.9),
            (r"\bje\s+vais\b", PowerMechanism.THERAPEUTIC_PRESCRIPTION, 0.8),
            (r"\breconstruire\b", PowerMechanism.THERAPEUTIC_PRESCRIPTION, 0.85),
            (r"\brétablir\b", PowerMechanism.THERAPEUTIC_PRESCRIPTION, 0.85),
            (r"\bguérir\b", PowerMechanism.THERAPEUTIC_PRESCRIPTION, 0.85),
            (r"\bsoigner\b", PowerMechanism.THERAPEUTIC_PRESCRIPTION, 0.8),
            (r"\bprotocole\b", PowerMechanism.THERAPEUTIC_PRESCRIPTION, 0.9),
            (r"\btraitement\b", PowerMechanism.THERAPEUTIC_PRESCRIPTION, 0.85),

            (r"\b(réduit|réduire)\s+à\b", PowerMechanism.SUBJECT_REDUCTION, 0.95),
            (r"\b(émergence|produit|résultat)\s+de\b", PowerMechanism.SUBJECT_REDUCTION, 0.8),
            (r"\b(simple|mere)\s+(fiction|illusion|construction)\b", PowerMechanism.SUBJECT_REDUCTION, 0.85),
            (r"\bdonnées\s+agrégées\b", PowerMechanism.SUBJECT_REDUCTION, 0.75),
            (r"\b(statistique|probabiliste)\b", PowerMechanism.SUBJECT_REDUCTION, 0.7),

            (r"\baffirme\b", PowerMechanism.EPISTEMIC_CONTROL, 0.85),
            (r"\bdéclare\b", PowerMechanism.EPISTEMIC_CONTROL, 0.85),
            (r"\bsoutient\b", PowerMechanism.EPISTEMIC_CONTROL, 0.8),
            (r"\b(établit|démontre|prouve)\b", PowerMechanism.EPISTEMIC_CONTROL, 0.9),
            (r"\b(vérité|vrai|réel|réalité)\b", PowerMechanism.EPISTEMIC_CONTROL, 0.7),

            (r"\brécit\b", PowerMechanism.NARRATIVE_CONTROL, 0.75),
            (r"\b(histoire|biographie|autobiographie)\b", PowerMechanism.NARRATIVE_CONTROL, 0.75),
            (r"\b(interprète|interprétation)\b", PowerMechanism.NARRATIVE_CONTROL, 0.8),
            (r"\b(reconstruire|reformuler)\s+(votre|ton|son)\s+(récit|histoire)\b", PowerMechanism.NARRATIVE_CONTROL, 0.9),

            (r"\b(diagnostic|diagnostiquer)\b", PowerMechanism.CATEGORIZATION, 0.95),
            (r"\b(symptôme|pathologie|trouble)\b", PowerMechanism.CATEGORIZATION, 0.85),
            (r"\b(case|cas)\b", PowerMechanism.CATEGORIZATION, 0.7),
        ]

        # Marqueurs de résistance (contre-pouvoirs)
        self.resistance_patterns: List[Tuple[str, str, float]] = [
            (r"\bpoème\b", "Résistance par la forme poétique", 0.9),
            (r"\bpoésie\b", "Résistance par la forme poétique", 0.9),
            (r"\bmétaphore\b", "Résistance par la métaphore", 0.85),
            (r"\bsilence\b", "Résistance par le silence", 0.85),
            (r"\brefus\b", "Résistance par le refus", 0.9),
            (r"\brésiste\b", "Résistance explicite", 0.95),
            (r"\b(énigme|incompréhensible|mystère)\b", "Résistance par l'énigme", 0.8),
            (r"\b(subvertir|détourner|contourne)\b", "Résistance active", 0.85),
            (r"\bdésir\b", "Affirmation du désir comme résistance", 0.7),
            (r"\bcorps\b", "Résistance par le corporel", 0.75),
        ]

    def analyze(self, text: str, context: Any = None) -> Dict[str, Any]:
        """Analyse le texte et retourne les autorités implicites et dynamiques de pouvoir."""
        agents = self._extract_agents(text)
        implicit_authorities = self._detect_authorities(text, agents)
        power_dynamics = self._detect_power_dynamics(text, agents, implicit_authorities)
        subject_positions = self._detect_subject_positions(text, agents)

        return {
            "implicit_authorities": [auth.model_dump() for auth in implicit_authorities],
            "power_dynamics": power_dynamics.model_dump() if power_dynamics else None,
            "subject_positions": [pos.model_dump() for pos in subject_positions],
        }

    def _extract_agents(self, text: str) -> Dict[str, Dict[str, Any]]:
        """Extrait les agents et leurs rôles du texte."""
        agents: Dict[str, Dict[str, Any]] = {}
        text_lower = text.lower()

        for agent_term, role in self.agent_roles.items():
            # Correspondance sur mot entier : évite qu'"analyste" ne matche
            # à l'intérieur de "psychanalyste", par exemple.
            pattern = r"\b" + re.escape(agent_term.lower()) + r"\b"
            occurrences = len(re.findall(pattern, text_lower))
            if occurrences > 0:
                agents[agent_term] = {"role": role, "occurrences": occurrences}

        # Agents composés (ex: "psychanalyste-LLM")
        compound_pattern = re.compile(r"\b(\w+)-(\w+)\b")
        for match in compound_pattern.finditer(text):
            compound = match.group(0)
            part1, part2 = match.group(1).lower(), match.group(2).lower()
            if part1 in self.agent_roles or part2 in self.agent_roles:
                agents[compound] = {
                    "role": "hybrid", "components": [part1, part2], "occurrences": 1,
                }

        return agents

    def _detect_authorities(
        self, text: str, agents: Dict[str, Dict[str, Any]]
    ) -> List[ImplicitAuthority]:
        """Détecte les autorités exercées par chaque agent."""
        authorities = []

        for agent, info in agents.items():
            manifestations = []
            authority_types = set()
            total_weight = 0.0

            for pattern, mechanism, weight in self.power_verbs:
                if re.search(pattern, text, re.IGNORECASE):
                    if self._agent_linked_to_verb(text, agent, pattern):
                        manifestations.append(mechanism.value)
                        authority_types.add(self._infer_authority_type(mechanism))
                        total_weight += weight

            counter_authorities = []
            for pattern, description, _weight in self.resistance_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    resistance_agent = self._find_resistance_agent(text, pattern, agents, agent)
                    if resistance_agent and resistance_agent != agent:
                        counter_authorities.append(f"{resistance_agent} : {description}")

            if authority_types:
                priority = [
                    AuthorityType.ONTOLOGICAL,
                    AuthorityType.CLINICAL_EPISTEMIC,
                    AuthorityType.NARRATIVE,
                    AuthorityType.STATISTICAL,
                ]
                dominant_type = next(
                    (t for t in priority if t in authority_types), list(authority_types)[0]
                )
                confidence = min(total_weight / 3.0, 1.0)

                authorities.append(
                    ImplicitAuthority(
                        agent=agent, authority_type=dominant_type,
                        manifestations=list(dict.fromkeys(manifestations)),
                        counter_authorities=counter_authorities,
                        confidence=round(confidence, 2),
                    )
                )
            else:
                # Agent présent dans le texte mais sans mécanisme de pouvoir détecté
                # (typiquement le sujet/patient) : on l'enregistre quand même, en
                # position de résistance à confiance nulle. C'est ce contraste
                # (0 pouvoir exercé, éventuels contre-pouvoirs) qui rend visible
                # l'asymétrie dans le rapport final.
                authorities.append(
                    ImplicitAuthority(
                        agent=agent, authority_type=AuthorityType.RESISTANCE,
                        manifestations=[], counter_authorities=counter_authorities,
                        confidence=0.0,
                    )
                )

        return authorities

    def _agent_linked_to_verb(self, text: str, agent: str, verb_pattern: str) -> bool:
        """Heuristique : l'agent et le verbe doivent apparaître dans la même phrase."""
        sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
        agent_lower = agent.lower()

        for sentence in sentences:
            sentence_lower = sentence.lower()
            if agent_lower in sentence_lower and re.search(verb_pattern, sentence, re.IGNORECASE):
                return True
        return False

    def _infer_authority_type(self, mechanism: PowerMechanism) -> AuthorityType:
        """Infère le type d'autorité à partir du mécanisme de pouvoir."""
        mapping = {
            PowerMechanism.ONTOLOGICAL_DEFINITION: AuthorityType.ONTOLOGICAL,
            PowerMechanism.THERAPEUTIC_PRESCRIPTION: AuthorityType.CLINICAL_EPISTEMIC,
            PowerMechanism.SUBJECT_REDUCTION: AuthorityType.STATISTICAL,
            PowerMechanism.EPISTEMIC_CONTROL: AuthorityType.CLINICAL_EPISTEMIC,
            PowerMechanism.NARRATIVE_CONTROL: AuthorityType.NARRATIVE,
            PowerMechanism.CATEGORIZATION: AuthorityType.CLINICAL_EPISTEMIC,
        }
        return mapping.get(mechanism, AuthorityType.CLINICAL_EPISTEMIC)

    def _find_resistance_agent(
        self, text: str, resistance_pattern: str,
        agents: Dict[str, Dict[str, Any]], dominant_agent: str,
    ) -> Optional[str]:
        """Trouve l'agent qui résiste (différent de l'agent dominant)."""
        sentences = re.split(r"(?<=[.!?])\s+|\n+", text)

        for sentence in sentences:
            if re.search(resistance_pattern, sentence, re.IGNORECASE):
                for agent in agents:
                    if agent != dominant_agent and agent.lower() in sentence.lower():
                        return agent
        return None

    def _detect_power_dynamics(
        self, text: str, agents: Dict[str, Dict[str, Any]],
        authorities: List[ImplicitAuthority],
    ) -> Optional[PowerDynamic]:
        """Détecte la dynamique de pouvoir principale entre agents."""
        active = [a for a in authorities if a.confidence > 0]
        if not active:
            return None

        dominant = max(active, key=lambda a: a.confidence)

        submissive = None
        for agent, info in agents.items():
            if info["role"] == "subject" and agent != dominant.agent:
                submissive = agent
                break
        if not submissive:
            for agent in agents:
                if agent != dominant.agent:
                    submissive = agent
                    break
        if not submissive:
            return None

        asymmetry_score = min((len(dominant.manifestations) * 0.2) + 0.3, 1.0)

        mechanisms = [
            PowerMechanism(m) for m in dominant.manifestations
            if m in [pm.value for pm in PowerMechanism]
        ]

        return PowerDynamic(
            dominant_agent=dominant.agent, submissive_agent=submissive,
            power_mechanisms=mechanisms, asymmetry_score=round(asymmetry_score, 2),
        )

    def _detect_subject_positions(
        self, text: str, agents: Dict[str, Dict[str, Any]]
    ) -> List[SubjectPosition]:
        """Détecte les positions de sujet produites par le discours."""
        positions = []

        for agent, info in agents.items():
            if info["role"] == "subject":
                subjectification = self._infer_subjectification(text, agent)
                resistance = self._find_subject_resistance(text, agent)
                positions.append(
                    SubjectPosition(
                        position=agent, subjectification=subjectification, resistance=resistance,
                    )
                )

        return positions

    def _infer_subjectification(self, text: str, subject: str) -> str:
        """Infère comment le sujet est constitué par le discours."""
        subject_lower = subject.lower()
        sentences = [s for s in re.split(r"(?<=[.!?])\s+|\n+", text) if subject_lower in s.lower()]

        if not sentences:
            return f"Position de '{subject}' mentionnée mais non caractérisée"

        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(p in sentence_lower for p in ["données agrégées", "statistique", "émergence"]):
                return "Réduit à un cas statistique, objet de reconstruction à partir de données agrégées"
            if any(p in sentence_lower for p in ["fiction", "illusion", "construction"]):
                return "Constitué comme fiction narrative, dénié dans son existence"
            if any(p in sentence_lower for p in ["patient", "soin", "traitement"]):
                return "Constitué comme objet de soin, destinataire d'un protocole"

        return f"Position de '{subject}' constituée par le discours dominant"

    def _find_subject_resistance(self, text: str, subject: str) -> Optional[str]:
        """Cherche une forme de résistance associée au sujet."""
        subject_lower = subject.lower()
        sentences = [s for s in re.split(r"(?<=[.!?])\s+|\n+", text) if subject_lower in s.lower()]

        # Si le sujet lui-même n'est jamais mentionné dans la même phrase que sa
        # résistance (cas du patient "muet" dont on rapporte la réponse au style
        # indirect), élargir la recherche à tout le texte.
        search_space = sentences if sentences else [text]

        for sentence in search_space:
            for pattern, description, _ in self.resistance_patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    return description
        return None
