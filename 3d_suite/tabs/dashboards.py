import os
import pandas as pd
import plotly.express as px
import streamlit as st

# Aba de Dashboards

def show_dashboards_tab(historico_csv: str, db_path: str):
    st.header("📈 Relatórios e Dashboards")

    # Carrega histórico (CSV) se existir
    if os.path.exists(historico_csv):
        df_dash = pd.read_csv(historico_csv)
    else:
        df_dash = pd.DataFrame()

    if df_dash.empty:
        st.warning("Nenhum orçamento registrado ainda!")
        return

    # Filtros
    st.subheader("🎯 Filtros para análise")
    colf1, colf2, colf3 = st.columns(3)
    clientes_op = ['Todos'] + sorted(df_dash['cliente'].dropna().unique())
    produtos_op = ['Todos'] + sorted(df_dash['produto_id'].dropna().unique())
    cliente_sel = colf1.selectbox("Cliente", clientes_op)
    produto_sel = colf2.selectbox("Produto", produtos_op)

    # Filtro por data
    datas = pd.to_datetime(df_dash['data'], errors='coerce')
    min_date = datas.min() if datas.notnull().any() else None
    max_date = datas.max() if datas.notnull().any() else None
    periodo = colf3.date_input("Período", (min_date, max_date) if min_date and max_date else ())

    df = df_dash.copy()
    if cliente_sel != "Todos":
        df = df[df['cliente'] == cliente_sel]
    if produto_sel != "Todos":
        df = df[df['produto_id'] == produto_sel]
    if periodo and len(periodo) == 2:
        df['data_dt'] = pd.to_datetime(df['data'], errors='coerce')
        df = df[(df['data_dt'] >= pd.to_datetime(periodo[0])) & (df['data_dt'] <= pd.to_datetime(periodo[1]))]

    # Indicadores
    st.subheader("📊 Indicadores")
    c1, c2, c3, c4 = st.columns(4)
    total_ven = df['preco_total'].astype(float).sum()
    lucro_tot = df['lucro_unit'].astype(float).sum()
    qtd_total = df['quantidade'].astype(float).sum()
    ticket = total_ven / qtd_total if qtd_total else 0
    c1.metric("Receita total", f"R$ {total_ven:,.2f}")
    c2.metric("Lucro total", f"R$ {lucro_tot:,.2f}")
    c3.metric("Qtd. peças", f"{int(qtd_total)}")
    c4.metric("Ticket médio", f"R$ {ticket:,.2f}")

    st.divider()

    # Evolução temporal
    st.subheader("📅 Evolução temporal")
    df['data_dt'] = pd.to_datetime(df['data'], errors='coerce')
    df_time = df.groupby(df['data_dt'].dt.to_period('M')).agg({
        'preco_total': 'sum',
        'lucro_unit': 'sum',
        'quantidade': 'sum'
    }).reset_index()
    df_time['data_dt'] = df_time['data_dt'].dt.strftime('%Y-%m')

    fig = px.bar(df_time, x='data_dt', y='preco_total', title='Receita Mensal')
    st.plotly_chart(fig, use_container_width=True)
    fig2 = px.line(df_time, x='data_dt', y='lucro_unit', title='Lucro Mensal')
    st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # Top produtos e clientes
    st.subheader("🏆 Produtos & Clientes")
    top_prod = df.groupby('produto_id').agg({'quantidade': 'sum', 'preco_total': 'sum'}).reset_index()
    if not top_prod.empty:
        figp = px.bar(
            top_prod.sort_values('quantidade', ascending=False).head(10),
            x='produto_id', y='quantidade', title='Top Produtos (Qtd)'
        )
        st.plotly_chart(figp)

    top_cli = df.groupby('cliente').agg({'preco_total': 'sum'}).reset_index()
    if not top_cli.empty:
        figc = px.bar(
            top_cli.sort_values('preco_total', ascending=False).head(10),
            x='cliente', y='preco_total', title='Top Clientes (Receita)'
        )
        st.plotly_chart(figc)

    st.divider()

    # Download dos dados filtrados
    st.subheader("📂 Download dos Dados")
    st.download_button(
        "Exportar dados filtrados (CSV)",
        df.to_csv(index=False).encode('utf-8'),
        file_name='relatorio_filtrado.csv'
    )
