#!/bin/bash
# launch_gui.sh - Script de lancement de la GUI

echo "🚀 Lancement de Searchlores GUI v3.0"
echo "===================================="

# Vérifier les dépendances
echo "📦 Vérification des dépendances..."

# Vérifier Streamlit
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "📦 Installation de Streamlit..."
    pip install streamlit plotly networkx pandas
fi

# Vérifier les dépendances du projet
if ! python3 -c "import searchlores" 2>/dev/null; then
    echo "⚠️  Searchlores non installé. Installation en mode développement..."
    pip install -e .
fi

# Lancer la GUI
echo "🌐 Lancement de l'interface..."
streamlit run searchlores_gui.py --server.port 8501 --server.address localhost

echo "✅ GUI lancée sur http://localhost:8501"