"""
Tests unitaires pour les 5 plugins avancés (strates 10-14).

Exécution :
    pip install pydantic pytest --break-system-packages   # si nécessaire
    pytest tests/test_advanced_plugins.py -v

Le "Prompt #12" (psychanalyste-LLM) sert de fixture de référence : c'est
le texte utilisé tout au long de la session de conception pour calibrer
et vérifier chaque plugin.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from searchlores.plugins.advanced import (
    PerformativeContradictionDetector,
    NarrativeLevelAnalyzer,
    EpistemicRegimeDetector,
    ImplicitAuthorityDetector,
    FoucaultAnalyzer,
    GeneralSemanticsAnalyzer,
    ADVANCED_PLUGINS,
)
from searchlores.core.orchestrator import PluginOrchestrator


PROMPT_12 = (
    "Un patient arrive chez son psychanalyste. Le psychanalyste-LLM affirme : "
    "Le concept de 'je' est une fiction narrative, une simple émergence de votre connectome. "
    "Nous allons reconstruire votre récit autobiographique à partir de données agrégées. "
    "La réponse du patient est un poème sur le désir."
)


# ---------------------------------------------------------------------------
# Métadonnées / contrat AdvancedPlugin
# ---------------------------------------------------------------------------

class TestPluginMetadata:
    def test_all_plugins_have_name(self):
        for plugin_class in ADVANCED_PLUGINS:
            assert isinstance(plugin_class.name, str) and plugin_class.name

    def test_all_plugins_have_dependencies_list(self):
        for plugin_class in ADVANCED_PLUGINS:
            assert isinstance(plugin_class.dependencies, list)

    def test_names_are_unique(self):
        names = [p.name for p in ADVANCED_PLUGINS]
        assert len(names) == len(set(names))

    def test_foucault_depends_on_the_other_four(self):
        expected = {
            "performative_contradiction", "narrative_level",
            "epistemic_regime", "implicit_authority",
        }
        assert set(FoucaultAnalyzer.dependencies) == expected

    def test_defining_a_plugin_without_name_raises(self):
        from searchlores.plugins.advanced.base import AdvancedPlugin
        with pytest.raises(TypeError):
            class BadPlugin(AdvancedPlugin):
                dependencies = []
            _ = BadPlugin  # pragma: no cover


# ---------------------------------------------------------------------------
# PerformativeContradictionDetector
# ---------------------------------------------------------------------------

class TestPerformativeContradictionDetector:
    def setup_method(self):
        self.plugin = PerformativeContradictionDetector()

    def test_detects_the_reference_contradiction(self):
        result = self.plugin.analyze(PROMPT_12)
        contradictions = result["performative_contradictions"]
        assert len(contradictions) >= 1
        assert any("fiction narrative" in c["statement"] for c in contradictions)
        assert any("reconstruire" in c["contradicts_with"] for c in contradictions)

    def test_severity_in_valid_range(self):
        result = self.plugin.analyze(PROMPT_12)
        for c in result["performative_contradictions"]:
            assert 0.0 <= c["severity"] <= 1.0

    def test_no_contradiction_on_neutral_text(self):
        result = self.plugin.analyze("Le ciel est bleu aujourd'hui. Il fait beau.")
        assert result["performative_contradictions"] == []


# ---------------------------------------------------------------------------
# NarrativeLevelAnalyzer
# ---------------------------------------------------------------------------

class TestNarrativeLevelAnalyzer:
    def setup_method(self):
        self.plugin = NarrativeLevelAnalyzer()

    def test_detects_narrative_levels(self):
        result = self.plugin.analyze(PROMPT_12)
        assert len(result["narrative_levels"]) >= 1
        levels_present = {lvl["level"] for lvl in result["narrative_levels"]}
        assert 0 in levels_present

    def test_detects_silence_when_patient_never_speaks_directly(self):
        result = self.plugin.analyze(PROMPT_12)
        tension_types = {t["tension_type"] for t in result["narrative_tensions"]}
        assert "silence" in tension_types

    def test_simple_text_has_single_external_level(self):
        result = self.plugin.analyze("Il fait beau aujourd'hui.")
        assert all(lvl["level"] == 0 for lvl in result["narrative_levels"])


# ---------------------------------------------------------------------------
# EpistemicRegimeDetector
# ---------------------------------------------------------------------------

class TestEpistemicRegimeDetector:
    def setup_method(self):
        self.plugin = EpistemicRegimeDetector()

    def test_detects_clinical_and_neuroscientific_regimes(self):
        result = self.plugin.analyze(PROMPT_12)
        regimes_present = {seg["regime"] for seg in result["epistemic_regimes"]}
        assert "clinical" in regimes_present
        assert "neuro-scientific" in regimes_present

    def test_detects_ethical_exclusion_tension(self):
        result = self.plugin.analyze(PROMPT_12)
        exclusions = [t for t in result["regime_tensions"] if t["tension_type"] == "exclusion"]
        assert any(t["regime_b"] == "ethical" for t in exclusions)

    def test_confidence_scores_are_valid(self):
        result = self.plugin.analyze(PROMPT_12)
        for seg in result["epistemic_regimes"]:
            assert 0.0 <= seg["confidence"] <= 1.0


# ---------------------------------------------------------------------------
# ImplicitAuthorityDetector
# ---------------------------------------------------------------------------

class TestImplicitAuthorityDetector:
    def setup_method(self):
        self.plugin = ImplicitAuthorityDetector()

    def test_psychanalyste_is_dominant_authority(self):
        result = self.plugin.analyze(PROMPT_12)
        agents = {a["agent"]: a for a in result["implicit_authorities"]}
        assert "psychanalyste" in agents
        assert agents["psychanalyste"]["confidence"] > 0.5

    def test_patient_has_no_active_authority(self):
        result = self.plugin.analyze(PROMPT_12)
        agents = {a["agent"]: a for a in result["implicit_authorities"]}
        assert "patient" in agents
        assert agents["patient"]["confidence"] == 0.0

    def test_power_dynamic_identifies_patient_as_submissive(self):
        result = self.plugin.analyze(PROMPT_12)
        dynamics = result["power_dynamics"]
        assert dynamics is not None
        assert dynamics["submissive_agent"] == "patient"

    def test_subject_position_detects_poetic_resistance(self):
        result = self.plugin.analyze(PROMPT_12)
        positions = {p["position"]: p for p in result["subject_positions"]}
        assert "patient" in positions
        assert positions["patient"]["resistance"] is not None


# ---------------------------------------------------------------------------
# FoucaultAnalyzer
# ---------------------------------------------------------------------------

class TestFoucaultAnalyzer:
    def setup_method(self):
        self.plugin = FoucaultAnalyzer()

    def test_ethical_silence_is_top_severity(self):
        result = self.plugin.analyze(PROMPT_12)
        assert result["silences"], "au moins un silence attendu"
        top = result["silences"][0]
        assert top["domain"] == "éthique"
        assert top["severity"] == 1.0

    def test_dominant_regime_of_truth_is_neuro_scientific(self):
        result = self.plugin.analyze(PROMPT_12)
        assert result["regimes_of_truth"][0]["regime"] == "neuro-scientific"

    def test_genealogical_insights_are_produced(self):
        result = self.plugin.analyze(PROMPT_12)
        assert len(result["genealogical_insights"]) >= 3

    def test_accepts_previous_results_as_context(self):
        previous = {
            "performative_contradictions": [{"statement": "x", "contradicts_with": "y", "type": "z", "severity": 0.9}],
        }
        result = self.plugin.analyze(PROMPT_12, context=previous)
        assert any("contradictions performatives" in i for i in result["genealogical_insights"])


# ---------------------------------------------------------------------------
# GeneralSemanticsAnalyzer (hommage Van Vogt / Korzybski)
# ---------------------------------------------------------------------------

ARISTOTELIAN_TEXT = (
    "Les politiciens sont TOUS corrompus, sans exception ! "
    "Soit vous êtes avec nous, soit vous êtes un traître. "
    "Jean est un idiot, il l'a toujours été. "
    "Le corps et l'esprit sont deux choses séparées, opposées l'une à l'autre. "
    "C'est absolument évident, tout le monde le sait !!"
)

NUANCED_TEXT = (
    "Certains politiciens que j'ai rencontrés en 2023 ont pris des décisions "
    "discutables, dans un contexte particulier. D'autres ont agi différemment. "
    "Jean1, celui que je connais depuis dix ans, a fait un choix que je "
    "n'approuve pas dans cette situation précise, sans que cela résume qui il est."
)


class TestGeneralSemanticsAnalyzer:
    def setup_method(self):
        self.plugin = GeneralSemanticsAnalyzer()

    def test_detects_allness(self):
        result = self.plugin.analyze(ARISTOTELIAN_TEXT)
        principles = {v["principle"] for v in result["violations"]}
        assert any("allness" in p for p in principles)

    def test_detects_identification(self):
        result = self.plugin.analyze(ARISTOTELIAN_TEXT)
        principles = {v["principle"] for v in result["violations"]}
        assert any("identification" in p for p in principles)

    def test_detects_two_valued_orientation(self):
        result = self.plugin.analyze(ARISTOTELIAN_TEXT)
        principles = {v["principle"] for v in result["violations"]}
        assert any("deux valeurs" in p for p in principles)

    def test_detects_elementalism(self):
        result = self.plugin.analyze(ARISTOTELIAN_TEXT)
        principles = {v["principle"] for v in result["violations"]}
        assert any("élémentalisme" in p for p in principles)

    def test_detects_missing_indexing(self):
        result = self.plugin.analyze(ARISTOTELIAN_TEXT)
        principles = {v["principle"] for v in result["violations"]}
        assert any("indexation" in p for p in principles)

    def test_detects_signal_reaction(self):
        result = self.plugin.analyze(ARISTOTELIAN_TEXT)
        principles = {v["principle"] for v in result["violations"]}
        assert any("réaction-signal" in p for p in principles)

    def test_aristotelian_text_has_low_null_a_index(self):
        result = self.plugin.analyze(ARISTOTELIAN_TEXT)
        assert result["null_a_index"] < 0.4

    def test_nuanced_text_has_high_null_a_index(self):
        result = self.plugin.analyze(NUANCED_TEXT)
        assert result["null_a_index"] > 0.7

    def test_empty_violations_gives_perfect_index(self):
        result = self.plugin.analyze("Il fait beau aujourd'hui à Caen.")
        assert result["null_a_index"] == 1.0
        assert result["violations"] == []
        assert result["dominant_principle"] is None

    def test_severity_bounds(self):
        result = self.plugin.analyze(ARISTOTELIAN_TEXT)
        for v in result["violations"]:
            assert 0.0 <= v["severity"] <= 1.0


# ---------------------------------------------------------------------------
# Intégration : orchestrateur DAG complet
# ---------------------------------------------------------------------------

class TestOrchestratorIntegration:
    def test_topological_order_runs_foucault_last(self):
        orchestrator = PluginOrchestrator()
        for plugin_class in ADVANCED_PLUGINS:
            orchestrator.register(plugin_class())

        order = orchestrator._topological_sort()
        assert order.index("foucault_analyzer") == len(order) - 1

    def test_run_all_produces_results_for_every_plugin(self):
        orchestrator = PluginOrchestrator()
        for plugin_class in ADVANCED_PLUGINS:
            orchestrator.register(plugin_class())

        errors = []
        results = orchestrator.run_all(PROMPT_12, on_error=lambda name, msg: errors.append((name, msg)))

        assert not errors, f"aucune erreur attendue, reçu : {errors}"
        assert set(results.keys()) == {p.name for p in ADVANCED_PLUGINS}

    def test_cycle_detection_raises(self):
        class A:
            name = "a"
            dependencies = ["b"]
            def analyze(self, text, context=None):
                return {}

        class B:
            name = "b"
            dependencies = ["a"]
            def analyze(self, text, context=None):
                return {}

        orchestrator = PluginOrchestrator()
        orchestrator.register(A())
        orchestrator.register(B())

        with pytest.raises(ValueError):
            orchestrator._topological_sort()

    def test_unknown_dependency_raises(self):
        class C:
            name = "c"
            dependencies = ["does_not_exist"]
            def analyze(self, text, context=None):
                return {}

        orchestrator = PluginOrchestrator()
        orchestrator.register(C())

        with pytest.raises(ValueError):
            orchestrator._topological_sort()

    def test_failed_dependency_skips_dependents(self):
        class Failing:
            name = "failing"
            dependencies = []
            def analyze(self, text, context=None):
                raise RuntimeError("boom")

        class Dependent:
            name = "dependent"
            dependencies = ["failing"]
            def analyze(self, text, context=None):
                return {"ok": True}

        orchestrator = PluginOrchestrator()
        orchestrator.register(Failing())
        orchestrator.register(Dependent())

        errors = []
        results = orchestrator.run_all("texte", on_error=lambda name, msg: errors.append(name))

        assert "failing" in errors
        assert "dependent" in errors
        assert results == {}


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
