from typing import Dict, List, Any
from searchlores.plugins.base import Plugin as InvestigationPlugin

class TemporalStrataDetector(InvestigationPlugin):
    """
    Détecte les couches temporelles et les anachronismes dans le discours
    """
    name = "TemporalStrataDetector"
    stratum = "temporal"

    TEMPORAL_MARKERS = {
        "presentisme": ["maintenant", "actuel", "aujourd'hui", "récent"],
        "futurisme": ["avenir", "futur", "demain", "prochain"],
        "passéisme": ["tradition", "héritage", "historique", "ancien"],
        "deep_time": ["millénaire", "siècle", "évolution", "longue durée"]
    }

    def run(self, context: Any) -> None:
        """Méthode requise par le moteur pour exécuter le plugin."""
        text = context.prompt.lower()
        findings = self.analyze(text, context)

        # Stocke les résultats dans le contexte pour que le moteur les récupère
        context.findings[self.name] = findings

    def analyze(self, text: str, context: Any) -> Dict[str, Any]:
        findings = {
            "temporal_dominance": [],
            "temporal_blind_spots": [],
            "anachronisms": []
        }
        text_lower = text.lower()

        # Détection de la dominance temporelle
        scores = {}
        for temporal_type, markers in self.TEMPORAL_MARKERS.items():
            score = sum(1 for marker in markers if marker in text_lower)
            if score > 0:
                scores[temporal_type] = score

        if scores:
            dominant = max(scores, key=scores.get)
            findings["temporal_dominance"].append({
                "type": dominant,
                "intensity": scores[dominant]
            })

        # Angles morts temporels
        if "deep_time" not in scores:
            findings["temporal_blind_spots"].append("Absence de perspective longue")
        if "passéisme" not in scores and "presentisme" in scores:
            findings["temporal_blind_spots"].append("Effacement des héritages historiques")

        return findings
