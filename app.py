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

# --- Função Inteligente para Mapear Colunas ---
def mapear_colunas_anvisa(df):
    # Limpa nomes das colunas originais
    df.columns = df.columns.str.strip()
    mapeamento = {}
    
    for col in df.columns:
        c = col.lower()
        # Procura colunas da Pesquisa
        if "tipo" in c and "manifesta" in c: mapeamento[col] = 'Tipo_Manifestacao'
        elif "satisfeito" in c: mapeamento[col] = 'Satisfacao'
        elif "área" in c and len(c) < 10: mapeamento[col] = 'Area_Pesquisa'
        
        # Procura colunas das Manifestações Gerais
        elif "assunto" in c and "sub" not in c: mapeamento[col] = 'Assunto'
        elif "situa" in c: mapeamento[col] = 'Situacao'
        elif "área responsável" in c or "area responsavel" in c: mapeamento[col] = 'Area_Responsavel'
        elif "data" in c and ("abertura" in c or "pesquisa" in c): mapeamento[col] = 'Data_Referencia'

    return df.rename(columns=mapeamento)

# --- Funções de Carregamento de Dados ---

@st.cache_data
def carregar_dados_dinamico(nome_arquivo, pular_linhas):
    try:
        # Lemos o arquivo respeitando o cabeçalho original
        df = pd.read_csv(nome_arquivo, sep=";", encoding="latin-1", skiprows=pular_linhas, on_bad_lines='skip')
        df = mapear_colunas_anvisa(df)
        df = corrigir_texto(df)
        
        if 'Data_Referencia' in df.columns:
            df['Data_Referencia'] = pd.to_datetime(df['Data_Referencia'], errors='coerce', dayfirst=True)
            df["mês"] = df['Data_Referencia'].dt.to_period('M')
        return df
    except Exception as e:
        st.error(f"Erro ao carregar '{nome_arquivo}': {e}")
        return None

# --- Execução do Carregamento ---
# Para manifestações pulamos 4 linhas de lixo; para pesquisa lemos do topo (skip=0 ou 1 dependendo do arquivo)
df_pesquisa = carregar_dados_dinamico("pesquisa.csv", 0) 
df_manifestacoes = carregar_dados_dinamico("ListaManifestacaoAtualizadaa.csv", 4)

if df_pesquisa is None or df_manifestacoes is None:
    st.stop()

# --- Filtros Laterais ---
st.sidebar.title("Filtros do Painel")
if "mês" in df_manifestacoes.columns and not df_manifestacoes["mês"].isnull().all():
    meses_disponiveis = sorted(df_manifestacoes["mês"].dropna().unique(), reverse=True)
    mapa_meses = {m.strftime('%B/%Y').capitalize(): m for m in meses_disponiveis}
    selecao_meses = st.sidebar.multiselect("Selecione o período:", options=list(mapa_meses.keys()), default=list(mapa_meses.keys())[:3])
    periodos_finais = [mapa_meses[m] for m in selecao_meses]
    
    df_manifest_filtrado = df_manifestacoes[df_manifestacoes["mês"].isin(periodos_finais)]
    df_pesq_filtrado = df_pesquisa[df_pesquisa["mês"].isin(periodos_finais)] if "mês" in df_pesquisa.columns else df_pesquisa
else:
    df_manifest_filtrado, df_pesq_filtrado = df_manifestacoes, df_pesquisa

# --- Layout do Dashboard ---
st.title("📊 Dashboard Ouvidoria ANVISA")
tab1, tab2 = st.tabs(["Análise da Pesquisa de Satisfação", "Painel de Manifestações Gerais"])

with tab1:
    st.header("Análise da Pesquisa de Satisfação")
    if not df_pesq_filtrado.empty:
        st.metric("Total de Respostas", len(df_pesq_filtrado))
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            if 'Tipo_Manifestacao' in df_pesq_filtrado.columns:
                st.plotly_chart(px.pie(df_pesq_filtrado, names='Tipo_Manifestacao', title='Tipo de Manifestação', hole=0.3), use_container_width=True)
        with col_p2:
            if 'Satisfacao' in df_pesq_filtrado.columns:
                dados_sat = df_pesq_filtrado['Satisfacao'].value_counts().reset_index()
                dados_sat.columns = ['Satisfacao', 'quantidade']
                st.plotly_chart(px.bar(dados_sat, x='quantidade', y='Satisfacao', orientation='h', title='Nível de Satisfação', color='Satisfacao'), use_container_width=True)

        if 'Area_Pesquisa' in df_pesq_filtrado.columns:
            st.divider()
            st.subheader("Respostas por Área Técnica")
            dados_area = df_pesq_filtrado['Area_Pesquisa'].value_counts().reset_index()
            dados_area.columns = ['Área', 'Quantidade']
            st.plotly_chart(px.bar(dados_area, x='Área', y='Quantidade', color='Área', text_auto=True), use_container_width=True)
    else:
        st.info("Sem dados para o período selecionado.")

with tab2:
    st.header("Painel de Manifestações Gerais")
    st.metric("📩 Total de Manifestações", len(df_manifest_filtrado))
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        if 'Assunto' in df_manifest_filtrado.columns:
            top_temas = df_manifest_filtrado['Assunto'].value_counts().nlargest(10).reset_index()
            top_temas.columns = ['Assunto', 'quantidade']
            st.plotly_chart(px.bar(top_temas, x='quantidade', y='Assunto', orientation='h', title="Top 10 Assuntos"), use_container_width=True)
    with col_m2:
        if 'Situacao' in df_manifest_filtrado.columns:
            st.plotly_chart(px.pie(df_manifest_filtrado, names='Situacao', title="Situação das Demandas"), use_container_width=True)

    if 'Area_Responsavel' in df_manifest_filtrado.columns:
        st.divider()
        st.subheader("Resumo por Área Responsável")
        resumo_area = df_manifest_filtrado['Area_Responsavel'].value_counts().reset_index()
        resumo_area.columns = ['Área Responsável', 'Total']
        st.dataframe(resumo_area, use_container_width=True, hide_index=True)
