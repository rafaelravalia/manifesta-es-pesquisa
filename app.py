import streamlit as st
import pandas as pd
import plotly.express as px

# --- Configurações Iniciais ---
st.set_page_config(
    page_title="Dashboard Ouvidoria ANVISA",
    page_icon="📊",
    layout="wide"
)

# --- Funções de Carregamento de Dados ---

@st.cache_data
def carregar_dados_pesquisa():
    """
    Carrega e processa os dados da pesquisa de satisfação (pesquisa.csv).
    """
    try:
        # Lendo com latin-1 para evitar erro nos acentos da ANVISA
        df = pd.read_csv("pesquisa.csv", sep=";", encoding="latin-1", on_bad_lines='skip')
        df.columns = df.columns.str.strip()

        coluna_satisfacao = "Você está satisfeito(a) com o atendimento prestado?"
        if coluna_satisfacao in df.columns:
            df[coluna_satisfacao] = df[coluna_satisfacao].str.strip()

        # Procurando a coluna de data (ajustada para os nomes reais do seu CSV)
        opcoes_coluna_data = ['Resposta à Pesquisa', 'Resposta à pesquisa', 'Data da Resposta']
        coluna_data_encontrada = None
        for coluna in opcoes_coluna_data:
            if coluna in df.columns:
                coluna_data_encontrada = coluna
                break
        
        if coluna_data_encontrada:
            df[coluna_data_encontrada] = pd.to_datetime(df[coluna_data_encontrada], errors='coerce', dayfirst=True)
            df["mês"] = df[coluna_data_encontrada].dt.to_period('M')
        else:
            st.warning("Aviso: Filtro de tempo da pesquisa desativado (coluna de data não encontrada).")
            df["mês"] = None
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar 'pesquisa.csv': {e}")
        return None

@st.cache_data
def carregar_dados_manifestacoes():
    """
    Carrega os dados gerais. Pula as 4 linhas bagunçadas do topo do arquivo da Ouvidoria.
    """
    # Nome exato do arquivo no seu GitHub
    arquivo = "ListaManifestacaoAtualizadaa.csv" 
    
    try:
        # Definindo as colunas manualmente para ignorar o cabeçalho quebrado
        colunas_corretas = [
            'Situação', 'NUP', 'Tipo', 'Registrado Por', 'Possui Denúncia', 
            'Assunto', 'Subassunto', 'Tag', 'Data', 'Data de Abertura', 
            'Prazo', 'Data Encaminhamento', 'Qtde', 'Esfera', 'Serviço Federal', 
            'Serviço Não Federal', 'Outro Serviço', 'Órgão Destinatário', 
            'Órgão Interesse', 'UF', 'Município', 'Data 1 Resp', 'Data Resp Concl', 
            'Área Responsável', 'Área Responsável 2', 'Campos', 'Canal'
        ]

        # skiprows=4 pula a parte suja; on_bad_lines='skip' evita travar em textos longos
        df = pd.read_csv(arquivo, sep=";", encoding='latin-1', skiprows=4, names=colunas_corretas, on_bad_lines='skip')
        
        # Limpeza básica
        df.columns = df.columns.str.strip()

        if 'Data de Abertura' in df.columns:
            df['Data de Abertura'] = pd.to_datetime(df['Data de Abertura'], errors='coerce', dayfirst=True)
            df["mês"] = df['Data de Abertura'].dt.to_period('M')
        else:
            df["mês"] = None

        return df

    except Exception as e:
        st.error(f"Erro crítico ao ler '{arquivo}': {e}")
        return None

# --- Execução do Carregamento ---
df_pesquisa = carregar_dados_pesquisa()
df_manifestacoes = carregar_dados_manifestacoes()

if df_pesquisa is None or df_manifestacoes is None:
    st.error("Falha ao carregar os dados. Verifique os arquivos CSV no GitHub.")
    st.stop()

# --- Filtros Laterais ---
st.sidebar.title("Filtros do Painel")
usar_data_invalida = st.sidebar.checkbox("Incluir manifestações sem data?", value=False)

# Filtro de Meses (baseado nas Manifestações)
if "mês" in df_manifestacoes.columns and not df_manifestacoes["mês"].isnull().all():
    meses_disponiveis = sorted(df_manifestacoes["mês"].dropna().unique(), reverse=True)
    mapa_meses = {m.strftime('%B/%Y').capitalize(): m for m in meses_disponiveis}
    
    selecao_meses = st.sidebar.multiselect(
        "Selecione o período:",
        options=list(mapa_meses.keys()),
        default=list(mapa_meses.keys())
    )
    
    periodos_finais = [mapa_meses[m] for m in selecao_meses]
    
    # Aplicando o filtro
    df_manifest_filtrado = df_manifestacoes[
        (df_manifestacoes["mês"].isin(periodos_finais)) |
        (usar_data_invalida & df_manifestacoes["mês"].isna())
    ]
    
    if df_pesquisa is not None and "mês" in df_pesquisa.columns:
        df_pesq_filtrado = df_pesquisa[df_pesquisa["mês"].isin(periodos_finais)]
    else:
        df_pesq_filtrado = df_pesquisa
else:
    df_manifest_filtrado = df_manifestacoes
    df_pesq_filtrado = df_pesquisa

# --- Layout do Dashboard ---
st.title("📊 Dashboard Ouvidoria ANVISA")

tab1, tab2 = st.tabs(["Satisfação do Usuário", "Manifestações Gerais"])

with tab1:
    st.header("Análise de Satisfação")
    if not df_pesq_filtrado.empty:
        st.metric("Total de Respostas", len(df_pesq_filtrado))
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            fig_tipo = px.pie(df_pesq_filtrado, names='Tipo de Manifestação', title='Tipo de Manifestação')
            st.plotly_chart(fig_tipo, use_container_width=True)
        
        with col_p2:
            col_sat = "Você está satisfeito(a) com o atendimento prestado?"
            if col_sat in df_pesq_filtrado.columns:
                fig_sat = px.bar(df_pesq_filtrado[col_sat].value_counts().reset_index(), 
                                 x='count', y=col_sat, orientation='h', title='Nível de Satisfação')
                st.plotly_chart(fig_sat, use_container_width=True)
    else:
        st.info("Sem dados de pesquisa para o período.")

with tab2:
    st.header("Painel Geral")
    st.metric("📩 Total de Manifestações", len(df_manifest_filtrado))
    
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.subheader("Top 10 Assuntos")
        top_temas = df_manifest_filtrado['Assunto'].value_counts().nlargest(10).reset_index()
        fig_temas = px.bar(top_temas, x='count', y='Assunto', orientation='h')
        st.plotly_chart(fig_temas, use_container_width=True)
        
    with col_m2:
        st.subheader("Situação das Demandas")
        fig_sit = px.pie(df_manifest_filtrado, names='Situação')
        st.plotly_chart(fig_sit, use_container_width=True)

    if "Área Responsável" in df_manifest_filtrado.columns:
        st.subheader("Demandas por Área")
        st.dataframe(df_manifest_filtrado['Área Responsável'].value_counts(), use_container_width=True)
