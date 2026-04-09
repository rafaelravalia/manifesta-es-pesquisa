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

# --- Função de Mapeamento Inteligente ---
def mapear_colunas(df):
    df.columns = df.columns.str.strip().str.encode('latin-1').str.decode('utf-8', 'ignore')
    mapeamento = {}
    for col in df.columns:
        c = col.lower()
        if "tipo" in c and "manifesta" in c: mapeamento[col] = "Tipo"
        elif "satisfeito" in c: mapeamento[col] = "Satisfacao"
        elif "assunto" in c and "sub" not in c: mapeamento[col] = "Assunto"
        elif "situa" in c: mapeamento[col] = "Situacao"
        elif "área" in c or "unidade" in c or "area" in c: mapeamento[col] = "Area"
        elif "data" in c or "abertura" in c:
            if "Data" not in mapeamento.values(): mapeamento[col] = "Data"
    return df.rename(columns=mapeamento)

# --- Carregamento de Dados ---
@st.cache_data
def carregar_dados(nome_arquivo):
    try:
        # Tenta ler do topo. Se falhar ou vier vazio, tenta pular 4 (formato antigo)
        df = pd.read_csv(nome_arquivo, sep=";", encoding="latin-1", on_bad_lines='skip')
        if df.shape[1] < 3: # Se leu errado, tenta o formato com cabeçalho deslocado
            df = pd.read_csv(nome_arquivo, sep=";", encoding="latin-1", skiprows=4, on_bad_lines='skip')
        
        df = mapear_colunas(df)
        df = corrigir_texto(df)
        
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(df["Data"], errors='coerce', dayfirst=True)
            df = df.dropna(subset=["Data"])
            df["mês"] = df["Data"].dt.to_period('M')
        return df
    except:
        return None

# --- Execução ---
df_p = carregar_dados("pesquisa.csv")
df_m = carregar_dados("ListaManifestacaoAtualizadaa.csv")

if df_p is None or df_m is None:
    st.error("Erro ao carregar arquivos. Verifique os nomes no GitHub.")
    st.stop()

# --- Filtros ---
st.sidebar.header("🗓️ Filtros")
if "mês" in df_m.columns:
    meses = sorted(df_m["mês"].unique(), reverse=True)
    mapa = {m.strftime('%B/%Y'): m for m in meses}
    escolha = st.sidebar.multiselect("Selecione os meses:", options=list(mapa.keys()), default=list(mapa.keys())[:3])
    periodos = [mapa[e] for e in escolha]
    df_m_filt = df_m[df_m["mês"].isin(periodos)]
    df_p_filt = df_p[df_p["mês"].isin(periodos)] if "mês" in df_p.columns else df_p
else:
    df_m_filt, df_p_filt = df_m, df_p

# --- Layout ---
st.title("📊 Dashboard Ouvidoria ANVISA")
t1, t2 = st.tabs(["🎯 Pesquisa de Satisfação", "📂 Manifestações Gerais"])

with t1:
    st.header("Análise da Pesquisa de Satisfação")
    if not df_p_filt.empty:
        st.metric("Total de Respostas", len(df_p_filt))
        c1, c2 = st.columns(2)
        with c1:
            if "Tipo" in df_p_filt.columns:
                st.plotly_chart(px.pie(df_p_filt, names='Tipo', title="Tipo de Manifestação", hole=0.3), use_container_width=True)
        with c2:
            if "Satisfacao" in df_p_filt.columns:
                sat_data = df_p_filt['Satisfacao'].value_counts().reset_index()
                sat_data.columns = ['Status', 'Total']
                st.plotly_chart(px.bar(sat_data, x='Total', y='Status', orientation='h', title="Satisfação", color='Status'), use_container_width=True)

        if "Area" in df_p_filt.columns:
            st.divider()
            st.subheader("Respostas por Área Técnica")
            area_df = df_p_filt['Area'].value_counts().reset_index()
            area_df.columns = ['Área', 'Quantidade']
            st.plotly_chart(px.bar(area_df, x='Área', y='Quantidade', color='Área', text_auto=True), use_container_width=True)

with t2:
    st.header("Painel de Manifestações Gerais")
    st.metric("📩 Total de Manifestações", len(df_m_filt))
    
    ca, cb = st.columns(2)
    with ca:
        if "Assunto" in df_m_filt.columns:
            top_a = df_m_filt['Assunto'].value_counts().nlargest(10).reset_index()
            top_a.columns = ['Assunto', 'Qtd']
            st.plotly_chart(px.bar(top_a, x='Qtd', y='Assunto', orientation='h', title="Top 10 Assuntos"), use_container_width=True)
    with cb:
        if "Situacao" in df_m_filt.columns:
            st.plotly_chart(px.pie(df_m_filt, names='Situacao', title="Situação das Demandas"), use_container_width=True)

    if "Area" in df_m_filt.columns:
        st.divider()
        st.subheader("Distribuição por Unidade Responsável")
        resumo = df_m_filt['Area'].value_counts().reset_index()
        resumo.columns = ['Unidade Administrativa', 'Total']
        
        # Adiciona Linha de Total Geral (Como no código do Riam)
        total_val = resumo['Total'].sum()
        total_df = pd.DataFrame([['TOTAL GERAL', total_val]], columns=['Unidade Administrativa', 'Total'])
        resumo_final = pd.concat([resumo, total_df], ignore_index=True)
        
        st.dataframe(resumo_final, use_container_width=True, hide_index=True)
