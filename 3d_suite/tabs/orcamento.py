import os
import csv
import sqlite3
import streamlit as st
import pandas as pd
import plotly.express as px
from fpdf import FPDF
import tempfile
import datetime

# Helpers

def slugify(text: str) -> str:
    return text.replace(' ', '_').lower()

# Histórico via CSV

def carregar_historico(historico_csv: str) -> pd.DataFrame:
    if os.path.exists(historico_csv):
        return pd.read_csv(historico_csv)
    cols = [
        "data","cliente","descricao","produto_id","quantidade",
        "preco_unit","preco_total","custo_unit","lucro_unit","margem_erro",
        "peso_filamento_g","custo_filamento_kg","tempo_impressao_h",
        "potencia_watts","tarifa_kwh","energia_manual","usar_auto",
        "tipo_dano_peca","lucro_min_ideal","mao_de_obra","embalagem","transporte",
        "desc_2_4","desc_5_9","desc_10p"
    ]
    return pd.DataFrame(columns=cols)

def salvar_orcamento(historico_csv: str, entry: dict):
    existe = os.path.exists(historico_csv)
    with open(historico_csv, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not existe:
            writer.writerow(list(entry.keys()))
        writer.writerow(list(entry.values()))

def excluir_orcamento(historico_csv: str, idx: int):
    df = carregar_historico(historico_csv)
    df = df.drop(idx)
    df.to_csv(historico_csv, index=False)

def carregar_para_form(row: pd.Series, st_state: dict):
    for k, v in row.items():
        if k in st_state:
            st_state[k] = v

# callback para exclusão em um clique
def _handle_excluir_orcamento(hist_csv: str, idx: int):
    excluir_orcamento(hist_csv, idx)
    st.warning("Orçamento excluído!")
    st.rerun()  # reinicia o app imediatamente

# Aba de Orçamento

def show_orcamento_tab(historico_csv: str, db_path: str):
    # Inicializa session_state se necessário
    if 'preco_rebuild' not in st.session_state:
        st.session_state['preco_rebuild'] = 0
    if 'preco_venda_usuario_value' not in st.session_state:
        st.session_state['preco_venda_usuario_value'] = 0.0

    # Cabeçalho
    st.header("🖨️ Orçamento e Histórico")

    # Histórico
    df_hist = carregar_historico(historico_csv)
    if not df_hist.empty:
        c1, c2, c3 = st.columns(3)
        cli_f = c1.text_input("Cliente", key="f1")
        desc_f = c2.text_input("Descrição", key="f2")
        date_f = c3.text_input("Data (MM/YYYY)", key="f3")

        filt = df_hist.copy()
        if cli_f:
            filt = filt[filt['cliente'].str.contains(cli_f, case=False)]
        if desc_f:
            filt = filt[filt['descricao'].str.contains(desc_f, case=False)]
        if date_f:
            filt = filt[filt['data'].str.contains(date_f, case=False)]

        st.dataframe(filt, use_container_width=True)

        sel = st.selectbox("Selecione Orçamento", filt.index, key="sel_hist")
        a1, a2 = st.columns(2)

        if a1.button("📝 Reutilizar"):
            carregar_para_form(filt.loc[sel], st.session_state)
            st.session_state['preco_rebuild'] += 1
            st.session_state['preco_venda_usuario_value'] = float(
                filt.loc[sel].get('preco_unit', 0.0)
            )
            st.success("Formulário preenchido com sucesso!")

        # agora exclusão com um clique
        a2.button(
            "❌ Excluir",
            key=f"excluir_orc_{sel}",
            on_click=_handle_excluir_orcamento,
            args=(historico_csv, sel)
        )

    else:
        st.info("Nenhum orçamento registrado.")

    st.divider()

    # Entradas
    st.subheader("🔢 Entradas do Orçamento")

    # Carrega produtos do catálogo via SQLite
    df_prod = pd.DataFrame()
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path, check_same_thread=False)
        df_prod = pd.read_sql_query("SELECT * FROM produtos", conn)

    opts = ["Nenhum"] + df_prod['nome'].tolist() if not df_prod.empty else ["Nenhum"]
    escolha = st.selectbox("Produto base (opcional)", opts, key="prod_sel")
    if escolha != "Nenhum":
        pr = df_prod[df_prod['nome'] == escolha].iloc[0]
        st.info(f"💲 Preço base: R$ {pr['preco']:.2f}")
        st.session_state['preco_venda_usuario_value'] = float(pr['preco'])

    peso_filamento_g    = st.number_input("Filamento usado (g)", 0.0, step=0.1, key="peso_filamento_g")
    custo_filamento_kg  = st.number_input("Custo do filamento por kg (R$)", 0.0, step=0.1, key="custo_filamento_kg")
    tempo_impressao_h   = st.number_input("Tempo de impressão (h)", 0.0, step=0.1, key="tempo_impressao_h")
    margem_erro_perc    = st.slider("Margem de erro (%)", 0, 100, 15, key="margem_erro_percentual")
    margem_erro         = margem_erro_perc / 100
    potencia_watts      = st.number_input("Potência (W)", 0, step=1, key="potencia_watts")
    tarifa_kwh          = st.number_input("Tarifa (R$/kWh)", 0.0, step=0.01, key="tarifa_kwh")

    # Energia elétrica
    if 'usar_auto' in st.session_state:
        st.session_state['usar_auto'] = bool(st.session_state['usar_auto'])
    usar_auto = st.checkbox("Cálculo automático de energia", key="usar_auto")
    energia = (
        (potencia_watts * tempo_impressao_h * tarifa_kwh) / 1000
        if usar_auto
        else st.number_input("Energia (manual R$)", 0.0, step=0.1, key="energia_manual")
    )

    tipo_dano   = st.selectbox("Tamanho da peça", ["Pequena","Média","Grande"], key="tipo_dano_peca")
    lucros_map  = {"Pequena":10.0,"Média":20.0,"Grande":50.0}
    lucro_min   = st.number_input(
        f"Lucro ideal ({tipo_dano})",
        0.0,
        value=lucros_map[tipo_dano],
        step=0.1,
        key="lucro_min_ideal"
    )

    preco_key = f"preco_venda_usuario_{st.session_state['preco_rebuild']}"
    preco_venda = st.number_input(
        "Preço de venda por unidade (R$)",
        0.0,
        step=0.1,
        value=st.session_state.get('preco_venda_usuario_value', 0.0),
        key=preco_key
    )
    st.session_state['preco_venda_usuario'] = preco_venda

    mao_obra   = st.number_input("Mão de obra (R$)", 0.0, step=0.1, key="mao_de_obra")
    embalagem   = st.number_input("Embalagem (R$)", 0.0, step=0.1, key="embalagem")
    transporte  = st.number_input("Transporte (R$)", 0.0, step=0.1, key="transporte")
    qtd         = st.number_input("Quantidade de peças", 1, step=1, key="quantidade_pecas")
    aplicar_desc= st.checkbox("Aplicar desconto progressivo", key="aplicar_desconto")
    d24 = st.number_input("Desconto 2-4 peças (%)", 0, 100, 5, key="desc_2_4")
    d59 = st.number_input("Desconto 5-9 peças (%)", 0, 100, 10, key="desc_5_9")
    d10 = st.number_input("Desconto 10+ peças (%)",0,100,15,key="desc_10p")

    def aplica_desc(p, q):
        if q>=10: d=d10
        elif q>=5: d=d59
        elif q>=2: d=d24
        else: d=0
        return p*(1-d/100), d

    def calcula():
        desg_map={"Pequena":0.5,"Média":1.5,"Grande":3.0}
        desg=desg_map[tipo_dano]
        cf=(peso_filamento_g/1000)*custo_filamento_kg
        cb=cf+energia+desg+mao_obra+embalagem+transporte
        cm=cb*(1+margem_erro)
        pu=preco_venda
        lu=pu-cm
        pd,dp=aplica_desc(pu,qtd) if aplicar_desc else (pu,0)
        tp=pd*qtd; tc=cm*qtd; tl=tp-tc
        tipo_est=("Pequena ou simples" if cm<=20 else "Média ou moderada" if cm<=80 else "Grande ou complexa")
        return {
            "custo_unit":cm,
            "preco_unit":pu,
            "lucro_unit":lu,
            "desconto":dp,
            "preco_desc":pd,
            "preco_total":tp,
            "custo_total":tc,
            "lucro_total":tl,
            "tipo":tipo_est,
            "componentes":[
                ("Filamento",cf),("Energia",energia),
                ("Desgaste",desg),("Mão de Obra",mao_obra),
                ("Embalagem",embalagem),("Transporte",transporte)
            ]
        }

    res=calcula()

    # Resultados
    st.header("📈 Resultados")
    st.success(f"Custo unitário: R$ {res['custo_unit']:.2f}")
    st.info   (f"Preço unitário: R$ {res['preco_unit']:.2f}")
    st.caption(f"Lucro unitário: R$ {res['lucro_unit']:.2f}")
    st.success(f"Custo total ({qtd}x): R$ {res['custo_total']:.2f}")
    st.info   (f"Preço total: R$ {res['preco_total']:.2f}")
    st.caption(f"Lucro total: R$ {res['lucro_total']:.2f}")

    # Avaliação de Lucro
    st.subheader("📈 Avaliação de Lucro")
    st.markdown(f"**Lucro ideal:** R$ {lucro_min:.2f}")
    st.markdown(f"**Lucro aplicado por peça:** R$ {res['lucro_unit']:.2f}")
    margem_real=res['lucro_unit']/lucro_min if lucro_min else 0
    if margem_real<0.9:
        st.error("🔴 Lucro abaixo do ideal (menos de 90%).")
    elif margem_real<=1.2:
        st.success("🟢 Lucro dentro da faixa ideal (entre 90% e 120%).")
    else:
        st.warning("🟡 Lucro muito acima do ideal (acima de 120%).")

    if res['desconto']>0:
        econom=(res['preco_unit']-res['preco_desc'])*qtd
        st.info(f"Desconto: {res['desconto']}% → R$ {res['preco_desc']:.2f}")
        st.info(f"Você economiza: R$ {econom:.2f}")

    st.subheader("📊 Composição de Custos")
    names, vals = zip(*res['componentes'])
    fig = px.pie(names=names, values=vals, title="Composição do Custo")
    st.plotly_chart(fig, use_container_width=True)

    # PDF e Histórico
    st.header("📄 Orçamento do Cliente")
    cliente = st.text_input("Nome do cliente", key="cliente")
    desc_pdf = st.text_area("Descrição (opcional)", key="desc_cli")
    if st.button("Gerar PDF e Salvar Histórico"):
        if not cliente:
            st.error("Informe o nome do cliente!")
        else:
            pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", size=12)
            now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
            pdf.cell(200,10,"Orçamento 3D",ln=True,align="C"); pdf.ln(5)
            pdf.cell(200,10,f"Cliente: {cliente}",ln=True)
            pdf.cell(200,10,f"Data: {now}",ln=True)
            if desc_pdf: pdf.multi_cell(200,10,f"Descrição: {desc_pdf}")
            pdf.cell(200,10,f"Quantidade: {qtd}",ln=True)
            pdf.cell(200,10,f"Preço unit.: R$ {res['preco_desc']:.2f}",ln=True)
            pdf.cell(200,10,f"Preço total: R$ {res['preco_total']:.2f}",ln=True)
            pdf.cell(200,10,f"Margem erro: {margem_erro_perc}%",ln=True)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                pdf.output(tmp.name)
                st.success("PDF pronto!")
                with open(tmp.name,"rb") as f:
                    st.download_button(
                        "Baixar PDF",
                        f,
                        file_name=f"orc_{slugify(cliente)}.pdf",
                        mime="application/pdf"
                    )
            entry = {
                'data': now, 'cliente': cliente, 'descricao': desc_pdf,
                'produto_id': escolha, 'quantidade': qtd,
                'preco_unit': res['preco_desc'], 'preco_total': res['preco_total'],
                'custo_unit': res['custo_unit'], 'lucro_unit': res['lucro_unit'],
                'margem_erro': margem_erro_perc,
                'peso_filamento_g': peso_filamento_g,
                'custo_filamento_kg': custo_filamento_kg,
                'tempo_impressao_h': tempo_impressao_h,
                'potencia_watts': potencia_watts,
                'tarifa_kwh': tarifa_kwh,
                'energia_manual': energia if not usar_auto else 0.0,
                'usar_auto': usar_auto,
                'tipo_dano_peca': tipo_dano,
                'lucro_min_ideal': lucro_min,
                'mao_de_obra': mao_obra,
                'embalagem': embalagem,
                'transporte': transporte,
                'desc_2_4': d24,
                'desc_5_9': d59,
                'desc_10p': d10
            }
            salvar_orcamento(historico_csv, entry)
            st.success("Orçamento salvo no histórico!")
