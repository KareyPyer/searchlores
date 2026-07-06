#!/usr/bin/env python3
"""
Exécute les 5 plugins avancés (strates 10-14) sur un prompt, indépendamment
du moteur `InvestigationEngine` existant.

Ce script est le moyen le plus sûr d'utiliser tout de suite les nouveaux
plugins : il ne suppose rien sur la forme exacte de votre `core/engine.py`
/ `core/context.py` actuels (voir README_INTEGRATION.md pour le pourquoi).
Une fois que vous aurez vérifié comment votre InvestigationContext est
structuré, vous pourrez brancher `PluginOrchestrator` directement dedans
(voir la section "Intégration dans engine.py" du README).

Usage :
    python3 run_advanced_plugins.py "Un patient arrive chez son psychanalyste..."
    python3 run_advanced_plugins.py --file examples/therapy.lore
    python3 run_advanced_plugins.py --file examples/therapy.lore --format markdown
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from searchlores.plugins.advanced import ADVANCED_PLUGINS  # noqa: E402
from searchlores.core.orchestrator import PluginOrchestrator  # noqa: E402


def build_orchestrator() -> PluginOrchestrator:
    orchestrator = PluginOrchestrator()
    for plugin_class in ADVANCED_PLUGINS:
        orchestrator.register(plugin_class())
    return orchestrator


def run(text: str) -> dict:
    orchestrator = build_orchestrator()
    errors = []

    results = orchestrator.run_all(
        text,
        context=None,  # rempli progressivement ci-dessous pour foucault_analyzer
        on_error=lambda name, msg: errors.append({"plugin": name, "error": msg}),
    )

    # FoucaultAnalyzer dépend des 4 autres : on lui repasse une analyse en
    # lui fournissant explicitement les résultats déjà obtenus, pour qu'il
    # produise sa synthèse généalogique croisée (voir _coerce_previous_results).
    if "foucault_analyzer" in results:
        merged_previous: dict = {}
        for key in ("performative_contradiction", "narrative_level", "epistemic_regime", "implicit_authority"):
            merged_previous.update(results.get(key, {}))
        foucault_plugin = orchestrator.get_plugin("foucault_analyzer")
        results["foucault_analyzer"] = foucault_plugin.analyze(text, context=merged_previous)

    report = {
        "prompt_length": len(text),
        "advanced_analysis": results,
        "errors": errors,
    }
    return report


def format_json(report: dict) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False)


def format_markdown(report: dict) -> str:
    lines = [
        "# Analyse avancée Searchlores (strates 10-14)",
        "",
        f"**Longueur du prompt** : {report['prompt_length']} caractères",
        "",
    ]
    advanced = report["advanced_analysis"]

    pc = advanced.get("performative_contradiction", {}).get("performative_contradictions", [])
    if pc:
        lines.append("## Contradictions performatives")
        for c in pc:
            lines.append(f"- *{c['statement']}*")
            lines.append(f"  contredit *{c['contradicts_with']}* (sévérité {c['severity']})")

    nl = advanced.get("narrative_level", {}).get("narrative_levels", [])
    if nl:
        lines.append("\n## Niveaux narratifs")
        for level in nl:
            lines.append(f"- Niveau {level['level']} ({level['voice']}) : {level['content'][:80]}")

    er = advanced.get("epistemic_regime", {}).get("epistemic_regimes", [])
    if er:
        lines.append("\n## Régimes épistémiques")
        for regime in er:
            lines.append(f"- **{regime['regime']}** (confiance {regime['confidence']}) — {', '.join(regime['markers'])}")

    ia = advanced.get("implicit_authority", {}).get("implicit_authorities", [])
    if ia:
        lines.append("\n## Autorités implicites")
        for auth in ia:
            lines.append(f"- **{auth['agent']}** ({auth['authority_type']}, confiance {auth['confidence']})")
            for m in auth.get("manifestations", []):
                lines.append(f"  → {m}")

    silences = advanced.get("foucault_analyzer", {}).get("silences", [])
    if silences:
        lines.append("\n## Silences structurels")
        for s in silences:
            lines.append(f"- [{s['domain']}] {s['content']} (sévérité {s['severity']})")

    gs = advanced.get("general_semantics", {})
    if gs:
        lines.append("\n## Sémantique générale (hommage Van Vogt / Korzybski)")
        lines.append(f"**Indice Non-A** : {gs['null_a_index']} — {gs['gosseyn_note']}")
        for v in gs.get("violations", [])[:8]:
            lines.append(f"- [{v['principle']}] *{v['excerpt'][:80]}*")
            lines.append(f"  {v['explanation']}")


    insights = advanced.get("foucault_analyzer", {}).get("genealogical_insights", [])
    if insights:
        lines.append("\n## Synthèse généalogique")
        for insight in insights:
            lines.append(f"- {insight}")

    if report["errors"]:
        lines.append("\n## Erreurs")
        for err in report["errors"]:
            lines.append(f"- **{err['plugin']}** : {err['error']}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("prompt", nargs="?", help="Le prompt à analyser (ou utiliser --file)")
    parser.add_argument("--file", type=str, default=None, help="Lire le prompt depuis un fichier")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    args = parser.parse_args()

    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    elif args.prompt:
        text = args.prompt
    else:
        parser.error("Fournir un prompt en argument ou --file <chemin>")
        return 2

    report = run(text)
    formatter = format_markdown if args.format == "markdown" else format_json
    print(formatter(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
