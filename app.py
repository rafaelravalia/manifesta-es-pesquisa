import streamlit as st
import pandas as pd
import plotly.express as px

# --- Configurações Iniciais ---
st.set_page_config(page_title="Dashboard Ouvidoria ANVISA", page_icon="📊", layout="wide")

# --- Função de Correção de Texto (Trata acentos e Ç) ---
def corrigir_texto(df):
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].apply(lambda x: x.encode('latin-1').decode('utf-8', 'ignore') if isinstance(x, str) else x)
    return df

# --- Função de Carregamento Inteligente ---
@st.cache_data
def carregar_dados_inteligente(nome_arquivo):
    try:
        # Lemos o arquivo ignorando linhas problemáticas
        df = pd.read_csv(nome_arquivo, sep=";", encoding="latin-1", on_bad_lines='skip')
        
        # 1. Limpeza radical de nomes de colunas
        df.columns = df.columns.str.strip().str.encode('latin-1').str.decode('utf-8', 'ignore')
        
        # 2. Mapeamento por Palavra-Chave (Independente da posição)
        mapeamento = {}
        for col in df.columns:
            c = col.lower()
            if "tipo" in c and "manifesta" in c: mapeamento[col] = "Tipo"
            elif "satisfeito" in c or "satisfação" in c: mapeamento[col] = "Satisfacao"
            elif "assunto" in c and "sub" not in c: mapeamento[col] = "Assunto"
            elif "situa" in c and "pedido" not in c: mapeamento[col] = "Situacao"
            elif "área" in c or "unidade" in c: mapeamento[col] = "Area"
            elif "data" in c or "abertura" in c: 
                if "Data" not in mapeamento.values(): mapeamento[col] = "Data"

        df = df.rename(columns=mapeamento)
        df = corrigir_texto(df)
        
        # 3. Tratamento de Data e Mês
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(df["Data"], errors='coerce', dayfirst=True)
            # Remove linhas onde a data é impossível de ler (evita o erro do gráfico vazio)
            df = df.dropna(subset=["Data"])
            df["mês"] = df["Data"].dt.to_period('M')
            
        return df
    except Exception as e:
        st.error(f"Erro ao ler {nome_arquivo}: {e}")
        return None

# --- Execução do Carregamento ---
df_p = carregar_dados_inteligente("pesquisa.csv")
df_m = carregar_dados_inteligente("ListaManifestacaoAtualizadaa.csv")

if df_p is None or df_m is None:
    st.stop()

# --- Filtros Laterais ---
st.sidebar.header("🗓️ Filtros de Período")
if "mês" in df_m.columns:
    meses_disponiveis = sorted(df_m["mês"].unique(), reverse=True)
    mapa_meses = {m.strftime('%B/%Y'): m for m in meses_disponiveis}
    selecao = st.sidebar.multiselect("Selecione os meses:", options=list(mapa_meses.keys()), default=list(mapa_meses.keys())[:3])
    periodos = [mapa_meses[s] for s in selecao]
    
    df_m_filt = df_m[df_m["mês"].isin(periodos
