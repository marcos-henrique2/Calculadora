import streamlit as st
import pandas as pd
import sqlite3
import uuid
import base64
from io import BytesIO
from streamlit.components.v1 import html

# Helpers para visualização de STL

def preview_stl(data: bytes):
    b64 = base64.b64encode(data).decode('utf-8')
    js = f"""
<script src='https://cdnjs.cloudflare.com/ajax/libs/three.js/r121/three.min.js'></script>
<script src='https://cdn.jsdelivr.net/npm/three@0.121/examples/js/loaders/STLLoader.js'></script>
<div id='viewer' style='width:100%; height:400px;'></div>
<script>
  var scene = new THREE.Scene();
  var camera = new THREE.PerspectiveCamera(75, window.innerWidth/window.innerHeight, 0.1, 1000);
  var renderer = new THREE.WebGLRenderer();
  renderer.setSize(window.innerWidth*0.5, 400);
  document.getElementById('viewer').appendChild(renderer.domElement);
  var loader = new THREE.STLLoader();
  var data = atob('{b64}');
  var array = new Uint8Array(data.length);
  for(var i=0; i<data.length; i++) {{ array[i] = data.charCodeAt(i); }}
  var geometry = loader.parse(array.buffer);
  var material = new THREE.MeshNormalMaterial();
  var mesh = new THREE.Mesh(geometry, material);
  scene.add(mesh);
  var box = new THREE.Box3().setFromObject(mesh);
  var size = box.getSize(new THREE.Vector3()).length();
  camera.position.set(size, size, size);
  camera.lookAt(box.getCenter(new THREE.Vector3()));
  function animate() {{ requestAnimationFrame(animate); renderer.render(scene, camera); }}
  animate();
</script>
"""
    html(js, height=420)

# Módulo da aba Catálogo
def show_catalogo_tab(historico_csv: str, db_path: str):
    # Conexão com SQLite
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cur = conn.cursor()

    # Funções CRUD
    def adicionar_produto(prod: dict):
        cur.execute(
            "INSERT OR REPLACE INTO produtos VALUES (?,?,?,?,?,?,?)",
            (prod['id'], prod['nome'], prod['descricao'], prod['categoria'], prod['preco'], prod['foto'], prod['arquivo'])
        )
        conn.commit()

    def excluir_produto(pid: str):
        cur.execute("DELETE FROM produtos WHERE id=?", (pid,))
        conn.commit()

    def listar_produtos() -> pd.DataFrame:
        return pd.read_sql_query("SELECT * FROM produtos", conn)

    # UI da aba
    st.header("📦 Catálogo de Produtos")
    st.subheader("➕ Adicionar/Atualizar Produto")
    with st.form("add_prod"):
        nome = st.text_input("Nome *", key="n")
        desc = st.text_area("Descrição", key="d")
        catg = st.text_input("Categoria *", key="c")
        preco = st.number_input("Preço (R$)", 0.0, 100000.0, step=0.1, key="preco")
        img = st.file_uploader("Foto (jpg/png)", type=["jpg", "png"], key="img")
        stl = st.file_uploader("Arquivo STL/3MF", type=["stl", "3mf"], key="stl")
        if st.form_submit_button("💾 Salvar Produto"):
            if not nome or not catg:
                st.error("Nome e Categoria são obrigatórios.")
            else:
                prod = {
                    'id': str(uuid.uuid4()),
                    'nome': nome,
                    'descricao': desc,
                    'categoria': catg,
                    'preco': preco,
                    'foto': img.read() if img else None,
                    'arquivo': stl.read() if stl else None
                }
                adicionar_produto(prod)
                st.success("Produto salvo com sucesso!")

    st.divider()
    st.subheader("🔍 Buscar & Página")
    df_cat = listar_produtos()
    filt_cat = st.text_input("Filtrar Categoria", key="fc")
    df_f2 = df_cat[df_cat['categoria'].str.contains(filt_cat, case=False)] if filt_cat else df_cat

    pg_size = st.number_input("Itens por página", 1, 50, 5, key="psz")
    total = len(df_f2)
    pages = max(1, (total - 1) // pg_size + 1)
    page = st.number_input("Página", 1, pages, value=1, key="pnum")

    st.write(f"Mostrando {(page-1)*pg_size+1} a {min(page*pg_size, total)} de {total} produtos")
    df_sub = df_f2.iloc[(page-1)*pg_size: page*pg_size]
    st.dataframe(df_sub[['nome','descricao','categoria','preco']], use_container_width=True)

    if not df_sub.empty:
        st.subheader("🛠 Ações no Produto")
        sel2 = st.selectbox(
            "Selecione Produto",
            df_sub['id'].tolist(),
            format_func=lambda i: df_sub.set_index('id').loc[i, 'nome'],
            key="sel2"
        )
        c1, c2, c3 = st.columns(3)
        if c1.button("🖼 Ver Foto") and df_sub.set_index('id').loc[sel2, 'foto']:
            st.image(df_sub.set_index('id').loc[sel2, 'foto'], width=200)
        if c2.button("🕹 Ver STL") and df_sub.set_index('id').loc[sel2, 'arquivo']:
            preview_stl(df_sub.set_index('id').loc[sel2, 'arquivo'])
        if c3.button("🗑 Excluir"):
            excluir_produto(sel2)
            st.warning("Produto excluído.")

    st.divider()
    st.subheader("📥 Import/Export")
    st.download_button("📄 Exportar CSV", df_cat.to_csv(index=False).encode('utf-8'), file_name="catalogo.csv")

    buf = BytesIO()
    df_cat.to_excel(buf, index=False, engine='openpyxl')
    buf.seek(0)
    st.download_button(
        "📊 Exportar XLSX",
        data=buf,
        file_name="catalogo.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    imp = st.file_uploader("📂 Importar CSV", type=["csv"], key="imp_csv")
    if imp:
        df_imp = pd.read_csv(imp)
        for _, r in df_imp.iterrows():
            prod = {
                'id': r.get('id', str(uuid.uuid4())),
                'nome': r['nome'],
                'descricao': r.get('descricao', ''),
                'categoria': r.get('categoria', ''),
                'preco': r.get('preco', 0.0),
                'foto': None,
                'arquivo': None
            }
            adicionar_produto(prod)
        st.success("Importação concluída com sucesso!")
