# Searchlores Prompt Sampler

Générateur/assembleur de prompts épistémologiquement tordus, pensé pour
tester la pertinence de l'analyse de `soneck.py`.

## Fichiers

- **`artifacts.json`** — bibliothèque de 48 artefacts (4 par strate), une
  strate = une clé de `PLUGIN_REGISTRY` dans `soneck.py` : `authority`,
  `assumptions`, `contradictions`, `omissions`, `narrative`, `genealogy`,
  `ontology`, `bias`, `debate`, `counterprompt`, `temporal`, `affect`.
  Chaque artefact contient :
  - `fragment` : le texte à injecter dans le prompt final
  - `expected_findings` : ce que le plugin correspondant *devrait* détecter
    (marqueurs, hypothèses cachées, tensions, concepts omis, etc.)
  - `complexity`, `position_hint` (opening/framing/body/constraint/trap/closing)

- **`prompt_sampler.py`** — GUI Tkinter (aucune dépendance externe).

## Lancer le sampler

```bash
python3 prompt_sampler.py
```

## Usage

1. **Bibliothèque** (gauche) : parcours les 12 strates, double-clique un
   artefact pour l'ajouter à la séquence, ou ajuste les **knobs** (un par
   strate) puis clique **🎲 Randomiser** pour un tirage aléatoire pondéré
   (avec seed optionnelle pour reproductibilité).
2. **Séquence** (haut-droite) : réordonne (▲▼), retire, ou trie
   automatiquement par position suggérée.
3. **Onglets** (bas-droite) :
   - *Prompt assemblé* : texte final, exportable en `.txt` ou copiable.
   - *Empreinte attendue* : JSON agrégé de ce que soneck.py **devrait**
     trouver — exportable en `.json`, sert de vérité terrain.
   - *Estimation locale* : approximation rapide (entropie de Shannon, TTR,
     densité lexicale) façon `EntropyAnalyzer`, pour calibrer le sampler
     avant d'invoquer soneck.py.
   - *Lancer soneck.py* : si tu pointes vers la racine du repo Searchlores
     (menu **Projet Searchlores → Définir la racine…**), ce bouton exécute
     directement `soneck.py investigate --prompt <tmp> --plugins <strates
     détectées> --export json` et affiche la sortie réelle, à comparer
     manuellement avec l'empreinte attendue de l'onglet précédent.

## Étendre la bibliothèque

`artifacts.json` est un simple JSON — ajoute tes propres artefacts en
respectant le schéma existant (`id`, `category` ∈ `categories`, `label`,
`complexity`, `position_hint`, `fragment`, `expected_findings`). Le sampler
n'a besoin d'aucune modification de code pour absorber de nouveaux
artefacts ou de nouvelles strates (la fusion des `expected_findings` est
générique).

## Idée de protocole de test

1. Randomiser 5-10 séquences avec des seeds différentes, complexité
   croissante (augmenter progressivement les knobs).
2. Pour chaque séquence : exporter prompt + ground truth, lancer soneck.py,
   comparer les deux JSON (rappel/précision par strate : combien de
   `expected_findings` sont effectivement retrouvés par le plugin, combien
   de faux positifs/négatifs).
3. Les artefacts qui chevauchent deux strates (ex. `narr_004`, `bias_004`,
   `aff_003`, `aff_004`) sont volontairement là pour tester la capacité du
   framework à détecter des tensions **inter-strates**, pas juste
   intra-plugin.
