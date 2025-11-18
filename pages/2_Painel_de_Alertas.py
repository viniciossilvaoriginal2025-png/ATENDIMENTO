import streamlit as st
import pandas as pd
import config # <-- Importa o arquivo de configuração
from streamlit_folium import st_folium 

st.set_page_config(layout="wide")
st.title("🚨 Painel de Alertas e Pendências (SLA Dinâmico)")

# Verifica se o DF PROCESSADO (não filtrado) existe
if 'df_processado' not in st.session_state or st.session_state['df_processado'].empty:
    st.error("Por favor, carregue um arquivo na página 'Visão Geral' primeiro.")
    st.stop()

# Busca o DF PROCESSADO COMPLETO
df_processado = st.session_state['df_processado']

# --- Limpeza de Registros Concluídos na Sessão ---
concluidos_list = st.session_state.get('concluidos_list', [])
if concluidos_list:
    df_processado = df_processado[~df_processado[config.COLUNA_ID_CLIENTE].isin(concluidos_list)]
    st.success(f"✅ {len(concluidos_list)} atendimentos concluídos removidos da lista.")

# ---- CRIA FILTROS PRÓPRIOS PARA ESTA PÁGINA ----
st.sidebar.subheader("Filtros do Painel de Alertas")
df_filtrado_alertas = df_processado.copy() 

cidades_selecionadas = st.sidebar.multiselect(
    f'Filtrar por {config.COLUNA_CIDADE}',
    options=sorted(df_processado[config.COLUNA_CIDADE].dropna().unique()),
    default=[], key='alertas_cidade' 
)
tecnicos_selecionados = []
if config.COLUNA_TECNICO in df_processado.columns:
    tecnicos_selecionados = st.sidebar.multiselect(
        f'Filtrar por {config.COLUNA_TECNICO}',
        options=sorted(df_processado[config.COLUNA_TECNICO].dropna().unique()),
        default=[], key='alertas_tecnico' 
    )
assuntos_selecionados = []
if config.COLUNA_ASSUNTO in df_processado.columns:
    assuntos_selecionados = st.sidebar.multiselect(
        f'Filtrar por {config.COLUNA_ASSUNTO}',
        options=sorted(df_processado[config.COLUNA_ASSUNTO].dropna().unique()),
        default=[], key='alertas_assunto' 
    )

status_selecionados = []
if config.COLUNA_STATUS in df_processado.columns:
    st.sidebar.subheader(f"Filtrar por {config.COLUNA_STATUS}")
    opcoes_status = sorted(df_processado[config.COLUNA_STATUS].dropna().unique())
    for status in opcoes_status:
        # Default: VISITA_AGENDADA
        is_default = (status == "VISITA_AGENDADA")
        if st.sidebar.checkbox(status, value=is_default, key=f"alertas_status_{status}"):
            status_selecionados.append(status)

# --- Aplica os filtros ---
if cidades_selecionadas:
    df_filtrado_alertas = df_filtrado_alertas[df_filtrado_alertas[config.COLUNA_CIDADE].isin(cidades_selecionadas)]
if tecnicos_selecionados and config.COLUNA_TECNICO in df_filtrado_alertas.columns:
    df_filtrado_alertas = df_filtrado_alertas[df_filtrado_alertas[config.COLUNA_TECNICO].isin(tecnicos_selecionados)]
if assuntos_selecionados and config.COLUNA_ASSUNTO in df_filtrado_alertas.columns:
    df_filtrado_alertas = df_filtrado_alertas[df_filtrado_alertas[config.COLUNA_ASSUNTO].isin(assuntos_selecionados)]
if config.COLUNA_STATUS in df_filtrado_alertas.columns:
    df_filtrado_alertas = df_filtrado_alertas[df_filtrado_alertas[config.COLUNA_STATUS].isin(status_selecionados)]

# ---- Lógica da Página ----
df_abertos = df_filtrado_alertas.copy()

if not df_abertos.empty:
    # 1. RECALCULA PRIORIDADE BASEADO NO FILTRO ATUAL (1 a N)
    df_abertos = df_abertos.sort_values(by='Tempo_Decorrido_Segundos', ascending=False).reset_index(drop=True)
    df_abertos.insert(0, 'Prioridade', df_abertos.index + 1) # Recontagem acontece aqui
    
    # 2. APLICA SLA DINÂMICO (Calcula Tempo Restante para cada linha)
    if config.COLUNA_ASSUNTO in df_abertos.columns:
        df_sla_info = df_abertos[config.COLUNA_ASSUNTO].apply(config.obter_sla_segundos).apply(pd.Series)
        df_sla_info.columns = ['SLA_Total_Segundos', 'SLA_Alerta_Segundos']
        # Junta as colunas de SLA ao dataframe
        df_abertos = pd.concat([df_abertos, df_sla_info], axis=1)

        # Calcula status de SLA
        df_abertos['Tempo_Restante_Segundos'] = df_abertos['SLA_Total_Segundos'] - df_abertos['Tempo_Decorrido_Segundos']
        df_abertos['SLA_Estourado'] = df_abertos['Tempo_Restante_Segundos'] < 0
        df_abertos['SLA_Alerta'] = df_abertos.apply(
            lambda row: row['Tempo_Restante_Segundos'] > 0 and 
                        row['Tempo_Restante_Segundos'] <= row['SLA_Alerta_Segundos'], axis=1
        )
    
    # Coluna para o seletor
    df_abertos['Ação'] = 'Aberto'

if df_abertos.empty:
    st.success("🎉 Nenhum chamado encontrado para os filtros atuais!")
else:
    # ---- KPIs ----
    st.subheader("KPIs dos Chamados Selecionados")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Chamados", len(df_abertos))
    col2.metric("Fora do Prazo", f"{df_abertos['SLA_Estourado'].sum()} 🚨")
    col3.metric("Em Alerta", f"{df_abertos['SLA_Alerta'].sum()} ⚠️")

    # ---- Mapa de Alertas ----
    st.subheader("Mapa de Chamados (Numeração = Prioridade)")
    if config.COLUNA_LATITUDE in df_abertos.columns:
        df_mapa_alertas = df_abertos.dropna(subset=[config.COLUNA_LATITUDE, config.COLUNA_LONGITUDE])
        if df_mapa_alertas.empty:
            st.info("Nenhum chamado com coordenadas válidas.")
        else:
            mapa_folium = config.criar_mapa_folium(df_mapa_alertas)
            st_folium(mapa_folium, use_container_width=True, height=400, returned_objects=[])

    # ---- Tabela de Chamados ----
    st.subheader("Lista de Chamados")
    
    # Prepara exibição
    df_display = df_abertos.copy()
    df_display['Data Abertura'] = df_display[config.COLUNA_ABERTURA].dt.strftime('%d/%m/%y %H:%M') 
    df_display['Tempo Aberto'] = df_display['Tempo_Decorrido_Segundos'].apply(config.formatar_hms)
    df_display['Restante SLA'] = df_display['Tempo_Restante_Segundos'].apply(config.formatar_hms)

    colunas_finais = [
        'Prioridade', config.COLUNA_ID_CLIENTE, config.COLUNA_NOME_CLIENTE, config.COLUNA_ASSUNTO, 
        config.COLUNA_STATUS, 'Data Abertura', 'Tempo Aberto', 'Restante SLA', 'Ação'
    ]
    if config.COLUNA_TECNICO in df_display.columns:
        colunas_finais.insert(5, config.COLUNA_TECNICO) 

    # Filtra apenas colunas que existem
    colunas_reais = [c for c in colunas_finais if c in df_display.columns]

    editor_key = 'action_editor_alerts'
    st.data_editor(
        df_display[colunas_reais],
        column_config={
            "Prioridade": st.column_config.Column("Priori.", width="small"),
            "Ação": st.column_config.SelectboxColumn(
                "Ação", width="small", options=['Aberto', 'Concluído'], required=True
            )
        },
        hide_index=True,
        use_container_width=True,
        key=editor_key
    )
    
    # Lógica de Conclusão
    if st.session_state.get(editor_key, False):
        edited = st.session_state[editor_key]
        if edited.get('edited_rows'):
            for idx, row in edited['edited_rows'].items():
                if row.get('Ação') == 'Concluído':
                    c_id = df_display.iloc[idx][config.COLUNA_ID_CLIENTE]
                    if c_id not in st.session_state.get('concluidos_list', []):
                        st.session_state.setdefault('concluidos_list', []).append(c_id)
                        st.experimental_rerun()
