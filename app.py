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

# --- Função de Mapeamento Inteligente (EVITA DUPLICATAS) ---
def mapear_colunas_anvisa(df):
    # Limpa nomes originais
    df.columns = df.columns.str.strip().str.encode('latin-1').str.decode('utf-8', 'ignore')
    
    # Remove colunas duplicadas que já venham no CSV original
    df = df.loc[:, ~df.columns.duplicated()]
    
    mapeamento = {}
    ja_mapeados = set()
    
    for col in df.columns:
        c = col.lower()
        if "tipo" in c and "Tipo" not in ja_mapeados:
            mapeamento[col] = "Tipo"; ja_mapeados.add("Tipo")
        elif "satisfeito" in c and "Satisfacao" not in ja_mapeados:
            mapeamento[col] = "Satisfacao"; ja_mapeados.add("Satisfacao")
        elif "assunto" in c and "sub" not in c and "Assunto" not in ja_mapeados:
            mapeamento[col] = "Assunto"; ja_mapeados.add("Assunto")
        elif "situa" in c and "Situacao" not in ja_mapeados:
            mapeamento[col] = "Situacao"; ja_mapeados.add("Situacao")
        elif ("área" in c or "unidade" in c) and "Area" not in ja_mapeados:
            mapeamento[col] = "Area"; ja_mapeados.add("Area")
        elif ("data" in c or "abertura" in c) and "Data" not in ja_mapeados:
            mapeamento[col] = "Data"; ja_mapeados.add("Data")

    return df.rename(columns=mapeamento)

# --- Carregamento de Dados ---
@st.cache_data
def carregar_dados_seguro(nome_arquivo):
    try:
        # Tenta ler do topo. Se falhar (poucas colunas), pula as 4 linhas do formato antigo
        df = pd.read_csv(nome_arquivo, sep=";", encoding="latin-1", on_bad_lines='skip')
        if df.shape[1] < 5:
            df = pd.read_csv(nome_arquivo, sep=";", encoding="latin-1", skiprows=4, on_bad_lines='skip')
        
        df = mapear_colunas_anvisa(df)
        df = corrigir_texto(df)
        
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(df["Data"], errors='coerce', dayfirst=True)
            df = df.dropna(subset=["Data"])
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
    meses = sorted(df_m["mês"].unique(), reverse=True)
    mapa = {m.strftime('%B/%Y'): m for m in meses}
    escolha = st.sidebar.multiselect("Selecione os meses:", options=list(mapa.keys()), default=list(mapa.keys())[:3])
    periodos = [mapa[e] for e in escolha]
    df_m_filt = df_m[df_m["mês"].isin(periodos)]
    df_p_filt = df_p[df_p["mês"].isin(periodos)] if "mês" in df_p.columns else df_p
else:
    df_m_filt, df_p_filt = df_m, df_p

# --- Dashboard ---
st.title("📊 Painel Estratégico | Ouvidoria ANVISA")

t1, t2 = st.tabs(["🎯 Pesquisa de Satisfação", "📂 Manifestações Gerais"])

with t1:
    st.metric("Total de Respostas", len(df_p_filt))
    c1, c2 = st.columns(2)
    with c1:
        if "Tipo" in df_p_filt.columns:
            st.plotly_chart(px.pie(df_p_filt, names='Tipo', title="Tipo de Manifestação", hole=0.3), use_container_width=True)
    with c2:
        if "Satisfacao" in df_p_filt.columns:
            sat_df = df_p_filt['Satisfacao'].value_counts().reset_index()
            sat_df.columns = ['Status', 'Total']
            st.plotly_chart(px.bar(sat_df, x='Total', y='Status', orientation='h', title="Nível de Satisfação", color='Status'), use_container_width=True)
    
    if "Area" in df_p_filt.columns:
        st.divider()
        st.subheader("Distribuição por Área (Pesquisa)")
        st.plotly_chart(px.bar(df_p_filt['Area'].value_counts().reset_index(), x='Area', y='count', color='Area', text_auto=True), use_container_width=True)

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
            st.plotly_chart(px.pie(df_m_filt, names='Situacao', title="Status das Demandas", hole=0.3), use_container_width=True)

    st.divider()
    if "Area" in df_m_filt.columns:
        st.subheader("Resumo por Unidade Responsável")
        resumo = df_m_filt['Area'].value_counts().reset_index()
        resumo.columns = ['Unidade Administrativa', 'Total']
        
        total_df = pd.DataFrame([['TOTAL GERAL', resumo['Total'].sum()]], columns=['Unidade Administrativa', 'Total'])
        st.dataframe(pd.concat([resumo, total_df], ignore_index=True), use_container_width=True, hide_index=True)
