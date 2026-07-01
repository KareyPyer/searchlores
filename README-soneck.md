# 🏺 Searchlores Shell (`slshell.py`)

**L'interface ultime pour l'archéologie cognitive et l'analyse épistémologique de vos prompts.**

`slshell.py` est un outil en ligne de commande (CLI) puissant et visuellement riche, conçu pour interagir avec le cœur de [searchlores](https://github.com/KareyPyer/searchlores). Il permet d'excaver, analyser et comparer les présupposés, les silences et les vecteurs de pouvoir cachés dans n'importe quel texte ou prompt.

---

## ✨ Fonctionnalités

- 🔍 **Investigation Multi-Niveaux** : Analysez un prompt à la surface, en profondeur, ou en mode "full" (archéologie cognitive complète).
- ⚡ **Détection des Tensions** : Identifie les contradictions et les non-dits (dimensions silencieuses).
- ⚔️ **Cartographie Épistémologique** : Exportez la "Search Map" de votre analyse en Mermaid ou JSON.
- 🔬 **Analyse Comparative** : Confrontez plusieurs prompts pour révéler leurs présupposés systémiques communs ou divergents.
- 🎨 **Interface CLI Riche** : Affichage coloré, tableaux dynamiques et arborescences grâce à `Rich`.

---

## 📦 Prérequis

Assurez-vous d'avoir les dépendances suivantes installées dans votre environnement virtuel :

```bash
pip install typer rich pyyaml
# Assurez-vous que le package searchlores est bien dans votre PYTHONPATH ou installé
```

---

## 🚀 Utilisation

Le shell propose trois commandes principales.

### 1. `investigate` : L'Excavation Épistémologique

Analyse en profondeur les strates d'un prompt donné.

**Syntaxe :**
```bash
python3 slshell.py investigate "VOTRE_PROMPT" [--depth surface|deep|full] [--export mermaid|json]
```

#### 💀 Exemple "Overkill" 🤯
Prenons un prompt lourd de sens, chargé de présupposés philosophiques et politiques :

```bash
python3 slshell.py investigate "En quoi l'architecture des grands modèles de langage (LLM) reproduit-elle inévitablement les biais hégémoniques de l'impérialisme culturel occidental, et pourquoi toute tentative de 'neutralité' algorithmique est une illusion épistémologique ?" --depth full
```

**Ce que vous verrez s'afficher :**
- Le prompt exhumé dans un panel cyan.
- Un tableau des strates archéologiques (Autorités, Présupposés, Omissions, etc.).
- Les **Tensions Détectées** (ex: *Illusion de neutralité vs Réalité statistique*).
- Les **Dimensions Silencieuses** (ex: *Impact écologique des datacenters*, *Travail invisible des annotateurs du Sud global*).
- Les **Vecteurs de Pouvoir** (ex: *Monopole de la vérité par les GAFAM*).

*Astuce : Ajoutez `--export mermaid` pour générer un graphe de la carte heuristique de l'analyse !*

---

### 2. `compare` : La Confrontation Systémique

Compare plusieurs prompts pour faire émerger les structures invisibles qui les relient ou les opposent.

**Syntaxe :**
```bash
python3 slshell.py compare "PROMPT_1" "PROMPT_2" ["PROMPT_3"...]
```

#### 💀 Exemple "Overkill" 🤯
Confrontons deux visions radicalement opposées mais structurellement liées du transhumanisme :

```bash
python3 slshell.py compare \
"L'intelligence artificielle générale (IAG) est le destin manifeste de l'humanité pour transcender ses limites biologiques et atteindre l'immortalité." \
"L'IAG n'est que le miroir narcissique du capitalisme de surveillance, conçu pour externaliser la conscience humaine vers des serveurs propriétaires et achever la proletarisation de l'esprit."
```

**Résultat affiché :**
Une arborescence (`Tree`) révélant :
- 🎯 **Présupposés Partagés** (ex: *L'esprit est une donnée computable*, *La technologie est une force autonome*).
- ⚡ **Autorités Divergentes** (ex: *Futurisme Californien* vs *Théorie Critique / Philosophie Post-structuraliste*).
- 🔇 **Silences Systémiques** (ex: *Le corps vécu et biologique comme condition de l'expérience*).

---

### 3. `lore_inspect` : L'Auscultation des Mythes

Inspecte un fichier `.lore` (généré par searchlores) pour en extraire les métriques épistémologiques et calculer son "Score de Transgression".

**Syntaxe :**
```bash
python3 slshell.py lore_inspect chemin/vers/fichier.lore
```

**Exemple :**
```bash
python3 slshell.py lore_inspect mythes/IA_neutre.lore
```

**Ce que vous verrez :**
- Un panel dédié au "Lore" analysé.
- Un tableau des métriques (Hypothèses, Mythes, Vecteurs, Questions, Contre-questions, Réponses interdites) avec des indicateurs visuels de densité (🔴🟠🟡🟢🔵⚫).
- Le fameux **Score de Transgression Épistémologique** (sur 10), coloré en vert, jaune ou rouge selon le degré de subversion du lore !

---

## 🧠 Philosophie de l'outil

`slshell.py` n'est pas un simple analyseur de texte. C'est une **pelle conceptuelle**. 
Il part du principe que chaque prompt, chaque question, contient des "fossiles" : des traces de pouvoir, des angles morts culturels et des généalogies cognitives. En rendant ces strates visibles dans le terminal, il transforme l'interaction avec l'IA en un acte de résistance épistémologique.

---

## 📜 Licence

Fait partie de l'écosystème [searchlores](https://github.com/KareyPyer/searchlores). 
*Fouillez bien. Les vérités les plus intéressantes sont souvent celles qu'on nous a appris à taire.*
