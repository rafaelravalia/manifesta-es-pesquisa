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

# --- Carregamento de Dados ---
@st.cache_data
def carregar_dados_seguro(nome_arquivo):
    try:
        # Tenta ler o arquivo. O 'on_bad_lines' evita erros de linhas extras.
        df = pd.read_csv(nome_arquivo, sep=";", encoding="latin-1", on_bad_lines='skip')
        
        # Limpa os nomes das colunas de caracteres invisíveis
        df.columns = df.columns.str.encode('latin-1').str.decode('utf-8', 'ignore').str.strip()
        
        # Mapeamento Flexível
        mapeamento = {}
        for col in df.columns:
            c = col.lower()
            if "tipo" in c: mapeamento[col] = "Tipo"
            elif "satisfeito" in c or "satisfação" in c: mapeamento[col] = "Satisfacao"
            elif "assunto" in c and "sub" not in c: mapeamento[col] = "Assunto"
            elif "situa" in c: mapeamento[col] = "Situacao"
            elif "área" in c or "unidade" in c or "setor" in c: mapeamento[col] = "Unidade"
            elif "data" in c or "abertura" in c or "resposta" in c: 
                if "Data" not in mapeamento.values(): mapeamento[col] = "Data"

        df = df.rename(columns=mapeamento)
        df = corrigir_texto(df)
        
        # Tratamento de Data
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(df["Data"], errors='coerce', dayfirst=True)
            df["mês"] = df["Data"].dt.to_period('M')
        return df
    except Exception as e:
        st.error(f"Erro ao ler {nome_arquivo}: {e}")
        return None

# --- Execução ---
df_p = carregar_dados_seguro("pesquisa.csv")
df_m = carregar_dados_seguro("ListaManifestacaoAtualizadaa.csv")

if df_p is None or df_m is None:
    st.stop()

# --- Filtros ---
st.sidebar.header("🗓️ Filtros")
if "mês" in df_m.columns:
    meses = sorted(df_m["mês"].dropna().unique(), reverse=True)
    mapa = {m.strftime('%B/%Y'): m for m in meses}
    escolha = st.sidebar.multiselect("Selecione os meses:", options=list(mapa.keys()), default=list(mapa.keys())[:3])
    periodos = [mapa[e] for e in escolha]
    df_m_filt = df_m[df_m["mês"].isin(periodos)]
    df_p_filt = df_p[df_p["mês"].isin(periodos)] if "mês" in df_p.columns else df_p
else:
    df_m_filt, df_p_filt = df_m, df_p

# --- Dashboard ---
st.title("📊 Painel Ouvidoria ANVISA")

t1, t2 = st.tabs(["🎯 Pesquisa de Satisfação", "📂 Manifestações Gerais"])

with t1:
    st.metric("Total de Respostas", len(df_p_filt))
    col1, col2 = st.columns(2)
    with col1:
        if "Tipo" in df_p_filt.columns:
            st.plotly_chart(px.pie(df_p_filt, names='Tipo', title="Tipo de Manifestação"), use_container_width=True)
    with col2:
        if "Satisfacao" in df_p_filt.columns:
            sat_df = df_p_filt['Satisfacao'].value_counts().reset_index()
            sat_df.columns = ['Status', 'Total']
            st.plotly_chart(px.bar(sat_df, x='Total', y='Status', orientation='h', title="Satisfação"), use_container_width=True)

with t2:
    st.metric("Total de Demandas", len(df_m_filt))
    ca, cb = st.columns(2)
    with ca:
        if "Assunto" in df_m_filt.columns:
            top = df_m_filt['Assunto'].value_counts().nlargest(10).reset_index()
            top.columns = ['Assunto', 'Qtd']
            st.plotly_chart(px.bar(top, x='Qtd', y='Assunto', orientation='h', title="Top 10 Assuntos"), use_container_width=True)
    with cb:
        if "Situacao" in df_m_filt.columns:
            st.plotly_chart(px.pie(df_m_filt, names='Situacao', title="Status das Demandas"), use_container_width=True)

    st.divider()
    if "Unidade" in df_m_filt.columns:
        st.subheader("Demandas por Área")
        resumo = df_m_filt['Unidade'].value_counts().reset_index()
        resumo.columns = ['Área', 'Total']
        st.dataframe(resumo, use_container_width=True, hide_index=True)
