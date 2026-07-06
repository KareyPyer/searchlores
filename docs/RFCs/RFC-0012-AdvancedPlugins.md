# RFC-0012 — Plugins avancés (strates 10-14)

- **Statut** : Proposé
- **Origine** : session de conception "Archéologie des pouvoirs discursifs"
  (Qwen, conception ; consolidation et intégration ultérieures)
- **Prompt de référence** : Prompt #12, le "psychanalyste-LLM" (voir
  `examples/therapy.lore`)

## 1. Motivation

L'analyse du Prompt #12 par les strates existantes de Searchlores a révélé
des angles morts récurrents :

- **Autorité implicite** non détectée : qui, dans le prompt, exerce un
  pouvoir de définition sans jamais être nommé comme "autorité" ?
- **Contradictions performatives** ignorées : un énoncé peut nier quelque
  chose (ex. l'existence d'un sujet) tout en accomplissant un acte qui
  présuppose ce même quelque chose (ex. "nous allons reconstruire *votre*
  récit").
- **Niveaux narratifs enchâssés** non cartographiés : qui parle, à quel
  niveau de récit, et quelles voix restent absentes ?
- **Régimes épistémiques** non distingués : un texte peut mélanger
  plusieurs régimes de savoir (clinique, neuro-scientifique, poétique...)
  sans que leurs tensions ou hybridations soient rendues visibles.
- **Silences et rapports de pouvoir** non analysés : ce qui n'est *pas* dit
  (l'éthique, le corps, l'affect) est souvent plus révélateur que ce qui
  est dit.

Ce RFC introduit 5 plugins qui portent la profondeur archéologique de 9 à
14 strates.

## 2. Les 5 plugins

| Strate | Plugin | Nom (`name`) | Dépendances |
|---|---|---|---|
| 10 | `PerformativeContradictionDetector` | `performative_contradiction` | aucune |
| 11 | `NarrativeLevelAnalyzer` | `narrative_level` | aucune |
| 12 | `EpistemicRegimeDetector` | `epistemic_regime` | aucune |
| 13 | `ImplicitAuthorityDetector` | `implicit_authority` | aucune |
| 14 | `FoucaultAnalyzer` | `foucault_analyzer` | les 4 précédentes |
| 15 | `GeneralSemanticsAnalyzer` | `general_semantics` | aucune |

`FoucaultAnalyzer` est le seul plugin synthétique : il croise les résultats
des 4 autres (via le paramètre `context` de `analyze()`) pour produire une
synthèse généalogique. C'est pourquoi il déclare des `dependencies` — voir
§4.

### 2.1 `PerformativeContradictionDetector`

Détecte les couples (négation, acte performatif) situés dans des phrases
différentes : une négation ("le 'je' est une fiction") et un acte qui
présuppose ce qui vient d'être nié ("nous allons reconstruire votre
récit"). Sortie : liste de `PerformativeContradiction {statement,
contradicts_with, type, severity}`.

### 2.2 `NarrativeLevelAnalyzer`

Segmente le texte par marqueurs de discours (guillemets, tirets) et
attribue un niveau d'enchâssement à chaque segment (0 = narrateur externe,
1+ = discours enchâssé). Détecte trois types de tensions : `contradiction`
(conflit entre niveaux), `silence` (voix attendue mais absente — ex. le
patient dont on rapporte la réponse sans jamais la citer), `rupture`
(saut brusque de niveau).

### 2.3 `EpistemicRegimeDetector`

Classifie chaque phrase selon 8 régimes de savoir (neuro-scientifique,
clinique, poétique-esthétique, philosophique, éthique, technique,
narratif, statistique) via des lexiques pondérés. Détecte les tensions :
`transition` (changement brusque), `hybridation` (mélange dans un même
segment), `conflit` / `exclusion` (tensions structurelles pré-définies,
ex. absence de régime éthique dans un contexte clinique).

### 2.4 `ImplicitAuthorityDetector`

Extrait les agents du texte (rôles clinicien/sujet/narrateur/technique),
détecte les verbes de pouvoir associés à chacun (définition ontologique,
prescription thérapeutique, réduction statistique, contrôle épistémique,
contrôle narratif, catégorisation), et cartographie la dynamique de
pouvoir dominant/subordonné ainsi que les contre-pouvoirs (résistance
poétique, silence, refus...).

### 2.5 `FoucaultAnalyzer`

Synthèse foucaldienne : silences structurels (domaines sémantiques
attendus mais absents — corporel, éthique, historique, social, politique,
affectif, matériel, temporel, relationnel), régimes de vérité (énoncés
acceptés vs structurellement exclus), positions de sujet et leur
subjectivation/résistance, conditions de possibilité du discours, et
insights généalogiques croisant tout ce qui précède.

### 2.6 `GeneralSemanticsAnalyzer` (hommage à Van Vogt / Korzybski)

Strate ajoutée dans un second temps, en hommage au *Monde des Non-A*
d'A.E. Van Vogt (lui-même inspiré de la Sémantique Générale d'Alfred
Korzybski). Détecte six violations classiques : **identification**
(carte confondue avec le territoire, via le "est" d'identité sur des
labels évaluatifs), **allness** (totalisation illégitime : "tous",
"toujours", "jamais"...), **orientation à deux valeurs** (faux dilemme,
tiers exclu), **élémentalisme** (scission verbale d'un tout : "corps et
esprit", "raison contre émotion"...), **absence d'indexation**
(généralisation catégorielle non qualifiée : "les X sont Y"), et
**réaction-signal** (emphase typographique trahissant un réflexe
sémantique non différé). Calcule un **indice Non-A** (0 = discours
pleinement aristotélicien, 1 = nuancé/indexé/multi-valué) — clin d'œil
direct à l'entraînement de Gilbert Gosseyn.

Ce plugin est autonome (`dependencies = []`), mais rien n'empêche de le
raccorder plus tard à `FoucaultAnalyzer` (ses violations pourraient
enrichir la synthèse généalogique) en l'ajoutant à ses `dependencies`.

## 3. Architecture

```
searchlores/
├── plugins/
│   └── advanced/
│       ├── base.py                      # AdvancedPlugin (contrat + validation)
│       ├── performative_contradiction.py
│       ├── narrative_level.py
│       ├── epistemic_regime.py
│       ├── implicit_authority.py
│       ├── foucault_analyzer.py
│       └── __init__.py                  # ADVANCED_PLUGINS
├── core/
│   └── orchestrator.py                  # PluginOrchestrator (DAG, tri topologique)
run_advanced_plugins.py                  # CLI autonome (voir §5)
tests/test_advanced_plugins.py
examples/therapy.lore
```

Chaque plugin hérite de `AdvancedPlugin` (`plugins/advanced/base.py`), qui
valide à la définition de la classe (`__init_subclass__`) que `name` est
défini — erreur immédiate (`TypeError`) plutôt qu'à l'exécution.

## 4. Orchestration par DAG

`PluginOrchestrator` (`core/orchestrator.py`) résout l'ordre d'exécution
par tri topologique de Kahn sur les `dependencies` déclarées. Propriétés :

- Si un plugin lève une exception, ses dépendants sont sautés (erreur
  tracée) mais les branches indépendantes du graphe continuent.
- Une dépendance vers un plugin non enregistré, ou un cycle, lève
  `ValueError` **avant** toute exécution (fail-fast).
- L'orchestrateur est autonome : il ne dépend d'aucun autre module de
  Searchlores, et peut être utilisé indépendamment de `core/engine.py`.

## 5. Intégration

Deux niveaux d'intégration sont proposés :

1. **Immédiat, sans risque** : `run_advanced_plugins.py` à la racine du
   repo exécute les 5 plugins via `PluginOrchestrator` sans toucher au
   moteur (`InvestigationEngine`) existant.
   ```bash
   python3 run_advanced_plugins.py --file examples/therapy.lore --format markdown
   ```
2. **Intégration profonde dans `soneck.py` / `core/engine.py`** : voir
   `README_INTEGRATION.md` à la racine de cette livraison, qui documente
   comment brancher `PluginOrchestrator` dans votre `InvestigationEngine`
   actuel. Cette étape nécessite de connaître la forme exacte de votre
   `InvestigationContext` (attributs `layers`/`findings`/autre) — voir la
   note de prudence dans ce même document.

## 6. Contraintes respectées

- Pure Python 3.11+, une seule dépendance : `pydantic` (déjà utilisée
  dans le projet pour la validation des structures de données).
- Aucune dépendance lourde (pas de spaCy, pas de transformers, pas
  d'appel API externe) : conforme à l'esprit "sans jamais les soumettre
  aux LLMs" du projet.
- Chaque plugin est autonome et testable indépendamment
  (`tests/test_advanced_plugins.py`, 27 tests, tous verts).

## 7. Limites connues

- Les heuristiques (regex + lexiques pondérés) sont volontairement
  explicables mais grossières : elles ne remplacent pas une analyse
  linguistique complète. Comme le note la session de conception
  elle-même, "l'outil ne trouvera que les silences qu'il a été programmé
  pour voir" — les lexiques de `expected_domains` (FoucaultAnalyzer) et
  `regime_lexicons` (EpistemicRegimeDetector) sont ouverts à extension.
- `_detect_contradiction` (NarrativeLevelAnalyzer) et les lexiques de
  `ImplicitAuthorityDetector` sont calibrés sur un français contemporain ;
  ils dégradent en anglais ou dans d'autres langues.
- Les scores de confiance/sévérité sont des heuristiques relatives, pas
  des probabilités calibrées.

## 8. Alternatives envisagées

- Un unique "méga-plugin" qui ferait tout en une passe : rejeté, car il
  aurait rendu impossible l'exécution/test indépendant de chaque strate,
  et aurait empêché l'orchestration par dépendances (FoucaultAnalyzer a
  explicitement besoin des résultats des 4 autres).
- Une classe de base `Protocol` plutôt qu'`ABC` : `ABC` a été préférée
  pour la validation fail-fast via `__init_subclass__`, qui n'est pas
  disponible avec un simple `Protocol`.
