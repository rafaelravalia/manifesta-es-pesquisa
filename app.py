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
    Usa busca flexível para encontrar colunas mesmo com erros de acento.
    """
    try:
        # Lendo com latin-1 e ignorando linhas com erro (quebras de linha no CSV)
        df = pd.read_csv("pesquisa.csv", sep=";", encoding="latin-1", on_bad_lines='skip')
        df.columns = df.columns.str.strip()

        # --- Busca Flexível de Colunas para evitar KeyError ---
        for col in df.columns:
            nome_low = col.lower()
            
            # Identifica coluna de Tipo de Manifestação
            if "tipo" in nome_low and "manifesta" in nome_low:
                df.rename(columns={col: "Tipo_Manifestacao_Limpo"}, inplace=True)
            
            # Identifica coluna de Satisfação
            if "satisfeito" in nome_low:
                df.rename(columns={col: "Satisfacao_Limpa"}, inplace=True)
            
            # Identifica coluna de Data da Resposta
            if "resposta" in nome_low and "pesquisa" in nome_low:
                df.rename(columns={col: "Data_Pesquisa_Limpa"}, inplace=True)

        # Processamento da Data da Pesquisa
        if "Data_Pesquisa_Limpa" in df.columns:
            df["Data_Pesquisa_Limpa"] = pd.to_datetime(df["Data_Pesquisa_Limpa"], errors='coerce', dayfirst=True)
            df["mês"] = df["Data_Pesquisa_Limpa"].dt.to_period('M')
        else:
            df["mês"] = None
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar 'pesquisa.csv': {e}")
        return None

@st.cache_data
def carregar_dados_manifestacoes():
    """
    Carrega os dados gerais pulando o cabeçalho quebrado do arquivo da ANVISA.
    """
    arquivo = "ListaManifestacaoAtualizadaa.csv" 
    
    try:
        # Títulos manuais para ignorar as 4 linhas sujas do topo
        colunas_corretas = [
            'Situação', 'NUP', 'Tipo', 'Registrado Por', 'Possui Denúncia', 
            'Assunto', 'Subassunto', 'Tag', 'Data', 'Data de Abertura', 
            'Prazo', 'Data Encaminhamento', 'Qtde', 'Esfera', 'Serviço Federal', 
            'Serviço Não Federal', 'Outro Serviço', 'Órgão Destinatário', 
            'Órgão Interesse', 'UF', 'Município', 'Data 1 Resp', 'Data Resp Concl', 
            'Área Responsável', 'Área Responsável 2', 'Campos', 'Canal'
        ]

        # skiprows=4 pula a parte corrompida; on_bad_lines='skip' evita travar em textos longos
        df = pd.read_csv(arquivo, sep=";", encoding='latin-1', skiprows=4, names=colunas_corretas, on_bad_lines='skip')
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
    st.stop()

# --- Filtros Laterais ---
st.sidebar.title("Filtros do Painel")
usar_data_invalida = st.sidebar.checkbox("Incluir manifestações sem data?", value=False)

# Filtro de Meses baseado no arquivo principal
if "mês" in df_manifestacoes.columns and not df_manifestacoes["mês"].isnull().all():
    meses_disponiveis = sorted(df_manifestacoes["mês"].dropna().unique(), reverse=True)
    mapa_meses = {m.strftime('%B/%Y').capitalize(): m for m in meses_disponiveis}
    
    selecao_meses = st.sidebar.multiselect(
        "Selecione o período:",
        options=list(mapa_meses.keys()),
        default=list(mapa_meses.keys())
    )
    
    periodos_finais = [mapa_meses[m] for m in selecao_meses]
    
    # Aplicação do Filtro
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
            # Gráfico de Tipo usando a coluna renomeada na busca flexível
            c_tipo = "Tipo_Manifestacao_Limpo"
            if c_tipo in df_pesq_filtrado.columns:
                fig_tipo = px.pie(df_pesq_filtrado, names=c_tipo, title='Tipo de Manifestação')
                st.plotly_chart(fig_tipo, use_container_width=True)
            else:
                st.warning("Coluna 'Tipo de Manifestação' não encontrada.")
        
        with col_p2:
            # Gráfico de Satisfação usando a coluna renomeada
            c_sat = "Satisfacao_Limpa"
            if c_sat in df_pesq_filtrado.columns:
                dados_sat = df_pesq_filtrado[c_sat].value_counts().reset_index()
                fig_sat = px.bar(dados_sat, x='count', y=c_sat, orientation='h', title='Nível de Satisfação')
                st.plotly_chart(fig_sat, use_container_width=True)
            else:
                st.warning("Coluna de Satisfação não encontrada.")
    else:
        st.info("Sem dados de pesquisa para o período selecionado.")

with tab2:
    st.header("Painel de Manifestações Gerais")
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
