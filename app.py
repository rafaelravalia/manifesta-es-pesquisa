import streamlit as st
import pandas as pd
import plotly.express as px

# --- Configurações Iniciais ---
st.set_page_config(page_title="Dashboard Ouvidoria ANVISA", page_icon="📊", layout="wide")

# --- Função de Limpeza e Tradução de Colunas ---
def ajustar_colunas(df):
    # Remove caracteres estranhos dos nomes das colunas originais
    df.columns = df.columns.str.encode('latin-1').str.decode('utf-8', 'ignore').str.strip()
    
    mapeamento = {}
    for col in df.columns:
        c = col.lower()
        # Busca inteligente por palavras-chave
        if "tipo" in c: mapeamento[col] = "Tipo"
        elif "satisfeito" in c or "satisfação" in c: mapeamento[col] = "Satisfacao"
        elif "assunto" in c and "sub" not in c: mapeamento[col] = "Assunto"
        elif "situa" in c: mapeamento[col] = "Situacao"
        elif "área" in c or "unidade" in c or "setor" in c: 
            # Se for do arquivo de manifestações, vira Unidade. Se for pesquisa, Area_Pesq
            mapeamento[col] = "Unidade" 
        elif "data" in c or "abertura" in c or "resposta" in c: 
            if "Data" not in mapeamento.values(): mapeamento[col] = "Data"

    return df.rename(columns=mapeamento)

def corrigir_texto(df):
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].apply(lambda x: x.encode('latin-1').decode('utf-8', 'ignore') if isinstance(x, str) else x)
    return df

# --- Carregamento ---
@st.cache_data
def carregar_dados(nome_arquivo, pular):
    try:
        df = pd.read_csv(nome_arquivo, sep=";", encoding="latin-1", skiprows=pular, on_bad_lines='skip')
        df = ajustar_colunas(df)
        df = corrigir_texto(df)
        
        # Tenta converter data dinamicamente
        colunas_data = [c for c in df.columns if "Data" in c]
        if colunas_data:
            df[colunas_data[0]] = pd.to_datetime(df[colunas_data[0]], errors='coerce', dayfirst=True)
            df["mês"] = df[colunas_data[0]].dt.to_period('M')
        return df
    except: return None

# --- Execução ---
# Tentamos carregar sem pular linhas para detectar o cabeçalho novo
df_p = carregar_dados("pesquisa.csv", 0) 
df_m = carregar_dados("ListaManifestacaoAtualizadaa.csv", 0)

# Se falhar sem pular, tentamos o padrão antigo da ANVISA (pular 4)
if df_m is not None and df_m.shape[1] < 5: 
    df_m = carregar_dados("ListaManifestacaoAtualizadaa.csv", 4)

if df_p is None or df_m is None:
    st.error("Erro crítico: Verifique se os arquivos CSV estão no GitHub com os nomes corretos.")
    st.stop()

# --- Sidebar ---
st.sidebar.header("🗓️ Filtros")
if "mês" in df_m.columns:
    meses = sorted(df_m["mês"].dropna().unique(), reverse=True)
    mapa = {m.strftime('%B/%Y'): m for m in meses}
    escolha = st.sidebar.multiselect("Selecione os meses:", options=list(mapa.keys()), default=list(mapa.keys())[:3])
    periodos = [mapa[e] for e in escolha]
    df_m_filt = df_m[df_m["mês"].isin(periodos)]
    df_p_filt = df_p[df_p["mês"].isin(periodos)] if "mês" in df_p.columns else df_p
else:
    df_m_filt, df_p_filt, escolha = df_m, df_p, ["Todo o período"]

# --- Dashboard ---
st.title("📊 Painel Ouvidoria ANVISA")

t1, t2 = st.tabs(["🎯 Pesquisa de Satisfação", "📂 Manifestações Gerais"])

with t1:
    st.metric("Total de Respostas", len(df_p_filt))
    c1, c2 = st.columns(2)
    with c1:
        # Tenta mostrar Tipo, se não achar, avisa qual coluna encontrou
        col_tipo = "Tipo" if "Tipo" in df_p_filt.columns else df_p_filt.columns[0]
        st.plotly_chart(px.pie(df_p_filt, names=col_tipo, title=f"Distribuição por {col_tipo}"), use_container_width=True)
    with c2:
        col_sat = "Satisfacao" if "Satisfacao" in df_p_filt.columns else None
        if col_sat:
            sat_df = df_p_filt[col_sat].value_counts().reset_index()
            sat_df.columns = ['Status', 'Total']
            st.plotly_chart(px.bar(sat_df, x='Total', y='Status', orientation='h', title="Nível de Satisfação"), use_container_width=True)

with t2:
    st.metric("Total de Demandas", len(df_m_filt))
    ca, cb = st.columns(2)
    with ca:
        col_assunto = "Assunto" if "Assunto" in df_m_filt.columns else None
        if col_assunto:
            top = df_m_filt[col_assunto].value_counts().nlargest(10).reset_index()
            top.columns = ['Assunto', 'Qtd']
            st.plotly_chart(px.bar(top, x='Qtd', y='Assunto', orientation='h', title="Top 10 Assuntos"), use_container_width=True)
    with cb:
        col_sit = "Situacao" if "Situacao" in df_m_filt.columns else None
        if col_sit:
            st.plotly_chart(px.pie(df_m_filt, names=col_sit, title="Status das Demandas"), use_container_width=True)

    st.divider()
    col_uni = "Unidade" if "Unidade" in df_m_filt.columns else None
    if col_uni:
        st.subheader("Demandas por Área")
        resumo = df_m_filt[col_uni].value_counts().reset_index()
        resumo.columns = ['Área', 'Total']
        st.dataframe(resumo, use_container_width=True, hide_index=True)
