# tabs/impressoras.py

import streamlit as st
import sqlite3
import pandas as pd
import uuid
from datetime import date

def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS impressoras (
        id TEXT PRIMARY KEY,
        marca TEXT NOT NULL,
        modelo TEXT NOT NULL,
        status TEXT NOT NULL,
        horas_trabalhadas REAL DEFAULT 0.0
    );
    CREATE TABLE IF NOT EXISTS materiais (
        id TEXT PRIMARY KEY,
        tipo TEXT NOT NULL,
        cor TEXT,
        estoque REAL NOT NULL,
        unidade TEXT NOT NULL,
        fornecedor TEXT,
        preco_unit REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS manutencoes (
        id TEXT PRIMARY KEY,
        impressora_id TEXT NOT NULL REFERENCES impressoras(id),
        data TEXT NOT NULL,
        descricao TEXT,
        pecas_trocadas TEXT,
        custo REAL DEFAULT 0.0
    );
    """)
    conn.commit()
    return conn

def show_impressoras_tab(db_path: str):
    conn = init_db(db_path)
    cur = conn.cursor()

    st.header("🖨️ Impressoras & Materiais")

    # Impressoras
    st.subheader("🏭 Impressoras")
    with st.expander("➕ Adicionar / Editar Impressora", expanded=False):
        marca = st.text_input("Marca", key="imp_marca")
        modelo = st.text_input("Modelo", key="imp_modelo")
        status = st.selectbox("Status", ["operacao", "manutencao", "parada"], key="imp_status")
        horas = st.number_input("Horas trabalhadas", 0.0, step=0.1, key="imp_horas")
        if st.button("Salvar Impressora", key="imp_salvar"):
            pid = str(uuid.uuid4())
            cur.execute(
                "INSERT OR REPLACE INTO impressoras VALUES (?,?,?,?,?)",
                (pid, marca, modelo, status, horas)
            )
            conn.commit()
            st.success("Impressora salva com sucesso!")

    df_imp = pd.read_sql_query("SELECT * FROM impressoras", conn)
    st.dataframe(df_imp, use_container_width=True)
    if not df_imp.empty:
        sel_imp = st.selectbox(
            "Excluir Impressora",
            df_imp["id"],
            format_func=lambda i: df_imp.set_index("id").loc[i, "modelo"],
            key="imp_exc"
        )
        if st.button("❌ Excluir Impressora", key="imp_excluir"):
            cur.execute("DELETE FROM impressoras WHERE id = ?", (sel_imp,))
            conn.commit()
            st.warning("Impressora excluída.")
            st.experimental_rerun()

    st.markdown("---")

    # Materiais
    st.subheader("📦 Materiais (Filamentos e Resinas)")
    gatilho = st.number_input("Gatilho baixo (g ou L)", 0.0, step=0.1, key="mat_gatilho")
    with st.expander("➕ Adicionar / Editar Material", expanded=False):
        tipo = st.selectbox("Tipo", ["PLA","PETG","ABS","resina_padrao","resina_flexivel"], key="mat_tipo")
        cor = st.text_input("Cor", key="mat_cor")
        estoque = st.number_input("Quantidade em estoque", 0.0, step=0.1, key="mat_estoque")
        unidade = st.selectbox("Unidade", ["g","L"], key="mat_unidade")
        fornecedor = st.text_input("Fornecedor", key="mat_fornecedor")
        preco = st.number_input("Preço unitário", 0.0, step=0.01, key="mat_preco")
        if st.button("Salvar Material", key="mat_salvar"):
            mid = str(uuid.uuid4())
            cur.execute(
                "INSERT OR REPLACE INTO materiais VALUES (?,?,?,?,?,?,?)",
                (mid, tipo, cor, estoque, unidade, fornecedor, preco)
            )
            conn.commit()
            st.success("Material salvo com sucesso!")

    df_mat = pd.read_sql_query("SELECT * FROM materiais", conn)

    # Filtros Avançados de Materiais
    st.markdown("**Filtros Avançados de Materiais**")
    m1, m2, m3 = st.columns(3)
    with m1:
        tipo_filtro = st.selectbox("Filtrar por Tipo", ["Todos"] + sorted(df_mat["tipo"].dropna().unique().tolist()))
    with m2:
        cor_filtro = st.selectbox("Filtrar por Cor", ["Todos"] + sorted(df_mat["cor"].dropna().unique().tolist()))
    with m3:
        forn_filtro = st.selectbox("Filtrar por Fornecedor", ["Todos"] + sorted(df_mat["fornecedor"].dropna().unique().tolist()))

    df_mat_filt = df_mat.copy()
    if tipo_filtro != "Todos":
        df_mat_filt = df_mat_filt[df_mat_filt["tipo"] == tipo_filtro]
    if cor_filtro != "Todos":
        df_mat_filt = df_mat_filt[df_mat_filt["cor"] == cor_filtro]
    if forn_filtro != "Todos":
        df_mat_filt = df_mat_filt[df_mat_filt["fornecedor"] == forn_filtro]

    for _, row in df_mat_filt.iterrows():
        if row["estoque"] < gatilho:
            st.warning(f"⚠️ Estoque baixo: {row['tipo']} ({row['cor']}): {row['estoque']} {row['unidade']}")
    st.dataframe(df_mat_filt, use_container_width=True)
    if not df_mat_filt.empty:
        sel_mat = st.selectbox(
            "Excluir Material",
            df_mat_filt["id"],
            format_func=lambda i: f"{df_mat_filt.set_index('id').loc[i,'tipo']} ({df_mat_filt.set_index('id').loc[i,'cor']})",
            key="mat_exc"
        )
        if st.button("❌ Excluir Material", key="mat_excluir"):
            cur.execute("DELETE FROM materiais WHERE id = ?", (sel_mat,))
            conn.commit()
            st.warning("Material excluído.")
            st.experimental_rerun()

    st.markdown("---")

    # Histórico de Manutenções
    st.subheader("🛠 Histórico de Manutenções")
    df_man = pd.read_sql_query("SELECT * FROM manutencoes", conn)

    with st.expander("➕ Registrar Manutenção", expanded=False):
        imp_sel = st.selectbox(
            "Impressora",
            df_imp["id"],
            format_func=lambda i: df_imp.set_index("id").loc[i,'modelo'],
            key="man_imp"
        )
        data = st.date_input("Data", key="man_data", min_value=date(2000,1,1))
        desc = st.text_area("Descrição", key="man_desc")
        pecas = st.text_input("Peças Trocadas", key="man_pecas")
        custo = st.number_input("Custo (R$)", 0.0, step=0.1, key="man_custo")
        if st.button("Registrar Manutenção", key="man_salvar"):
            mid = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO manutencoes VALUES (?,?,?,?,?,?)",
                (mid, imp_sel, data.isoformat(), desc, pecas, custo)
            )
            conn.commit()
            st.success("Manutenção registrada!")

    # ── Filtros Avançados de Manutenção ───────────────────────────────────────
    st.markdown("**Filtros Avançados de Manutenção**")
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        imp_filtro = st.selectbox("Filtrar por Impressora", ["Todas"] + sorted(df_man["impressora_id"].dropna().unique().tolist()))

    # — aqui o único change: adicionamos key="man_periodo" —
    datas = pd.to_datetime(df_man["data"], errors="coerce").dt.date.dropna()
    start_default = datas.min() if not datas.empty else date.today()
    end_default   = datas.max() if not datas.empty else date.today()
    with f2:
        periodo = st.date_input(
            "Período",
            value=(start_default, end_default),
            key="man_periodo"
        )

    # preparo do intervalo de custos
    custos = df_man["custo"].dropna()
    min_cost = float(custos.min()) if not custos.empty else 0.0
    max_cost = float(custos.max()) if not custos.empty else 0.0
    with f3:
        if min_cost < max_cost:
            custo_min, custo_max = st.slider(
                "Intervalo de Custo (R$)",
                min_value=min_cost,
                max_value=max_cost,
                value=(min_cost, max_cost),
                step=0.1
            )
        else:
            st.write(f"Custo fixo: R$ {min_cost:,.2f}")
            custo_min, custo_max = min_cost, max_cost

    with f4:
        termo = st.text_input("Busca na Descrição", key="man_busca")

    # aplica filtros...
    df_man_filt = df_man.copy()
    if imp_filtro != "Todas":
        df_man_filt = df_man_filt[df_man_filt["impressora_id"] == imp_filtro]
    if isinstance(periodo, tuple):
        start, end = periodo
        df_man_filt = df_man_filt[
            (pd.to_datetime(df_man_filt["data"]).dt.date >= start) &
            (pd.to_datetime(df_man_filt["data"]).dt.date <= end)
        ]
    df_man_filt = df_man_filt[
        (df_man_filt["custo"] >= custo_min) &
        (df_man_filt["custo"] <= custo_max)
    ]
    if termo:
        df_man_filt = df_man_filt[df_man_filt["descricao"].str.contains(termo, case=False, na=False)]

    st.dataframe(df_man_filt, use_container_width=True)

    conn.close()
