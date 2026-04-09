import streamlit as st
import pandas as pd
import plotly.express as px

# --- Configurações Iniciais ---
st.set_page_config(page_title="Dashboard Ouvidoria ANVISA", page_icon="📊", layout="wide")

# --- Função de Limpeza (Sem estragar os acentos) ---
def limpar_texto(df):
    # Remove colunas com nomes duplicados para evitar o "DuplicateError"
    df = df.loc[:, ~df.columns.duplicated()]
    for col in df.columns:
        if df[col].dtype == 'object':
            # Remove apenas o "??" e espaços sobrando, mantendo os acentos e emojis intactos
            df[col] = df[col].astype(str).str.replace('??', '', regex=False).str.strip()
    return df

# --- Funções de Carregamento Ultra-Seguras ---
@st.cache_data
def carregar_pesquisa():
    try:
        # Lê usando utf-8-sig para garantir acentos e emojis corretos
        df = pd.read_csv("pesquisa.csv", sep=";", encoding="utf-8-sig", on_bad_lines="skip")
        df.columns = df.columns.str.strip()
        df = limpar_texto(df)

        # Pesca as colunas certas independente da ordem
        col_tipo = next((c for c in df.columns if "tipo" in c.lower() and "manifesta" in c.lower()), None)
        col_sat = next((c for c in df.columns if "satisfeito" in c.lower() or "satisfação" in c.lower()), None)
        col_area = next((c for c in df.columns if c.lower() in ["área", "area", "area responsavel", "área responsável"]), None)
        
        # Busca a coluna de data
        col_data = next((c for c in df.columns if "resposta à pesquisa" in c.lower() or "resposta a pesquisa" in c.lower()), None)
        if not col_data: 
            col_data = next((c for c in df.columns if "data" in c.lower() or "resposta" in c.lower()), None)

        # Monta a tabela limpa
        df_limpo = pd.DataFrame()
        df_limpo["Tipo"] = df[col_tipo] if col_tipo else "Não Informado"
        df_limpo["Satisfacao"] = df[col_sat] if col_sat else "Não Informado"
        df_limpo["Area_Tecnica"] = df[col_area] if col_area else "Não Informado"
        
        if col_data:
            df_limpo["Data"] = pd.to_datetime(df[col_data], errors="coerce", dayfirst=True)
        else:
            df_limpo["Data"] = pd.NaT

        df_limpo = df_limpo.dropna(subset=["Data"])
        df_limpo["mês"] = df_limpo["Data"].dt.to_period("M")
        return df_limpo
    except Exception as e:
        st.error(f"Erro ao processar pesquisa.csv: {e}")
        return pd.DataFrame()

@st.cache_data
def carregar_manifestacoes():
    try:
        # Sem 'skiprows=4' aqui! Lê a planilha direto para não apagar o cabeçalho.
        df = pd.read_csv("ListaManifestacaoAtualizadaa.csv", sep=";", encoding="utf-8-sig", on_bad_lines="skip")
        df.columns = df.columns.str.strip()
        df = limpar_texto(df)

        col_assunto = next((c for c in df.columns if "assunto" in c.lower() and "sub" not in c.lower()), None)
        col_sit = next((c for c in df.columns if "situa" in c.lower()), None)
        col_unidade = next((c for c in df.columns if "área responsável" in c.lower() or "area responsavel" in c.lower()), None)
        
        col_data = next((c for c in df.columns if "abertura" in c.lower()), None)
        if not col_data:
            col_data = next((c for c in df.columns if "data" in c.lower()), None)

        df_limpo = pd.DataFrame()
        df_limpo["Assunto"] = df[col_assunto] if col_assunto else "Não Informado"
        df_limpo["Situacao"] = df[col_sit] if col_sit else "Não Informado"
        df_limpo["Unidade"] = df[col_unidade] if col_unidade else "Não Informado"

        if col_data:
            df_limpo["Data"] = pd.to_datetime(df[col_data], errors="coerce", dayfirst=True)
        else:
            df_limpo["Data"] = pd.NaT

        df_limpo = df_limpo.dropna(subset=["Data"])
        df_limpo["mês"] = df_limpo["Data"].dt.to_period("M")
        return df_limpo
    except Exception as e:
        st.error(f"Erro ao processar ListaManifestacaoAtualizadaa.csv: {e}")
        return pd.DataFrame()

# --- Execução Central ---
df_p = carregar_pesquisa()
df_m = carregar_manifestacoes()

# --- Filtro da Barra Lateral ---
st.sidebar.header("🗓️ Período de Análise")

meses_disponiveis = set()
if not df_m.empty and "mês" in df_m.columns:
    meses_disponiveis.update(df_m["mês"].unique())
if not df_p.empty and "mês" in df_p.columns:
    meses_disponiveis.update(df_p["mês"].unique())

if not meses_disponiveis:
    st.warning("Aguardando carregamento de planilhas com datas válidas...")
    st.stop()

meses_ordenados = sorted(list(meses_disponiveis), reverse=True)
mapa_meses = {m.strftime('%B / %Y').title(): m for m in meses_ordenados}

escolha_meses = st.sidebar.multiselect(
    "Selecione os meses:",
    options=list(mapa_meses.keys()),
    default=list(mapa_meses.keys())[:3] if len(mapa_meses) >= 3 else list(mapa_meses.keys())
)

periodos_selecionados = [mapa_meses[e] for e in escolha_meses]

df_m_f = df_m[df_m["mês"].isin(periodos_selecionados)] if not df_m.empty else df_m
df_p_f = df_p[df_p["mês"].isin(periodos_selecionados)] if not df_p.empty else df_p

# --- Layout do Dashboard ---
st.title("📊 Painel Estratégico | Ouvidoria ANVISA")

tab1, tab2 = st.tabs(["🎯 Pesquisa de Satisfação", "📂 Gestão de Manifestações"])

with tab1:
    st.header("Análise de Satisfação")
    if not df_p_f.empty:
        st.metric("Total de Respostas", len(df_p_f))
        st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            if not df_p_f["Tipo"].eq("Não Informado").all():
                fig_tipo = px.pie(df_p_f, names='Tipo', title="Tipos de Manifestação", hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe)
                st.plotly_chart(fig_tipo, use_container_width=True)
        with col2:
            if not df_p_f["Satisfacao"].eq("Não Informado").all():
                sat_data = df_p_f["Satisfacao"].value_counts().reset_index()
                fig_sat = px.bar(sat_data, x='count', y='Satisfacao', orientation='h', title="Nível de Satisfação", color='Satisfacao')
                st.plotly_chart(fig_sat, use_container_width=True)
        
        st.divider()
        if not df_p_f["Area_Tecnica"].eq("Não Informado").all():
            st.subheader("Volume por Área Técnica (Pesquisa)")
            area_data = df_p_f["Area_Tecnica"].value_counts().reset_index()
            fig_area = px.bar(area_data, x='Area_Tecnica', y='count', text_auto=True, color='Area_Tecnica')
            st.plotly_chart(fig_area, use_container_width=True)
    else:
        st.info("Nenhum dado de pesquisa encontrado para o período selecionado.")

with tab2:
    st.header("Gestão Geral de Demandas")
    if not df_m_f.empty:
        st.metric("Total de Manifestações", len(df_m_f))
        st.divider()
        
        c_a, c_b = st.columns(2)
        with c_a:
            if not df_m_f["Assunto"].eq("Não Informado").all():
                top_10 = df_m_f["Assunto"].value_counts().nlargest(10).reset_index()
                fig_ass = px.bar(top_10, x='count', y='Assunto', orientation='h', title="Top 10 Assuntos Recorrentes")
                st.plotly_chart(fig_ass, use_container_width=True)
        with c_b:
            if not df_m_f["Situacao"].eq("Não Informado").all():
                fig_sit = px.pie(df_m_f, names='Situacao', title="Status das Manifestações", hole=0.4)
                st.plotly_chart(fig_sit, use_container_width=True)
        
        st.divider()
        if not df_m_f["Unidade"].eq("Não Informado").all():
            st.subheader("Distribuição por Unidade Responsável")
            resumo_u = df_m_f["Unidade"].value_counts().reset_index()
            resumo_u.columns = ['Unidade Administrativa', 'Total de Demandas']
            
            # Tabela Final com o Total Geral
            total_geral = pd.DataFrame([['TOTAL GERAL', resumo_u['Total de Demandas'].sum()]], columns=['Unidade Administrativa', 'Total de Demandas'])
            tabela_final = pd.concat([resumo_u, total_geral], ignore_index=True)
            st.dataframe(tabela_final, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma manifestação encontrada para o período selecionado.")
