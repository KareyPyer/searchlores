import streamlit as st
import json
import os
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import networkx as nx
from collections import Counter
import re

st.set_page_config(
    page_title="Searchlores DataViz",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Searchlores - Analyse des Prompts")
st.caption("Exploration visuelle des fichiers JSON générés par le Framework Searchlores")

# Sidebar : sélection du fichier
DATA_DIR = "./data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
    st.warning(f"Le dossier {DATA_DIR} n'existe pas. Veuillez y placer vos fichiers JSON.")

json_files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith('.json')])

if not json_files:
    st.error("Aucun fichier JSON trouvé dans le dossier ./data")
    st.stop()

selected_file = st.sidebar.selectbox("📄 Sélectionner un fichier", json_files)

@st.cache_data
def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def safe_get(data, *keys, default=None):
    """Récupère une valeur dans un dict imbriqué de façon sécurisée."""
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key)
        else:
            return default
    return data if data is not None else default

data = load_json(os.path.join(DATA_DIR, selected_file))

# Affichage du prompt
with st.expander("📝 Prompt original", expanded=False):
    st.markdown(f"> {safe_get(data, 'prompt', default='Prompt non trouvé')}")

# Métadonnées
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📊 Findings", safe_get(data, 'metadata', 'findings_count', default=0))
with col2:
    mode = safe_get(data, 'metadata', 'mode', default='inconnu')
    st.metric("⚙️ Mode", mode)
with col3:
    lore = safe_get(data, 'metadata', 'lore_applied', default='Non spécifié')
    st.metric("📚 Lore", lore)

# ==================== 1. RÉGIMES ÉPISTÉMIQUES ====================
st.header("🧠 Régimes Épistémiques")

regimes_data = safe_get(data, 'findings', 'epistemic_regimes', default=[])

if regimes_data:
    # Heatmap des scores par régime
    df_scores = pd.DataFrame([
        {
            "Segment": r.get("segment", "")[:80] + "...",
            "Régime": r.get("regime", "unknown"),
            "Confiance": r.get("confidence", 0),
            **r.get("regime_scores", {})
        }
        for r in regimes_data
        if isinstance(r, dict)
    ])

    if not df_scores.empty:
        col1, col2 = st.columns([2, 1])

        with col1:
            # Heatmap des scores
            score_cols = [c for c in df_scores.columns if c not in ["Segment", "Régime", "Confiance"]]
            if score_cols:
                fig_heatmap = px.imshow(
                    df_scores[score_cols].T,
                    labels=dict(x="Segment", y="Régime", color="Score"),
                    title="Scores par Régime Épistémique",
                    text_auto=True,
                    aspect="auto",
                    color_continuous_scale="Viridis"
                )
                fig_heatmap.update_layout(
                    xaxis=dict(tickangle=45, tickfont=dict(size=8)),
                    yaxis=dict(title="Régime"),
                )
                st.plotly_chart(fig_heatmap, use_container_width=True)

        with col2:
            # Distribution des régimes
            regime_counts = df_scores["Régime"].value_counts()
            fig_pie = px.pie(
                values=regime_counts.values,
                names=regime_counts.index,
                title="Distribution des Régimes"
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        # Tableau des scores
        st.subheader("Détail des régimes épistémiques")
        st.dataframe(
            df_scores.style.background_gradient(subset=["Confiance"] + score_cols, cmap="Blues"),
            use_container_width=True,
            height=300
        )

# ==================== 2. SILENCES ====================
st.header("🔇 Silences")

silences = safe_get(data, 'findings', 'silences', default=[])
if silences:
    df_silences = pd.DataFrame([
        {
            "Domaine": s.get("domain", "inconnu"),
            "Contenu": s.get("content", "")[:100] + "...",
            "Severité": s.get("severity", 0),
            "Raison": s.get("reason", "")[:80] + "..."
        }
        for s in silences
        if isinstance(s, dict)
    ])

    if not df_silences.empty:
        fig = px.bar(
            df_silences.sort_values("Severité", ascending=False),
            x="Domaine",
            y="Severité",
            title="Severité des Silences par Domaine",
            color="Severité",
            color_continuous_scale="Reds",
            text_auto=".2f"
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(df_silences, use_container_width=True, height=300)

# ==================== 3. NARRATIVE LEVELS ====================
st.header("📖 Niveaux Narratifs")

narrative_levels = safe_get(data, 'findings', 'narrative_levels', default=[])
if narrative_levels:
    df_narr = pd.DataFrame([
        {
            "Niveau": l.get("level", 0),
            "Voix": l.get("voice", "inconnue"),
            "Contenu": l.get("content", "")[:150] + "...",
            "Début": l.get("start_pos", 0),
            "Fin": l.get("end_pos", 0)
        }
        for l in narrative_levels
        if isinstance(l, dict)
    ])

    # Visualisation en timeline
    if not df_narr.empty:
        fig = go.Figure()
        colors = ["#2E86AB", "#A23B72", "#F18F01", "#C73E1D", "#6A994E"]

        for i, row in df_narr.iterrows():
            fig.add_trace(go.Bar(
                y=[row["Niveau"]],
                x=[row["Fin"] - row["Début"]],
                base=[row["Début"]],
                orientation="h",
                name=row["Voix"],
                text=f"N{row['Niveau']}: {row['Voix']}",
                marker_color=colors[i % len(colors)],
                textposition="inside",
                hovertemplate=f"<b>{row['Voix']}</b><br>"
                              f"Début: {row['Début']}<br>"
                              f"Fin: {row['Fin']}<br>"
                              f"Longueur: {row['Fin'] - row['Début']} caractères<br>"
                              f"{row['Contenu']}<extra></extra>"
            ))

        fig.update_layout(
            title="Structure Narrative du Prompt",
            xaxis_title="Position dans le texte (caractères)",
            yaxis_title="Niveau Narratif",
            barmode="stack",
            height=300,
            showlegend=True
        )
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(df_narr[["Niveau", "Voix", "Contenu"]], use_container_width=True, height=200)

# ==================== 4. TENSIONS NARRATIVES ====================
st.header("⚡ Tensions Narratives")

tensions = safe_get(data, 'findings', 'narrative_tensions', default=[])
if tensions:
    df_tensions = pd.DataFrame([
        {
            "Description": t.get("description", "")[:120] + "...",
            "Type": t.get("tension_type", "inconnu"),
            "Niveau A": t.get("level_a", 0),
            "Niveau B": t.get("level_b", 0)
        }
        for t in tensions
        if isinstance(t, dict)
    ])

    if not df_tensions.empty:
        # Comptage par type
        type_counts = df_tensions["Type"].value_counts()
        col1, col2 = st.columns(2)

        with col1:
            fig_pie_tensions = px.pie(
                values=type_counts.values,
                names=type_counts.index,
                title="Types de Tensions Narratives",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig_pie_tensions, use_container_width=True)

        with col2:
            fig_bar_tensions = px.bar(
                df_tensions,
                x="Description",
                y="Niveau A",
                color="Type",
                title="Tensions entre niveaux narratifs",
                barmode="group"
            )
            fig_bar_tensions.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_bar_tensions, use_container_width=True)

        st.dataframe(df_tensions, use_container_width=True, height=200)

# ==================== 5. RÉGIMES DE VÉRITÉ ====================
st.header("🎯 Régimes de Vérité")

regimes_truth = safe_get(data, 'findings', 'regimes_of_truth', default=[])
if regimes_truth:
    df_truth = pd.DataFrame([
        {
            "Régime": r.get("regime", "inconnu"),
            "Énoncés acceptés": ", ".join(r.get("statements_accepted", [])[:3]) + ("..." if len(r.get("statements_accepted", [])) > 3 else ""),
            "Énoncés exclus": ", ".join(r.get("statements_excluded", [])[:3]) + ("..." if len(r.get("statements_excluded", [])) > 3 else ""),
            "Conditions": ", ".join(r.get("conditions_of_possibility", [])[:3])
        }
        for r in regimes_truth
        if isinstance(r, dict)
    ])

    if not df_truth.empty:
        # Visualisation des conditions de possibilité sous forme de sunburst
        all_conditions = []
        for r in regimes_truth:
            regime = r.get("regime", "inconnu")
            for c in r.get("conditions_of_possibility", []):
                all_conditions.append({"Régime": regime, "Condition": c})

        if all_conditions:
            df_cond = pd.DataFrame(all_conditions)
            fig_sunburst = px.sunburst(
                df_cond,
                path=["Régime", "Condition"],
                title="Conditions de possibilité par Régime de Vérité"
            )
            st.plotly_chart(fig_sunburst, use_container_width=True)

        st.dataframe(df_truth, use_container_width=True, height=300)

# ==================== 6. AUTORITÉS IMPLICITES ====================
st.header("👤 Autorités Implicites")

implicit_auth = safe_get(data, 'findings', 'implicit_authorities', default=[])
if implicit_auth:
    df_auth = pd.DataFrame([
        {
            "Agent": a.get("agent", "inconnu"),
            "Type": a.get("authority_type", "inconnu"),
            "Confiance": a.get("confidence", 0),
            "Manifestations": ", ".join(a.get("manifestations", [])[:3]) + ("..." if len(a.get("manifestations", [])) > 3 else ""),
            "Contre-autorités": ", ".join(a.get("counter_authorities", [])[:3]) + ("..." if len(a.get("counter_authorities", [])) > 3 else "")
        }
        for a in implicit_auth
        if isinstance(a, dict)
    ])

    if not df_auth.empty:
        fig = px.scatter(
            df_auth,
            x="Agent",
            y="Confiance",
            color="Type",
            size="Confiance",
            hover_data=["Manifestations"],
            title="Autorités Implicites - Niveau de Confiance"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(df_auth, use_container_width=True, height=250)

# ==================== 7. DYNAMIQUES DE POUVOIR ====================
st.header("⚖️ Dynamiques de Pouvoir")

power_dyn = safe_get(data, 'findings', 'power_dynamics', default=[])
if power_dyn:
    df_power = pd.DataFrame([
        {
            "Agent dominant": d.get("dominant_agent", "inconnu") if isinstance(d, dict) else "inconnu",
            "Agent soumis": d.get("submissive_agent", "inconnu") if isinstance(d, dict) else "inconnu",
            "Score asymétrie": d.get("asymmetry_score", 0) if isinstance(d, dict) else 0,
            "Mécanismes": ", ".join(d.get("power_mechanisms", [])[:3]) + ("..." if len(d.get("power_mechanisms", [])) > 3 else "") if isinstance(d, dict) else ""
        }
        for d in power_dyn
        if d is not None
    ])

    if not df_power.empty and df_power.iloc[0]["Agent dominant"] != "inconnu":
        # Graphique en réseau des relations de pouvoir
        G = nx.DiGraph()
        for _, row in df_power.iterrows():
            if row["Agent dominant"] and row["Agent soumis"]:
                G.add_edge(row["Agent dominant"], row["Agent soumis"], 
                          weight=row["Score asymétrie"])

        if G.edges():
            pos = nx.spring_layout(G, seed=42)
            edge_trace = []
            for edge in G.edges(data=True):
                x0, y0 = pos[edge[0]]
                x1, y1 = pos[edge[1]]
                edge_trace.append(go.Scatter(
                    x=[x0, x1, None],
                    y=[y0, y1, None],
                    mode='lines',
                    line=dict(width=edge[2].get("weight", 1) * 3, color='#888'),
                    hoverinfo='none'
                ))

            node_trace = go.Scatter(
                x=[pos[n][0] for n in G.nodes()],
                y=[pos[n][1] for n in G.nodes()],
                mode='markers+text',
                marker=dict(size=[30]*len(G.nodes()), color='#2E86AB'),
                text=list(G.nodes()),
                textposition="middle center",
                hoverinfo='text'
            )

            fig_power = go.Figure(data=edge_trace + [node_trace])
            fig_power.update_layout(
                title="Réseau des Relations de Pouvoir",
                showlegend=False,
                hovermode='closest',
                xaxis=dict(showgrid=False, zeroline=False, visible=False),
                yaxis=dict(showgrid=False, zeroline=False, visible=False),
                height=400
            )
            st.plotly_chart(fig_power, use_container_width=True)

        st.dataframe(df_power, use_container_width=True, height=200)

# ==================== 8. MATRICE DE CONCORDANCE / CONFUSION ====================
st.header("📊 Matrices de Concordance")

# Matrice de confusion entre régimes épistémiques et silences
if regimes_data and silences:
    # Créer une matrice de co-occurrence
    regimes_list = [r.get("regime", "unknown") for r in regimes_data if isinstance(r, dict)]
    silence_domains = [s.get("domain", "inconnu") for s in silences if isinstance(s, dict)]

    # Heatmap de co-occurrence
    cooccurrence = {}
    for regime in set(regimes_list):
        for domain in set(silence_domains):
            key = (regime, domain)
            cooccurrence[key] = 0

    # Compter les cooccurrences (simplifié)
    if regimes_data and silences:
        # On associe chaque segment de régime à un silence
        for r in regimes_data:
            if isinstance(r, dict):
                regime = r.get("regime", "unknown")
                for s in silences:
                    if isinstance(s, dict):
                        domain = s.get("domain", "inconnu")
                        if domain != "inconnu":
                            key = (regime, domain)
                            cooccurrence[key] = cooccurrence.get(key, 0) + 1

    df_cooc = pd.DataFrame([
        {"Régime": k[0], "Domaine silence": k[1], "Cooccurrence": v}
        for k, v in cooccurrence.items() if v > 0
    ])

    if not df_cooc.empty:
        fig_cooc = px.density_heatmap(
            df_cooc,
            x="Régime",
            y="Domaine silence",
            z="Cooccurrence",
            title="Matrice de Cooccurrence : Régimes Épistémiques × Silences",
            color_continuous_scale="Blues",
            text_auto=True
        )
        st.plotly_chart(fig_cooc, use_container_width=True)

# ==================== 9. WORD CLOUD / FREQUENCES ====================
st.header("📝 Fréquences des termes clés")

prompt_text = safe_get(data, 'prompt', default="")
if prompt_text:
    # Nettoyage basique
    words = re.findall(r'\b[a-z]{3,}\b', prompt_text.lower())
    word_counts = Counter(words)
    top_words = dict(word_counts.most_common(20))

    if top_words:
        df_words = pd.DataFrame({
            "Mot": list(top_words.keys()),
            "Fréquence": list(top_words.values())
        })

        fig_words = px.bar(
            df_words,
            x="Mot",
            y="Fréquence",
            title="Mots les plus fréquents dans le prompt",
            color="Fréquence",
            color_continuous_scale="Viridis"
        )
        fig_words.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_words, use_container_width=True)

# ==================== 10. Aperçu complet ====================
st.header("📋 Données brutes (aperçu)")

with st.expander("Voir les données complètes du fichier JSON", expanded=False):
    st.json(data)

# Export
st.sidebar.markdown("---")
st.sidebar.markdown("### 📥 Export")
if st.sidebar.button("Exporter les données en CSV"):
    # Export des données principales en CSV
    @st.cache_data
    def export_data():
        # Créer un DataFrame à partir des findings
        findings = data.get("findings", {})
        rows = []
        for key, value in findings.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        rows.append({"catégorie": key, **item})
        return pd.DataFrame(rows)

    df_export = export_data()
    csv = df_export.to_csv(index=False)
    st.sidebar.download_button(
        label="Télécharger CSV",
        data=csv,
        file_name=f"searchlores_export_{selected_file.replace('.json', '.csv')}",
        mime="text/csv"
    )

st.sidebar.markdown("---")
st.sidebar.caption("🔍 DataViz pour Searchlores | Made with ❤️")
