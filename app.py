import streamlit as st
import pandas as pd
import plotly.express as px

# --- Configurações Iniciais ---
st.set_page_config(page_title="Dashboard Ouvidoria ANVISA", page_icon="📊", layout="wide")

# --- Função de Correção de Texto ---
def corrigir_texto(df):
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].apply(lambda x: x.encode('latin-1').decode('utf-8', 'ignore') if isinstance(x, str) else x)
    return df

# --- Carregamento Inteligente ---
@st.cache_data
def carregar_dados_pesquisa():
    try:
        # Pesquisa geralmente começa direto no cabeçalho (skiprows=0)
        df = pd.read_csv("pesquisa.csv", sep=";", encoding="latin-1", on_bad_lines='skip')
        df.columns = df.columns.str.strip().str.encode('latin-1').str.decode('utf-8', 'ignore')
        
        mapeamento = {}
        for col in df.columns:
            c = col.lower()
            if "tipo" in c and "manifesta" in c: mapeamento[col] = "Tipo"
            elif "satisfeito" in c: mapeamento[col] = "Satisfacao"
            elif ("área" in c or c == "area") and len(c) < 10: mapeamento[col] = "Area_Pesquisa"
            elif "resposta" in c and "pesquisa" in c: mapeamento[col] = "Data"
        
        df = df.rename(columns=mapeamento)
        df = corrigir_texto(df)
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(df["Data"], errors='coerce', dayfirst=True)
            df["mês"] = df["Data"].dt.to_period('M')
        return df
    except: return None

@st.cache_data
def carregar_dados_manifestacoes():
    try:
        # Manifestações geralmente tem 4 linhas de cabeçalho administrativo
        df = pd.read_csv("ListaManifestacaoAtualizadaa.csv", sep=";", encoding="latin-1", skiprows=4, on_bad_lines='skip')
        df.columns = df.columns.str.strip().str.encode('latin-1').str.decode('utf-8', 'ignore')
        
        mapeamento = {}
        ja_foi = set()
        for col in df.columns:
            c = col.lower()
            if "assunto" in c and "sub" not in c: mapeamento[col] = "Assunto"
            elif "situa" in c: mapeamento[col] = "Situacao"
            elif "abertura" in c: mapeamento[col] = "Data"
            elif "área responsável" in c or "area responsavel" in c:
                if "Unidade" not in ja_foi:
                    mapeamento[col] = "Unidade"
                    ja_foi.add("Unidade")
        
        df = df.rename(columns=mapeamento)
        df = corrigir_texto(df)
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(df["Data"], errors='coerce', dayfirst=True)
            df["mês"] = df["Data"].dt.to_period('M')
        return df
    except: return None

# --- Execução ---
df_p = carregar_dados_pesquisa()
df_m = carregar_dados_manifestacoes()

if df_p is None or df_m is None:
    st.error("Erro ao carregar arquivos. Verifique os nomes no GitHub.")
    st.stop()

# --- Filtros ---
st.sidebar.header("🗓️ Filtros")
if "mês" in df_m.columns:
    meses = sorted(df_m["mês"].unique(), reverse=True)
    mapa = {m.strftime('%B/%Y'): m for m in meses}
    escolha = st.sidebar.multiselect("Selecione os meses:", options=list(mapa.keys()), default=list(mapa.keys())[:3])
    periodos = [mapa[e] for e in escolha]
    df_m_filt = df_m[df_m["mês"].isin(periodos)]
    df_p_filt = df_p[df_p["mês"].isin(periodos)] if "mês" in df_p.columns else df_p
else:
    df_m_filt, df_p_filt = df_m, df_p

# --- Dashboard ---
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
        
        if "Area_Pesquisa" in df_p_filt.columns:
            st.divider()
            st.subheader("Respostas por Área Técnica (Pesquisa)")
            st.plotly_chart(px.bar(df_p_filt['Area_Pesquisa'].value_counts().reset_index(), x='Area_Pesquisa', y='count', color='Area_Pesquisa', text_auto=True), use_container_width=True)
    else:
        st.info("Sem dados de pesquisa para o período.")

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
    if "Unidade" in df_m_filt.columns:
        st.subheader("Resumo por Unidade Responsável")
        resumo = df_m_filt['Unidade'].value_counts().reset_index()
        resumo.columns = ['Unidade Administrativa', 'Total']
        total_df = pd.DataFrame([['TOTAL GERAL', resumo['Total'].sum()]], columns=['Unidade Administrativa', 'Total'])
        st.dataframe(pd.concat([resumo, total_df], ignore_index=True), use_container_width=True, hide_index=True)
