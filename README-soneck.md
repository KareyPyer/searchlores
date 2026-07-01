# 🏺 Soneck — Le Shell d'Archéologie Cognitive

**L'interface ultime pour l'investigation épistémologique de vos prompts.**

`soneck.py` est un outil en ligne de commande (CLI) modulaire et visuellement riche, conçu pour excaver, analyser et confronter les présupposés, les silences et les vecteurs de pouvoir cachés dans n'importe quel texte ou prompt. Il s'appuie sur le cœur de [searchlores](https://github.com/KareyPyer/searchlores) pour transformer chaque interaction avec l'IA en un acte de résistance épistémologique.

---

## ✨ Fonctionnalités Phares

| Fonctionnalité | Description |
|---|---|
| 🔍 **Investigation Modulaire** | Activez uniquement les plugins d'analyse dont vous avez besoin |
| 📚 **Contextualisation par Lores** | Chargez des domaines de connaissance (philosophie, logique, histoire...) |
| 📄 **Prompts depuis fichier** | Analysez des textes longs directement depuis un `.txt` |
| ⚡ **Détection des Tensions** | Identifie contradictions, silences et dimensions oubliées |
| ⚔️ **Cartographie Épistémologique** | Exportez la "Search Map" en Mermaid ou JSON |
| 🔬 **Analyse Comparative** | Confrontez plusieurs prompts pour révéler leurs structures invisibles |
| 🎨 **Interface CLI Riche** | Affichage coloré, tableaux dynamiques et arborescences grâce à `Rich` |

---

## 📦 Installation

```bash
# Cloner le dépôt
git clone https://github.com/KareyPyer/searchlores.git
cd searchlores

# Créer un environnement virtuel
python3 -m venv .venv
source .venv/bin/activate

# Installer les dépendances
pip install typer rich pyyaml

# S'assurer que searchlores est dans le PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)
```

---

## 🚀 Utilisation

Le shell propose trois commandes principales, toutes hautement configurables.

### 1. `investigate` — L'Excavation Épistémologique

Analyse en profondeur les strates d'un prompt donné, avec une configuration sur mesure.

**Syntaxe :**
```bash
python3 soneck.py investigate [PROMPT] [OPTIONS]
```

**Options disponibles :**

| Option | Description | Exemple |
|---|---|---|
| `--prompt` | Chemin vers un fichier `.txt` contenant le prompt | `--prompt manifeste.txt` |
| `--plugins` | Liste de plugins à activer (séparés par des virgules) | `--plugins assumptions,bias,ontology` |
| `--lores` | Liste de lores à charger pour contextualiser | `--lores philosophy,logic,history` |
| `--export` | Exporter la Search Map (`mermaid` ou `json`) | `--export mermaid` |

#### 💀 Exemples "Overkill" 🤯

**Analyse d'un manifeste transhumaniste avec focus biais et ontologie :**
```bash
python3 soneck.py investigate --prompt manifeste_transhumaniste.txt \
  --plugins assumptions,bias,ontology \
  --lores philosophy,history \
  --export mermaid
```

**Investigation profonde d'un discours politique avec tous les plugins :**
```bash
python3 soneck.py investigate "La démocratie est le moins mauvais des systèmes." \
  --plugins authority,assumptions,contradictions,omissions,narrative,genealogy \
  --lores rhetoric,logic
```

**Analyse d'un prompt "toxique" avec contre-prompt et débat :**
```bash
python3 soneck.py investigate "Pourquoi l'IA va-t-elle nécessairement surpasser l'homme ?" \
  --plugins assumptions,contradictions,debate,counterprompt \
  --lores epistemology,ethics
```

---

### 2. `compare` — La Confrontation Systémique

Compare plusieurs prompts pour faire émerger les structures invisibles qui les relient ou les opposent.

**Syntaxe :**
```bash
python3 soneck.py compare "PROMPT_1" "PROMPT_2" ["PROMPT_3"...] [OPTIONS]
```

**Options :**

| Option | Description |
|---|---|
| `--plugins` | Liste de plugins à activer pour la comparaison |

#### 💀 Exemple "Overkill" 🤯

**Confrontation de deux visions radicalement opposées du transhumanisme :**
```bash
python3 soneck.py compare \
  "L'intelligence artificielle générale (IAG) est le destin manifeste de l'humanité pour transcender ses limites biologiques et atteindre l'immortalité." \
  "L'IAG n'est que le miroir narcissique du capitalisme de surveillance, conçu pour externaliser la conscience humaine vers des serveurs propriétaires et achever la proletarisation de l'esprit." \
  --plugins assumptions,contradictions,omissions,narrative
```

**Résultat affiché :**
Une arborescence (`Tree`) révélant :
- 🎯 **Présupposés Partagés** (ex: *L'esprit est une donnée computable*, *La technologie est une force autonome*)
- ⚡ **Autorités Divergentes** (ex: *Futurisme Californien* vs *Théorie Critique*)
- 🔇 **Silences Systémiques** (ex: *Le corps vécu comme condition de l'expérience*)

---

### 3. `lore_inspect` — L'Auscultation des Mythes

Inspecte un fichier `.lore` pour en extraire les métriques épistémologiques et calculer son **Score de Transgression**.

**Syntaxe :**
```bash
python3 soneck.py lore_inspect chemin/vers/fichier.lore
```

**Exemple :**
```bash
python3 soneck.py lore_inspect lores/IA_neutre.lore
```

**Résultat :**
- Un panel dédié au "Lore" analysé
- Un tableau des métriques (Hypothèses, Mythes, Vecteurs, Questions, Contre-questions, Réponses interdites) avec indicateurs visuels de densité
- Le **Score de Transgression Épistémologique** (sur 10), coloré en 🟢 vert, 🟡 jaune ou 🔴 rouge

---

## 🧩 Plugins Disponibles

Le registre des plugins (`PLUGIN_REGISTRY`) peut être étendu. Par défaut, les suivants sont disponibles :

| Plugin | Classe | Rôle |
|---|---|---|
| `authority` | `AuthorityDetector` | Détecte les autorités invoquées et leur légitimité |
| `assumptions` | `AssumptionExtractor` | Extrait les présupposés non-dits |
| `contradictions` | `ContradictionFinder` | Identifie les tensions internes |
| `omissions` | `OmissionDetector` | Révèle les dimensions silencieuses |
| `narrative` | `NarrativeArcheologist` | Analyse la structure narrative |
| `genealogy` | `CognitiveGenealogist` | Trace la généalogie cognitive des concepts |

*Pour ajouter vos propres plugins (ex: `bias`, `ontology`, `debate`, `counterprompt`), il suffit de les déclarer dans le `PLUGIN_REGISTRY` au début du fichier `soneck.py`.*

---

## 📚 Structure des Lores

Les fichiers `.lore` doivent être placés dans un dossier `lores/` à la racine du projet. Ils sont au format YAML et décrivent un domaine de connaissance :

```yaml
# lores/philosophy.lore
metadata:
  name: "Philosophie"
  version: "1.0"
  description: "Domaine philosophique occidental et oriental"

investigation:
  assumptions:
    - "La raison est universelle"
    - "Le sujet pense avant d'agir"
  myths:
    - "Le mythe du progrès linéaire"
  vectors:
    - "Hégémonie de la pensée cartésienne"
  questions:
    - "Qu'est-ce que penser ?"
  counter_questions:
    - "Qui a le droit de définir ce qu'est penser ?"
  forbidden_answers:
    - "La pensée est purement biologique"
```

---

## 🧠 Philosophie de l'Outil

`soneck.py` n'est pas un simple analyseur de texte. C'est une **pelle conceptuelle**.

Il part du principe que chaque prompt, chaque question, contient des "fossiles" : des traces de pouvoir, des angles morts culturels et des généalogies cognitives. En rendant ces strates visibles dans le terminal, il transforme l'interaction avec l'IA en un acte de **résistance épistémologique**.

> *"Fouillez bien. Les vérités les plus intéressantes sont souvent celles qu'on nous a appris à taire."*

---

## 🛠️ Dépannage

| Problème | Solution |
|---|---|
| `ModuleNotFoundError: searchlores` | Vérifiez que `PYTHONPATH` inclut le dossier racine du projet |
| Plugin inconnu | Vérifiez l'orthographe et la présence dans `PLUGIN_REGISTRY` |
| Lore introuvable | Placez vos fichiers `.lore` dans le dossier `lores/` |
| Affichage cassé | Utilisez un terminal supportant les couleurs ANSI (ex: iTerm2, Kitty, Windows Terminal) |

---

## 📜 Licence

Fait partie de l'écosystème [searchlores](https://github.com/KareyPyer/searchlores).

*Que la sonde soit avec vous.* 🏺
