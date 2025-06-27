# app.py
import os
import streamlit as st

from tabs.orcamento import show_orcamento_tab
from tabs.catalogo import show_catalogo_tab
from tabs.dashboards import show_dashboards_tab
from tabs.impressoras import show_impressoras_tab


# 📁 Paths para os dados (dentro da pasta `data/`)
HISTORICO_CSV = os.path.join("data", "historico_orcamentos.csv")
DB_PATH = os.path.join("data", "db_catalogo.db")

# 🌐 Configuração geral da página
st.set_page_config(
    page_title="3D Suite",
    page_icon="📦",
    layout="wide",
)

# ─── Cria as abas ──────────────────────────────────────────────────────────────
tab_orc, tab_cat, tab_dash, tab_imp = st.tabs([
    "🖨️ Orçamento",
    "📦 Catálogo",
    "📈 Relatórios e Dashboards",
    "🖨️ Impressoras & Materiais"          # ← nova aba
])

# ─── Aba 1: Orçamento ──────────────────────────────────────────────────────────
with tab_orc:
    show_orcamento_tab(HISTORICO_CSV, DB_PATH)

# ─── Aba 2: Catálogo ───────────────────────────────────────────────────────────
with tab_cat:
    show_catalogo_tab(HISTORICO_CSV, DB_PATH)

# ─── Aba 3: Dashboards ─────────────────────────────────────────────────────────
with tab_dash:
    show_dashboards_tab(HISTORICO_CSV, DB_PATH)

# ─── Aba 4: Impressoras & Materiais ───────────────────────────────────────────
with tab_imp:
    show_impressoras_tab(DB_PATH)
