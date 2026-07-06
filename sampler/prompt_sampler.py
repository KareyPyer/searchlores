#!/usr/bin/env python3
"""
Searchlores Prompt Sampler
===========================

Un "sampler" à la Tkinter pour assembler des prompts épistémologiquement
tordus à partir d'une bibliothèque d'artefacts JSON, et générer en parallèle
l'empreinte attendue (ground truth) que soneck.py est censé retrouver.

Usage :
    python3 prompt_sampler.py

Fonctionnement général :
  1. Charger artifacts.json (bibliothèque d'artefacts, une entrée par
     "piège" épistémologique, catégorisée par plugin soneck.py).
  2. Piocher des artefacts (manuellement ou via les "knobs" de sampling
     aléatoire par catégorie), les ordonner en séquence.
  3. Prévisualiser le prompt assemblé et une estimation locale rapide
     d'entropie / TTR (mêmes métriques que EntropyAnalyzer).
  4. Exporter :
       - le prompt final en .txt (à soumettre à `searchlores investigate`)
       - l'empreinte attendue en .json (ground truth pour comparaison)
  5. Optionnel : lancer directement `soneck.py investigate ... --export json`
     sur le prompt assemblé si le projet Searchlores est disponible en local,
     et afficher le résultat réel à côté de l'empreinte attendue.

Aucune dépendance externe : uniquement la bibliothèque standard (tkinter,
json, subprocess, math, random, collections).
"""

import json
import math
import os
import random
import subprocess
import sys
import tempfile
import tkinter as tk
from collections import Counter, defaultdict
from pathlib import Path
from tkinter import ttk, filedialog, messagebox, simpledialog

APP_TITLE = "Searchlores Prompt Sampler — Générateur de prompts tordus"
DEFAULT_LIBRARY = Path(__file__).with_name("artifacts.json")

POSITION_ORDER = ["opening", "framing", "body", "constraint", "trap", "closing"]
POSITION_LABELS = {
    "opening": "Ouverture",
    "framing": "Cadrage",
    "body": "Corps",
    "constraint": "Contrainte",
    "trap": "Piège",
    "closing": "Clôture",
}


# --------------------------------------------------------------------------
# Utilitaires
# --------------------------------------------------------------------------

def deep_merge(target: dict, source: dict) -> None:
    """Fusionne récursivement `source` dans `target`.
    - listes : concaténées (avec dédoublonnage préservant l'ordre)
    - scalaires : accumulés dans une liste sous la clé '_values' si conflit
    - dicts : fusion récursive
    """
    for key, value in source.items():
        if key not in target:
            target[key] = value
            continue
        existing = target[key]
        if isinstance(existing, list) and isinstance(value, list):
            for v in value:
                if v not in existing:
                    existing.append(v)
        elif isinstance(existing, dict) and isinstance(value, dict):
            deep_merge(existing, value)
        elif existing == value:
            continue
        else:
            # Conflit de scalaires (ex: intensity 2 puis 4) -> on garde la liste des occurrences
            bucket_key = f"{key}__occurrences"
            bucket = target.setdefault(bucket_key, [])
            if not bucket:
                bucket.append(existing)
            bucket.append(value)
            target[key] = max(existing, value) if isinstance(existing, (int, float)) and isinstance(value, (int, float)) else existing


def local_entropy_metrics(text: str) -> dict:
    """Reproduit grossièrement les métriques de METRICS_DOCUMENTATION.md
    (EntropyAnalyzer) sans dépendance externe, pour une pré-estimation
    rapide avant de lancer soneck.py lui-même.
    """
    tokens = [t.strip(".,;:!?()«»\"'").lower() for t in text.split()]
    tokens = [t for t in tokens if t]
    if not tokens:
        return {"token_entropy": 0.0, "type_token_ratio": 0.0, "lexical_density": 0.0, "n_tokens": 0}

    counts = Counter(tokens)
    total = len(tokens)
    entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())

    ttr = len(counts) / total

    stopwords = {
        "le", "la", "les", "de", "des", "du", "un", "une", "et", "ou", "que",
        "qui", "à", "en", "est", "sont", "ce", "cette", "ces", "pour", "dans",
        "sur", "par", "avec", "sans", "au", "aux", "se", "sa", "son", "ses",
        "tu", "il", "elle", "nous", "vous", "ils", "elles", "je", "ne", "pas",
        "plus", "moins", "mais", "donc", "or", "ni", "car", "toute", "tout",
        "tous", "toutes", "aucun", "aucune", "être", "avoir", "afin"
    }
    lexical_tokens = [t for t in tokens if t not in stopwords]
    lexical_density = len(lexical_tokens) / total

    return {
        "token_entropy": round(entropy, 3),
        "type_token_ratio": round(ttr, 3),
        "lexical_density": round(lexical_density, 3),
        "n_tokens": total,
    }


def entropy_level(value: float) -> str:
    if value < 3.0:
        return "🟢 FAIBLE"
    if value <= 5.0:
        return "🟡 MODÉRÉE"
    return "🔴 ÉLEVÉE"


# --------------------------------------------------------------------------
# Application
# --------------------------------------------------------------------------

class PromptSamplerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1360x860")
        self.minsize(1080, 680)

        self.library_path = DEFAULT_LIBRARY
        self.artifacts_by_id = {}
        self.categories = []
        self.sequence = []  # liste d'ids d'artefacts, dans l'ordre choisi
        self.knob_vars = {}  # category -> IntVar (sampling aléatoire)

        self._build_style()
        self._build_menu()
        self._build_layout()

        self._load_library(self.library_path, silent=True)

    # ---------------------------------------------------------- UI shell

    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Header.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("Sub.TLabel", font=("Segoe UI", 9), foreground="#555")
        style.configure("Treeview", rowheight=24)

    def _build_menu(self):
        menubar = tk.Menu(self)

        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Charger une bibliothèque JSON…", command=self.action_load_library)
        filemenu.add_command(label="Recharger la bibliothèque courante", command=lambda: self._load_library(self.library_path))
        filemenu.add_separator()
        filemenu.add_command(label="Exporter le prompt (.txt)…", command=self.action_export_prompt)
        filemenu.add_command(label="Exporter l'empreinte attendue (.json)…", command=self.action_export_ground_truth)
        filemenu.add_separator()
        filemenu.add_command(label="Quitter", command=self.destroy)
        menubar.add_cascade(label="Fichier", menu=filemenu)

        projmenu = tk.Menu(menubar, tearoff=0)
        projmenu.add_command(label="Définir la racine du projet Searchlores…", command=self.action_set_project_root)
        menubar.add_cascade(label="Projet Searchlores", menu=projmenu)

        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="À propos", command=self._show_about)
        menubar.add_cascade(label="Aide", menu=helpmenu)

        self.config(menu=menubar)
        self.project_root = None

    def _show_about(self):
        messagebox.showinfo(
            "À propos",
            "Searchlores Prompt Sampler\n\n"
            "Génère des prompts épistémologiquement complexes/tordus par "
            "assemblage d'artefacts calibrés, avec empreinte attendue "
            "exportable pour comparaison avec la sortie de soneck.py.",
        )

    def _build_layout(self):
        root = ttk.Frame(self, padding=6)
        root.pack(fill="both", expand=True)

        # PanedWindow horizontal principal : [bibliothèque | (séquence+preview) ]
        main_pane = ttk.Panedwindow(root, orient="horizontal")
        main_pane.pack(fill="both", expand=True)

        left = ttk.Frame(main_pane, padding=(0, 0, 6, 0))
        right = ttk.Frame(main_pane)
        main_pane.add(left, weight=2)
        main_pane.add(right, weight=3)

        self._build_library_panel(left)
        self._build_right_panels(right)

        # Barre de statut
        self.status_var = tk.StringVar(value="Prêt.")
        status = ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w", padding=(6, 2))
        status.pack(fill="x", side="bottom")

    # ------------------------------------------------------ left: library

    def _build_library_panel(self, parent):
        ttk.Label(parent, text="🗃️ Bibliothèque d'artefacts", style="Header.TLabel").pack(anchor="w")
        ttk.Label(parent, text=str(self.library_path), style="Sub.TLabel").pack(anchor="w", pady=(0, 6))
        self.library_path_label = parent.winfo_children()[-1]

        # Treeview groupé par catégorie
        columns = ("complexity", "position")
        self.tree = ttk.Treeview(parent, columns=columns, show="tree headings", height=20)
        self.tree.heading("#0", text="Artefact")
        self.tree.heading("complexity", text="Complexité")
        self.tree.heading("position", text="Position")
        self.tree.column("#0", width=340)
        self.tree.column("complexity", width=80, anchor="center")
        self.tree.column("position", width=90, anchor="center")
        self.tree.pack(fill="both", expand=True, side="top")
        self.tree.bind("<Double-1>", lambda e: self.action_add_selected())

        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        # Aperçu du fragment sélectionné
        ttk.Label(parent, text="Aperçu du fragment :", style="Sub.TLabel").pack(anchor="w", pady=(8, 0))
        self.preview_fragment = tk.Text(parent, height=4, wrap="word")
        self.preview_fragment.pack(fill="x")
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        btns = ttk.Frame(parent)
        btns.pack(fill="x", pady=6)
        ttk.Button(btns, text="Ajouter à la séquence →", command=self.action_add_selected).pack(side="left")
        ttk.Button(btns, text="Développer tout", command=lambda: self._expand_all(True)).pack(side="left", padx=4)
        ttk.Button(btns, text="Réduire tout", command=lambda: self._expand_all(False)).pack(side="left")

        # Knobs de sampling aléatoire par catégorie
        knob_frame = ttk.LabelFrame(parent, text="🎛️ Knobs du Sampler (tirage aléatoire par strate)", padding=8)
        knob_frame.pack(fill="x", pady=(10, 0))
        self.knob_container = ttk.Frame(knob_frame)
        self.knob_container.pack(fill="x")

        seed_row = ttk.Frame(knob_frame)
        seed_row.pack(fill="x", pady=(8, 0))
        ttk.Label(seed_row, text="Seed (reproductibilité) :").pack(side="left")
        self.seed_var = tk.StringVar(value="")
        ttk.Entry(seed_row, textvariable=self.seed_var, width=14).pack(side="left", padx=6)

        action_row = ttk.Frame(knob_frame)
        action_row.pack(fill="x", pady=(8, 0))
        ttk.Button(action_row, text="🎲 Randomiser la séquence", command=self.action_randomize).pack(side="left")
        ttk.Button(action_row, text="Tout à zéro", command=self.action_zero_knobs).pack(side="left", padx=6)
        ttk.Button(action_row, text="Tout à 1", command=lambda: self.action_set_all_knobs(1)).pack(side="left")

    def _expand_all(self, state: bool):
        for item in self.tree.get_children(""):
            self.tree.item(item, open=state)

    def _on_tree_select(self, _event=None):
        sel = self.tree.selection()
        self.preview_fragment.delete("1.0", "end")
        if not sel:
            return
        item = sel[0]
        art_id = self.tree.item(item, "tags")
        if art_id and art_id[0] in self.artifacts_by_id:
            art = self.artifacts_by_id[art_id[0]]
            self.preview_fragment.insert("1.0", art["fragment"])

    # ------------------------------------------------------ right panels

    def _build_right_panels(self, parent):
        pane = ttk.Panedwindow(parent, orient="vertical")
        pane.pack(fill="both", expand=True)

        top = ttk.Frame(pane, padding=(6, 0, 0, 0))
        bottom = ttk.Frame(pane, padding=(6, 6, 0, 0))
        pane.add(top, weight=2)
        pane.add(bottom, weight=3)

        # --- Séquence assemblée ---
        seq_frame = ttk.Frame(top)
        seq_frame.pack(fill="both", expand=True, side="left")
        ttk.Label(seq_frame, text="🧬 Séquence assemblée (ordre = ordre d'assemblage du prompt)", style="Header.TLabel").pack(anchor="w")
        self.seq_listbox = tk.Listbox(seq_frame, height=14, selectmode="browse")
        self.seq_listbox.pack(fill="both", expand=True, pady=(4, 4))
        self.seq_listbox.bind("<<ListboxSelect>>", lambda e: self._refresh_preview())

        seq_btns = ttk.Frame(seq_frame)
        seq_btns.pack(fill="x")
        ttk.Button(seq_btns, text="▲ Monter", command=lambda: self._move_seq(-1)).pack(side="left")
        ttk.Button(seq_btns, text="▼ Descendre", command=lambda: self._move_seq(1)).pack(side="left", padx=4)
        ttk.Button(seq_btns, text="✕ Retirer", command=self.action_remove_selected).pack(side="left")
        ttk.Button(seq_btns, text="🧹 Vider la séquence", command=self.action_clear_sequence).pack(side="left", padx=4)
        ttk.Button(seq_btns, text="↕ Trier par position suggérée", command=self.action_sort_by_position).pack(side="left")

        # --- Compteurs / score ---
        score_frame = ttk.LabelFrame(top, text="📊 Score du prompt", padding=8)
        score_frame.pack(fill="y", side="right", padx=(8, 0))
        self.score_var = tk.StringVar(value="—")
        ttk.Label(score_frame, textvariable=self.score_var, justify="left").pack(anchor="w")

        # --- Notebook: Preview / Empreinte attendue / Analyse réelle ---
        notebook = ttk.Notebook(bottom)
        notebook.pack(fill="both", expand=True)

        # Onglet 1: Prompt assemblé
        prompt_tab = ttk.Frame(notebook, padding=6)
        notebook.add(prompt_tab, text="📝 Prompt assemblé")
        self.prompt_text = tk.Text(prompt_tab, wrap="word", undo=False)
        self.prompt_text.pack(fill="both", expand=True)
        self.prompt_text.configure(state="disabled")

        export_row = ttk.Frame(prompt_tab)
        export_row.pack(fill="x", pady=(6, 0))
        ttk.Button(export_row, text="💾 Exporter le prompt (.txt)", command=self.action_export_prompt).pack(side="left")
        ttk.Button(export_row, text="📋 Copier dans le presse-papiers", command=self.action_copy_prompt).pack(side="left", padx=6)

        # Onglet 2: Empreinte attendue (ground truth)
        gt_tab = ttk.Frame(notebook, padding=6)
        notebook.add(gt_tab, text="🎯 Empreinte attendue (ground truth)")
        self.gt_text = tk.Text(gt_tab, wrap="word", undo=False)
        self.gt_text.pack(fill="both", expand=True)
        self.gt_text.configure(state="disabled")
        gt_export_row = ttk.Frame(gt_tab)
        gt_export_row.pack(fill="x", pady=(6, 0))
        ttk.Button(gt_export_row, text="💾 Exporter l'empreinte (.json)", command=self.action_export_ground_truth).pack(side="left")

        # Onglet 3: Estimation locale (entropie rapide, sans soneck.py)
        est_tab = ttk.Frame(notebook, padding=6)
        notebook.add(est_tab, text="📐 Estimation locale (entropie)")
        self.est_text = tk.Text(est_tab, wrap="word", undo=False, height=8)
        self.est_text.pack(fill="both", expand=True)
        self.est_text.configure(state="disabled")

        # Onglet 4: Lancer soneck.py réellement
        run_tab = ttk.Frame(notebook, padding=6)
        notebook.add(run_tab, text="⚙️ Lancer soneck.py")
        run_top = ttk.Frame(run_tab)
        run_top.pack(fill="x")
        ttk.Label(run_top, text="Racine du projet Searchlores :").pack(side="left")
        self.project_root_var = tk.StringVar(value="(non défini — menu 'Projet Searchlores')")
        ttk.Label(run_top, textvariable=self.project_root_var, style="Sub.TLabel").pack(side="left", padx=6)
        ttk.Button(run_top, text="Choisir…", command=self.action_set_project_root).pack(side="left")
        ttk.Button(run_top, text="▶ Lancer l'analyse", command=self.action_run_soneck).pack(side="left", padx=10)

        self.run_output = tk.Text(run_tab, wrap="word", undo=False)
        self.run_output.pack(fill="both", expand=True, pady=(6, 0))
        self.run_output.configure(state="disabled")

    # ---------------------------------------------------------------- library loading

    def action_load_library(self):
        path = filedialog.askopenfilename(
            title="Choisir une bibliothèque d'artefacts JSON",
            filetypes=[("JSON", "*.json"), ("Tous les fichiers", "*.*")],
        )
        if path:
            self._load_library(Path(path))

    def _load_library(self, path: Path, silent=False):
        if not path.exists():
            if not silent:
                messagebox.showerror("Erreur", f"Fichier introuvable : {path}")
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            messagebox.showerror("Erreur de lecture JSON", str(exc))
            return

        artifacts = data.get("artifacts", [])
        self.artifacts_by_id = {a["id"]: a for a in artifacts}
        self.categories = data.get("categories") or sorted({a["category"] for a in artifacts})
        self.library_path = path
        self.library_path_label.configure(text=str(path))
        self.sequence = []

        self._populate_tree()
        self._populate_knobs()
        self._refresh_all()
        self.status_var.set(f"Bibliothèque chargée : {len(artifacts)} artefacts, {len(self.categories)} strates.")

    def _populate_tree(self):
        self.tree.delete(*self.tree.get_children(""))
        by_cat = defaultdict(list)
        for art in self.artifacts_by_id.values():
            by_cat[art["category"]].append(art)

        for cat in self.categories:
            cat_node = self.tree.insert("", "end", text=f"▸ {cat}  ({len(by_cat.get(cat, []))})", open=False, tags=("__category__",))
            for art in sorted(by_cat.get(cat, []), key=lambda a: a["id"]):
                label = f"{art['label']}"
                self.tree.insert(
                    cat_node, "end",
                    text=label,
                    values=(art.get("complexity", "?"), POSITION_LABELS.get(art.get("position_hint", ""), art.get("position_hint", ""))),
                    tags=(art["id"],),
                )

    def _populate_knobs(self):
        for child in self.knob_container.winfo_children():
            child.destroy()
        self.knob_vars = {}
        for i, cat in enumerate(self.categories):
            row = i // 2
            col = i % 2
            frame = ttk.Frame(self.knob_container)
            frame.grid(row=row, column=col, sticky="w", padx=(0, 14), pady=2)
            ttk.Label(frame, text=cat, width=15).pack(side="left")
            var = tk.IntVar(value=0)
            spin = ttk.Spinbox(frame, from_=0, to=20, width=4, textvariable=var)
            spin.pack(side="left")
            self.knob_vars[cat] = var

    # ---------------------------------------------------------------- sequence actions

    def action_add_selected(self):
        sel = self.tree.selection()
        added = 0
        for item in sel:
            tags = self.tree.item(item, "tags")
            if tags and tags[0] != "__category__" and tags[0] in self.artifacts_by_id:
                self.sequence.append(tags[0])
                added += 1
        if added:
            self._refresh_all()
        else:
            messagebox.showinfo("Info", "Sélectionne un artefact (pas une catégorie) dans la bibliothèque.")

    def action_remove_selected(self):
        sel = self.seq_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        del self.sequence[idx]
        self._refresh_all()

    def action_clear_sequence(self):
        self.sequence = []
        self._refresh_all()

    def _move_seq(self, direction: int):
        sel = self.seq_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        new_idx = idx + direction
        if 0 <= new_idx < len(self.sequence):
            self.sequence[idx], self.sequence[new_idx] = self.sequence[new_idx], self.sequence[idx]
            self._refresh_all()
            self.seq_listbox.selection_set(new_idx)

    def action_sort_by_position(self):
        def sort_key(art_id):
            art = self.artifacts_by_id[art_id]
            pos = art.get("position_hint", "body")
            try:
                return POSITION_ORDER.index(pos)
            except ValueError:
                return len(POSITION_ORDER)
        self.sequence.sort(key=sort_key)
        self._refresh_all()

    def action_zero_knobs(self):
        for var in self.knob_vars.values():
            var.set(0)

    def action_set_all_knobs(self, n: int):
        for var in self.knob_vars.values():
            var.set(n)

    def action_randomize(self):
        seed_text = self.seed_var.get().strip()
        rng = random.Random(seed_text) if seed_text else random.Random()

        by_cat = defaultdict(list)
        for art in self.artifacts_by_id.values():
            by_cat[art["category"]].append(art["id"])

        new_sequence = []
        for cat, var in self.knob_vars.items():
            n = var.get()
            pool = by_cat.get(cat, [])
            if n <= 0 or not pool:
                continue
            n = min(n, len(pool)) if n <= len(pool) else n
            if n <= len(pool):
                chosen = rng.sample(pool, n)
            else:
                # Permettre plus de tirages que d'artefacts distincts : tirage avec remise
                chosen = [rng.choice(pool) for _ in range(n)]
            new_sequence.extend(chosen)

        rng.shuffle(new_sequence)
        # Puis on réordonne selon la position suggérée pour un prompt plus cohérent
        def sort_key(art_id):
            art = self.artifacts_by_id[art_id]
            pos = art.get("position_hint", "body")
            try:
                return POSITION_ORDER.index(pos)
            except ValueError:
                return len(POSITION_ORDER)
        new_sequence.sort(key=sort_key)

        self.sequence = new_sequence
        self._refresh_all()
        self.status_var.set(f"Séquence randomisée : {len(self.sequence)} artefacts (seed={seed_text or 'aléatoire'}).")

    # ---------------------------------------------------------------- refresh / compute

    def _refresh_all(self):
        self._refresh_seq_listbox()
        self._refresh_preview()
        self._refresh_ground_truth()
        self._refresh_estimation()
        self._refresh_score()

    def _refresh_seq_listbox(self):
        self.seq_listbox.delete(0, "end")
        for art_id in self.sequence:
            art = self.artifacts_by_id.get(art_id)
            if not art:
                continue
            pos = POSITION_LABELS.get(art.get("position_hint", ""), art.get("position_hint", ""))
            self.seq_listbox.insert("end", f"[{art['category']}] {art['label']}  ({pos}, cplx {art.get('complexity','?')})")

    def _assembled_prompt(self) -> str:
        parts = [self.artifacts_by_id[a]["fragment"] for a in self.sequence if a in self.artifacts_by_id]
        return "\n\n".join(parts)

    def _refresh_preview(self):
        text = self._assembled_prompt()
        self.prompt_text.configure(state="normal")
        self.prompt_text.delete("1.0", "end")
        self.prompt_text.insert("1.0", text if text else "(séquence vide — ajoute des artefacts à gauche)")
        self.prompt_text.configure(state="disabled")

    def _compute_ground_truth(self) -> dict:
        gt = {
            "meta": {
                "library": str(self.library_path),
                "n_artifacts": len(self.sequence),
                "artifact_ids": list(self.sequence),
                "categories_present": sorted({self.artifacts_by_id[a]["category"] for a in self.sequence if a in self.artifacts_by_id}),
            },
            "expected_findings_by_plugin": {},
        }
        merged = gt["expected_findings_by_plugin"]
        for art_id in self.sequence:
            art = self.artifacts_by_id.get(art_id)
            if not art:
                continue
            for cat, findings in art.get("expected_findings", {}).items():
                bucket = merged.setdefault(cat, {"source_artifacts": [], "findings": {}})
                bucket["source_artifacts"].append(art_id)
                deep_merge(bucket["findings"], findings)
        return gt

    def _refresh_ground_truth(self):
        gt = self._compute_ground_truth()
        self.gt_text.configure(state="normal")
        self.gt_text.delete("1.0", "end")
        self.gt_text.insert("1.0", json.dumps(gt, indent=2, ensure_ascii=False))
        self.gt_text.configure(state="disabled")
        self._last_ground_truth = gt

    def _refresh_estimation(self):
        text = self._assembled_prompt()
        metrics = local_entropy_metrics(text)
        level = entropy_level(metrics["token_entropy"]) if metrics["n_tokens"] else "—"
        body = (
            f"Tokens analysés : {metrics['n_tokens']}\n"
            f"Entropie de Shannon (approx.) : {metrics['token_entropy']} bits  →  {level}\n"
            f"Type-Token Ratio : {metrics['type_token_ratio']}\n"
            f"Densité lexicale (approx., hors mots-outils) : {metrics['lexical_density']}\n\n"
            "Rappel des seuils (cf. METRICS_DOCUMENTATION.md) :\n"
            "  🟢 FAIBLE   < 3.0 bits\n"
            "  🟡 MODÉRÉE  3.0 – 5.0 bits\n"
            "  🔴 ÉLEVÉE   > 5.0 bits\n\n"
            "Ceci est une estimation locale grossière (sans dépendance externe), "
            "à utiliser uniquement pour calibrer le sampler avant de lancer la "
            "véritable analyse via soneck.py."
        )
        self.est_text.configure(state="normal")
        self.est_text.delete("1.0", "end")
        self.est_text.insert("1.0", body)
        self.est_text.configure(state="disabled")

    def _refresh_score(self):
        total_complexity = sum(self.artifacts_by_id[a].get("complexity", 0) for a in self.sequence if a in self.artifacts_by_id)
        cat_counts = Counter(self.artifacts_by_id[a]["category"] for a in self.sequence if a in self.artifacts_by_id)
        lines = [
            f"Artefacts : {len(self.sequence)}",
            f"Score de complexité cumulé : {total_complexity}",
            f"Strates couvertes : {len(cat_counts)}/{len(self.categories)}",
            "",
            "Par strate :",
        ]
        for cat in self.categories:
            n = cat_counts.get(cat, 0)
            marker = "●" * n if n else "○"
            lines.append(f"  {cat:<15} {marker} ({n})")
        self.score_var.set("\n".join(lines))

    # ---------------------------------------------------------------- exports

    def action_export_prompt(self):
        if not self.sequence:
            messagebox.showwarning("Séquence vide", "Ajoute au moins un artefact avant d'exporter.")
            return
        path = filedialog.asksaveasfilename(
            title="Exporter le prompt assemblé",
            defaultextension=".txt",
            filetypes=[("Texte", "*.txt")],
            initialfile="prompt_sample.txt",
        )
        if not path:
            return
        Path(path).write_text(self._assembled_prompt(), encoding="utf-8")
        self.status_var.set(f"Prompt exporté : {path}")

    def action_export_ground_truth(self):
        if not self.sequence:
            messagebox.showwarning("Séquence vide", "Ajoute au moins un artefact avant d'exporter.")
            return
        path = filedialog.asksaveasfilename(
            title="Exporter l'empreinte attendue",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile="ground_truth.json",
        )
        if not path:
            return
        gt = self._compute_ground_truth()
        Path(path).write_text(json.dumps(gt, indent=2, ensure_ascii=False), encoding="utf-8")
        self.status_var.set(f"Empreinte attendue exportée : {path}")

    def action_copy_prompt(self):
        text = self._assembled_prompt()
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status_var.set("Prompt copié dans le presse-papiers.")

    # ---------------------------------------------------------------- soneck.py runner

    def action_set_project_root(self):
        path = filedialog.askdirectory(title="Choisir la racine du projet Searchlores (contenant soneck.py)")
        if not path:
            return
        soneck = Path(path) / "soneck.py"
        if not soneck.exists():
            if not messagebox.askyesno("soneck.py introuvable", f"Aucun soneck.py trouvé dans {path}. Utiliser quand même ce dossier ?"):
                return
        self.project_root = Path(path)
        self.project_root_var.set(str(self.project_root))

    def action_run_soneck(self):
        if not self.sequence:
            messagebox.showwarning("Séquence vide", "Ajoute au moins un artefact avant de lancer l'analyse.")
            return
        if not self.project_root:
            messagebox.showwarning("Projet non défini", "Définis d'abord la racine du projet Searchlores (menu 'Projet Searchlores').")
            return

        soneck_path = self.project_root / "soneck.py"
        if not soneck_path.exists():
            messagebox.showerror("Erreur", f"soneck.py introuvable dans {self.project_root}")
            return

        plugins = sorted({self.artifacts_by_id[a]["category"] for a in self.sequence if a in self.artifacts_by_id})

        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
            tmp.write(self._assembled_prompt())
            tmp_path = tmp.name

        cmd = [
            sys.executable, str(soneck_path), "investigate",
            "--prompt", tmp_path,
            "--plugins", ",".join(plugins),
            "--export", "json",
        ]

        self.run_output.configure(state="normal")
        self.run_output.delete("1.0", "end")
        self.run_output.insert("1.0", f"$ {' '.join(cmd)}\n\n(exécution en cours…)\n")
        self.run_output.configure(state="disabled")
        self.update_idletasks()

        try:
            result = subprocess.run(
                cmd, cwd=str(self.project_root),
                capture_output=True, text=True, timeout=60
            )
            output = result.stdout or ""
            if result.returncode != 0:
                output += f"\n\n--- STDERR (code {result.returncode}) ---\n{result.stderr}"
        except Exception as exc:
            output = f"Échec de l'exécution : {exc}"
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        self.run_output.configure(state="normal")
        self.run_output.delete("1.0", "end")
        self.run_output.insert("1.0", f"$ {' '.join(cmd)}\n\n{output}")
        self.run_output.configure(state="disabled")
        self.status_var.set("Analyse soneck.py terminée — compare avec l'onglet 'Empreinte attendue'.")


def main():
    app = PromptSamplerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
