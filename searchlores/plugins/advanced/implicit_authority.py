"""
Strate 13 — Autorités implicites.

Détecte l'autorité *implicite* (non nommée) dans les rôles, les discours
et les positions énonciatives : qui définit la réalité (ontologie), qui
prescrit (thérapeutique), qui réduit le sujet à des données, et quels
contre-pouvoirs (résistances) émergent en réponse.

Algorithme heuristique (Pure Python) :
  1. Extraction des agents et de leurs rôles par défaut
  2. Localisation de chaque mention d'agent dans le texte, avec
     distinction sujet/objet grammatical (heuristique par préposition)
  3. Résolution heuristique de quelques pronoms de reprise ("nous",
     "vous"/"votre"/"vos"...) vers l'agent nommé le plus proche
  4. Attribution des verbes de pouvoir à l'agent-sujet le plus plausible
     dans la phrase (et non plus à "n'importe quel agent nommé dans la
     même phrase")
  5. Détection des relations asymétriques (dominant/subordonné)
  6. Cartographie des contre-pouvoirs (résistance)

Origine : session de conception avec Qwen, testé sur le Prompt #12.

PATCH (révision de robustesse) : la version précédente attribuait un
mécanisme de pouvoir à un agent dès que son nom apparaissait *n'importe
où* dans la même phrase que le marqueur regex correspondant, sans
vérifier qui en était réellement le sujet grammatical. Sur des phrases
longues à discours rapporté imbriqué (cas fréquent en français, ex.
Prompt #12), cela faisait remonter la confiance du *patient* au-dessus
de celle du *psychanalyste*/*LLM* — simplement parce que le mot
"patient" apparaissait dans les mêmes phrases que les marqueurs
d'autorité ontologique et de prescription thérapeutique, sans jamais
en être l'agent. `_detect_power_dynamics()` sélectionnant l'agent de
plus haute confiance comme `dominant_agent`, le patient se retrouvait
désigné comme dominant et le psychanalyste comme soumis — l'inverse de
ce que dit le texte.

Cette révision introduit :
  - une distinction sujet/objet par préposition immédiatement précédente
    (ex. "chez son psychanalyste", "la réponse **du** patient" → objet) ;
  - une résolution limitée de "nous"/"vous"/"votre"/"vos" vers l'agent
    nommé le plus proche, pour ne pas perdre l'attribution dans les
    phrases qui ne renomment plus les agents explicitement ;
  - une attribution par phrase qui ne retient que les agents-sujets
    proches du marqueur détecté quand plusieurs agents sont présents,
    au lieu de les créditer tous indistinctement ;
  - une sélection de `submissive_agent` fondée sur le rôle sémantique
    ("subject") plutôt que sur l'ordre d'insertion dans un dict, pour
    éviter qu'une éventuelle nouvelle régression sur les scores ne
    produise à nouveau une inversion silencieuse.

Limite assumée et documentée : quand une phrase ne contient aucune
mention nommée ou résolue d'agent (ex. tournures totalement impersonnelles),
le mécanisme de pouvoir détecté reste non attribué plutôt que d'être
assigné par défaut à un agent — une perte d'information est jugée
préférable à une mauvaise attribution.
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


# Un "mention" est un tuple (start, end, agent_key, is_object) :
#   - start/end : offsets dans le texte source
#   - agent_key : clé d'agent (ex. "psychanalyste", "llm", "patient")
#   - is_object : True si la mention est en position d'objet/possessif/
#                 destinataire (donc jamais créditée comme agent-sujet
#                 d'un mécanisme de pouvoir)
Mention = Tuple[int, int, str, bool]


# Prépositions/tournures qui, immédiatement avant une mention d'agent,
# indiquent une position d'objet/possessif plutôt que de sujet
# (ex. "chez son psychanalyste", "la réponse du patient").
_OBJECT_PREPOSITION_RE = re.compile(
    r"\b(?:de|du|des|d['’]|au|aux|à|chez|par|pour|sur|avec|envers|vers)\s+"
    r"(?:le\s+|la\s+|les\s+|l['’]\s*|son\s+|sa\s+|ses\s+|leur\s+|leurs\s+)?$",
    re.IGNORECASE,
)

# Fenêtre de recherche (en caractères) utilisée pour vérifier si une
# mention d'agent est précédée d'une préposition-objet.
_OBJECT_CONTEXT_WINDOW = 40

# Fenêtre de proximité (en caractères) au sein d'une phrase pour
# attribuer un mécanisme de pouvoir à un agent-sujet, quand plusieurs
# agents-sujets distincts sont présents dans la même phrase.
_PROXIMITY_WINDOW = 60

# Segmentation de phrases : coupe après [.!?], en tolérant un guillemet
# fermant intercalé avant l'espace (cas très fréquent en français avec
# du discours rapporté : "...suis.' Le psychanalyste...").
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])['’\"”]?\s+|\n+")

# Pronoms/possessifs de 2e personne : toujours résolus comme position
# d'objet/destinataire (jamais comme agent-sujet d'un mécanisme de
# pouvoir), pour ne pas recréer le bug initial sous une autre forme.
_SUBJECT_REFERENCE_PRONOUNS = ("vous", "votre", "vos", "toi", "ton", "ta", "tes")

# Pronoms de 1re personne du pluriel : résolus comme agent-sujet
# (rôle clinicien/technique/hybride) le plus proche précédemment nommé.
_AGENT_REFERENCE_PRONOUNS = ("nous",)


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
            (r"\best\b.*?\b(fiction|illusion|construction)\b", PowerMechanism.ONTOLOGICAL_DEFINITION, 0.95),
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
            (r"\b(symptômes?|pathologie|trouble)\b", PowerMechanism.CATEGORIZATION, 0.85),
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

    # ------------------------------------------------------------------
    # Point d'entrée
    # ------------------------------------------------------------------
    def analyze(self, text: str, context: Any = None) -> Dict[str, Any]:
        """Analyse le texte et retourne les autorités implicites et dynamiques de pouvoir."""
        agents = self._extract_agents(text)
        mentions = self._find_all_mentions(text, agents)
        implicit_authorities = self._detect_authorities(text, agents, mentions)
        power_dynamics = self._detect_power_dynamics(text, agents, implicit_authorities)
        subject_positions = self._detect_subject_positions(text, agents)

        return {
            "implicit_authorities": [auth.model_dump() for auth in implicit_authorities],
            "power_dynamics": power_dynamics.model_dump() if power_dynamics else None,
            "subject_positions": [pos.model_dump() for pos in subject_positions],
        }

    # ------------------------------------------------------------------
    # Extraction des agents (non modifié)
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # PATCH : localisation des mentions avec distinction sujet/objet
    # ------------------------------------------------------------------
    def _is_object_position(self, text: str, start: int) -> bool:
        """
        Heuristique : une mention d'agent est en position d'objet/possessif
        si elle est immédiatement précédée d'une préposition du type
        "de/du/des/au/chez/par/pour/sur..." (éventuellement suivie d'un
        déterminant). Ex. "chez son psychanalyste", "la réponse du patient".
        """
        window_start = max(0, start - _OBJECT_CONTEXT_WINDOW)
        preceding = text[window_start:start]
        return bool(_OBJECT_PREPOSITION_RE.search(preceding))

    def _find_agent_mentions(
        self, text: str, agents: Dict[str, Dict[str, Any]]
    ) -> List[Mention]:
        """Localise toutes les occurrences nommées de chaque agent, avec leur statut sujet/objet."""
        mentions: List[Mention] = []
        for agent_key, info in agents.items():
            pattern = r"\b" + re.escape(agent_key.lower()) + r"\b"
            for m in re.finditer(pattern, text, re.IGNORECASE):
                is_object = self._is_object_position(text, m.start())
                mentions.append((m.start(), m.end(), agent_key, is_object))
        return mentions

    def _find_pronoun_mentions(
        self, text: str, named_mentions: List[Mention]
    ) -> List[Mention]:
        """
        Résout heuristiquement "nous" (→ agent-sujet clinicien/technique le
        plus proche précédemment nommé) et "vous"/"votre"/"vos"/... (→
        toujours en position d'objet, vers l'agent-"subject" le plus proche
        précédemment nommé), afin de conserver l'attribution dans les
        phrases qui ne renomment plus les agents explicitement.
        """
        named_sorted = sorted(named_mentions, key=lambda mo: mo[0])
        pronoun_mentions: List[Mention] = []

        def _nearest_preceding(pos: int, role_ok) -> Optional[Mention]:
            candidates = [
                mo for mo in named_sorted
                if mo[0] < pos and not mo[3] and role_ok(mo[2])
            ]
            return candidates[-1] if candidates else None

        for pronoun in _SUBJECT_REFERENCE_PRONOUNS:
            for m in re.finditer(r"\b" + pronoun + r"\b", text, re.IGNORECASE):
                ref = _nearest_preceding(m.start(), lambda a: self.agent_roles.get(a) == "subject")
                if ref:
                    # Toujours objet : cf. limite documentée en tête de fichier.
                    pronoun_mentions.append((m.start(), m.end(), ref[2], True))

        for pronoun in _AGENT_REFERENCE_PRONOUNS:
            for m in re.finditer(r"\b" + pronoun + r"\b", text, re.IGNORECASE):
                ref = _nearest_preceding(
                    m.start(),
                    lambda a: self.agent_roles.get(a) in ("clinician", "technical_agent", "hybrid"),
                )
                if ref:
                    pronoun_mentions.append((m.start(), m.end(), ref[2], False))

        return pronoun_mentions

    def _find_all_mentions(
        self, text: str, agents: Dict[str, Dict[str, Any]]
    ) -> List[Mention]:
        named = self._find_agent_mentions(text, agents)
        pronouns = self._find_pronoun_mentions(text, named)
        return sorted(named + pronouns, key=lambda mo: mo[0])

    # ------------------------------------------------------------------
    # Segmentation de phrases (partagée), avec offsets
    # ------------------------------------------------------------------
    def _split_sentences_with_spans(self, text: str) -> List[Tuple[int, int]]:
        spans: List[Tuple[int, int]] = []
        start = 0
        for m in _SENTENCE_SPLIT_RE.finditer(text):
            end = m.start()
            if end > start:
                spans.append((start, end))
            start = m.end()
        if start < len(text):
            spans.append((start, len(text)))
        return spans

    def _split_sentences(self, text: str) -> List[str]:
        return [text[s:e] for s, e in self._split_sentences_with_spans(text)]

    # ------------------------------------------------------------------
    # PATCH : attribution des mécanismes de pouvoir par phrase, en ne
    # créditant que l'agent-sujet le plus plausible (et non plus tout
    # agent simplement co-présent dans la phrase).
    # ------------------------------------------------------------------
    def _detect_authorities(
        self,
        text: str,
        agents: Dict[str, Dict[str, Any]],
        mentions: List[Mention],
    ) -> List[ImplicitAuthority]:
        """Détecte les autorités exercées par chaque agent."""
        manifestations: Dict[str, List[str]] = {agent: [] for agent in agents}
        authority_types: Dict[str, set] = {agent: set() for agent in agents}
        weights: Dict[str, float] = {agent: 0.0 for agent in agents}

        sentence_spans = self._split_sentences_with_spans(text)

        for s_start, s_end in sentence_spans:
            sentence = text[s_start:s_end]

            # Agents-sujets (non-objets) présents dans cette phrase.
            subject_mentions_in_sentence = [
                mo for mo in mentions
                if s_start <= mo[0] < s_end and not mo[3] and mo[2] in agents
            ]
            distinct_agents = {mo[2] for mo in subject_mentions_in_sentence}

            if not distinct_agents:
                # Aucun agent-sujet identifiable dans cette phrase : on
                # préfère ne rien attribuer plutôt que de deviner (cf.
                # limite documentée en tête de fichier).
                continue

            for pattern, mechanism, weight in self.power_verbs:
                match = re.search(pattern, sentence, re.IGNORECASE)
                if not match:
                    continue
                match_abs_pos = s_start + match.start()

                if len(distinct_agents) == 1:
                    # Un seul agent-sujet dans la phrase : pas d'ambiguïté
                    # possible, peu importe la distance au marqueur.
                    credited_agents = distinct_agents
                else:
                    # Plusieurs agents-sujets : on ne crédite que ceux
                    # suffisamment proches du marqueur détecté (fenêtre de
                    # proximité), pour éviter qu'un agent mentionné loin
                    # dans une phrase-tiroir (discours rapporté imbriqué)
                    # n'hérite d'un mécanisme qui ne le concerne pas.
                    credited_agents = {
                        mo[2] for mo in subject_mentions_in_sentence
                        if abs(mo[0] - match_abs_pos) <= _PROXIMITY_WINDOW
                    }
                    if not credited_agents:
                        continue

                for agent_key in credited_agents:
                    manifestations[agent_key].append(mechanism.value)
                    authority_types[agent_key].add(self._infer_authority_type(mechanism))
                    weights[agent_key] += weight

        authorities: List[ImplicitAuthority] = []
        for agent, info in agents.items():
            counter_authorities = self._collect_counter_authorities(text, sentence_spans, mentions, agent)

            if authority_types[agent]:
                priority = [
                    AuthorityType.ONTOLOGICAL,
                    AuthorityType.CLINICAL_EPISTEMIC,
                    AuthorityType.NARRATIVE,
                    AuthorityType.STATISTICAL,
                ]
                dominant_type = next(
                    (t for t in priority if t in authority_types[agent]),
                    next(iter(authority_types[agent])),
                )
                confidence = min(weights[agent] / 3.0, 1.0)

                authorities.append(
                    ImplicitAuthority(
                        agent=agent, authority_type=dominant_type,
                        manifestations=list(dict.fromkeys(manifestations[agent])),
                        counter_authorities=counter_authorities,
                        confidence=round(confidence, 2),
                    )
                )
            else:
                # Agent présent dans le texte mais sans mécanisme de pouvoir
                # détecté (typiquement le sujet/patient) : on l'enregistre
                # quand même, en position de résistance à confiance nulle.
                authorities.append(
                    ImplicitAuthority(
                        agent=agent, authority_type=AuthorityType.RESISTANCE,
                        manifestations=[], counter_authorities=counter_authorities,
                        confidence=0.0,
                    )
                )

        return authorities

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

    # ------------------------------------------------------------------
    # Contre-pouvoirs (résistance) — logique inchangée, réutilise
    # désormais la segmentation de phrases partagée.
    # ------------------------------------------------------------------
    def _collect_counter_authorities(
        self,
        text: str,
        sentence_spans: List[Tuple[int, int]],
        mentions: List[Mention],
        dominant_agent: str,
    ) -> List[str]:
        counter_authorities: List[str] = []
        for pattern, description, _weight in self.resistance_patterns:
            for s_start, s_end in sentence_spans:
                sentence = text[s_start:s_end]
                if not re.search(pattern, sentence, re.IGNORECASE):
                    continue
                resistance_agent = self._find_resistance_agent_in_sentence(
                    s_start, s_end, mentions, dominant_agent
                )
                if resistance_agent:
                    entry = f"{resistance_agent} : {description}"
                    if entry not in counter_authorities:
                        counter_authorities.append(entry)
        return counter_authorities

    def _find_resistance_agent_in_sentence(
        self,
        s_start: int,
        s_end: int,
        mentions: List[Mention],
        dominant_agent: str,
    ) -> Optional[str]:
        """Trouve, dans une phrase donnée, un agent nommé différent de l'agent dominant."""
        for mo in mentions:
            if s_start <= mo[0] < s_end and mo[2] != dominant_agent:
                return mo[2]
        return None

    # ------------------------------------------------------------------
    # PATCH : dynamique de pouvoir — le choix du submissive_agent
    # privilégie désormais le rôle sémantique "subject" plutôt que
    # l'ordre d'insertion dans le dict des agents. Ceci ajoute une
    # protection supplémentaire : même si le calcul de confiance en
    # amont venait à se dégrader à nouveau pour une raison X, le
    # "patient"/"sujet" ne redeviendrait pas silencieusement le
    # dominant simplement parce qu'il apparaît en tête d'un dict.
    # ------------------------------------------------------------------
    def _detect_power_dynamics(
        self, text: str, agents: Dict[str, Dict[str, Any]],
        authorities: List[ImplicitAuthority],
    ) -> Optional[PowerDynamic]:
        """Détecte la dynamique de pouvoir principale entre agents."""
        active = [a for a in authorities if a.confidence > 0]
        if not active:
            return None

        dominant = max(active, key=lambda a: a.confidence)

        # 1) Préférence : un agent de rôle "subject" différent du dominant.
        submissive = None
        for agent, info in agents.items():
            if agent != dominant.agent and info.get("role") == "subject":
                submissive = agent
                break

        # 2) Sinon : l'agent actif le moins doté en autorité (le plus dominé).
        if not submissive:
            others = [a for a in active if a.agent != dominant.agent]
            if others:
                submissive = min(others, key=lambda a: a.confidence).agent

        # 3) Dernier recours : n'importe quel autre agent connu.
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

    # ------------------------------------------------------------------
    # Positions de sujet — logique inchangée (non concernée par le bug),
    # réutilise seulement la segmentation de phrases partagée.
    # ------------------------------------------------------------------
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
        sentences = [s for s in self._split_sentences(text) if subject_lower in s.lower()]

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
        sentences = [s for s in self._split_sentences(text) if subject_lower in s.lower()]

        # Si le sujet lui-même n'est jamais mentionné dans la même phrase que sa
        # résistance (cas du patient "muet" dont on rapporte la réponse au style
        # indirect), élargir la recherche à tout le texte.
        search_space = sentences if sentences else [text]

        for sentence in search_space:
            for pattern, description, _ in self.resistance_patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    return description
        return None
