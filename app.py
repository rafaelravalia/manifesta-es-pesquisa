import streamlit as st
import pandas as pd
import plotly.express as px

# --- Configurações Iniciais ---
st.set_page_config(page_title="Dashboard Ouvidoria ANVISA", page_icon="📊", layout="wide")

# --- Função de Limpeza de Texto ---
def tratar_texto(df):
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).apply(lambda x: x.encode('latin-1', 'ignore').decode('utf-8', 'ignore').strip())
    return df

# --- Função Anti-Duplicata ---
def renomear_colunas_anvisa(df, mapa_desejado):
    colunas_novas = []
    contagem = {}
    for col in df.columns:
        nome_low = col.lower()
        nome_final = col
        for chave, valor in mapa_desejado.items():
            if chave in nome_low:
                nome_final = valor
                break
        if nome_final in contagem:
            contagem[nome_final] += 1
            colunas_novas.append(f"{nome_final}_{contagem[nome_final]}")
        else:
            contagem[nome_final] = 0
            colunas_novas.append(nome_final)
    df.columns = colunas_novas
    return df

# --- Carregamento de Dados ---
@st.cache_data
def carregar_pesquisa():
    try:
        # Ajustado para o nome exato da sua imagem: pesquisa (2).csv
        df = pd.read_csv("pesquisa (2).csv", sep=";", encoding="latin-1", on_bad_lines='skip')
        mapa = {"satisfeito": "Satisfacao", "tipo": "Tipo", "área": "Area_Tecnica", "area": "Area_Tecnica", "resposta": "Data"}
        df = renomear_colunas_anvisa(df, mapa)
        df = tratar_texto(df)
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(df["Data"], errors='coerce', dayfirst=True)
            df = df.dropna(subset=["Data"])
            df["mês"] = df["Data"].dt.to_period('M')
        return df
    except: return None

@st.cache_data
def carregar_manifestacoes():
    try:
        # Ajustado para o nome exato da sua imagem: ListaManifestacaoAtualizadaa.csv
        df = pd.read_csv("ListaManifestacaoAtualizadaa.csv", sep=";", encoding="latin-1", skiprows=4, on_bad_lines='skip')
        mapa = {"assunto": "Assunto", "situa": "Situacao", "abertura": "Data", "área responsável": "Unidade", "area responsavel": "Unidade"}
        df = renomear_colunas_anvisa(df, mapa)
        df = tratar_texto(df)
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(df["Data"], errors='coerce', dayfirst=True)
            df = df.dropna(subset=["Data"])
            df["mês"] = df["Data"].dt.to_period('M')
        return df
    except: return None

# --- Processamento ---
df_p = carregar_pesquisa()
df_m = carregar_manifestacoes()

if df_p is None or df_m is None:
    st.error("Erro ao carregar arquivos. Verifique se 'pesquisa (2).csv' e 'ListaManifestacaoAtualizadaa.csv' estão no GitHub.")
    st.stop()

# --- Filtros ---
st.sidebar.header("🗓️ Filtros")
meses = sorted(df_m["mês"].unique(), reverse=True)
escolha = st.sidebar.multiselect("Selecione os meses:", options=meses, default=meses[:3], format_func=lambda x: x.strftime('%B/%Y'))
df_m_f = df_m[df_m["mês"].isin(escolha)]
df_p_f = df_p[df_p["mês"].isin(escolha)] if "mês" in df_p.columns else df_p

# --- Dashboard Layout ---
st.title("📊 Dashboard Ouvidoria ANVISA")
t1, t2 = st.tabs(["🎯 Pesquisa de Satisfação", "📂 Manifestações Gerais"])

with t1:
    st.header("Análise de Satisfação")
    if not df_p_f.empty:
        st.metric("Total de Respostas", len(df_p_f))
        c1, c2 = st.columns(2)
        with c1:
            if "Tipo" in df_p_f.columns:
                st.plotly_chart(px.pie(df_p_f, names='Tipo', title="Tipo de Manifestação", hole=0.4), use_container_width=True)
        with c2:
            if "Satisfacao" in df_p_f.columns:
                sat_data = df_p_f["Satisfacao"].value_counts().reset_index()
                st.plotly_chart(px.bar(sat_data, x='count', y='Satisfacao', orientation='h', title="Satisfação", color='Satisfacao'), use_container_width=True)
        
        st.divider()
        if "Area_Tecnica" in df_p_f.columns:
            st.subheader("Volume por Área Técnica")
            area_data = df_p_f["Area_Tecnica"].value_counts().reset_index()
            st.plotly_chart(px.bar(area_data, x='Area_Tecnica', y='count', color='Area_Tecnica', text_auto=True), use_container_width=True)

with t2:
    st.header("Gestão de Demandas")
    st.metric("Total de Manifestações", len(df_m_f))
    ca, cb = st.columns(2)
    with ca:
        if "Assunto" in df_m_f.columns:
            top = df_m_f["Assunto"].value_counts().nlargest(10).reset_index()
            st.plotly_chart(px.bar(top, x='count', y='Assunto', orientation='h', title="Top 10 Assuntos"), use_container_width=True)
    with cb:
        if "Situacao" in df_m_f.columns:
            st.plotly_chart(px.pie(df_m_f, names='Situacao', title="Status das Demandas", hole=0.4), use_container_width=True)

    st.divider()
    if "Unidade" in df_m_f.columns:
        st.subheader("Resumo por Unidade Responsável")
        resumo = df_m_f["Unidade"].value_counts().reset_index()
        resumo.columns = ['Unidade Administrativa', 'Total']
        total_df = pd.DataFrame([['TOTAL GERAL', resumo['Total'].sum()]], columns=['Unidade Administrativa', 'Total'])
        st.table(pd.concat([resumo, total_df], ignore_index=True))
