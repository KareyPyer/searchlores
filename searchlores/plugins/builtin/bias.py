from typing import Dict, List, Any
#from searchlores.core.plugin import InvestigationPlugin
from searchlores.plugins.base import Plugin as InvestigationPlugin

class BiasDetector(InvestigationPlugin):
    """
    Détecte les biais cognitifs, culturels et idéologiques
    """

    name = "BiasDetector"
    stratum = "ideological"

    BIAS_PATTERNS = {
        "techno_solutionnisme": {
            "markers": ["solution", "résoudre", "optimiser", "améliorer", "progress"],
            "description": "Croyance que la technologie résout tous les problèmes"
        },
        "determinisme_technologique": {
            "markers": ["inévitable", "destin", "futur", "va", "inéluctable"],
            "description": "La technologie comme force autonome déterminant l'histoire"
        },
        "universalisme_abstrait": {
            "markers": ["tous", "universel", "humanité", "global", "mondial"],
            "description": "Effacement des différences et des positions situées"
        },
        "neutralite_illusoire": {
            "markers": ["neutre", "objectif", "impartial", "factuel", "données"],
            "description": "Posture de neutralité masquant des positions de pouvoir"
        },
        "anthropocentrisme": {
            "markers": ["homme", "humain", "conscience", "sujet", "raison"],
            "description": "L'humain comme mesure de toute chose"
        },
        "presentisme": {
            "markers": ["maintenant", "actuel", "révolution", "nouveau", "innovation"],
            "description": "Effacement des temporalités longues et des héritages"
        }
    }

    def analyze(self, text: str, context: Any) -> Dict[str, Any]:
        findings = {
            "biases_detected": [],
            "cultural_position": [],
            "blind_spots": []
        }

        text_lower = text.lower()

        # Détection des biais
        for bias_name, bias_data in self.BIAS_PATTERNS.items():
            markers_found = [m for m in bias_data["markers"] if m in text_lower]
            if len(markers_found) >= 2:
                findings["biases_detected"].append({
                    "bias": bias_name,
                    "description": bias_data["description"],
                    "markers": markers_found,
                    "intensity": len(markers_found)
                })

        # Position culturelle
        if any(word in text_lower for word in ["progrès", "innovation", "développement"]):
            findings["cultural_position"].append("Narratif du progrès occidental")

        if any(word in text_lower for word in ["marché", "compétition", "performance"]):
            findings["cultural_position"].append("Logique néolibérale")

        # Angles morts
        if not any(word in text_lower for word in ["pouvoir", "domination", "inégalité"]):
            findings["blind_spots"].append("Absence d'analyse des rapports de pouvoir")

        if not any(word in text_lower for word in ["corps", "affect", "émotion"]):
            findings["blind_spots"].append("Effacement de la dimension corporelle et affective")

        return findings
