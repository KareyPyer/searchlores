"""
Classe de base pour les plugins avancés Searchlores (strates 10-14).

Issu de la session de conception avec Qwen (archéologie des pouvoirs
discursifs). Définit le contrat commun et valide les métadonnées de
chaque plugin dès sa définition (fail-fast à l'import plutôt qu'à
l'exécution).
"""
from typing import List, Dict, Any
from abc import ABC


class AdvancedPlugin(ABC):
    """
    Classe de base abstraite pour les plugins avancés.

    Chaque plugin concret doit définir :
      - name (str)          : identifiant unique, utilisé par l'orchestrateur
                               et par InvestigationContext.register_plugin()
      - dependencies (list) : noms des plugins (valeur de leur `name`) qui
                               doivent s'exécuter avant celui-ci

    Validation automatique via __init_subclass__ :
      - lève TypeError si `name` n'est pas défini ou n'est pas une str
      - normalise `dependencies` à [] si absent, lève TypeError si ce n'est
        pas une liste
    """

    name: str
    dependencies: List[str]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        if not hasattr(cls, "name") or not isinstance(cls.name, str) or not cls.name:
            raise TypeError(
                f"{cls.__name__} doit définir un attribut de classe 'name' (str non vide)"
            )

        if not hasattr(cls, "dependencies"):
            cls.dependencies = []
        elif not isinstance(cls.dependencies, list):
            raise TypeError(
                f"{cls.__name__}.dependencies doit être une liste, "
                f"reçu {type(cls.dependencies)}"
            )

    def analyze(self, text: str, context: Any = None) -> Dict[str, Any]:
        """
        Exécute l'analyse et retourne les résultats sous forme de dict
        JSON-sérialisable. Doit être implémentée par chaque plugin concret.

        `context` (optionnel) donne accès aux résultats des plugins déjà
        exécutés dans le pipeline (utile pour les plugins qui déclarent des
        `dependencies`, ex. FoucaultAnalyzer).
        """
        raise NotImplementedError(f"{self.__class__.__name__} doit implémenter analyze()")

    # Alias pour compatibilité avec un éventuel appel `plugin.run(text)`
    def run(self, text: str, context: Any = None) -> Dict[str, Any]:
        return self.analyze(text, context)
