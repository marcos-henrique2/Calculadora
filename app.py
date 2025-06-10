import streamlit as st
import plotly.graph_objects as go
from fpdf import FPDF
import tempfile
import datetime

st.set_page_config(page_title="Calculadora 3D", page_icon="🖨️", layout="centered")

st.title("🖨️ Calculadora de Impressão 3D")
st.caption("Veja seu custo e lucro. O cliente recebe apenas o orçamento final no PDF.")

# Entradas principais
st.header("🔢 Entradas")
peso_filamento_g = st.number_input("Filamento usado (g)", min_value=0.0, step=0.1)
custo_filamento_kg = st.number_input("Custo do filamento por kg (R$)", min_value=0.0, step=0.1)
tempo_impressao_h = st.number_input("Tempo de impressão (h)", min_value=0.0, step=0.1)

# Margem de erro
st.subheader("⚠️ Margem de Erro")
margem_erro_percentual = st.slider("Margem de erro na impressão (%)", 0, 100, 15)
margem_erro_valor = margem_erro_percentual / 100

# Energia elétrica
st.subheader("🔌 Energia Elétrica")
potencia_watts = st.number_input("Potência média da impressora (Watts)", value=150)
tarifa_kwh = st.number_input("Tarifa de energia (R$/kWh)", value=0.90)
usar_auto = st.checkbox("Usar cálculo automático de energia", value=True)
energia = (potencia_watts * tempo_impressao_h * tarifa_kwh) / 1000 if usar_auto else st.number_input("Energia elétrica (manual R$)", min_value=0.0, step=0.1)

# Outros custos
st.subheader("💼 Outros custos")
tipo_dano_peca = st.selectbox("Tamanho da peça", ["Pequena", "Média", "Grande"])

lucros_ideais = {"Pequena": 10.0, "Média": 20.0, "Grande": 50.0}
desgastes = {"Pequena": 0.50, "Média": 1.50, "Grande": 3.00}
desgaste = desgastes[tipo_dano_peca]
lucro_min_ideal = st.number_input(f"Lucro ideal ({tipo_dano_peca})", min_value=0.0, value=lucros_ideais[tipo_dano_peca])

st.subheader("💰 Preço de Venda")
preco_venda_usuario = st.number_input("Preço que deseja cobrar por unidade (R$)", min_value=0.0, step=0.1)

mao_de_obra = st.number_input("Mão de obra (R$)", min_value=0.0, step=0.1)
embalagem = st.number_input("Embalagem (R$)", min_value=0.0, step=0.1)
transporte = st.number_input("Transporte (R$)", min_value=0.0, step=0.1)

# Quantidade e desconto
st.subheader("📦 Quantidade de peças")
quantidade_pecas = st.number_input("Quantidade de peças", min_value=1, step=1, value=1)
aplicar_desconto = st.checkbox("Aplicar desconto progressivo")

st.subheader("⚙️ Configuração de Descontos")
descontos = {
    "2-4": st.number_input("Desconto para 2-4 peças (%)", 0, 100, 5),
    "5-9": st.number_input("Desconto para 5-9 peças (%)", 0, 100, 10),
    "10+": st.number_input("Desconto para 10 ou mais peças (%)", 0, 100, 15),
}

def aplicar_desconto_progressivo(preco_unit, qtd):
    if qtd >= 10:
        d = descontos["10+"]
    elif qtd >= 5:
        d = descontos["5-9"]
    elif qtd >= 2:
        d = descontos["2-4"]
    else:
        d = 0
    return preco_unit * (1 - d / 100), d

# Cálculos principais
def calcular():
    custo_filamento = (peso_filamento_g / 1000) * custo_filamento_kg
    custo_base = custo_filamento + energia + desgaste + mao_de_obra + embalagem + transporte
    custo_com_margem = custo_base * (1 + margem_erro_valor)

    preco_final_unit = preco_venda_usuario
    lucro_unit_final = preco_final_unit - custo_com_margem

    tipo_estimado = (
        "Pequena ou simples" if custo_com_margem <= 20
        else "Média ou moderada" if custo_com_margem <= 80
        else "Grande ou complexa"
    )

    if aplicar_desconto:
        preco_com_desc, desconto_aplicado = aplicar_desconto_progressivo(preco_final_unit, quantidade_pecas)
    else:
        preco_com_desc, desconto_aplicado = preco_final_unit, 0

    preco_total = preco_com_desc * quantidade_pecas
    custo_total = custo_com_margem * quantidade_pecas
    lucro_total = preco_total - custo_total

    return {
        "custo_unit": custo_com_margem,
        "preco_unit": preco_final_unit,
        "lucro_unit": lucro_unit_final,
        "desconto": desconto_aplicado,
        "preco_desc": preco_com_desc,
        "preco_total": preco_total,
        "custo_total": custo_total,
        "lucro_total": lucro_total,
        "tipo": tipo_estimado,
    }

resultado = calcular()

# Exibição dos resultados
st.header("📊 Resultados")
st.success(f"Custo total por peça: R$ {resultado['custo_unit']:.2f}")
st.info(f"💰 Preço de venda informado: R$ {resultado['preco_unit']:.2f}")
st.caption(f"Lucro estimado por peça: R$ {resultado['lucro_unit']:.2f}")

st.success(f"Custo total ({quantidade_pecas}x): R$ {resultado['custo_total']:.2f}")
st.info(f"💰 Preço total: R$ {resultado['preco_total']:.2f}")
st.caption(f"Lucro total: R$ {resultado['lucro_total']:.2f}")

if resultado["desconto"] > 0:
    economia = (resultado["preco_unit"] - resultado["preco_desc"]) * quantidade_pecas
    st.info(f"💸 Desconto aplicado: {resultado['desconto']}%")
    st.info(f"Preço unitário com desconto: R$ {resultado['preco_desc']:.2f}")
    st.info(f"Você economiza: R$ {economia:.2f}")
else:
    st.info(f"Preço unitário final: R$ {resultado['preco_unit']:.2f}")

# Avaliação de lucro
st.subheader("📈 Avaliação de Lucro")
st.markdown(f"**Tipo estimado da peça:** {resultado['tipo']}")
st.markdown(f"**Lucro ideal:** R$ {lucro_min_ideal:.2f}")
st.markdown(f"**Lucro aplicado por peça:** R$ {resultado['lucro_unit']:.2f}")

margem_real = resultado['lucro_unit'] / lucro_min_ideal if lucro_min_ideal else 0

if margem_real < 0.9:
    st.error("🔴 Lucro abaixo do ideal (menos de 90%).")
elif 0.9 <= margem_real <= 1.2:
    st.success("🟢 Lucro dentro da faixa ideal (entre 90% e 120%).")
else:
    st.warning("🟡 Lucro muito acima do ideal (acima de 120%).")

# Geração de PDF
st.header("📄 Orçamento do Cliente")
cliente = st.text_input("Nome do cliente")
descricao_peca = st.text_area("Descrição da peça (opcional)")
if st.button("Gerar PDF") and cliente:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    data = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    pdf.cell(200, 10, "Orçamento de Impressão 3D", ln=True, align="C")
    pdf.ln(5)
    pdf.cell(200, 10, f"Cliente: {cliente}", ln=True)
    pdf.cell(200, 10, f"Data: {data}", ln=True)
    if descricao_peca:
        pdf.multi_cell(200, 10, f"Descrição: {descricao_peca}")
    pdf.cell(200, 10, f"Quantidade: {quantidade_pecas}", ln=True)
    pdf.cell(200, 10, f"Preço unitário: R$ {resultado['preco_desc']:.2f}", ln=True)
    pdf.cell(200, 10, f"Preço total: R$ {resultado['preco_total']:.2f}", ln=True)
    pdf.cell(200, 10, f"Margem de erro considerada: {margem_erro_percentual}%", ln=True)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        st.success("PDF gerado com sucesso!")
        with open(tmp.name, "rb") as f:
            st.download_button("📥 Baixar Orçamento", f, file_name=f"orcamento_{cliente}.pdf", mime="application/pdf")
