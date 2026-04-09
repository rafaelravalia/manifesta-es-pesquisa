import streamlit as st
import pandas as pd
import plotly.express as px

# --- Configurações Iniciais ---
st.set_page_config(
    page_title="Dashboard Ouvidoria ANVISA",
    page_icon="📊",
    layout="wide"
)

# --- Função de Tratamento de Texto ---
def limpar_e_corrigir(df):
    # Remove colunas totalmente vazias ou repetidas que causam o erro de duplicatas
    df = df.loc[:, ~df.columns.duplicated()]
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).apply(
                lambda x: x.encode('latin-1', 'ignore').decode('utf-8', 'ignore').strip()
            )
    return df

# --- Carregamento de Dados com Caching ---

@st.cache_data
def carregar_pesquisa():
    try:
        # A pesquisa geralmente não tem as linhas de metadados no topo
        df = pd.read_csv("pesquisa.csv", sep=";", encoding="latin-1", on_bad_lines='skip')
        df.columns = df.columns.str.strip()
        df = limpar_e_corrigir(df)
        
        # Mapeamento dinâmico para garantir que os gráficos encontrem as colunas
        mapa = {}
        for c in df.columns:
            low = c.lower()
            if "satisfeito" in low: mapa[c] = "Satisfacao"
            elif "tipo" in low and "manifesta" in low: mapa[c] = "Tipo"
            elif "área" in low or low == "area": mapa[c] = "Area_Tecnica"
            elif "resposta" in low and "pesquisa" in low: mapa[c] = "Data"
        
        df = df.rename(columns=mapa)
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(df["Data"], errors='coerce', dayfirst=True)
            df = df.dropna(subset=["Data"])
            df["mês"] = df["Data"].dt.to_period('M')
        return df
    except Exception as e:
        st.error(f"Erro ao carregar pesquisa.csv: {e}")
        return None

@st.cache_data
def carregar_manifestacoes():
    try:
        # Manifestações da ANVISA costumam ter 4 linhas de cabeçalho administrativo
        df = pd.read_csv("ListaManifestacaoAtualizadaa.csv", sep=";", encoding="latin-1", skiprows=4, on_bad_lines='skip')
        df.columns = df.columns.str.strip()
        df = limpar_e_corrigir(df)
        
        mapa = {}
        for c in df.columns:
            low = c.lower()
            if "assunto" in low and "sub" not in low: mapa[c] = "Assunto"
            elif "situa" in low: mapa[c] = "Situacao"
            elif "data" in low or "abertura" in low: mapa[c] = "Data"
            elif "área responsável" in low or "area responsavel" in low: mapa[c] = "Unidade"
        
        df = df.rename(columns=mapa)
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(df["Data"], errors='coerce', dayfirst=True)
            df = df.dropna(subset=["Data"])
            df["mês"] = df["Data"].dt.to_period('M')
        return df
    except Exception as e:
        st.error(f"Erro ao carregar ListaManifestacaoAtualizadaa.csv: {e}")
        return None

# --- Execução do Carregamento ---
df_p = carregar_pesquisa()
df_m = carregar_manifestacoes()

if df_p is None or df_m is None:
    st.stop()

# --- Sidebar de Filtros ---
st.sidebar.header("🗓️ Período de Análise")
if "mês" in df_m.columns:
    meses_m = set(df_m["mês"].unique())
    meses_p = set(df_p["mês"].unique()) if "mês" in df_p.columns else set()
    todos_meses = sorted(list(meses_m | meses_p), reverse=True)
    
    escolha_meses = st.sidebar.multiselect(
        "Selecione os meses:", 
        options=todos_meses, 
        default=todos_meses[:3],
        format_func=lambda x: x.strftime('%B / %Y')
    )
    
    df_m_f = df_m[df_m["mês"].isin(escolha_meses)]
    df_p_f = df_p[df_p["mês"].isin(escolha_meses)] if "mês" in df_p.columns else df_p
else:
    df_m_f, df_p_f = df_m, df_p

# --- Dashboard Principal ---
st.title("📊 Painel Estratégico | Ouvidoria ANVISA")

tab1, tab2 = st.tabs(["🎯 Pesquisa de Satisfação", "📂 Gestão de Manifestações"])

with tab1:
    st.header("Análise de Satisfação")
    if not df_p_f.empty:
        m1, m2 = st.columns(2)
        m1.metric("Total de Respostas", len(df_p_f))
        
        st.divider()
        col1, col2 = st.columns(2)
        
        with col1:
            if "Tipo" in df_p_f.columns:
                fig_tipo = px.pie(df_p_f, names='Tipo', title="Tipos de Manifestação", hole=0.4)
                st.plotly_chart(fig_tipo, use_container_width=True)
        
        with col2:
            if "Satisfacao" in df_p_f.columns:
                sat_data = df_p_f["Satisfacao"].value_counts().reset_index()
                fig_sat = px.bar(sat_data, x='count', y='Satisfacao', orientation='h', title="Nível de Satisfação", color='Satisfacao')
                st.plotly_chart(fig_sat, use_container_width=True)
        
        st.divider()
        if "Area_Tecnica" in df_p_f.columns:
            st.subheader("Volume por Área Técnica (Pesquisa)")
            area_data = df_p_f["Area_Tecnica"].value_counts().reset_index()
            fig_area = px.bar(area_data, x='Area_Tecnica', y='count', text_auto=True, color='Area_Tecnica')
            st.plotly_chart(fig_area, use_container_width=True)
    else:
        st.info("Nenhum dado de pesquisa encontrado para o período.")

with tab2:
    st.header("Gestão Geral de Demandas")
    if not df_m_f.empty:
        st.metric("Total de Manifestações", len(df_m_f))
        
        c_a, c_b = st.columns(2)
        with c_a:
            if "Assunto" in df_m_f.columns:
                top_10 = df_m_f["Assunto"].value_counts().nlargest(10).reset_index()
                fig_assunto = px.bar(top_10, x='count', y='Assunto', orientation='h', title="Top 10 Assuntos Recorrentes")
                st.plotly_chart(fig_assunto, use_container_width=True)
        
        with c_b:
            if "Situacao" in df_m_f.columns:
                fig_sit = px.pie(df_m_f, names='Situacao', title="Situação Atual das Demandas", hole=0.4)
                st.plotly_chart(fig_sit, use_container_width=True)
        
        st.divider()
        if "Unidade" in df_m_f.columns:
            st.subheader("Distribuição por Unidade Responsável")
            resumo_u = df_m_f["Unidade"].value_counts().reset_index()
            resumo_u.columns = ['Unidade Administrativa', 'Total de Demandas']
            
            # Cálculo do Total Geral para a tabela
            total_geral = pd.DataFrame([['TOTAL GERAL', resumo_u['Total de Demandas'].sum()]], 
                                     columns=['Unidade Administrativa', 'Total de Demandas'])
            tabela_final = pd.concat([resumo_u, total_geral], ignore_index=True)
            
            st.dataframe(tabela_final, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma manifestação encontrada para o período.")
