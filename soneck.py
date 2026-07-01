import typer
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich import box
import json

# Imports depuis ton package searchlores
from searchlores.core.engine import InvestigationEngine
from searchlores.plugins.builtin.authority import (
    AuthorityDetector, AssumptionExtractor, ContradictionFinder,
    OmissionDetector, NarrativeArcheologist, CognitiveGenealogist
)
from searchlores.graph.searchmap import SearchMap

app = typer.Typer(help="Searchlores Ultimate — Archéologie Cognitive", add_completion=False)
console = Console()

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
    prompt: str = typer.Argument(..., help="Le prompt à excaver"),
    depth: str = typer.Option("full", help="Profondeur : surface | deep | full"),
    export: Optional[str] = typer.Option(None, help="Exporter la Search Map (mermaid|json)")
):
    engine = InvestigationEngine()
    engine.register(AuthorityDetector())
    engine.register(AssumptionExtractor())
    engine.register(ContradictionFinder())

    # Nettoyage des espaces pour que la comparaison fonctionne
    if depth in ["deep", "full"]:
        engine.register(OmissionDetector())
        engine.register(NarrativeArcheologist())

    if depth == "full":
        engine.register(CognitiveGenealogist())

    context = engine.run(prompt)

    console.print(Panel(
        f"[bold white]{prompt}[/bold white]",
        title="🔍 PROMPT EXCAVÉ",
        subtitle=f"Profondeur: [bold]{depth}[/bold]",
        border_style="bright_cyan",
        box=box.ROUNDED
    ))

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
    prompts: List[str] = typer.Argument(..., help="Les prompts à comparer")
):
    engine = InvestigationEngine()
    engine.register(AuthorityDetector())
    engine.register(AssumptionExtractor())
    engine.register(OmissionDetector())

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
    import yaml
    from searchlores.lore.models import Lore

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

    # Utilisation de getattr pour éviter les erreurs si des champs sont absents
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
