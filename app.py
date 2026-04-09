import streamlit as st
import pandas as pd
import plotly.express as px

# --- Configurações Iniciais ---
st.set_page_config(
    page_title="Dashboard Ouvidoria ANVISA",
    page_icon="📊",
    layout="wide"
)

# --- Função para Corrigir Textos (Acentos e Ç) ---
def corrigir_texto(df):
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].apply(lambda x: x.encode('latin-1').decode('utf-8', 'ignore') if isinstance(x, str) else x)
    return df

# --- Função de Carregamento Inteligente ---
@st.cache_data
def carregar_dados_ouvidoria(nome_arquivo):
    try:
        # Lemos o arquivo com separador ; e encoding latino
        df = pd.read_csv(nome_arquivo, sep=";", encoding="latin-1", on_bad_lines='skip')
        
        # Limpeza nos nomes das colunas
        df.columns = df.columns.str.strip().str.encode('latin-1').str.decode('utf-8', 'ignore')
        
        # Mapeamento dinâmico (Procura a coluna pelo que ela parece ser)
        novas_colunas = {}
        for col in df.columns:
            c = col.lower()
            if "tipo" in c and "manifesta" in c: novas_colunas[col] = "Tipo"
            elif "satisfeito" in c: novas_colunas[col] = "Satisfacao"
            elif "assunto" in c and "sub" not in c: novas_colunas[col] = "Assunto"
            elif "situa" in c: novas_colunas[col] = "Situacao"
            elif "área" in c or "unidade" in c or "setor" in c: novas_colunas[col] = "Area"
            elif "data" in c or "abertura" in c: novas_colunas[col] = "Data"
        
        df = df.rename(columns=novas_colunas)
        df = corrigir_texto(df)
        
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(df["Data"], errors='coerce', dayfirst=True)
            df["mês"] = df["Data"].dt.to_period('M')
        return df
    except Exception as e:
        st.error(f"Erro ao carregar {nome_arquivo}: {e}")
        return None

# --- Execução ---
df_p = carregar_dados_ouvidoria("pesquisa.csv")
# O código tenta o nome com "a" extra, se não achar, tenta o normal
df_m = carregar_dados_ouvidoria("ListaManifestacaoAtualizadaa.csv") 

if df_p is None or df_m is None:
    st.info("Certifique-se de que os arquivos 'pesquisa.csv' e 'ListaManifestacaoAtualizadaa.csv' estão no seu GitHub.")
    st.stop()

# --- Filtros ---
st.sidebar.title("🗓️ Filtros")
if "mês" in df_m.columns:
    meses_disponiveis = sorted(df_m["mês"].dropna().unique(), reverse=True)
    mapa_meses = {m.strftime('%B/%Y'): m for m in meses_disponiveis}
    selecao = st.sidebar.multiselect("Selecione o período:", options=list(mapa_meses.keys()), default=list(mapa_meses.keys())[:3])
    periodos = [mapa_meses[s] for s in selecao]
    
    df_m_filt = df_m[df_m["mês"].isin(periodos)]
    df_p_filt = df_p[df_p["mês"].isin(periodos)] if "mês" in df_p.columns else df_p
else:
    df_m_filt, df_p_filt = df_m, df_p

# --- Dashboard Layout ---
st.title("📊 Dashboard Ouvidoria ANVISA")

tab1, tab2 = st.tabs(["🎯 Pesquisa de Satisfação", "📂 Manifestações Gerais"])

with tab1:
    st.header("Análise da Pesquisa de Satisfação")
    st.metric("Total de Respostas", len(df_p_filt))
    
    col1, col2 = st.columns(2)
    with col1:
        if "Tipo" in df_p_filt.columns:
            st.plotly_chart(px.pie(df_p_filt, names='Tipo', title="Tipo de Manifestação", hole=0.3), use_container_width=True)
    with col2:
        if "Satisfacao" in df_p_filt.columns:
            sat = df_p_filt['Satisfacao'].value_counts().reset_index()
            sat.columns = ['Status', 'Total']
            st.plotly_chart(px.bar(sat, x='Total', y='Status', orientation='h', title="Nível de Satisfação", color='Status'), use_container_width=True)

    if "Area" in df_p_filt.columns:
        st.divider()
        st.subheader("Distribuição por Área Técnica")
        areas_p = df_p_filt['Area'].value_counts().reset_index()
        areas_p.columns = ['Área', 'Qtd']
        st.plotly_chart(px.bar(areas_p, x='Área', y='Qtd', text_auto=True), use_container_width=True)

with tab2:
    st.header("Painel de Manifestações Gerais")
    st.metric("📩 Total de Manifestações", len(df_m_filt))
    
    colA, colB = st.columns(2)
    with colA:
        if "Assunto" in df_m_filt.columns:
            top = df_m_filt['Assunto'].value_counts().nlargest(10).reset_index()
            top.columns = ['Assunto', 'Qtd']
            st.plotly_chart(px.bar(top, x='Qtd', y='Assunto', orientation='h', title="Top 10 Assuntos"), use_container_width=True)
    with colB:
        if "Situacao" in df_m_filt.columns:
            st.plotly_chart(px.pie(df_m_filt, names='Situacao', title="Situação das Demandas"), use_container_width=True)

    st.divider()
    if "Area" in df_m_filt.columns:
        st.subheader("Resumo por Unidade Responsável")
        resumo = df_m_filt['Area'].value_counts().reset_index()
        resumo.columns = ['Unidade Administrativa', 'Total']
        # Mostra o total geral no final como o Riam queria
        st.dataframe(resumo, use_container_width=True, hide_index=True)
        st.info(f"Soma Total das Unidades: {resumo['Total'].sum()}")
