#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
searchlores_gui.py - Interface Graphique Streamlit pour Searchlores
Version 3.0 - Cognitive Archaeology Laboratory

Installation:
    pip install streamlit plotly networkx pandas

Utilisation:
    streamlit run searchlores_gui.py
"""

import streamlit as st
import sys
import os
from pathlib import Path
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import networkx as nx
from typing import List, Dict, Any, Optional
import base64
from io import StringIO

# Configuration de la page
st.set_page_config(
    page_title="Searchlores - Cognitive Archaeology Lab",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé pour un look moderne
st.markdown("""
<style>
    /* Style général */
    .main {
        background-color: #0e1117;
    }
    
    /* Titres */
    .big-title {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(90deg, #00d4ff, #7b2ffc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .sub-title {
        font-size: 1.2rem;
        color: #8892b0;
        margin-bottom: 2rem;
    }
    
    /* Cartes */
    .stat-card {
        background: linear-gradient(135deg, #1a1d24, #2d313a);
        border-radius: 10px;
        padding: 1.5rem;
        border: 1px solid #2d313a;
        transition: all 0.3s;
    }
    
    .stat-card:hover {
        transform: translateY(-5px);
        border-color: #7b2ffc;
    }
    
    .stat-number {
        font-size: 2.5rem;
        font-weight: 700;
        color: #00d4ff;
    }
    
    .stat-label {
        color: #8892b0;
        font-size: 0.9rem;
    }
    
    /* Résultats */
    .result-card {
        background: #1a1d24;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        border-left: 4px solid #7b2ffc;
    }
    
    .plugin-tag {
        display: inline-block;
        background: #2d313a;
        padding: 0.2rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        margin: 0.2rem;
        color: #ccd6f6;
    }
    
    .plugin-tag.active {
        background: #7b2ffc;
        color: white;
    }
    
    /* Graphiques */
    .graph-container {
        background: #1a1d24;
        border-radius: 10px;
        padding: 1rem;
        border: 1px solid #2d313a;
    }
    
    /* Sidebar */
    .sidebar-content {
        padding: 1rem;
    }
    
    .sidebar-title {
        font-size: 1.2rem;
        font-weight: 600;
        color: #ccd6f6;
        margin-bottom: 1rem;
    }
    
    /* Animations */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .fade-in {
        animation: fadeIn 0.5s ease-out;
    }
</style>
""", unsafe_allow_html=True)

# --- Ajout du chemin du projet ---
sys.path.insert(0, str(Path(__file__).parent))

# --- Imports du projet ---
try:
    from searchlores.core.engine import InvestigationEngine
    from searchlores.core.context import InvestigationContext
    from searchlores.lore.loader import load_lore
    from searchlores.lore.models import Lore
    SEARCHLORES_AVAILABLE = True
except ImportError:
    SEARCHLORES_AVAILABLE = False
    st.warning("⚠️  Searchlores core non disponible")

# --- Imports des plugins ---
# Plugin Manager (copié depuis soneck.py)
class PluginManager:
    def __init__(self):
        self.all_plugins = {}
        self.advanced_plugins = {}
        self.builtin_plugins = {}
        
        # Plugins built-in avec fallbacks
        self.builtin_plugins = {
            'authority': {'name': 'authority', 'description': 'Détection d\'autorités', 'category': 'builtin'},
            'assumptions': {'name': 'assumptions', 'description': 'Extraction d\'hypothèses', 'category': 'builtin'},
            'contradictions': {'name': 'contradictions', 'description': 'Détection de contradictions', 'category': 'builtin'},
            'ontology': {'name': 'ontology', 'description': 'Analyse ontologique', 'category': 'builtin'},
            'bias': {'name': 'bias', 'description': 'Détection de biais', 'category': 'builtin'},
            'counterprompt': {'name': 'counterprompt', 'description': 'Génération de contre-prompts', 'category': 'builtin'},
            'debate': {'name': 'debate', 'description': 'Analyse de débat', 'category': 'builtin'},
            'temporal': {'name': 'temporal', 'description': 'Analyse temporelle', 'category': 'builtin'},
            'affect': {'name': 'affect', 'description': 'Détection affective', 'category': 'builtin'},
        }
        
        # Plugins avancés
        try:
            from searchlores.plugins.advanced import ADVANCED_PLUGINS
            for plugin_class in ADVANCED_PLUGINS:
                try:
                    instance = plugin_class()
                    name = getattr(instance, 'name', plugin_class.__name__.lower())
                    self.advanced_plugins[name] = {
                        'name': name,
                        'description': getattr(instance, 'description', 'N/A'),
                        'category': 'advanced',
                        'dependencies': getattr(instance, 'dependencies', [])
                    }
                except:
                    pass
        except:
            pass
        
        self.all_plugins = {**self.builtin_plugins, **self.advanced_plugins}
    
    def get_plugin_info(self, name):
        return self.all_plugins.get(name)

class LoreManager:
    def __init__(self, lore_dir="lores"):
        self.lore_dir = Path(lore_dir)
    
    def get_available_lores(self):
        lores = []
        if self.lore_dir.exists():
            for lore_file in self.lore_dir.glob("*.lore"):
                try:
                    lore = load_lore(str(lore_file))
                    if lore and lore.metadata:
                        lores.append({
                            'name': lore.metadata.name,
                            'author': lore.metadata.author or 'Inconnu',
                            'version': lore.metadata.version or 'N/A',
                            'file': lore_file.name,
                            'lore': lore
                        })
                except:
                    pass
        return lores

# --- Fonctions d'analyse simulées (pour démonstration) ---
def simulate_analysis(prompt: str, plugins: List[str], lores: List[str]) -> Dict[str, Any]:
    """Simule une analyse pour la démonstration."""
    
    findings = {}
    
    # Simuler les résultats des plugins
    plugin_results = {
        'authority': ['expert', 'scientist', 'researcher'] if 'expert' in prompt.lower() else [],
        'assumptions': ['because', 'since'] if 'because' in prompt.lower() else [],
        'contradictions': ['but', 'however'] if 'but' in prompt.lower() else [],
        'ontology': ['is', 'exists'] if 'is' in prompt.lower() else [],
        'bias': ['obviously'] if 'obviously' in prompt.lower() else [],
        'counterprompt': ["What if the opposite were true?"],
        'debate': ['argue', 'discuss'] if 'argue' in prompt.lower() else [],
        'temporal': ['now', 'future'] if 'future' in prompt.lower() else [],
        'affect': ['believe', 'think'] if 'believe' in prompt.lower() else [],
    }
    
    # Ajouter les résultats des plugins sélectionnés
    for plugin in plugins:
        if plugin in plugin_results:
            findings[plugin] = plugin_results[plugin]
    
    # Simuler les résultats des Lores
    if lores:
        findings['lore_assumptions'] = ['La connaissance est mesurable', 'L\'expertise existe']
        findings['lore_myths'] = ['L\'IA pense comme un humain']
        findings['lore_questions'] = ['Qu\'est-ce que la compréhension ?']
    
    # Métadonnées
    metadata = {
        'timestamp': datetime.now().isoformat(),
        'plugins_used': plugins,
        'lores_used': lores,
        'findings_count': sum(len(v) if isinstance(v, list) else 1 for v in findings.values())
    }
    
    return {
        'findings': findings,
        'metadata': metadata,
        'prompt': prompt
    }

# --- Interface principale ---
def main():
    # Sidebar
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-content">
            <div style="text-align: center; margin-bottom: 2rem;">
                <div style="font-size: 3rem;">🔍</div>
                <div style="font-size: 1.5rem; font-weight: 700; color: #ccd6f6;">Searchlores</div>
                <div style="color: #8892b0; font-size: 0.9rem;">v3.0 - Cognitive Archaeology</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Sélection des plugins
        st.markdown("### 🧩 Plugins")
        
        plugin_manager = PluginManager()
        
        # Catégories
        plugin_categories = {
            '📦 Built-in': list(plugin_manager.builtin_plugins.keys()),
            '🔬 Advanced': list(plugin_manager.advanced_plugins.keys())
        }
        
        selected_plugins = []
        
        for category, plugins in plugin_categories.items():
            if plugins:
                st.markdown(f"**{category}**")
                for plugin in plugins:
                    info = plugin_manager.get_plugin_info(plugin)
                    if info:
                        if st.checkbox(
                            f"{plugin}",
                            value=True,
                            help=info.get('description', ''),
                            key=f"plugin_{plugin}"
                        ):
                            selected_plugins.append(plugin)
                st.markdown("---")
        
        # Sélection des Lores
        st.markdown("### 📚 Lores")
        
        lore_manager = LoreManager()
        available_lores = lore_manager.get_available_lores()
        
        selected_lores = []
        
        if available_lores:
            for lore_info in available_lores:
                if st.checkbox(
                    f"📖 {lore_info['name']}",
                    value=False,
                    help=f"Par {lore_info['author']} (v{lore_info['version']})",
                    key=f"lore_{lore_info['name']}"
                ):
                    selected_lores.append(lore_info['name'])
        else:
            st.info("Aucun Lore trouvé. Placez vos fichiers .lore dans le dossier `lores/`")
        
        # Options avancées
        st.markdown("### ⚙️ Options")
        use_advanced = st.checkbox("Mode avancé", value=False, help="Utilise l'orchestrateur pour les plugins avancés")
        verbose = st.checkbox("Mode verbeux", value=False)
        
        # Bouton d'analyse
        st.markdown("---")
        analyze_button = st.button(
            "🚀 Lancer l'investigation",
            use_container_width=True,
            type="primary"
        )
    
    # Zone principale
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.markdown("""
        <div class="stat-card">
            <div class="stat-number">{}</div>
            <div class="stat-label">Plugins disponibles</div>
        </div>
        """.format(len(plugin_manager.all_plugins)), unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="stat-card">
            <div class="stat-number">{}</div>
            <div class="stat-label">Lores disponibles</div>
        </div>
        """.format(len(available_lores)), unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="stat-card">
            <div class="stat-number">{}</div>
            <div class="stat-label">Analyses effectuées</div>
        </div>
        """.format(st.session_state.get('analysis_count', 0)), unsafe_allow_html=True)
    
    # Zone de prompt
    st.markdown("### 📝 Prompt à analyser")
    
    prompt_input = st.text_area(
        "Entrez votre prompt ici ou chargez un fichier",
        height=150,
        placeholder="Exemple: You are an expert in AI. Explain why LLMs understand language.",
        key="prompt_input"
    )
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "📂 ou chargez un fichier texte",
            type=['txt', 'md'],
            accept_multiple_files=False,
            key="file_upload"
        )
        
        if uploaded_file is not None:
            prompt_input = uploaded_file.getvalue().decode("utf-8")
            st.success(f"✅ Fichier chargé: {uploaded_file.name}")
    
    with col2:
        if st.button("🗑️ Effacer", use_container_width=True):
            st.session_state.prompt_input = ""
            st.session_state.file_upload = None
            st.rerun()
    
    # Analyse
    if analyze_button and prompt_input:
        with st.spinner("🔍 Investigation en cours..."):
            # Ici, utiliser le vrai moteur ou la simulation
            if SEARCHLORES_AVAILABLE:
                # Version réelle
                result = real_analysis(prompt_input, selected_plugins, selected_lores, use_advanced, verbose)
            else:
                # Version simulée pour démonstration
                result = simulate_analysis(prompt_input, selected_plugins, selected_lores)
            
            st.session_state['last_result'] = result
            st.session_state['analysis_count'] = st.session_state.get('analysis_count', 0) + 1
            
            # Afficher les résultats
            display_results(result)
    
    elif analyze_button and not prompt_input:
        st.warning("⚠️  Veuillez entrer un prompt à analyser")
    
    # Afficher les résultats précédents
    if 'last_result' in st.session_state and not analyze_button:
        display_results(st.session_state['last_result'])

def real_analysis(prompt: str, plugins: List[str], lores: List[str], use_advanced: bool, verbose: bool):
    """Version réelle de l'analyse."""
    # Implémentez ici la vraie analyse avec vos plugins
    # Pour l'instant, on utilise la simulation
    return simulate_analysis(prompt, plugins, lores)

def display_results(result: Dict[str, Any]):
    """Affiche les résultats de l'analyse."""
    
    st.markdown("---")
    st.markdown("## 📊 Résultats de l'Archéologie Cognitive")
    
    findings = result.get('findings', {})
    metadata = result.get('metadata', {})
    prompt = result.get('prompt', '')
    
    if not findings:
        st.info("ℹ️  Aucune trouvaille. Le prompt est peut-être trop neutre.")
        return
    
    # Métriques rapides
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Trouvailles", metadata.get('findings_count', 0))
    with col2:
        st.metric("Plugins utilisés", len(metadata.get('plugins_used', [])))
    with col3:
        st.metric("Lores appliqués", len(metadata.get('lores_used', [])))
    
    # Tableau des résultats
    st.markdown("### 🎯 Détails des trouvailles")
    
    # Créer un DataFrame pour l'affichage
    data = []
    for key, value in findings.items():
        if isinstance(value, list):
            for item in value:
                data.append({
                    'Catégorie': key.replace('_', ' ').title(),
                    'Trouvaille': item,
                    'Type': 'Liste'
                })
        else:
            data.append({
                'Catégorie': key.replace('_', ' ').title(),
                'Trouvaille': str(value),
                'Type': 'Valeur'
            })
    
    if data:
        df = pd.DataFrame(data)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Catégorie": st.column_config.TextColumn("Catégorie", width="medium"),
                "Trouvaille": st.column_config.TextColumn("Trouvaille", width="large"),
                "Type": st.column_config.TextColumn("Type", width="small"),
            }
        )
    
    # Visualisation avec Plotly
    st.markdown("### 📈 Visualisation")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Graphique à barres des catégories
        categories = [k.replace('_', ' ').title() for k in findings.keys()]
        counts = []
        for key in findings.keys():
            if isinstance(findings[key], list):
                counts.append(len(findings[key]))
            else:
                counts.append(1)
        
        fig = go.Figure(data=[
            go.Bar(
                x=categories,
                y=counts,
                marker_color='#7b2ffc',
                text=counts,
                textposition='auto',
            )
        ])
        
        fig.update_layout(
            title="Nombre de trouvailles par catégorie",
            xaxis_title="Catégories",
            yaxis_title="Nombre",
            template="plotly_dark",
            showlegend=False,
            height=300,
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Diagramme en anneau des plugins
        plugin_counts = {}
        for key in findings.keys():
            if key.startswith('lore_'):
                plugin_counts['Lores'] = plugin_counts.get('Lores', 0) + 1
            else:
                plugin_counts['Plugins'] = plugin_counts.get('Plugins', 0) + 1
        
        fig = go.Figure(data=[
            go.Pie(
                labels=list(plugin_counts.keys()),
                values=list(plugin_counts.values()),
                hole=0.4,
                marker_colors=['#7b2ffc', '#00d4ff'],
                textinfo='label+percent',
            )
        ])
        
        fig.update_layout(
            title="Répartition des trouvailles",
            template="plotly_dark",
            height=300,
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Graphique réseau (si assez de données)
    if len(findings) > 3:
        st.markdown("### 🕸️ Réseau conceptuel")
        
        G = nx.Graph()
        
        # Ajouter les nœuds
        for key in findings.keys():
            G.add_node(key.replace('_', ' ').title(), type='category')
            if isinstance(findings[key], list):
                for item in findings[key][:5]:  # Limiter pour la lisibilité
                    if isinstance(item, str) and len(item) < 50:
                        G.add_node(item[:30], type='item')
                        G.add_edge(key.replace('_', ' ').title(), item[:30])
        
        if len(G.nodes) > 2:
            pos = nx.spring_layout(G, k=1, iterations=50)
            
            # Créer les traces
            edge_x = []
            edge_y = []
            for edge in G.edges():
                x0, y0 = pos[edge[0]]
                x1, y1 = pos[edge[1]]
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])
            
            edge_trace = go.Scatter(
                x=edge_x, y=edge_y,
                line=dict(width=0.5, color='#8892b0'),
                hoverinfo='none',
                mode='lines'
            )
            
            node_x = []
            node_y = []
            node_text = []
            node_color = []
            
            for node in G.nodes():
                x, y = pos[node]
                node_x.append(x)
                node_y.append(y)
                node_text.append(node)
                
                # Couleur selon le type
                if G.nodes[node].get('type') == 'category':
                    node_color.append('#7b2ffc')
                else:
                    node_color.append('#00d4ff')
            
            node_trace = go.Scatter(
                x=node_x, y=node_y,
                mode='markers+text',
                hoverinfo='text',
                text=node_text,
                textposition='top center',
                textfont=dict(size=10, color='#ccd6f6'),
                marker=dict(
                    size=20 if G.nodes[node].get('type') == 'category' else 10,
                    color=node_color,
                    line=dict(width=2, color='#1a1d24')
                )
            )
            
            fig = go.Figure(
                data=[edge_trace, node_trace],
                layout=go.Layout(
                    title="Réseau conceptuel des trouvailles",
                    template="plotly_dark",
                    showlegend=False,
                    hovermode='closest',
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    height=400,
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    # Métadonnées
    with st.expander("📋 Métadonnées", expanded=False):
        st.json(metadata)
    
    # Export
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 Exporter en JSON", use_container_width=True):
            json_str = json.dumps(result, indent=2, default=str)
            b64 = base64.b64encode(json_str.encode()).decode()
            href = f'<a href="data:application/json;base64,{b64}" download="searchlores_result.json">Télécharger JSON</a>'
            st.markdown(href, unsafe_allow_html=True)
    
    with col2:
        if st.button("📥 Exporter en Markdown", use_container_width=True):
            md_lines = []
            md_lines.append(f"# Rapport Searchlores\n")
            md_lines.append(f"**Prompt**: {prompt}\n")
            md_lines.append(f"**Date**: {metadata.get('timestamp', 'N/A')}\n")
            md_lines.append("## Résultats\n")
            for key, value in findings.items():
                if isinstance(value, list):
                    md_lines.append(f"### {key.replace('_', ' ').title()}")
                    for item in value:
                        md_lines.append(f"- {item}")
                    md_lines.append("")
            
            md_str = "\n".join(md_lines)
            b64 = base64.b64encode(md_str.encode()).decode()
            href = f'<a href="data:text/markdown;base64,{b64}" download="searchlores_report.md">Télécharger Markdown</a>'
            st.markdown(href, unsafe_allow_html=True)
    
    with col3:
        if st.button("📥 Exporter en CSV", use_container_width=True):
            df = pd.DataFrame(data)
            csv = df.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="searchlores_results.csv">Télécharger CSV</a>'
            st.markdown(href, unsafe_allow_html=True)

if __name__ == "__main__":
    main()