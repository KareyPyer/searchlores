from typing import Dict, List, Any
#from searchlores.core.plugin import InvestigationPlugin
from searchlores.plugins.base import Plugin as InvestigationPlugin

class DebateAnalyzer(InvestigationPlugin):
    """
    Analyse la structure argumentative et les positions dialectiques
    """

    name = "DebateAnalyzer"
    stratum = "dialectical"

    def analyze(self, text: str, context: Any) -> Dict[str, Any]:
        findings = {
            "argumentative_structure": [],
            "positions_identified": [],
            "excluded_voices": [],
            "dialectical_tensions": []
        }

        text_lower = text.lower()

        # Structure argumentative
        if "parce que" in text_lower or "car" in text_lower or "puisque" in text_lower:
            findings["argumentative_structure"].append("Argumentation causale")

        if "mais" in text_lower or "cependant" in text_lower or "toutefois" in text_lower:
            findings["argumentative_structure"].append("Structure dialectique (thèse-antithèse)")

        # Positions identifiées
        if any(word in text_lower for word in ["pour", "défend", "soutient"]):
            findings["positions_identified"].append("Position affirmative")

        if any(word in text_lower for word in ["contre", "critique", "rejette"]):
            findings["positions_identified"].append("Position critique")

        # Voix exclues
        if not any(word in text_lower for word in ["certains", "d'autres", "opposants"]):
            findings["excluded_voices"].append("Absence de reconnaissance des positions adverses")

        # Tensions dialectiques
        if "thèse" in text_lower and "antithèse" in text_lower:
            findings["dialectical_tensions"].append("Tension dialectique explicite")

        return findings
