import streamlit as st
import pandas as pd
import plotly.express as px

# --- Configurações Iniciais ---
st.set_page_config(page_title="Dashboard Ouvidoria ANVISA", page_icon="📊", layout="wide")

# --- Função de Limpeza de Texto ---
def tratar_texto(df):
    for col in df.columns:
        if df[col].dtype == 'object':
            # Remove caracteres estranhos e espaços extras
            df[col] = df[col].astype(str).apply(lambda x: x.encode('latin-1', 'ignore').decode('utf-8', 'ignore').strip())
    return df

# --- Carregamento Seguro de Dados ---
@st.cache_data
def carregar_dados_pesquisa():
    try:
        # Pesquisa da ANVISA geralmente não tem as linhas de cabeçalho administrativo
        df = pd.read_csv("pesquisa.csv", sep=";", encoding="latin-1", on_bad_lines='skip')
        df.columns = df.columns.str.strip().str.replace('\n', ' ')
        df = df.loc[:, ~df.columns.duplicated()] # Remove colunas com nomes idênticos
        
        # Mapeamento dinâmico para garantir que os gráficos funcionem
        mapa = {}
        for c in df.columns:
            low = c.lower()
            if "satisfeito" in low: mapa[c] = "Satisfacao"
            elif "tipo" in low and "manifesta" in low: mapa[c] = "Tipo"
            elif "área" in low or low == "area": mapa[c] = "Area_Tecnica"
            elif "resposta" in low and "pesquisa" in low: mapa[c] = "Data"
        
        df = df.rename(columns=mapa)
        df = tratar_texto(df)
        
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(df["Data"], errors='coerce', dayfirst=True)
            df = df.dropna(subset=["Data"])
            df["mês"] = df["Data"].dt.to_period('M')
        return df
    except Exception as e:
        st.error(f"Erro ao ler pesquisa: {e}")
        return None

@st.cache_data
def carregar_dados_manifestacoes():
    try:
        # Manifestações costumam ter 4 linhas iniciais que não são dados (pula com skiprows)
        df = pd.read_csv("ListaManifestacaoAtualizadaa.csv", sep=";", encoding="latin-1", skiprows=4, on_bad_lines='skip')
        df.columns = df.columns.str.strip().str.replace('\n', ' ')
        df = df.loc[:, ~df.columns.duplicated()]
        
        mapa = {}
        for c in df.columns:
            low = c.lower()
            if "assunto" in low and "sub" not in low: mapa[c] = "Assunto"
            elif "situa" in low: mapa[c] = "Situacao"
            elif "data" in low or "abertura" in low: mapa[c] = "Data"
            elif "área responsável" in low or "area responsavel" in low: mapa[c] = "Unidade"
        
        df = df.rename(columns=mapa)
        df = tratar_texto(df)
        
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(df["Data"], errors='coerce', dayfirst=True)
            df = df.dropna(subset=["Data"])
            df["mês"] = df["Data"].dt.to_period('M')
        return df
    except Exception as e:
        st.error(f"Erro ao ler manifestações: {e}")
        return None

# --- Processamento ---
df_p = carregar_dados_pesquisa()
df_m = carregar_dados_manifestacoes()

if df_p is None or df_m is None:
    st.warning("Aguardando carregamento dos arquivos CSV no repositório...")
    st.stop()

# --- Sidebar (Filtros) ---
st.sidebar.header("🗓️ Período de Análise")
meses_disponiveis = sorted(df_m["mês"].unique(), reverse=True)
escolha_meses = st.sidebar.multiselect(
    "Selecione os meses:", 
    options=meses_disponiveis, 
    default=meses_disponiveis[:3],
    format_func=lambda x: x.strftime('%B / %Y')
)

# Aplicar Filtro
df_m_f = df_m[df_m["mês"].isin(escolha_meses)]
df_p_f = df_p[df_p["mês"].isin(escolha_meses)] if "mês" in df_p.columns else df_p

# --- Dashboard Layout ---
st.title("📊 Dashboard Ouvidoria ANVISA")

tab1, tab2 = st.tabs(["🎯 Pesquisa de Satisfação", "📂 Manifestações Gerais"])

with tab1:
    st.header("Análise de Satisfação")
    if not df_p_f.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            if "Tipo" in df_p_f.columns:
                fig_tipo = px.pie(df_p_f, names='Tipo', title="Manifestações por Tipo", hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe)
                st.plotly_chart(fig_tipo, use_container_width=True)
        
        with col2:
            if "Satisfacao" in df_p_f.columns:
                sat_counts = df_p_f["Satisfacao"].value_counts().reset_index()
                fig_sat = px.bar(sat_counts, x='count', y='Satisfacao', orientation='h', title="Nível de Satisfação", color='Satisfacao')
                st.plotly_chart(fig_sat, use_container_width=True)
        
        if "Area_Tecnica" in df_p_f.columns:
            st.subheader("Volume por Área Técnica (Pesquisa)")
            fig_area = px.bar(df_p_f["Area_Tecnica"].value_counts().reset_index(), x='Area_Tecnica', y='count', color='Area_Tecnica')
            st.plotly_chart(fig_area, use_container_width=True)
    else:
        st.info("Nenhum dado de pesquisa encontrado para este período.")

with tab2:
    st.header("Painel de Gestão de Demandas")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total de Demandas", len(df_m_f))
    
    c_a, c_b = st.columns(2)
    
    with c_a:
        if "Assunto" in df_m_f.columns:
            top_assuntos = df_m_f["Assunto"].value_counts().nlargest(10).reset_index()
            fig_assunto = px.bar(top_assuntos, x='count', y='Assunto', orientation='h', title="Top 10 Assuntos Mais Recorrentes")
            st.plotly_chart(fig_assunto, use_container_width=True)
            
    with c_b:
        if "Situacao" in df_m_f.columns:
            fig_sit = px.pie(df_m_f, names='Situacao', title="Status das Manifestações", hole=0.4)
            st.plotly_chart(fig_sit, use_container_width=True)

    st.divider()
    if "Unidade" in df_m_f.columns:
        st.subheader("Distribuição por Unidade Responsável")
        resumo_area = df_m_f["Unidade"].value_counts().reset_index()
        resumo_area.columns = ['Unidade Administrativa', 'Total de Demandas']
        
        # Linha de Total
        total_row = pd.DataFrame([['TOTAL GERAL', resumo_area['Total de Demandas'].sum()]], columns=['Unidade Administrativa', 'Total de Demandas'])
        st.table(pd.concat([resumo_area, total_row], ignore_index=True))
