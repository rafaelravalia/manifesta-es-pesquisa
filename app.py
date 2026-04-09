import streamlit as st
import pandas as pd
import plotly.express as px

# --- Configurações Iniciais ---
st.set_page_config(page_title="Dashboard Ouvidoria ANVISA", page_icon="📊", layout="wide")

# --- Função de Limpeza de Texto e Caracteres ---
def tratar_texto(df):
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).apply(lambda x: x.encode('latin-1', 'ignore').decode('utf-8', 'ignore').strip())
    return df

# --- Função para Evitar Colunas Duplicadas (Causa do erro de Data) ---
def renomear_colunas_sem_duplicar(df, mapa_desejado):
    colunas_novas = []
    contagem = {}
    
    # Primeiro, criamos os nomes baseados no mapeamento inteligente
    for col in df.columns:
        nome_low = col.lower()
        nome_final = col
        for chave, valor in mapa_desejado.items():
            if chave in nome_low:
                nome_final = valor
                break
        
        # Se o nome já existir, adiciona um sufixo para não dar DuplicateError
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
        df = pd.read_csv("pesquisa (2).csv", sep=";", encoding="latin-1", on_bad_lines='skip')
        mapa = {
            "satisfeito": "Satisfacao",
            "tipo": "Tipo",
            "área": "Area_Tecnica",
            "area": "Area_Tecnica",
            "resposta": "Data"
        }
        df = renomear_colunas_sem_duplicar(df, mapa)
        df = tratar_texto(df)
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(df["Data"], errors='coerce', dayfirst=True)
            df = df.dropna(subset=["Data"])
            df["mês"] = df["Data"].dt.to_period('M')
        return df
    except Exception as e:
        st.error(f"Erro na Pesquisa: {e}")
        return None

@st.cache_data
def carregar_manifestacoes():
    try:
        # Pula as 4 linhas de cabeçalho administrativo da ANVISA
        df = pd.read_csv("ListaManifestacaoAtualizadaa.csv", sep=";", encoding="latin-1", skiprows=4, on_bad_lines='skip')
        mapa = {
            "assunto": "Assunto",
            "situa": "Situacao",
            "abertura": "Data",
            "área responsável": "Unidade",
            "area responsavel": "Unidade"
        }
        df = renomear_colunas_sem_duplicar(df, mapa)
        df = tratar_texto(df)
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(df["Data"], errors='coerce', dayfirst=True)
            df = df.dropna(subset=["Data"])
            df["mês"] = df["Data"].dt.to_period('M')
        return df
    except Exception as e:
        st.error(f"Erro nas Manifestações: {e}")
        return None

# --- Processamento ---
df_p = carregar_pesquisa()
df_m = carregar_manifestacoes()

if df_p is None or df_m is None:
    st.stop()

# --- Sidebar (Filtros) ---
st.sidebar.header("🗓️ Filtros")
meses = sorted(df_m["mês"].unique(), reverse=True)
escolha = st.sidebar.multiselect("Selecione os meses:", options=meses, default=meses[:3], format_func=lambda x: x.strftime('%B/%Y'))

df_m_f = df_m[df_m["mês"].isin(escolha)]
df_p_f = df_p[df_p["mês"].isin(escolha)] if "mês" in df_p.columns else df_p

# --- Layout ---
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
                sat_data.columns = ['Nível', 'Qtd']
                st.plotly_chart(px.bar(sat_data, x='Qtd', y='Nível', orientation='h', title="Satisfação", color='Nível'), use_container_width=True)
        
        st.divider()
        if "Area_Tecnica" in df_p_f.columns:
            st.subheader("Volume por Área Técnica")
            area_data = df_p_f["Area_Tecnica"].value_counts().reset_index()
            area_data.columns = ['Área', 'Total']
            st.plotly_chart(px.bar(area_data, x='Área', y='Total', color='Área', text_auto=True), use_container_width=True)
    else:
        st.info("Sem dados para o período.")

with t2:
    st.header("Gestão de Demandas")
    st.metric("Total de Manifestações", len(df_m_f))
    ca, cb = st.columns(2)
    with ca:
        if "Assunto" in df_m_f.columns:
            top = df_m_f["Assunto"].value_counts().nlargest(10).reset_index()
            top.columns = ['Assunto', 'Total']
            st.plotly_chart(px.bar(top, x='Total', y='Assunto', orientation='h', title="Top 10 Assuntos"), use_container_width=True)
    with cb:
        if "Situacao" in df_m_f.columns:
            st.plotly_chart(px.pie(df_m_f, names='Situacao', title="Status das Demandas", hole=0.4), use_container_width=True)

    st.divider()
    if "Unidade" in df_m_f.columns:
        st.subheader("Resumo por Unidade Responsável")
        resumo = df_m_f["Unidade"].value_counts().reset_index()
        resumo.columns = ['Unidade Administrativa', 'Total']
        # Adiciona a linha de total como o Riam queria
        total_df = pd.DataFrame([['TOTAL GERAL', resumo['Total'].sum()]], columns=['Unidade Administrativa', 'Total'])
        st.table(pd.concat([resumo, total_df], ignore_index=True))
