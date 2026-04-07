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
    try:
        # Definimos os nomes das colunas manualmente para evitar erro de acento/caracteres estranhos
        colunas_pesquisa = [
            'Tipo_Manifestacao', 'Assunto', 'Subassunto', 'Data_Resposta_1', 'Data_Resposta_2',
            'Resp_Manifestacao_1', 'Resp_Manifestacao_2', 'Atendida', 'Facil_Compreender',
            'Satisfacao', 'Numero_Manifestacao', 'Teor', 'Parecer', 'Comentario', 'Reabertura', 'Area'
        ]
        
        # skiprows=1 pula a linha de títulos original que está vindo "suja"
        df = pd.read_csv("pesquisa.csv", sep=";", encoding="latin-1", skiprows=1, names=colunas_pesquisa, on_bad_lines='skip')
        
        # Limpeza de dados
        df['Satisfacao'] = df['Satisfacao'].astype(str).str.strip()
        
        # Processamento da Data (usando a primeira coluna de data disponível)
        df['Data_Resposta_1'] = pd.to_datetime(df['Data_Resposta_1'], errors='coerce', dayfirst=True)
        df["mês"] = df['Data_Resposta_1'].dt.to_period('M')
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar 'pesquisa.csv': {e}")
        return None

@st.cache_data
def carregar_dados_manifestacoes():
    arquivo = "ListaManifestacaoAtualizadaa.csv" 
    try:
        colunas_gerais = [
            'Situação', 'NUP', 'Tipo', 'Registrado Por', 'Possui Denúncia', 
            'Assunto', 'Subassunto', 'Tag', 'Data', 'Data de Abertura', 
            'Prazo', 'Data Encaminhamento', 'Qtde', 'Esfera', 'Serviço Federal', 
            'Serviço Não Federal', 'Outro Serviço', 'Órgão Destinatário', 
            'Órgão Interesse', 'UF', 'Município', 'Data 1 Resp', 'Data Resp Concl', 
            'Área Responsável', 'Área Responsável 2', 'Campos', 'Canal'
        ]
        # skiprows=4 pula o topo bagunçado do arquivo da Ouvidoria
        df = pd.read_csv(arquivo, sep=";", encoding='latin-1', skiprows=4, names=colunas_gerais, on_bad_lines='skip')
        
        df['Data de Abertura'] = pd.to_datetime(df['Data de Abertura'], errors='coerce', dayfirst=True)
        df["mês"] = df['Data de Abertura'].dt.to_period('M')
        
        return df
    except Exception as e:
        st.error(f"Erro crítico ao ler '{arquivo}': {e}")
        return None

# --- Execução ---
df_pesquisa = carregar_dados_pesquisa()
df_manifestacoes = carregar_dados_manifestacoes()

if df_pesquisa is None or df_manifestacoes is None:
    st.stop()

# --- Filtros ---
st.sidebar.title("Filtros do Painel")
if "mês" in df_manifestacoes.columns and not df_manifestacoes["mês"].isnull().all():
    meses_disponiveis = sorted(df_manifestacoes["mês"].dropna().unique(), reverse=True)
    mapa_meses = {m.strftime('%B/%Y').capitalize(): m for m in meses_disponiveis}
    selecao_meses = st.sidebar.multiselect("Selecione o período:", options=list(mapa_meses.keys()), default=list(mapa_meses.keys()))
    periodos_finais = [mapa_meses[m] for m in selecao_meses]
    
    df_manifest_filtrado = df_manifestacoes[df_manifestacoes["mês"].isin(periodos_finais)]
    df_pesq_filtrado = df_pesquisa[df_pesquisa["mês"].isin(periodos_finais)] if "mês" in df_pesquisa.columns else df_pesquisa
else:
    df_manifest_filtrado, df_pesq_filtrado = df_manifestacoes, df_pesquisa

# --- Layout ---
st.title("📊 Dashboard Ouvidoria ANVISA")
tab1, tab2 = st.tabs(["Satisfação do Usuário", "Manifestações Gerais"])

with tab1:
    st.header("Análise de Satisfação")
    if not df_pesq_filtrado.empty:
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            # Gráfico de Pizza usando o nome de coluna que nós criamos
            fig_tipo = px.pie(df_pesq_filtrado, names='Tipo_Manifestacao', title='Tipo de Manifestação')
            st.plotly_chart(fig_tipo, use_container_width=True)
            
        with col_p2:
            # Gráfico de Barras de Satisfação
            dados_sat = df_pesq_filtrado['Satisfacao'].value_counts().reset_index()
            dados_sat.columns = ['Satisfacao', 'quantidade']
            fig_sat = px.bar(dados_sat, x='quantidade', y='Satisfacao', orientation='h', title='Nível de Satisfação')
            st.plotly_chart(fig_sat, use_container_width=True)
    else:
        st.info("Sem dados para o período.")

with tab2:
    st.header("Painel Geral de Manifestações")
    st.metric("📩 Total de Manifestações", len(df_manifest_filtrado))
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        top_temas = df_manifest_filtrado['Assunto'].value_counts().nlargest(10).reset_index()
        top_temas.columns = ['Assunto', 'quantidade']
        st.plotly_chart(px.bar(top_temas, x='quantidade', y='Assunto', orientation='h', title="Top 10 Assuntos"), use_container_width=True)
    with col_m2:
        st.plotly_chart(px.pie(df_manifest_filtrado, names='Situação', title="Situação das Demandas"), use_container_width=True)
