import streamlit as st
import pandas as pd
import plotly.express as px

# --- Configurações Iniciais ---
st.set_page_config(page_title="Dashboard Ouvidoria ANVISA", page_icon="📊", layout="wide")

# --- Função de Correção de Texto ---
def corrigir_texto(df):
    # Correção para compatibilidade com versões novas do Pandas
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].apply(lambda x: x.encode('latin-1').decode('utf-8', 'ignore') if isinstance(x, str) else x)
    return df

# --- Carregamento Inteligente ---
@st.cache_data
def carregar_dados(nome_arquivo, tipo):
    try:
        # Pesquisa (tipo=0) lê do topo; Manifestações (tipo=1) pula 4 linhas
        skip = 4 if tipo == 1 else 0
        df = pd.read_csv(nome_arquivo, sep=";", encoding="latin-1", skiprows=skip, on_bad_lines='skip')
        
        # Limpa nomes de colunas
        df.columns = df.columns.str.strip().str.encode('latin-1').str.decode('utf-8', 'ignore')
        
        mapeamento = {}
        ja_atribuido = set()
        
        for col in df.columns:
            c = col.lower()
            target = None
            if "tipo" in c and "manifesta" in c: target = "Tipo"
            elif "satisfeito" in c: target = "Satisfacao"
            elif "assunto" in c and "sub" not in c: target = "Assunto"
            elif "situa" in c: target = "Situacao"
            elif "data" in c or "resposta" in c or "abertura" in c: target = "Data"
            elif "área" in c or "unidade" in c: target = "Area"
            
            if target and target not in ja_atribuido:
                mapeamento[col] = target
                ja_atribuido.add(target)
        
        df = df.rename(columns=mapeamento)
        df = df.loc[:, ~df.columns.duplicated()] # Mata duplicatas reais
        df = corrigir_texto(df)
        
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(df["Data"], errors='coerce', dayfirst=True)
            df = df.dropna(subset=["Data"])
            df["mês"] = df["Data"].dt.to_period('M')
        return df
    except: return None

# --- Execução ---
df_p = carregar_dados("pesquisa.csv", 0)
df_m = carregar_dados("ListaManifestacaoAtualizadaa.csv", 1)

if df_p is None or df_m is None:
    st.error("Erro ao carregar arquivos. Verifique os nomes no GitHub.")
    st.stop()

# --- Filtros ---
st.sidebar.header("🗓️ Filtros")
# Usamos os meses da base de manifestações como referência principal
if "mês" in df_m.columns:
    meses_m = set(df_m["mês"].unique())
    meses_p = set(df_p["mês"].unique()) if "mês" in df_p.columns else set()
    todos_meses = sorted(list(meses_m | meses_p), reverse=True)
    
    mapa = {m.strftime('%B/%Y'): m for m in todos_meses}
    escolha = st.sidebar.multiselect("Selecione os meses:", options=list(mapa.keys()), default=list(mapa.keys())[:3])
    periodos = [mapa[e] for e in escolha]
    
    df_m_filt = df_m[df_m["mês"].isin(periodos)]
    df_p_filt = df_p[df_p["mês"].isin(periodos)] if "mês" in df_p.columns else df_p
else:
    df_m_filt, df_p_filt = df_m, df_p

# --- Layout ---
st.title("📊 Dashboard Ouvidoria ANVISA")
t1, t2 = st.tabs(["🎯 Pesquisa de Satisfação", "📂 Manifestações Gerais"])

with t1:
    st.header("Análise da Pesquisa de Satisfação")
    if not df_p_filt.empty:
        st.metric("Total de Respostas", len(df_p_filt))
        c1, c2 = st.columns(2)
        with c1:
            if "Tipo" in df_p_filt.columns:
                st.plotly_chart(px.pie(df_p_filt, names='Tipo', title="Tipo de Manifestação", hole=0.3), use_container_width=True)
        with c2:
            if "Satisfacao" in df_p_filt.columns:
                sat_df = df_p_filt['Satisfacao'].value_counts().reset_index()
                sat_df.columns = ['Status', 'Total']
                st.plotly_chart(px.bar(sat_df, x='Total', y='Status', orientation='h', title="Satisfação", color='Status'), use_container_width=True)
        
        if "Area" in df_p_filt.columns:
            st.divider()
            st.subheader("Respostas por Área Técnica (Pesquisa)")
            area_data = df_p_filt['Area'].value_counts().reset_index()
            area_data.columns = ['Área', 'Quantidade']
            st.plotly_chart(px.bar(area_data, x='Área', y='Quantidade', color='Área', text_auto=True), use_container_width=True)
    else:
        st.info("Nenhum dado de pesquisa encontrado para o período selecionado.")

with t2:
    st.header("Painel de Manifestações Gerais")
    st.metric("📩 Total de Manifestações", len(df_m_filt))
    ca, cb = st.columns(2)
    with ca:
        if "Assunto" in df_m_filt.columns:
            top = df_m_filt['Assunto'].value_counts().nlargest(10).reset_index()
            top.columns = ['Assunto', 'Qtd']
            st.plotly_chart(px.bar(top, x='Qtd', y='Assunto', orientation='h', title="Top 10 Assuntos"), use_container_width=True)
    with cb:
        if "Situacao" in df_m_filt.columns:
            st.plotly_chart(px.pie(df_m_filt, names='Situacao', title="Status das Demandas", hole=0.3), use_container_width=True)

    st.divider()
    if "Area" in df_m_filt.columns:
        st.subheader("Resumo por Unidade Responsável")
        resumo = df_m_filt['Area'].value_counts().reset_index()
        resumo.columns = ['Unidade Administrativa', 'Total']
        total_df = pd.DataFrame([['TOTAL GERAL', resumo['Total'].sum()]], columns=['Unidade Administrativa', 'Total'])
        st.dataframe(pd.concat([resumo, total_df], ignore_index=True), use_container_width=True, hide_index=True)
