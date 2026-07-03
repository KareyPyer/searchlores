import typer
import os
import json
import yaml
from typing import List, Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich import box

# Imports depuis ton package searchlores
from searchlores.core.engine import InvestigationEngine
from searchlores.plugins.builtin.authority import (
    AuthorityDetector, AssumptionExtractor, ContradictionFinder,
    OmissionDetector, NarrativeArcheologist, CognitiveGenealogist
)
from searchlores.graph.searchmap import SearchMap
from searchlores.lore.models import Lore

from searchlores.plugins.builtin.affect import AffectMapper
from searchlores.plugins.builtin.ontology import OntologyMapper
from searchlores.plugins.builtin.bias import BiasDetector
# etc.

app = typer.Typer(help="Searchlores Ultimate — Archéologie Cognitive", add_completion=False)
console = Console()

# 🧩 REGISTRE DES PLUGINS DISPONIBLES
# Ajoute ici tes propres plugins au fur et à mesure
PLUGIN_REGISTRY = {
    "authority": AuthorityDetector,
    "assumptions": AssumptionExtractor,
    "contradictions": ContradictionFinder,
    "omissions": OmissionDetector,
    "narrative": NarrativeArcheologist,
    "genealogy": CognitiveGenealogist,
    # Nouveaux plugins
    "ontology": OntologyMapper,
    "bias": BiasDetector,
    "debate": DebateAnalyzer,
    "counterprompt": CounterPromptGenerator,
    "temporal": TemporalStrataDetector,
    "affect": AffectMapper
}

def load_prompt_from_source(prompt_source: str) -> str:
    """Charge le prompt depuis une chaîne ou un fichier."""
    path = Path(prompt_source)
    if path.exists() and path.is_file():
        console.print(f"[dim]📖 Chargement du prompt depuis : {path}[/dim]")
        return path.read_text(encoding='utf-8').strip()
    return prompt_source

def load_lores(lore_names: List[str]) -> List[Lore]:
    """Charge les fichiers .lore depuis le répertoire ./lores/"""
    lores = []
    lore_dir = Path("lores")
    for name in lore_names:
        lore_path = lore_dir / f"{name}.lore"
        if lore_path.exists():
            with open(lore_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                lores.append(Lore(**data))
                console.print(f"[green]✓ Lore chargé : {name}[/green]")
        else:
            console.print(f"[yellow]⚠ Lore introuvable : {lore_path}[/yellow]")
    return lores

def setup_plugins(plugin_names: List[str]) -> InvestigationEngine:
    """Configure le moteur avec les plugins demandés."""
    engine = InvestigationEngine()
    loaded = []
    for name in plugin_names:
        if name in PLUGIN_REGISTRY:
            engine.register(PLUGIN_REGISTRY[name]())
            loaded.append(name)
        else:
            console.print(f"[red]✗ Plugin inconnu : {name}[/red]")

    if not loaded:
        console.print("[bold red]Aucun plugin valide chargé. Utilisation des plugins par défaut.[/bold red]")
        engine.register(AuthorityDetector())
        engine.register(AssumptionExtractor())
        return engine

    return engine

def print_banner():
    banner = """
    [bold cyan]   _____                       _      _ORE[/bold cyan]
    [cyan]  / ____|                     | |    | |[/cyan]
    [cyan] | (___   ___  _ __   ___  ___| | _  | |[/cyan]
    [cyan]  \___ \ / _ \| '_ \ / _ \/ __| |/ / | |[/cyan]
    [cyan]  ____) | (_) | | | |  __/ (__|   <  | |[/cyan]
    [cyan] |_____/ \___/|_| |_|\___|\___|_|\_\ |_|[/cyan]

    [dim]Archéologie Cognitive & Analyse Épistémologique[/dim]
    """
    console.print(Panel(banner, box=box.DOUBLE_EDGE, border_style="bright_cyan"))

@app.callback()
def main():
    print_banner()

@app.command()
def investigate(
    prompt: Optional[str] = typer.Argument(None, help="Le prompt à excaver (ou utiliser --prompt)"),
    prompt_file: Optional[str] = typer.Option(None, "--prompt", help="Chemin vers un fichier .txt contenant le prompt"),
    lores: Optional[str] = typer.Option(None, "--lores", help="Liste de lores à charger (ex: philosophy,logic,history)"),
    plugins: Optional[str] = typer.Option(None, "--plugins", help="Liste de plugins à activer (ex: assumptions,bias,ontology)"),
    export: Optional[str] = typer.Option(None, help="Exporter la Search Map (mermaid|json)")
):
    # 1. Résolution du prompt
    prompt_source = prompt_file if prompt_file else prompt
    if not prompt_source:
        console.print("[bold red]Erreur : Vous devez fournir un prompt soit en argument, soit via --prompt.[/bold red]")
        raise typer.Exit(1)

    final_prompt = load_prompt_from_source(prompt_source)

    # 2. Configuration des plugins
    if plugins:
        plugin_list = [p.strip() for p in plugins.split(",")]
    else:
        plugin_list = ["authority", "assumptions", "contradictions"]

    engine = setup_plugins(plugin_list)

    # 3. Chargement des lores (contexte épistémologique)
    loaded_lores = []
    if lores:
        lore_list = [l.strip() for l in lores.split(",")]
        loaded_lores = load_lores(lore_list)
        # Injection des lores dans le moteur si l'API le supporte
        # engine.load_lores(loaded_lores)  # À adapter selon ton API

    # 4. Panel de configuration de la session
    config_table = Table(box=box.SIMPLE, show_header=False)
    config_table.add_column("Paramètre", style="cyan")
    config_table.add_column("Valeur", style="white")
    config_table.add_row("Plugins actifs", ", ".join(plugin_list))
    if loaded_lores:
        config_table.add_row("Lore(s) chargé(s)", ", ".join([l.metadata.name for l in loaded_lores]))

    console.print(Panel(config_table, title="⚙️ CONFIGURATION DE LA SONDE", border_style="bright_blue"))

    # 5. L'investigation
    context = engine.run(final_prompt)

    console.print(Panel(
        f"[bold white]{final_prompt[:200]}{'...' if len(final_prompt) > 200 else ''}[/bold white]",
        title="🔍 PROMPT EXCAVÉ",
        border_style="bright_cyan",
        box=box.ROUNDED
    ))

    # 6. Affichage des résultats
    table = Table(title="🏺 Strates Archéologiques", box=box.ROUNDED, show_lines=True, header_style="bold magenta")
    table.add_column("Strate", style="cyan", no_wrap=True)
    table.add_column("Plugin", style="green", no_wrap=True)
    table.add_column("Découverte", style="yellow")

    for layer in context.layers:
        try:
            findings_str = json.dumps(layer['findings'], indent=2, ensure_ascii=False)
            if len(findings_str) > 150:
                findings_str = findings_str[:150] + "..."
        except Exception:
            findings_str = str(layer['findings'])[:150]

        table.add_row(layer['stratum'], layer['plugin'], findings_str)

    console.print(table)

    if context.contradictions:
        console.print(Panel(
            "\n".join([f"[red]• {c['tension']}[/red] — [dim]{c['description']}[/dim]" for c in context.contradictions]),
            title="⚡ TENSIONS DÉTECTÉES",
            border_style="red",
            box=box.SQUARE
        ))

    if context.omissions:
        console.print(Panel(
            ", ".join([f"[dim]{o}[/dim]" for o in context.omissions]),
            title="🔇 DIMENSIONS SILENCIEUSES",
            border_style="bright_black",
            box=box.SQUARE
        ))

    if context.power_vectors:
        console.print(Panel(
            "\n".join([f"[bold red]→ {v}[/bold red]" for v in context.power_vectors]),
            title="⚔️ VECTEURS DE POUVOIR",
            border_style="bright_red",
            box=box.SQUARE
        ))

    if export == "mermaid":
        sm = SearchMap(context)
        console.print(Panel(sm.to_mermaid(), title="📊 SEARCH MAP (Mermaid)", border_style="blue"))
    elif export == "json":
        console.print(Panel(
            json.dumps(context.to_searchmap(), indent=2, ensure_ascii=False),
            title="📊 SEARCH MAP (JSON)",
            border_style="blue"
        ))

@app.command()
def compare(
    prompts: List[str] = typer.Argument(..., help="Les prompts à comparer"),
    plugins: Optional[str] = typer.Option(None, "--plugins", help="Liste de plugins à activer")
):
    if plugins:
        plugin_list = [p.strip() for p in plugins.split(",")]
    else:
        plugin_list = ["authority", "assumptions", "omissions"]

    engine = setup_plugins(plugin_list)
    analysis = engine.comparative_analysis(prompts)

    console.print(Panel(
        "[bold]ANALYSE COMPARATIVE SYSTÉMIQUE[/bold]",
        border_style="bright_blue",
        box=box.DOUBLE
    ))

    tree = Tree("🔬 [bold]Résultats[/bold]")

    shared = tree.add("🎯 [bold cyan]Présupposés Partagés[/bold cyan]")
    for a in analysis.get("shared_assumptions", []):
        shared.add(f"[green]{a}[/green]")

    divergent = tree.add("⚡ [bold yellow]Autorités Divergentes[/bold yellow]")
    for a in analysis.get("divergent_authorities", []):
        divergent.add(f"[yellow]{a}[/yellow]")

    systemic = tree.add("🔇 [bold dim]Silences Systémiques[/bold dim]")
    for s in analysis.get("systemic_omissions", []):
        systemic.add(f"[dim]{s}[/dim]")

    console.print(tree)

@app.command()
def lore_inspect(lore_file: str = typer.Argument(..., help="Chemin vers le fichier .lore")):
    with open(lore_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    lore = Lore(**data)

    console.print(Panel(
        f"[bold]{lore.metadata.name}[/bold]",
        title="📜 LORE",
        subtitle=f"Fichier: [dim]{lore_file}[/dim]",
        border_style="purple",
        box=box.ROUNDED
    ))

    metrics = Table(title="📐 Métriques Épistémologiques", box=box.ROUNDED, show_lines=True, header_style="bold purple")
    metrics.add_column("Dimension", style="cyan")
    metrics.add_column("Count", style="white", justify="center")
    metrics.add_column("Densité", justify="center")

    assumptions = getattr(lore.investigation, 'assumptions', [])
    myths = getattr(lore.investigation, 'myths', [])
    vectors = getattr(lore.investigation, 'vectors', [])
    questions = getattr(lore.investigation, 'questions', [])
    counter_questions = getattr(lore.investigation, 'counter_questions', [])
    forbidden_answers = getattr(lore.investigation, 'forbidden_answers', [])

    metrics.add_row("Hypothèses", str(len(assumptions)), "🔴 " * min(5, len(assumptions)))
    metrics.add_row("Mythes", str(len(myths)), "🟠 " * min(5, len(myths)))
    metrics.add_row("Vecteurs", str(len(vectors)), "🟡 " * min(5, len(vectors)))
    metrics.add_row("Questions", str(len(questions)), "🟢 " * min(5, len(questions)))
    metrics.add_row("Contre-questions", str(len(counter_questions)), "🔵 " * min(5, len(counter_questions)))
    metrics.add_row("Réponses interdites", str(len(forbidden_answers)), "⚫ " * min(5, len(forbidden_answers)))

    console.print(metrics)

    transgression_score = len(counter_questions) + len(forbidden_answers)
    score_color = "green" if transgression_score < 4 else "yellow" if transgression_score < 7 else "red"

    console.print(Panel(
        f"[bold]Score de Transgression Épistémologique : [{score_color}]{transgression_score}/10[/{score_color}][/bold]",
        border_style=score_color,
        box=box.HEAVY
    ))

if __name__ == "__main__":
    app()
