import streamlit as st
import pandas as pd
import config # <-- Importa o arquivo de configuração

st.set_page_config(layout="wide")
st.title("🚨 Painel de Alertas e Pendências (SLA 24h)")

# --- MUDANÇA AQUI ---
# 1. Verifica se o DF PROCESSADO (não filtrado) existe
if 'df_processado' not in st.session_state or st.session_state['df_processado'].empty:
    st.error("Por favor, carregue um arquivo na página 'Visão Geral' primeiro.")
    st.stop()

# 2. Busca o DF PROCESSADO COMPLETO
df_processado = st.session_state['df_processado']

# ---- 3. (NOVO) CRIA FILTROS PRÓPRIOS PARA ESTA PÁGINA ----
st.sidebar.subheader("Filtros do Painel de Alertas")
df_filtrado_alertas = df_processado.copy() # Começa com todos os dados

cidades_selecionadas = st.sidebar.multiselect(
    f'Filtrar por {config.COLUNA_CIDADE}',
    options=sorted(df_processado[config.COLUNA_CIDADE].dropna().unique()),
    default=[],
    key='alertas_cidade' # Chave única para este filtro
)
tecnicos_selecionados = []
if config.COLUNA_TECNICO in df_processado.columns:
    tecnicos_selecionados = st.sidebar.multiselect(
        f'Filtrar por {config.COLUNA_TECNICO}',
        options=sorted(df_processado[config.COLUNA_TECNICO].dropna().unique()),
        default=[],
        key='alertas_tecnico' # Chave única
    )
assuntos_selecionados = []
if config.COLUNA_ASSUNTO in df_processado.columns:
    assuntos_selecionados = st.sidebar.multiselect(
        f'Filtrar por {config.COLUNA_ASSUNTO}',
        options=sorted(df_processado[config.COLUNA_ASSUNTO].dropna().unique()),
        default=[],
        key='alertas_assunto' # Chave única
    )
# Nota: Não adicionamos filtro de Status aqui, pois esta página já
# filtra automaticamente pela lista STATUS_ABERTOS do config.py

# --- 4. (NOVO) Aplica os filtros desta página ---
if cidades_selecionadas:
    df_filtrado_alertas = df_filtrado_alertas[df_filtrado_alertas[config.COLUNA_CIDADE].isin(cidades_selecionadas)]
if tecnicos_selecionados and config.COLUNA_TECNICO in df_filtrado_alertas.columns:
    df_filtrado_alertas = df_filtrado_alertas[df_filtrado_alertas[config.COLUNA_TECNICO].isin(tecnicos_selecionados)]
if assuntos_selecionados and config.COLUNA_ASSUNTO in df_filtrado_alertas.columns:
    df_filtrado_alertas = df_filtrado_alertas[df_filtrado_alertas[config.COLUNA_ASSUNTO].isin(assuntos_selecionados)]


# ---- Início da Lógica da Página de Alertas ----

st.info(f"Focando em status: {', '.join(config.STATUS_ABERTOS)}.")

# --- MUDANÇA AQUI ---
# 5. Usa o dataframe filtrado DESTA PÁGINA (df_filtrado_alertas)
df_abertos = df_filtrado_alertas[df_filtrado_alertas[config.COLUNA_STATUS].isin(config.STATUS_ABERTOS)].copy()

if not df_abertos.empty:
    # Cálculos de Alerta e Tempo Restante
    df_abertos['Tempo_Restante_Segundos'] = config.SLA_SEGUNDOS - df_abertos['Tempo_Decorrido_Segundos']
    df_abertos['SLA_Estourado'] = df_abertos['Tempo_Restante_Segundos'] < 0
    df_abertos['SLA_Alerta'] = df_abertos['Tempo_Restante_Segundos'].between(0, config.ALERTA_SEGUNDOS) # Alerta nas próximas 4h
else:
    df_abertos['Tempo_Restante_Segundos'] = pd.NaT
    df_abertos['SLA_Estourado'] = False
    df_abertos['SLA_Alerta'] = False

if df_abertos.empty:
    st.success("🎉 Nenhum chamado pendente para a seleção atual!")
else:
    # ---- KPIs Principais ----
    st.subheader("KPIs de Pendências")
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    
    total_abertos = len(df_abertos)
    total_fora_sla = df_abertos['SLA_Estourado'].sum()
    total_em_alerta = df_abertos['SLA_Alerta'].sum()
    
    col_kpi1.metric("Total de Chamados Pendentes", total_abertos)
    col_kpi2.metric("Total Fora do SLA (Estourado)", f"{total_fora_sla} 🚨")
    col_kpi3.metric("Total em Alerta (Próx. 4h)", f"{total_em_alerta} ⚠️")

    # ---- KPIs de Alerta por Hora de Abertura (19h, 20h, 21h, 22h) ----
    st.subheader("Monitoramento de Tempo Aberto (Próximo do SLA)")
    col_alerta1, col_alerta2, col_alerta3, col_alerta4 = st.columns(4)
    
    h19, h20, h21, h22, h23 = 19*3600, 20*3600, 21*3600, 22*3600, 23*3600

    abertos_19h = df_abertos[df_abertos['Tempo_Decorrido_Segundos'].between(h19, h20, inclusive='left')].shape[0]
    abertos_20h = df_abertos[df_abertos['Tempo_Decorrido_Segundos'].between(h20, h21, inclusive='left')].shape[0]
    abertos_21h = df_abertos[df_abertos['Tempo_Decorrido_Segundos'].between(h21, h22, inclusive='left')].shape[0]
    abertos_22h = df_abertos[df_abertos['Tempo_Decorrido_Segundos'].between(h22, h23, inclusive='left')].shape[0]

    col_alerta1.metric("Abertos há 19h", f"{abertos_19h} 🟡")
    col_alerta2.metric("Abertos há 20h", f"{abertos_20h} 🟠")
    col_alerta3.metric("Abertos há 21h", f"{abertos_21h} 🔴")
    col_alerta4.metric("Abertos há 22h", f"{abertos_22h} 🚨")
    
    # ---- Tabela de Chamados Pendentes ----
    st.subheader("Lista de Chamados Pendentes (Ordenado por mais antigo)")
    
    colunas_para_mostrar = [
        config.COLUNA_ID_CLIENTE, config.COLUNA_NOME_CLIENTE, config.COLUNA_ASSUNTO,
        config.COLUNA_STATUS, config.COLUNA_ABERTURA,
        'Tempo_Decorrido_Segundos', 'Tempo_Restante_Segundos', 
        'SLA_Estourado', 'SLA_Alerta'
    ]
    if config.COLUNA_TECNICO in df_abertos.columns:
        colunas_para_mostrar.insert(4, config.COLUNA_TECNICO) 
    
    colunas_para_mostrar = [col for col in colunas_para_mostrar if col in df_abertos.columns]
    df_display = df_abertos[colunas_para_mostrar].sort_values(by='Tempo_Decorrido_Segundos', ascending=False)
    
    df_display['Data Abertura'] = df_display[config.COLUNA_ABERTURA].dt.strftime('%d/%m/%y %H:%M') 
    df_display['Tempo Aberto (H:M:S)'] = df_display['Tempo_Decorrido_Segundos'].apply(config.formatar_hms)
    df_display['Tempo Restante SLA (H:M:S)'] = df_display['Tempo_Restante_Segundos'].apply(config.formatar_hms)
    
    colunas_finais = [
        config.COLUNA_ID_CLIENTE, config.COLUNA_NOME_CLIENTE, config.COLUNA_ASSUNTO, 
        config.COLUNA_STATUS, 'Data Abertura', 'Tempo Aberto (H:M:S)', 'Tempo Restante SLA (H:M:S)'
    ]
    if config.COLUNA_TECNICO in df_display.columns:
        colunas_finais.insert(4, config.COLUNA_TECNICO) 
    
    colunas_finais = [col for col in colunas_finais if col in df_display.columns or col in ['Data Abertura', 'Tempo Aberto (H:M:S)', 'Tempo Restante SLA (H:M:S)']]

    colunas_para_esconder = [
        'Tempo_Decorrido_Segundos', 'Tempo_Restante_Segundos', 
        'SLA_Estourado', 'SLA_Alerta'
    ]
    colunas_para_esconder = [col for col in colunas_para_esconder if col in df_display.columns]

    st.dataframe(
        df_display.style.apply(config.highlight_sla, axis=1) # Aplica a cor
                         .hide(axis="columns", subset=colunas_para_esconder), # Esconde colunas
        use_container_width=True,
        column_order=colunas_finais # Define a ordem
    )
