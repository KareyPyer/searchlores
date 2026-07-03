from typing import Dict, List, Any
from searchlores.plugins.base import Plugin as InvestigationPlugin

class AffectMapper(InvestigationPlugin):
    """
    Cartographie les dimensions affectives et émotionnelles du discours
    """
    name = "AffectMapper"
    stratum = "affective"

    AFFECTIVE_FIELDS = {
        "crainte": ["peur", "danger", "menace", "risque", "catastrophe"],
        "espoir": ["espoir", "promesse", "potentiel", "opportunité", "avenir"],
        "colere": ["injustice", "domination", "oppression", "résistance"],
        "fascination": ["fascination", "mystère", "merveille", "extraordinaire"],
        "melancolie": ["perte", "disparition", "nostalgie", "fin"]
    }

    def run(self, context: Any) -> None:
        """Méthode requise par le moteur pour exécuter le plugin."""
        text = context.prompt.lower()
        findings = self.analyze(text, context)

        # Stocke les résultats dans le contexte pour que le moteur les récupère
        context.findings[self.name] = findings

        # Ajout optionnel d'un vecteur de pouvoir si des affects sont détectés
        scores = findings.get("affective_tone", [])
        if scores:
            affects_detected = [score["dominant_affect"] for score in scores]
            if hasattr(context, 'power_vectors'):
                context.power_vectors.append(
                    f"Charge affective détectée: {affects_detected} mobilisée pour orienter la réception du discours"
                )

    def analyze(self, text: str, context: Any) -> Dict[str, Any]:
        findings = {
            "affective_tone": [],
            "emotional_strategies": [],
            "suppressed_affects": []
        }
        text_lower = text.lower()

        # Détection du ton affectif dominant
        scores = {}
        for affect, markers in self.AFFECTIVE_FIELDS.items():
            score = sum(1 for marker in markers if marker in text_lower)
            if score > 0:
                scores[affect] = score

        if scores:
            dominant = max(scores, key=scores.get)
            findings["affective_tone"].append({
                "dominant_affect": dominant,
                "intensity": scores[dominant]
            })

        # Stratégies émotionnelles
        if "crainte" in scores and "espoir" in scores:
            findings["emotional_strategies"].append("Alternance peur/espoir")

        # Affects supprimés
        if not scores:
            findings["suppressed_affects"].append("Discours présenté comme neutre (affect masqué)")

        return findings
