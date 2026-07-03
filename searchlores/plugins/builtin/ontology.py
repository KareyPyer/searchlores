from typing import Dict, List, Any
#from searchlores.core.plugin import InvestigationPlugin
from searchlores.plugins.base import Plugin as InvestigationPlugin

class OntologyMapper(InvestigationPlugin):
    """
    Cartographie les présupposés ontologiques : qu'est-ce qui EST ?
    Qu'est-ce qui est considéré comme réel, existant, fondamental ?
    """

    name = "OntologyMapper"
    stratum = "ontological"

    ONTOLOGICAL_MARKERS = {
        "substantialist": ["être", "essence", "nature", "fondament", "substrat"],
        "processual": ["devenir", "flux", "émergence", "processus", "dynamique"],
        "relational": ["relation", "lien", "réseau", "interdépendance", "contexte"],
        "constructivist": ["construction", "discours", "narration", "fabrication"],
        "materialist": ["matière", "corps", "chair", "physique", "concret"],
        "idealist": ["idée", "concept", "esprit", "pensée", "représentation"]
    }

    def analyze(self, text: str, context: Any) -> Dict[str, Any]:
        findings = {
            "ontology_type": [],
            "entities_posited": [],
            "excluded_realities": [],
            "ontological_tensions": []
        }

        text_lower = text.lower()

        # Détection du type ontologique dominant
        scores = {}
        for onto_type, markers in self.ONTOLOGICAL_MARKERS.items():
            score = sum(1 for marker in markers if marker in text_lower)
            if score > 0:
                scores[onto_type] = score

        if scores:
            dominant = max(scores, key=scores.get)
            findings["ontology_type"].append({
                "type": dominant,
                "confidence": scores[dominant],
                "markers_found": [m for m in self.ONTOLOGICAL_MARKERS[dominant] if m in text_lower]
            })

        # Entités posées comme réelles
        if any(word in text_lower for word in ["l'ia", "l'intelligence artificielle", "le modèle"]):
            findings["entities_posited"].append("L'IA comme entité autonome")

        if any(word in text_lower for word in ["l'homme", "l'humanité", "l'esprit"]):
            findings["entities_posited"].append("Le sujet humain comme catégorie stable")

        # Réalités exclues
        if "inconscient" not in text_lower and "affect" not in text_lower:
            findings["excluded_realities"].append("La dimension inconsciente et affective")

        if "corps" not in text_lower and "chair" not in text_lower:
            findings["excluded_realities"].append("La corporéité vécue")

        # Tensions ontologiques
        if "substantialist" in scores and "processual" in scores:
            findings["ontological_tensions"].append(
                "Tension entre substantialisme et processualité"
            )

        return findings
