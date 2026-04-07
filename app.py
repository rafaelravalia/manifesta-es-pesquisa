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
        # Lemos com latin-1
        df = pd.read_csv("pesquisa.csv", sep=";", encoding="latin-1", on_bad_lines='skip')
        
        # ESSA LINHA É A CURA: Remove caracteres estranhos dos nomes das colunas
        df.columns = df.columns.str.encode('latin-1').str.decode('utf-8', errors='ignore').str.strip()
        
        # --- Busca Flexível de Colunas ---
        for col in df.columns:
            nome_low = col.lower()
            if "tipo" in nome_low and "manifesta" in nome_low:
                df.rename(columns={col: "Tipo_Manifestacao_Limpo"}, inplace=True)
            if "satisfeito" in nome_low:
                df.rename(columns={col: "Satisfacao_Limpa"}, inplace=True)
            if "resposta" in nome_low and "pesquisa" in nome_low:
                df.rename(columns={col: "Data_Pesquisa_Limpa"}, inplace=True)

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
    arquivo = "ListaManifestacaoAtualizadaa.csv" 
    try:
        colunas_corretas = [
            'Situação', 'NUP', 'Tipo', 'Registrado Por', 'Possui Denúncia', 
            'Assunto', 'Subassunto', 'Tag', 'Data', 'Data de Abertura', 
            'Prazo', 'Data Encaminhamento', 'Qtde', 'Esfera', 'Serviço Federal', 
            'Serviço Não Federal', 'Outro Serviço', 'Órgão Destinatário', 
            'Órgão Interesse', 'UF', 'Município', 'Data 1 Resp', 'Data Resp Concl', 
            'Área Responsável', 'Área Responsável 2', 'Campos', 'Canal'
        ]
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
            # Gráfico de Pizza Seguro
            c_tipo = "Tipo_Manifestacao_Limpo" if "Tipo_Manifestacao_Limpo" in df_pesq_filtrado.columns else None
            if c_tipo:
                fig_tipo = px.pie(df_pesq_filtrado, names=c_tipo, title='Tipo de Manifestação')
                st.plotly_chart(fig_tipo, use_container_width=True)
        with col_p2:
            c_sat = "Satisfacao_Limpa" if "Satisfacao_Limpa" in df_pesq_filtrado.columns else None
            if c_sat:
                dados_sat = df_pesq_filtrado[c_sat].value_counts().reset_index()
                dados_sat.columns = [c_sat, 'quantidade']
                fig_sat = px.bar(dados_sat, x='quantidade', y=c_sat, orientation='h', title='Nível de Satisfação')
                st.plotly_chart(fig_sat, use_container_width=True)
    else:
        st.info("Sem dados para o período.")

with tab2:
    st.header("Painel Geral")
    st.metric("📩 Total de Manifestações", len(df_manifest_filtrado))
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        top_temas = df_manifest_filtrado['Assunto'].value_counts().nlargest(10).reset_index()
        top_temas.columns = ['Assunto', 'quantidade']
        st.plotly_chart(px.bar(top_temas, x='quantidade', y='Assunto', orientation='h', title="Top 10 Assuntos"), use_container_width=True)
    with col_m2:
        st.plotly_chart(px.pie(df_manifest_filtrado, names='Situação', title="Situação das Demandas"), use_container_width=True)
