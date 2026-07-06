# Intégration des 5 plugins avancés — notes importantes

Ce dossier contient les nouveaux fichiers issus de ta session de
conception avec Qwen ("Archéologie des pouvoirs discursifs"), prêts à
copier dans ton repo `searchlores`. **Lis cette page avant de merger quoi
que ce soit** : je t'explique ce qui est testé et garanti, et ce qui reste
à vérifier de ton côté.

## Ce qui est fourni, testé, et fonctionne tel quel

```
searchlores/plugins/advanced/
├── base.py                       # AdvancedPlugin (contrat + validation)
├── performative_contradiction.py # strate 10
├── narrative_level.py            # strate 11
├── epistemic_regime.py           # strate 12
├── implicit_authority.py         # strate 13
├── foucault_analyzer.py          # strate 14 (synthèse, dépend des 4 autres)
└── __init__.py                   # ADVANCED_PLUGINS

searchlores/core/orchestrator.py  # PluginOrchestrator (DAG, tri topologique)
run_advanced_plugins.py           # CLI autonome, ne touche à rien d'existant
tests/test_advanced_plugins.py    # 27 tests, tous verts
examples/therapy.lore             # Prompt #12 (le psychanalyste-LLM)
docs/RFCs/RFC-0012-AdvancedPlugins.md
```

J'ai exécuté ces 27 tests localement (avec un shim minimal de `pydantic`
pour la validation, ta vraie installation `pydantic` fonctionnera de la
même façon) et fait tourner le pipeline complet sur le Prompt #12 via
`run_advanced_plugins.py` : les 5 plugins s'exécutent dans le bon ordre
(DAG), et `FoucaultAnalyzer` reçoit bien les résultats des 4 autres pour
sa synthèse généalogique.

**Utilisation immédiate, sans rien modifier dans ton repo actuel :**
```bash
pip install pydantic --break-system-packages   # si pas déjà présent
python3 run_advanced_plugins.py --file examples/therapy.lore --format markdown
```

## Ce que je n'ai pas pu vérifier — important

Je n'ai pas pu récupérer le contenu réel de tes fichiers `soneck.py`,
`core/engine.py`, `core/context.py` ou `plugins/builtin/*.py` : mes outils
de lecture web n'ont renvoyé que le titre des pages GitHub, jamais le code
source. Je n'ai donc **aucune certitude** sur :

- la forme exacte de ton `InvestigationContext` actuel (attributs
  `layers` ? `findings` ? autre chose ?)
- la signature exacte de `engine.register()` / `engine.run()`
- les options déjà supportées par ton CLI `soneck.py`

Conséquence pratique : **je n'ai pas touché à `soneck.py`, `engine.py` ou
`context.py`**, et je n'ai pas non plus recréé le "Stratum1SurfaceAnalyzer
... Stratum9EthicalAnalyzer" que Qwen a proposé dans la conversation — ce
sont des strates 1-9 entièrement réinventées par Qwen, qui dupliqueraient
très probablement les 9 (ou 12, selon la version) plugins que ton repo a
déjà (`authority.py`, `assumptions.py`, `contradictions.py`, etc. d'après
la description de ton repo). Les ajouter aveuglément risquerait de créer
des doublons ou des conflits de noms.

Ce que je te recommande à la place, pour l'intégration profonde dans ton
CLI existant :

1. Ouvre ton `core/context.py` actuel et regarde comment un plugin
   standard écrit ses résultats (`context.findings[...] = ...` ? une
   liste `context.layers.append(...)` ?).
2. Dans ton `core/engine.py`, après la boucle qui exécute les plugins
   standards, ajoute :
   ```python
   from searchlores.plugins.advanced import ADVANCED_PLUGINS
   from searchlores.core.orchestrator import PluginOrchestrator

   if advanced_mode:  # ton flag existant, ou un nouveau
       orchestrator = PluginOrchestrator()
       for plugin_class in ADVANCED_PLUGINS:
           orchestrator.register(plugin_class())

       orchestrator.run_all(
           prompt,
           context=context,  # ou le dict de résultats déjà accumulés
           on_result=lambda name, results: context.findings.update(results),  # adapte à ta structure
           on_error=lambda name, msg: context.errors.append({"plugin": name, "error": msg}),  # adapte
       )
   ```
3. Ajoute une option `--advanced` (ou équivalent) à ton CLI pour activer
   ce bloc.

## Documents de la session Qwen non retenus tels quels

La conversation contenait aussi des propositions de refonte plus larges
(un CLI `argparse` complet pour `soneck.py`, un `InvestigationContext`
étendu avec `advanced_analysis`/`cross_analysis`, 9 "strates standards"
Stratum1-9). Je ne les ai **pas** copiées dans cette livraison : elles
supposent une architecture que je n'ai pas pu confirmer face à ton code
réel, et les livrer telles quelles risquerait de casser ton `soneck.py`
actuel si sa structure diffère. Le RFC (`docs/RFCs/RFC-0012-AdvancedPlugins.md`)
documente ces pistes pour référence, mais l'intégration dans ton CLI reste
un geste manuel à faire toi-même (ou avec un futur assistant ayant un
accès direct — lecture de fichiers — à ton repo, par exemple Claude Code
ou Qwen re-connecté à ton dépôt local).

## Dépendances

Seule nouvelle dépendance : `pydantic` (déjà utilisée par le projet selon
la conversation). Aucune autre bibliothèque lourde.
