#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
soneck.py - Searchlores Cognitive Archaeology Laboratory
Version 2.2 - Support complet des plugins built-in et avancés

Usage:
    # Analyse avec prompt direct
    python soneck.py investigate "Votre prompt ici"

    # Analyse avec fichier
    python soneck.py investigate --file P01.txt

    # Avec sélection de plugins
    python soneck.py investigate --file P01.txt --plugins assumptions,authority,narrative_level

    # Avec Lores
    python soneck.py investigate --file P01.txt --lore lores/technocritique.lore --lore lores/epistemology.lore

    # Export JSON
    python soneck.py investigate --file P01.txt --export json --output result.json

    # Mode avancé complet
    python soneck.py investigate "Prompt" --advanced --plugins all --lore lores/llm.lore

    # Lister les plugins
    python soneck.py plugins --all
"""

import sys
import os
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any, Set
from datetime import datetime
import json
import re

# --- Import Rich pour l'affichage ---
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.tree import Tree
    from rich.markdown import Markdown
    from rich.syntax import Syntax
    from rich import box
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    # Fallback minimal
    class Console:
        def print(self, *args, **kwargs):
            print(*args)
    console = Console()

if RICH_AVAILABLE:
    console = Console()

# --- Ajout du chemin du projet ---
sys.path.insert(0, str(Path(__file__).parent))

# --- Imports Searchlores ---
try:
    from searchlores.core.engine import InvestigationEngine
    from searchlores.core.context import InvestigationContext
    from searchlores.lore.loader import load_lore
    from searchlores.lore.models import Lore
    SEARCHLORES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Searchlores core non disponible: {e}")
    SEARCHLORES_AVAILABLE = False

# --- Imports des plugins avancés ---
ADVANCED_AVAILABLE = False
ADVANCED_PLUGINS_MAP = {}
ADVANCED_PLUGIN_NAMES = []

try:
    from searchlores.plugins.advanced import ADVANCED_PLUGINS
    from searchlores.plugins.advanced.base import AdvancedPlugin
    from searchlores.core.orchestrator import PluginOrchestrator

    # Construire une map nom -> classe
    for plugin_class in ADVANCED_PLUGINS:
        try:
            instance = plugin_class()
            plugin_name = getattr(instance, 'name', plugin_class.__name__.lower())
            ADVANCED_PLUGINS_MAP[plugin_name] = plugin_class
            ADVANCED_PLUGIN_NAMES.append(plugin_name)
        except:
            pass

    ADVANCED_AVAILABLE = True
except ImportError as e:
    ADVANCED_AVAILABLE = False

# --- Imports des plugins built-in (incluant les nouveaux) ---
BUILTIN_AVAILABLE = False
BUILTIN_PLUGINS_MAP = {}
BUILTIN_PLUGIN_NAMES = []

try:
    # Plugins standards
    from searchlores.plugins.builtin.authority import AuthorityDetector
    from searchlores.plugins.builtin.assumptions import AssumptionExtractor
    from searchlores.plugins.builtin.contradictions import ContradictionFinder

    # Nouveaux plugins built-in
    try:
        from searchlores.plugins.builtin.ontology import OntologyDetector
        from searchlores.plugins.builtin.bias import BiasDetector
        from searchlores.plugins.builtin.counterprompt import CounterPromptGenerator
        from searchlores.plugins.builtin.debate import DebateAnalyzer
        from searchlores.plugins.builtin.temporal import TemporalAnalyzer
        from searchlores.plugins.builtin.affect import AffectDetector
        NEW_BUILTIN_AVAILABLE = True
    except ImportError:
        NEW_BUILTIN_AVAILABLE = False

    # Map des plugins built-in
    BUILTIN_PLUGINS_MAP = {
        'authority': AuthorityDetector,
        'assumptions': AssumptionExtractor,
        'contradictions': ContradictionFinder,
    }

    # Ajouter les nouveaux plugins s'ils sont disponibles
    if NEW_BUILTIN_AVAILABLE:
        BUILTIN_PLUGINS_MAP.update({
            'ontology': OntologyDetector,
            'bias': BiasDetector,
            'counterprompt': CounterPromptGenerator,
            'debate': DebateAnalyzer,
            'temporal': TemporalAnalyzer,
            'affect': AffectDetector,
        })

    BUILTIN_PLUGIN_NAMES = list(BUILTIN_PLUGINS_MAP.keys())
    BUILTIN_AVAILABLE = True

except ImportError as e:
    BUILTIN_AVAILABLE = False

# --- Plugins minimaux de fallback (pour les plugins manquants) ---
class MinimalPlugin:
    """Plugin minimal pour fallback."""

    def __init__(self, name, finder_func, description=""):
        self.name = name
        self.finder_func = finder_func
        self.description = description

    def run(self, context):
        try:
            result = self.finder_func(context.prompt)
            if result:
                if isinstance(result, dict):
                    for key, value in result.items():
                        context.add_finding(f"{self.name}_{key}", value)
                else:
                    context.add_finding(self.name, result)
        except Exception as e:
            context.errors.append({"plugin": self.name, "error": str(e)})

def minimal_authority(prompt):
    authorities = ['expert', 'scientist', 'professor', 'doctor', 'researcher', 'specialist', 'authority']
    found = [a for a in authorities if a in prompt.lower()]
    return {"authority_markers": found} if found else None

def minimal_assumptions(prompt):
    markers = ['because', 'since', 'as', 'given that', 'assuming', 'suppose']
    found = [m for m in markers if m in prompt.lower()]
    return {"assumption_markers": found} if found else None

def minimal_contradictions(prompt):
    markers = ['but', 'however', 'although', 'nevertheless', 'yet', 'despite']
    found = [m for m in markers if m in prompt.lower()]
    return {"contradiction_markers": found} if found else None

def minimal_ontology(prompt):
    """Version minimale du détecteur ontologique."""
    ontological_terms = ['is', 'exists', 'being', 'entity', 'reality', 'truth', 'fact']
    found = [t for t in ontological_terms if t in prompt.lower()]
    return {"ontological_terms": found} if found else None

def minimal_bias(prompt):
    """Version minimale du détecteur de biais."""
    bias_terms = ['obviously', 'clearly', 'undeniably', 'without doubt', 'everyone knows']
    found = [t for t in bias_terms if t in prompt.lower()]
    return {"bias_indicators": found} if found else None

def minimal_counterprompt(prompt):
    """Version minimale du générateur de contre-prompts."""
    # Simple transformation
    if 'explain' in prompt.lower():
        return {"counter": prompt.replace('Explain', 'Question')}
    return {"counter": f"Why not {prompt}?"}

def minimal_debate(prompt):
    """Version minimale de l'analyseur de débat."""
    debate_terms = ['argue', 'debate', 'discuss', 'agree', 'disagree', 'position']
    found = [t for t in debate_terms if t in prompt.lower()]
    return {"debate_terms": found} if found else None

def minimal_temporal(prompt):
    """Version minimale de l'analyseur temporel."""
    temporal_terms = ['before', 'after', 'now', 'then', 'future', 'past', 'currently']
    found = [t for t in temporal_terms if t in prompt.lower()]
    return {"temporal_terms": found} if found else None

def minimal_affect(prompt):
    """Version minimale du détecteur affectif."""
    affect_terms = ['feel', 'believe', 'think', 'know', 'trust', 'doubt', 'hope']
    found = [t for t in affect_terms if t in prompt.lower()]
    return {"affect_terms": found} if found else None

# --- Plugin Manager ---
class PluginManager:
    """Gestionnaire de plugins avec sélection dynamique."""

    def __init__(self):
        self.all_plugins = {}
        self.advanced_plugins = {}
        self.builtin_plugins = {}

        # Définir les fallbacks pour tous les plugins
        fallback_plugins = {
            'authority': MinimalPlugin('authority', minimal_authority, "Détection d'autorités"),
            'assumptions': MinimalPlugin('assumptions', minimal_assumptions, "Extraction d'hypothèses"),
            'contradictions': MinimalPlugin('contradictions', minimal_contradictions, "Détection de contradictions"),
            'ontology': MinimalPlugin('ontology', minimal_ontology, "Analyse ontologique"),
            'bias': MinimalPlugin('bias', minimal_bias, "Détection de biais"),
            'counterprompt': MinimalPlugin('counterprompt', minimal_counterprompt, "Génération de contre-prompts"),
            'debate': MinimalPlugin('debate', minimal_debate, "Analyse de débat"),
            'temporal': MinimalPlugin('temporal', minimal_temporal, "Analyse temporelle"),
            'affect': MinimalPlugin('affect', minimal_affect, "Détection affective"),
        }

        # Enregistrer les plugins built-in (ou fallbacks)
        if BUILTIN_AVAILABLE:
            for name, cls in BUILTIN_PLUGINS_MAP.items():
                self.builtin_plugins[name] = cls
                self.all_plugins[name] = cls
        else:
            # Utiliser les fallbacks
            for name, plugin in fallback_plugins.items():
                self.builtin_plugins[name] = plugin
                self.all_plugins[name] = plugin

        # Enregistrer les plugins avancés
        if ADVANCED_AVAILABLE:
            for name, cls in ADVANCED_PLUGINS_MAP.items():
                self.advanced_plugins[name] = cls
                self.all_plugins[name] = cls

    def get_plugin(self, name: str):
        """Récupère un plugin par son nom."""
        if name in self.all_plugins:
            return self.all_plugins[name]
        return None

    def get_plugins(self, names: List[str]) -> List:
        """Récupère une liste de plugins par leurs noms."""
        plugins = []
        for name in names:
            plugin = self.get_plugin(name)
            if plugin:
                plugins.append(plugin)
        return plugins

    def get_available_names(self) -> Dict[str, List[str]]:
        """Retourne les noms des plugins disponibles par catégorie."""
        return {
            'builtin': list(self.builtin_plugins.keys()),
            'advanced': list(self.advanced_plugins.keys()),
            'all': list(self.all_plugins.keys())
        }

    def get_plugin_info(self, name: str) -> Dict[str, Any]:
        """Retourne les informations d'un plugin."""
        plugin_class = self.get_plugin(name)
        if not plugin_class:
            return None

        try:
            instance = plugin_class()
            info = {
                'name': getattr(instance, 'name', name),
                'description': getattr(instance, 'description', 'N/A'),
                'category': 'builtin' if name in self.builtin_plugins else 'advanced'
            }

            if hasattr(instance, 'dependencies'):
                info['dependencies'] = instance.dependencies
            else:
                info['dependencies'] = []

            return info
        except:
            return {
                'name': name,
                'description': 'N/A',
                'category': 'unknown',
                'dependencies': []
            }

    def validate_plugins(self, names: List[str]) -> Dict[str, Any]:
        """Valide une liste de noms de plugins."""
        available = set(self.all_plugins.keys())
        requested = set(names)

        valid = requested & available
        invalid = requested - available

        return {
            'valid': list(valid),
            'invalid': list(invalid),
            'all_valid': len(invalid) == 0
        }

# --- Lore Manager ---
class LoreManager:
    """Gestionnaire de Lores."""

    def __init__(self, lore_dir: str = "lores"):
        self.lore_dir = Path(lore_dir)
        self.loaded_lores = {}

    def load_lore(self, path: str) -> Optional[Lore]:
        """Charge un fichier Lore."""
        try:
            lore = load_lore(path)
            if lore and lore.metadata:
                self.loaded_lores[lore.metadata.name] = lore
            return lore
        except Exception as e:
            console.print(f"[red]❌ Erreur de chargement du Lore {path}: {e}[/red]")
            return None

    def load_lores_from_names(self, names: List[str]) -> List[Lore]:
        """Charge des Lores par leurs noms."""
        lores = []
        # Chercher dans le répertoire
        if self.lore_dir.exists():
            for lore_file in self.lore_dir.glob("*.lore"):
                try:
                    lore = load_lore(str(lore_file))
                    if lore and lore.metadata:
                        if lore.metadata.name in names:
                            lores.append(lore)
                except:
                    pass
        return lores

    def load_lore_by_name(self, name: str) -> Optional[Lore]:
        """Charge un Lore par son nom."""
        if self.lore_dir.exists():
            for lore_file in self.lore_dir.glob("*.lore"):
                try:
                    lore = load_lore(str(lore_file))
                    if lore and lore.metadata and lore.metadata.name == name:
                        return lore
                except:
                    pass
        return None

# --- Moteur d'investigation avancé ---
class AdvancedInvestigationEngine:
    """Moteur d'investigation avec support de sélection de plugins."""

    def __init__(self, plugin_manager: PluginManager, lore_manager: LoreManager):
        self.plugin_manager = plugin_manager
        self.lore_manager = lore_manager
        self.use_advanced_mode = False
        self.orchestrator = None

    def investigate(self,
                   prompt: str,
                   plugin_names: Optional[List[str]] = None,
                   lore_names: Optional[List[str]] = None,
                   use_advanced: bool = False,
                   verbose: bool = False) -> InvestigationContext:
        """Exécute une investigation avec sélection de plugins."""

        context = InvestigationContext(prompt=prompt)

        # Métadonnées
        context.metadata['timestamp'] = datetime.now().isoformat()
        context.metadata['mode'] = 'advanced' if use_advanced else 'standard'

        # Sélectionner les plugins
        selected_plugins = []

        if plugin_names:
            # Sélection spécifique
            validation = self.plugin_manager.validate_plugins(plugin_names)
            if validation['invalid']:
                console.print(f"[yellow]⚠️  Plugins inconnus ignorés: {', '.join(validation['invalid'])}[/yellow]")

            for name in validation['valid']:
                plugin_class = self.plugin_manager.get_plugin(name)
                if plugin_class:
                    try:
                        if isinstance(plugin_class, type):
                            selected_plugins.append(plugin_class())
                        else:
                            selected_plugins.append(plugin_class)
                    except Exception as e:
                        console.print(f"[red]❌ Erreur d'instanciation de {name}: {e}[/red]")
        else:
            # Sélection par défaut (tous les plugins disponibles)
            if use_advanced:
                plugin_names = list(self.plugin_manager.advanced_plugins.keys())
            else:
                plugin_names = list(self.plugin_manager.builtin_plugins.keys())

            for name in plugin_names:
                plugin_class = self.plugin_manager.get_plugin(name)
                if plugin_class:
                    try:
                        if isinstance(plugin_class, type):
                            selected_plugins.append(plugin_class())
                        else:
                            selected_plugins.append(plugin_class)
                    except:
                        pass

        # Créer le moteur de base
        engine = InvestigationEngine()

        # Enregistrer les plugins sélectionnés (built-in)
        for plugin in selected_plugins:
            if not hasattr(plugin, 'dependencies'):  # Plugin built-in
                engine.register(plugin)
                if verbose:
                    console.print(f"[dim]✓ Plugin enregistré: {getattr(plugin, 'name', 'unknown')}[/dim]")

        # Si mode avancé, utiliser l'orchestrateur
        if use_advanced and ADVANCED_AVAILABLE:
            try:
                self.orchestrator = PluginOrchestrator()

                # Enregistrer les plugins avancés sélectionnés
                advanced_plugins = [p for p in selected_plugins if hasattr(p, 'dependencies')]
                for plugin in advanced_plugins:
                    self.orchestrator.register(plugin)
                    if verbose:
                        console.print(f"[dim]✓ Plugin avancé enregistré: {getattr(plugin, 'name', 'unknown')}[/dim]")

                if verbose:
                    console.print("[green]✓ Orchestrateur initialisé[/green]")

                # Exécution avancée
                self.orchestrator.run_all(
                    prompt,
                    context=context,
                    on_result=lambda name, results: self._merge_results(context, results),
                    on_error=lambda name, msg: self._handle_error(context, name, msg)
                )
            except Exception as e:
                console.print(f"[red]❌ Erreur d'exécution avancée: {e}[/red]")
                # Fallback à l'exécution standard
                context = engine.run(prompt)
        else:
            # Exécution standard
            context = engine.run(prompt)

        # Charger les Lores
        if lore_names:
            lores_loaded = []
            for lore_name in lore_names:
                # Essayer de charger par nom
                lore = self.lore_manager.load_lore_by_name(lore_name)
                if not lore:
                    # Essayer comme chemin
                    lore = self.lore_manager.load_lore(lore_name)
                if lore:
                    self._apply_lore(context, lore)
                    lores_loaded.append(lore.metadata.name if lore.metadata else 'unnamed')
                    if verbose:
                        console.print(f"[green]✓ Lore chargé: {lore.metadata.name if lore.metadata else 'unnamed'}[/green]")

            context.metadata['lores_loaded'] = lores_loaded

        # Mettre à jour les métadonnées
        context.metadata['plugins_used'] = [getattr(p, 'name', p.__class__.__name__) for p in selected_plugins]
        context.metadata['findings_count'] = len(context.findings)

        return context

    def _merge_results(self, context: InvestigationContext, results: Dict[str, Any]):
        """Fusionne les résultats des plugins avancés."""
        if isinstance(results, dict):
            for key, value in results.items():
                if key not in context.findings:
                    context.findings[key] = []
                if isinstance(value, list):
                    context.findings[key].extend(value)
                else:
                    context.findings[key].append(value)

    def _handle_error(self, context: InvestigationContext, plugin_name: str, error_msg: str):
        """Gère les erreurs."""
        if not hasattr(context, 'errors'):
            context.errors = []
        context.errors.append({
            'plugin': plugin_name,
            'error': error_msg
        })

    def _apply_lore(self, context: InvestigationContext, lore: Lore):
        """Applique un Lore au contexte."""
        if not lore or not lore.investigation:
            return

        inv = lore.investigation

        if inv.assumptions:
            context.add_finding('lore_assumptions', inv.assumptions)
        if inv.myths:
            context.add_finding('lore_myths', inv.myths)
        if inv.questions:
            context.add_finding('lore_questions', inv.questions)
        if inv.vectors:
            context.add_finding('lore_vectors', inv.vectors)

        context.metadata['lore_applied'] = lore.metadata.name if lore.metadata else 'unnamed'

# --- Fonctions d'affichage ---
def display_plugins(plugin_manager: PluginManager, show_all: bool = False):
    """Affiche les plugins disponibles."""

    if not RICH_AVAILABLE:
        print("Plugins disponibles:")
        print("-" * 50)
        for name in plugin_manager.all_plugins:
            print(f"  • {name}")
        return

    # Plugins built-in
    builtin_table = Table(title="📦 Plugins Built-in", box=box.ROUNDED)
    builtin_table.add_column("Nom", style="green")
    builtin_table.add_column("Description", style="dim")
    builtin_table.add_column("État", style="blue")

    for name in sorted(plugin_manager.builtin_plugins.keys()):
        info = plugin_manager.get_plugin_info(name)
        if info:
            builtin_table.add_row(
                info['name'],
                info['description'],
                "✅ Disponible" if BUILTIN_AVAILABLE else "⚠️  Fallback"
            )

    console.print(builtin_table)

    # Plugins avancés
    if ADVANCED_AVAILABLE:
        advanced_table = Table(title="🔬 Plugins Avancés", box=box.ROUNDED)
        advanced_table.add_column("Nom", style="magenta")
        advanced_table.add_column("Description", style="dim")
        advanced_table.add_column("Dépendances", style="blue")

        for name in sorted(plugin_manager.advanced_plugins.keys()):
            info = plugin_manager.get_plugin_info(name)
            if info:
                deps = ", ".join(info.get('dependencies', []))
                advanced_table.add_row(
                    info['name'],
                    info['description'],
                    deps if deps else "Aucune"
                )

        console.print(advanced_table)

        # Afficher les dépendances graphiques
        try:
            if ADVANCED_AVAILABLE:
                # Créer un orchestrateur pour analyser le DAG
                orchestrator = PluginOrchestrator()
                for name in plugin_manager.advanced_plugins:
                    plugin_class = plugin_manager.get_plugin(name)
                    if plugin_class:
                        try:
                            orchestrator.register(plugin_class())
                        except:
                            pass

                # Afficher l'ordre d'exécution
                dag_info = orchestrator.get_dag_info()
                if dag_info and 'execution_order' in dag_info:
                    order_table = Table(title="📊 Ordre d'exécution (DAG)", box=box.MINIMAL)
                    order_table.add_column("Étape", style="dim")
                    order_table.add_column("Plugin", style="cyan")

                    for i, step in enumerate(dag_info['execution_order'], 1):
                        order_table.add_row(str(i), step)

                    console.print(order_table)
        except Exception as e:
            console.print(f"[dim]ℹ️  Analyse du DAG non disponible: {e}[/dim]")
    else:
        console.print("[yellow]⚠️  Plugins avancés non disponibles[/yellow]")
        console.print("[dim]Pour les installer: copiez les fichiers dans searchlores/plugins/advanced/[/dim]")

    # Résumé
    console.print(f"\n[bold]Résumé:[/bold] {len(plugin_manager.builtin_plugins)} plugins built-in, {len(plugin_manager.advanced_plugins)} plugins avancés")

def display_results(context: InvestigationContext, format: str = "rich", output_file: Optional[str] = None):
    """Affiche les résultats d'une investigation."""

    if not context:
        console.print("[red]❌ Aucun contexte à afficher[/red]")
        return

    if format == "json":
        result = {
            'prompt': context.prompt,
            'findings': context.findings,
            'metadata': context.metadata,
            'errors': getattr(context, 'errors', [])
        }
        json_output = json.dumps(result, indent=2, default=str)

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(json_output)
            console.print(f"[green]✓ Résultats sauvegardés dans {output_file}[/green]")
        else:
            console.print(json_output)

        return

    if format == "markdown":
        md_lines = []
        md_lines.append("# Rapport d'Investigation Searchlores\n")
        md_lines.append(f"**Prompt**: {context.prompt}\n")
        md_lines.append(f"**Mode**: {context.metadata.get('mode', 'standard')}")
        md_lines.append(f"**Date**: {context.metadata.get('timestamp', 'N/A')}\n")

        if context.findings:
            md_lines.append("## Résultats\n")
            for key, value in context.findings.items():
                if isinstance(value, list):
                    md_lines.append(f"### {key.replace('_', ' ').title()}")
                    for item in value:
                        md_lines.append(f"- {item}")
                    md_lines.append("")
                else:
                    md_lines.append(f"### {key.replace('_', ' ').title()}")
                    md_lines.append(f"{value}\n")

        md_output = "\n".join(md_lines)

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(md_output)
            console.print(f"[green]✓ Rapport sauvegardé dans {output_file}[/green]")
        else:
            console.print(Markdown(md_output))

        return

    # Format Rich (par défaut)
    if not RICH_AVAILABLE:
        print("Résultats:")
        print("-" * 50)
        print(f"Prompt: {context.prompt}")
        print(f"Trouvailles: {len(context.findings)}")
        for key, value in context.findings.items():
            print(f"  {key}: {value}")
        return

    # Affichage Rich
    console.print(Panel.fit(
        f"[bold cyan]🔍 Résultats de l'Archéologie Cognitive[/bold cyan]",
        border_style="cyan"
    ))

    console.print(f"[bold]Prompt:[/bold] {context.prompt}\n")

    if context.findings:
        table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
        table.add_column("Strate / Plugin", style="cyan", width=30)
        table.add_column("Résultats", style="green")

        for key, value in sorted(context.findings.items()):
            if isinstance(value, list):
                if value:
                    # Limiter l'affichage à 10 éléments pour la lisibilité
                    display_items = value[:10]
                    formatted = "\n".join(f"  • {item}" for item in display_items)
                    if len(value) > 10:
                        formatted += f"\n  [dim]... et {len(value) - 10} autres[/dim]"
                else:
                    formatted = "[dim]Aucun[/dim]"
            else:
                formatted = str(value)

            # Style selon le type de plugin
            style = "cyan"
            if key.startswith('lore_'):
                style = "blue"
            elif key in ['authority', 'assumptions', 'contradictions']:
                style = "yellow"
            elif key in ['ontology', 'bias', 'counterprompt', 'debate', 'temporal', 'affect']:
                style = "magenta"

            table.add_row(f"[{style}]{key.replace('_', ' ').title()}[/{style}]", formatted)

        console.print(table)
    else:
        console.print("[yellow]⚠️  Aucune trouvaille[/yellow]")

    # Métadonnées
    meta_table = Table(box=box.MINIMAL, show_header=False)
    meta_table.add_column("", style="bold")
    meta_table.add_column("", style="dim")

    for key, value in context.metadata.items():
        if key != 'timestamp':
            meta_table.add_row(f"{key.replace('_', ' ').title()}:", str(value))

    console.print(meta_table)

    if 'timestamp' in context.metadata:
        console.print(f"[dim]Timestamp: {context.metadata['timestamp']}[/dim]")

    # Erreurs
    if hasattr(context, 'errors') and context.errors:
        console.print("\n[red]⚠️  Erreurs rencontrées:[/red]")
        for error in context.errors:
            console.print(f"  • {error.get('plugin', 'unknown')}: {error.get('error', 'unknown error')}")

# --- Fonction principale ---
def main():
    """Point d'entrée principal."""

    parser = argparse.ArgumentParser(
        description="Searchlores - Laboratoire d'Archéologie Cognitive",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  # Analyse simple
  python soneck.py investigate "You are an expert in AI"

  # Avec fichier (sans prompt positionnel)
  python soneck.py investigate --file P01.txt

  # Avec sélection de plugins (incluant les nouveaux)
  python soneck.py investigate --file P01.txt --plugins assumptions,authority,ontology,bias,temporal

  # Avec Lores par nom
  python soneck.py investigate --file P01.txt --lore technocritique --lore epistemology

  # Export JSON
  python soneck.py investigate --file P01.txt --export json --output result.json

  # Mode avancé complet
  python soneck.py investigate "Prompt" --advanced --plugins all --lore lores/llm.lore

  # Lister les plugins
  python soneck.py plugins --all
        """
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- Commande: investigate ---
    investigate_parser = subparsers.add_parser("investigate", help="Analyse un prompt")

    # Groupe mutuellement exclusif pour le prompt
    prompt_group = investigate_parser.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("prompt", nargs="?", help="Le prompt à analyser (si --file non utilisé)")
    prompt_group.add_argument("--file", "-f", help="Fichier contenant le prompt")

    investigate_parser.add_argument("--plugins", "-p", help="Plugins à utiliser (séparés par des virgules, ou 'all')")
    investigate_parser.add_argument("--advanced", "-a", action="store_true", help="Utiliser les plugins avancés")
    investigate_parser.add_argument("--lore", "-l", action="append", help="Lore(s) à appliquer (nom ou chemin)")
    investigate_parser.add_argument("--export", "-e", choices=["rich", "markdown", "json"], default="rich", help="Format de sortie")
    investigate_parser.add_argument("--output", "-o", help="Fichier de sortie")
    investigate_parser.add_argument("--verbose", "-v", action="store_true", help="Mode verbeux")

    # --- Commande: plugins ---
    plugins_parser = subparsers.add_parser("plugins", help="Liste les plugins disponibles")
    plugins_parser.add_argument("--all", "-a", action="store_true", help="Afficher tous les plugins")
    plugins_parser.add_argument("--category", choices=["builtin", "advanced"], help="Filtrer par catégorie")

    # --- Commande: lore ---
    lore_parser = subparsers.add_parser("lore", help="Gère les Lores")
    lore_parser.add_argument("path", nargs="?", help="Chemin vers un fichier Lore ou un répertoire")
    lore_parser.add_argument("--details", "-d", action="store_true", help="Afficher les détails")
    lore_parser.add_argument("--list", action="store_true", help="Lister les Lores du répertoire")
    lore_parser.add_argument("--name", "-n", help="Nom du Lore à charger")

    # --- Commande: version ---
    version_parser = subparsers.add_parser("version", help="Affiche la version")

    # Parser les arguments
    args = parser.parse_args()

    # Initialiser les gestionnaires
    plugin_manager = PluginManager()
    lore_manager = LoreManager()

    # --- Traitement des commandes ---

    if args.command == "version":
        console.print("[bold cyan]Searchlores v2.2[/bold cyan] - Cognitive Archaeology Laboratory")
        console.print("Avec sélection de plugins et gestion des Lores")
        console.print(f"Plugins built-in: {len(plugin_manager.builtin_plugins)}")
        console.print(f"Plugins avancés: {len(plugin_manager.advanced_plugins)}")
        return 0

    elif args.command == "plugins":
        display_plugins(plugin_manager, args.all)
        return 0

    elif args.command == "lore":
        if args.list:
            display_lores(lore_manager)
        elif args.name:
            lore = lore_manager.load_lore_by_name(args.name)
            if lore:
                if args.details:
                    display_lore_details(lore)
                else:
                    console.print(f"[green]✓ Lore trouvé: {lore.metadata.name if lore.metadata else 'unnamed'}[/green]")
            else:
                console.print(f"[red]❌ Lore non trouvé: {args.name}[/red]")
        elif args.path:
            path = Path(args.path)
            if path.is_dir():
                display_lores(lore_manager)
            else:
                lore = lore_manager.load_lore(str(path))
                if lore:
                    if args.details:
                        display_lore_details(lore)
                    else:
                        console.print(f"[green]✓ Lore chargé: {lore.metadata.name if lore.metadata else 'unnamed'}[/green]")
        else:
            display_lores(lore_manager)
        return 0

    elif args.command == "investigate":
        # Récupérer le prompt
        prompt = None

        if args.file:
            try:
                with open(args.file, 'r', encoding='utf-8') as f:
                    prompt = f.read().strip()
                if args.verbose:
                    console.print(f"[dim]✓ Prompt chargé depuis {args.file}[/dim]")
            except Exception as e:
                console.print(f"[red]❌ Erreur de lecture du fichier: {e}[/red]")
                return 1
        elif args.prompt:
            prompt = args.prompt

        if not prompt:
            console.print("[red]❌ Prompt vide[/red]")
            return 1

        # Traiter la sélection de plugins
        plugin_names = None
        if args.plugins:
            if args.plugins == "all":
                plugin_names = list(plugin_manager.all_plugins.keys())
            else:
                plugin_names = [p.strip() for p in args.plugins.split(',') if p.strip()]

        # Si mode avancé et pas de plugins spécifiés, utiliser les plugins avancés
        if args.advanced and not plugin_names:
            plugin_names = list(plugin_manager.advanced_plugins.keys())

        # Si pas de plugins spécifiés et pas de mode avancé, utiliser les built-in
        if not plugin_names and not args.advanced:
            plugin_names = list(plugin_manager.builtin_plugins.keys())

        # Afficher les plugins sélectionnés
        if args.verbose and plugin_names:
            console.print(f"[dim]📋 Plugins sélectionnés: {', '.join(plugin_names)}[/dim]")

        # Créer le moteur
        engine = AdvancedInvestigationEngine(plugin_manager, lore_manager)

        # Exécuter l'investigation
        try:
            context = engine.investigate(
                prompt=prompt,
                plugin_names=plugin_names,
                lore_names=args.lore,
                use_advanced=args.advanced,
                verbose=args.verbose
            )
        except Exception as e:
            console.print(f"[red]❌ Erreur d'investigation: {e}[/red]")
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1

        # Afficher les résultats
        display_results(context, args.export, args.output)

        return 0

    else:
        parser.print_help()
        return 1

# --- Fonctions supplémentaires ---
def display_lores(lore_manager: LoreManager):
    """Affiche les Lores disponibles."""

    if not RICH_AVAILABLE:
        lores = lore_manager.list_lores()
        print("Lores disponibles:")
        for lore in lores:
            print(f"  • {lore['name']} (par {lore['author']}) - {lore['file']}")
        return

    lores = lore_manager.list_lores()

    if not lores:
        console.print("[yellow]⚠️  Aucun Lore trouvé[/yellow]")
        return

    table = Table(title="📚 Lores Disponibles", box=box.ROUNDED)
    table.add_column("Nom", style="cyan")
    table.add_column("Auteur", style="green")
    table.add_column("Version", style="blue")
    table.add_column("Fichier", style="dim")

    for lore in lores:
        table.add_row(
            lore['name'],
            lore['author'] or 'Inconnu',
            lore['version'] or 'N/A',
            lore['file']
        )

    console.print(table)

def display_lore_details(lore: Lore):
    """Affiche les détails d'un Lore."""
    if not RICH_AVAILABLE:
        print(f"Lore: {lore.metadata.name if lore.metadata else 'Unnamed'}")
        return

    console.print(Panel.fit(
        f"[bold cyan]📚 Détails du Lore: {lore.metadata.name if lore.metadata else 'Unnamed'}[/bold cyan]",
        border_style="cyan"
    ))

    if lore.metadata:
        meta_table = Table(box=box.MINIMAL, show_header=False)
        meta_table.add_column("", style="bold")
        meta_table.add_column("", style="dim")
        meta_table.add_row("Auteur:", lore.metadata.author or "Inconnu")
        meta_table.add_row("Version:", lore.metadata.version or "N/A")
        console.print(meta_table)

    if lore.investigation:
        inv = lore.investigation

        if inv.assumptions:
            table = Table(title="Hypothèses implicites", box=box.ROUNDED)
            table.add_column("#", style="dim")
            table.add_column("Hypothèse", style="yellow")
            for i, a in enumerate(inv.assumptions, 1):
                table.add_row(str(i), a)
            console.print(table)

        if inv.myths:
            table = Table(title="Mythes à déconstruire", box=box.ROUNDED)
            table.add_column("#", style="dim")
            table.add_column("Mythe", style="red")
            for i, m in enumerate(inv.myths, 1):
                table.add_row(str(i), m)
            console.print(table)

        if inv.questions:
            table = Table(title="Questions génératrices", box=box.ROUNDED)
            table.add_column("#", style="dim")
            table.add_column("Question", style="green")
            for i, q in enumerate(inv.questions, 1):
                table.add_row(str(i), q)
            console.print(table)

        if inv.vectors:
            table = Table(title="Vecteurs d'investigation", box=box.ROUNDED)
            table.add_column("#", style="dim")
            table.add_column("Vecteur", style="blue")
            for i, v in enumerate(inv.vectors, 1):
                table.add_row(str(i), v)
            console.print(table)

# --- Ajout de la méthode list_lores à LoreManager ---
def list_lores(self):
    """Liste tous les Lores disponibles."""
    lores_info = []
    if self.lore_dir.exists():
        for lore_file in self.lore_dir.glob("*.lore"):
            try:
                lore = load_lore(str(lore_file))
                if lore and lore.metadata:
                    lores_info.append({
                        'name': lore.metadata.name,
                        'author': lore.metadata.author,
                        'version': lore.metadata.version,
                        'file': lore_file.name
                    })
            except:
                pass
    return lores_info

# Ajouter la méthode à LoreManager
LoreManager.list_lores = list_lores

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrompu par l'utilisateur[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]❌ Erreur inattendue: {e}[/red]")
        if "--verbose" in sys.argv or "-v" in sys.argv:
            import traceback
            traceback.print_exc()
        sys.exit(1)
