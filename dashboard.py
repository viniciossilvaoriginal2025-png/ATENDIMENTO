import streamlit as st
import pandas as pd
import plotly.express as px
import openpyxl
from datetime import datetime
import config # Importa o arquivo de configuração

# Configuração da página
st.set_page_config(layout="wide")

# ---- Função de Carregamento de Dados ----
@st.cache_data
def carregar_e_processar(arquivo_upado):
    try:
        # Lê os bytes do arquivo upado
        df = pd.read_excel(arquivo_upado.getvalue(), header=1) 
    except Exception as e:
        st.error(f"Erro ao ler o arquivo Excel (XLSX): {e}")
        return None

    colunas_data = [config.COLUNA_ABERTURA, config.COLUNA_ENCAMINHAMENTO, config.COLUNA_AGENDAMENTO]
    for col in colunas_data:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
        
    df['Tempo_Encaminhamento_Segundos'] = pd.NaT 
    if config.COLUNA_ABERTURA in df.columns and config.COLUNA_ENCAMINHAMENTO in df.columns:
        validos = df[[config.COLUNA_ABERTURA, config.COLUNA_ENCAMINHAMENTO]].dropna()
        if not validos.empty:
            df['Tempo_Encaminhamento_Segundos'] = (validos[config.COLUNA_ENCAMINHAMENTO] - validos[config.COLUNA_ABERTURA]).dt.total_seconds()
    
    df['Tempo_Agendamento_Segundos'] = pd.NaT
    if config.COLUNA_ABERTURA in df.columns and config.COLUNA_AGENDAMENTO in df.columns:
        validos = df[[config.COLUNA_ABERTURA, config.COLUNA_AGENDAMENTO]].dropna()
        if not validos.empty:
            df['Tempo_Agendamento_Segundos'] = (validos[config.COLUNA_AGENDAMENTO] - validos[config.COLUNA_ABERTURA]).dt.total_seconds()

    return df

# ---- Início da Interface do App ----
st.title("📊 Visão Geral dos Atendimentos")

st.sidebar.header("Controles do Dashboard")
uploaded_file = st.sidebar.file_uploader("Faça o upload do seu arquivo (XLSX)", type=["xlsx"])

# Botão para limpar o cache e carregar um novo arquivo
if st.sidebar.button("Limpar Dados e Recarregar"):
    st.session_state.clear()
    st.experimental_rerun()

# --- LÓGICA DE CARREGAMENTO CORRIGIDA ---
df = None # Inicializa df
if uploaded_file is not None:
    df = carregar_e_processar(uploaded_file)
    if df is not None:
        st.session_state['df_original'] = df
        st.sidebar.success("Arquivo carregado!")
        
elif 'df_original' in st.session_state:
    df = st.session_state['df_original']
else:
    st.info("Por favor, faça o upload de um arquivo XLSX na barra lateral para iniciar a análise.")
    st.stop() 

if df is None:
    st.error("Erro ao carregar o dataframe.")
    st.stop()

# ---- CÁLCULO "AO VIVO": Tempo Decorrido (em Segundos) ----
df_processado = df.copy()
if config.COLUNA_ABERTURA in df_processado.columns:
    agora = pd.Timestamp.now()
    df_processado['Tempo_Decorrido_Segundos'] = (agora - df_processado[config.COLUNA_ABERTURA]).dt.total_seconds()
else:
    df_processado['Tempo_Decorrido_Segundos'] = pd.NaT

st.session_state['df_processado'] = df_processado

# Verifica colunas essenciais
colunas_essenciais = [config.COLUNA_CIDADE, config.COLUNA_STATUS, config.COLUNA_ABERTURA, config.COLUNA_ID_CLIENTE, config.COLUNA_NOME_CLIENTE]
colunas_faltando = [col for col in colunas_essenciais if col not in df_processado.columns]

if colunas_faltando:
    st.error(f"Erro: O arquivo foi lido, mas algumas colunas essenciais não foram encontradas. Verifique os nomes na Linha 2.")
    st.error(f"Colunas Faltando: {', '.join(colunas_faltando)}")
    st.write("Colunas encontradas no arquivo:", df_processado.columns.tolist())
    st.stop()

# ---- Filtros na Barra Lateral (Para esta página) ----
st.sidebar.subheader("Filtros da Visão Geral")
df_filtrado = df_processado.copy() 

cidades_selecionadas = st.sidebar.multiselect(
    f'Filtrar por {config.COLUNA_CIDADE}',
    options=sorted(df[config.COLUNA_CIDADE].dropna().unique()),
    default=[],
    key='main_cidade' 
)
tecnicos_selecionados = []
if config.COLUNA_TECNICO in df.columns:
    tecnicos_selecionados = st.sidebar.multiselect(
        f'Filtrar por {config.COLUNA_TECNICO}',
        options=sorted(df[config.COLUNA_TECNICO].dropna().unique()),
        default=[],
        key='main_tecnico' 
    )
assuntos_selecionados = []
if config.COLUNA_ASSUNTO in df.columns:
    assuntos_selecionados = st.sidebar.multiselect(
        f'Filtrar por {config.COLUNA_ASSUNTO}',
        options=sorted(df[config.COLUNA_ASSUNTO].dropna().unique()),
        default=[],
        key='main_assunto' 
    )

# --- MUDANÇA AQUI: Filtro de Status trocado para Checkbox ---
status_selecionados = []
if config.COLUNA_STATUS in df.columns:
    st.sidebar.subheader(f"Filtrar por {config.COLUNA_STATUS}")
    opcoes_status = sorted(df[config.COLUNA_STATUS].dropna().unique())
    
    # Cria uma "flag" (checkbox) para cada status
    for status in opcoes_status:
        # Default=True significa que todos vêm marcados
        if st.sidebar.checkbox(status, value=True, key=f"main_status_{status}"):
            status_selecionados.append(status)
# --- FIM DA MUDANÇA ---


# --- Lógica de Filtro ---
if cidades_selecionadas:
    df_filtrado = df_filtrado[df_filtrado[config.COLUNA_CIDADE].isin(cidades_selecionadas)]
if tecnicos_selecionados and config.COLUNA_TECNICO in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado[config.COLUNA_TECNICO].isin(tecnicos_selecionados)]
if assuntos_selecionados and config.COLUNA_ASSUNTO in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado[config.COLUNA_ASSUNTO].isin(assuntos_selecionados)]

# --- MUDANÇA AQUI: Lógica de filtro para Checkbox ---
# Se o usuário desmarcar todas as caixas, a lista fica vazia e o filtro mostra tudo.
# Para evitar isso, aplicamos o filtro se *alguma* seleção (mesmo que todas) foi feita.
if config.COLUNA_STATUS in df_filtrado.columns:
    # O filtro agora é sempre aplicado. Se o usuário desmarcar tudo, não verá nada.
    df_filtrado = df_filtrado[df_filtrado[config.COLUNA_STATUS].isin(status_selecionados)]
# --- FIM DA MUDANÇA ---

# (Não precisamos salvar o df_filtrado no session_state)

# ---- SEÇÃO 1: Métricas Gerais (Agendamento / Encaminhamento) ----
st.header("Métricas Gerais de Tempo (Baseado nos Filtros)")

mediana_agendamento_seg = df_filtrado['Tempo_Agendamento_Segundos'].dropna().median()
media_agendamento_seg = df_filtrado['Tempo_Agendamento_Segundos'].dropna().mean()
mediana_encaminhamento_seg = df_filtrado['Tempo_Encaminhamento_Segundos'].dropna().median()
media_encaminhamento_seg = df_filtrado['Tempo_Encaminhamento_Segundos'].dropna().mean()

col1, col2 = st.columns(2)
with col1:
    st.subheader("Abertura até Agendamento (AD)")
    st.metric(label="Tempo Médio (H:M:S)", value=config.formatar_hms(media_agendamento_seg))
    st.metric(label="Tempo Mediano (H:M:S)", value=config.formatar_hms(mediana_agendamento_seg))
with col2:
    st.subheader("Abertura até Encaminhamento (X)")
    st.metric(label="Tempo Médio (H:M:S)", value=config.formatar_hms(media_encaminhamento_seg))
    st.metric(label="Tempo Mediano (H:M:S)", value=config.formatar_hms(mediana_encaminhamento_seg))

st.markdown("---")

# ---- SEÇÃO 2: Análises Gerais e Lista Resumida ----
st.header("Análises Gerais das Categorias (Baseado nos Filtros)")

col_graf1, col_graf2 = st.columns(2)
with col_graf1:
    if config.COLUNA_CIDADE in df_filtrado.columns:
        st.subheader(f"Chamados por {config.COLUNA_CIDADE} (Top 10)")
        top_cidades = df_filtrado[config.COLUNA_CIDADE].value_counts().nlargest(10).reset_index()
        fig_cidade = px.bar(top_cidades, x='count', y=config.COLUNA_CIDADE, orientation='h', 
                            title=f"Top 10 Cidades", text_auto=True)
        fig_cidade.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_cidade, use_container_width=True)
    if config.COLUNA_ASSUNTO in df_filtrado.columns:
        st.subheader(f"Chamados por {config.COLUNA_ASSUNTO} (Top 10)")
        top_assuntos = df_filtrado[config.COLUNA_ASSUNTO].value_counts().nlargest(10).reset_index()
        fig_assunto = px.bar(top_assuntos, x='count', y=config.COLUNA_ASSUNTO, orientation='h', 
                             title=f"Top 10 Assuntos", text_auto=True)
        fig_assunto.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_assunto, use_container_width=True)
with col_graf2:
    if config.COLUNA_TECNICO in df_filtrado.columns:
        st.subheader(f"Chamados por {config.COLUNA_TECNICO} (Top 10)")
        top_tecnicos = df_filtrado[config.COLUNA_TECNICO].value_counts().nlargest(10).reset_index()
        fig_tecnico = px.bar(top_tecnicos, x='count', y=config.COLUNA_TECNICO, orientation='h', 
                             title=f"Top 10 Técnicos", text_auto=True)
        fig_tecnico.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_tecnico, use_container_width=True)
    if config.COLUNA_STATUS in df_filtrado.columns:
        st.subheader(f"Chamados por {config.COLUNA_STATUS}")
        status_counts = df_filtrado[config.COLUNA_STATUS].value_counts().reset_index()
        fig_status = px.pie(status_counts, names=config.COLUNA_STATUS, values='count', 
                            title="Distribuição de Status")
        st.plotly_chart(fig_status, use_container_width=True)

# ---- Lista Resumida ----
st.markdown("---")
st.subheader("Lista Resumida (Todos os Chamados nos Filtros)")

colunas_lista_all = [
    config.COLUNA_ID_CLIENTE, config.COLUNA_CIDADE, config.COLUNA_ASSUNTO, 
    config.COLUNA_STATUS, config.COLUNA_ABERTURA, config.COLUNA_AGENDAMENTO,
    'Tempo_Decorrido_Segundos'
]
if config.COLUNA_TECNICO in df_filtrado.columns:
    colunas_lista_all.insert(4, config.COLUNA_TECNICO) 
colunas_lista_all = [col for col in colunas_lista_all if col in df_filtrado.columns]

df_display_all = df_filtrado[colunas_lista_all].sort_values(by='Tempo_Decorrido_Segundos', ascending=False).copy()

df_display_all['Data Abertura'] = df_display_all[config.COLUNA_ABERTURA].dt.strftime('%d/%m/%y %H:%M')
df_display_all['Data Agendamento'] = df_display_all[config.COLUNA_AGENDAMENTO].dt.strftime('%d/%m/%y %H:%M')
df_display_all['Tempo Aberto (H:M:S)'] = df_display_all['Tempo_Decorrido_Segundos'].apply(config.formatar_hms)

colunas_finais_all = [
    config.COLUNA_ID_CLIENTE, config.COLUNA_CIDADE, config.COLUNA_ASSUNTO, 
    config.COLUNA_STATUS, 'Data Abertura', 'Data Agendamento', 'Tempo Aberto (H:M:S)'
]
if config.COLUNA_TECNICO in df_display_all.columns:
    colunas_finais_all.insert(4, config.COLUNA_TECNICO) 

st.dataframe(df_display_all[colunas_finais_all], use_container_width=True)

with st.expander("Ver dados filtrados completos"):
    st.dataframe(df_filtrado)
