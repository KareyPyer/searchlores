from typing import Dict, List, Any
from searchlores.core.plugin import InvestigationPlugin

class CounterPromptGenerator(InvestigationPlugin):
    """
    Génère des contre-prompts qui subvertissent les présupposés du prompt original
    """

    name = "CounterPromptGenerator"
    stratum = "subversive"

    COUNTER_STRATEGIES = {
        "inversion": "Et si c'était l'inverse ?",
        "situation": "Du point de vue de qui ?",
        "temporalite": "À quelle échelle temporelle ?",
        "exclusion": "Qui ou quoi est exclu de cette question ?",
        "materialite": "Quelles sont les conditions matérielles de possibilité ?"
    }

    def analyze(self, text: str, context: Any) -> Dict[str, Any]:
        findings = {
            "counter_prompts": [],
            "subversion_strategies": []
        }

        text_lower = text.lower()

        # Génération de contre-prompts selon les marqueurs détectés
        if any(word in text_lower for word in ["l'ia", "l'intelligence artificielle"]):
            findings["counter_prompts"].append({
                "strategy": "inversion",
                "prompt": "En quoi l'humain est-il déjà une forme d'IA biologique ?"
            })

        if "progrès" in text_lower or "avenir" in text_lower:
            findings["counter_prompts"].append({
                "strategy": "temporalite",
                "prompt": "Quels passés avons-nous oublié de considérer ?"
            })

        if "humanité" in text_lower or "tous" in text_lower:
            findings["counter_prompts"].append({
                "strategy": "situation",
                "prompt": "De quelle position située parle-t-on ?"
            })

        findings["subversion_strategies"] = list(self.COUNTER_STRATEGIES.keys())

        return findings