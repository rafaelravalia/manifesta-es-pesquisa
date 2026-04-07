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

# --- Funções de Carregamento de Dados ---

@st.cache_data
def carregar_dados_pesquisa():
    try:
        # Nomes manuais para garantir que o gráfico encontre as colunas
        colunas_pesquisa = [
            'Tipo_Manifestacao', 'Assunto', 'Subassunto', 'Data_Resposta_1', 'Data_Resposta_2',
            'Resp_Manifestacao_1', 'Resp_Manifestacao_2', 'Atendida', 'Facil_Compreender',
            'Satisfacao', 'Numero_Manifestacao', 'Teor', 'Parecer', 'Comentario', 'Reabertura', 'Area'
        ]
        df = pd.read_csv("pesquisa.csv", sep=";", encoding="latin-1", skiprows=1, names=colunas_pesquisa, on_bad_lines='skip')
        df = corrigir_texto(df)
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
        df = pd.read_csv(arquivo, sep=";", encoding='latin-1', skiprows=4, names=colunas_gerais, on_bad_lines='skip')
        df = corrigir_texto(df)
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
tab1, tab2 = st.tabs(["Análise da Pesquisa de Satisfação", "Painel de Manifestações Gerais"])

# --- ABA 1: PESQUISA (RECUPERADA E COMPLETA) ---
with tab1:
    st.header("Análise da Pesquisa de Satisfação")
    if not df_pesq_filtrado.empty:
        st.metric("Total de Respostas no Período", len(df_pesq_filtrado))
        st.markdown("---")

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.subheader("Tipo de Manifestação")
            fig_tipo = px.pie(df_pesq_filtrado, names='Tipo_Manifestacao', hole=0.3)
            st.plotly_chart(fig_tipo, use_container_width=True)
            
        with col_p2:
            st.subheader("Satisfação com o Atendimento")
            dados_sat = df_pesq_filtrado['Satisfacao'].value_counts().reset_index()
            dados_sat.columns = ['Satisfacao', 'quantidade']
            fig_sat = px.bar(dados_sat, x='quantidade', y='Satisfacao', orientation='h', color='Satisfacao', text_auto=True)
            st.plotly_chart(fig_sat, use_container_width=True)

        st.markdown("---")
        st.subheader("Distribuição de Respostas por Área")
        # Gráfico que estava faltando no seu relato
        if 'Area' in df_pesq_filtrado.columns:
            dados_area = df_pesq_filtrado['Area'].value_counts().reset_index()
            dados_area.columns = ['Área', 'Quantidade']
            fig_area = px.bar(dados_area, x='Área', y='Quantidade', text_auto=True, color='Área')
            fig_area.update_layout(xaxis_tickangle=-45, showlegend=False)
            st.plotly_chart(fig_area, use_container_width=True)
    else:
        st.info("Sem dados de pesquisa para o período selecionado.")

# --- ABA 2: MANIFESTAÇÕES ---
with tab2:
    st.header("Painel de Manifestações Gerais")
    st.metric("📩 Total de Manifestações", len(df_manifest_filtrado))
    
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.subheader("Top 10 Assuntos")
        top_temas = df_manifest_filtrado['Assunto'].value_counts().nlargest(10).reset_index()
        top_temas.columns = ['Assunto', 'quantidade']
        st.plotly_chart(px.bar(top_temas, x='quantidade', y='Assunto', orientation='h'), use_container_width=True)
        
    with col_m2:
        st.subheader("Situação das Demandas")
        st.plotly_chart(px.pie(df_manifest_filtrado, names='Situação'), use_container_width=True)

    st.markdown("---")
    st.subheader("Resumo por Área Responsável")
    if "Área Responsável" in df_manifest_filtrado.columns:
        resumo_area = df_manifest_filtrado['Área Responsável'].value_counts().reset_index()
        resumo_area.columns = ['Área Responsável', 'Total de Manifestações']
        st.dataframe(resumo_area, use_container_width=True, hide_index=True)
