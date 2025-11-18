import streamlit as st
import pandas as pd
import config # <-- Importa o arquivo de configuração
from streamlit_folium import st_folium # <-- Importa o componente Folium

st.set_page_config(layout="wide")
st.title("🚨 Painel de Alertas e Pendências (SLA Dinâmico)")

# Verifica se o DF PROCESSADO (não filtrado) existe
if 'df_processado' not in st.session_state or st.session_state['df_processado'].empty:
    st.error("Por favor, carregue um arquivo na página 'Visão Geral' primeiro.")
    st.stop()

# Busca o DF PROCESSADO COMPLETO
df_processado = st.session_state['df_processado']

# --- Limpeza de Registros Concluídos na Sessão ---
# Filtra o dataframe principal removendo os IDs já marcados como concluídos
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
    default=[],
    key='alertas_cidade' 
)
tecnicos_selecionados = []
if config.COLUNA_TECNICO in df_processado.columns:
    tecnicos_selecionados = st.sidebar.multiselect(
        f'Filtrar por {config.COLUNA_TECNICO}',
        options=sorted(df_processado[config.COLUNA_TECNICO].dropna().unique()),
        default=[],
        key='alertas_tecnico' 
    )
assuntos_selecionados = []
if config.COLUNA_ASSUNTO in df_processado.columns:
    assuntos_selecionados = st.sidebar.multiselect(
        f'Filtrar por {config.COLUNA_ASSUNTO}',
        options=sorted(df_processado[config.COLUNA_ASSUNTO].dropna().unique()),
        default=[],
        key='alertas_assunto' 
    )

# --- Filtro de Status com Checkbox (Flags) ---
status_selecionados = []
if config.COLUNA_STATUS in df_processado.columns:
    st.sidebar.subheader(f"Filtrar por {config.COLUNA_STATUS}")
    opcoes_status = sorted(df_processado[config.COLUNA_STATUS].dropna().unique())
    
    for status in opcoes_status:
        is_default = (status == config.STATUS_ABERTOS[0]) # Default só para o primeiro status da lista
        if st.sidebar.checkbox(status, value=is_default, key=f"alertas_status_{status}"):
            status_selecionados.append(status)

# --- Aplica os filtros desta página ---
if cidades_selecionadas:
    df_filtrado_alertas = df_filtrado_alertas[df_filtrado_alertas[config.COLUNA_CIDADE].isin(cidades_selecionadas)]
if tecnicos_selecionados and config.COLUNA_TECNICO in df_filtrado_alertas.columns:
    df_filtrado_alertas = df_filtrado_alertas[df_filtrado_alertas[config.COLUNA_TECNICO].isin(tecnicos_selecionados)]
if assuntos_selecionados and config.COLUNA_ASSUNTO in df_filtrado_alertas.columns:
    df_filtrado_alertas = df_filtrado_alertas[df_filtrado_alertas[config.COLUNA_ASSUNTO].isin(assuntos_selecionados)]
if config.COLUNA_STATUS in df_filtrado_alertas.columns:
    df_filtrado_alertas = df_filtrado_alertas[df_filtrado_alertas[config.COLUNA_STATUS].isin(status_selecionados)]

# ---- Início da Lógica da Página de Alertas ----

df_abertos = df_filtrado_alertas.copy()

if not df_abertos.empty:
    # 1. Cálculos de Prioridade
    df_abertos = df_abertos.sort_values(by='Tempo_Decorrido_Segundos', ascending=False).reset_index(drop=True)
    df_abertos.insert(0, 'Prioridade', df_abertos.index + 1)
    
    # Cálculos de SLA
    df_abertos['Tempo_Restante_Segundos'] = df_abertos['SLA_Total_Segundos'] - df_abertos['Tempo_Decorrido_Segundos']
    df_abertos['SLA_Estourado'] = df_abertos['Tempo_Restante_Segundos'] < 0
    df_abertos['SLA_Alerta'] = df_abertos.apply(
        lambda row: row['Tempo_Restante_Segundos'] > 0 and 
                    row['Tempo_Restante_Segundos'] <= row['SLA_Alerta_Segundos'], axis=1
    )
    
    # Adiciona a coluna para o seletor de ação
    df_abertos['Ação'] = 'Aberto' # Coluna para o seletor de ação


if df_abertos.empty:
    st.success("🎉 Nenhum chamado encontrado para os filtros atuais!")
else:
    # ---- KPIs Principais ----
    st.subheader("KPIs dos Chamados Selecionados")
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    
    total_abertos = len(df_abertos)
    total_fora_sla = df_abertos['SLA_Estourado'].sum()
    total_em_alerta = df_abertos['SLA_Alerta'].sum()
    
    col_kpi1.metric("Total de Chamados na Lista", total_abertos)
    col_kpi2.metric("Total Fora do SLA (Estourado)", f"{total_fora_sla} 🚨")
    col_kpi3.metric("Total em Alerta (Regra de 4h)", f"{total_em_alerta} ⚠️")

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
    
    # ---- Mapa de Alertas ----
    st.subheader("Mapa de Chamados Pendentes")
    if config.COLUNA_LATITUDE in df_abertos.columns and config.COLUNA_LONGITUDE in df_abertos.columns:
        df_mapa_alertas = df_abertos.dropna(subset=[config.COLUNA_LATITUDE, config.COLUNA_LONGITUDE])
        if df_mapa_alertas.empty:
            st.info("Nenhum chamado pendente com coordenadas válidas encontrado.")
        else:
            mapa_folium = config.criar_mapa_folium(df_mapa_alertas)
            st_folium(mapa_folium, use_container_width=True, height=400, returned_objects=[])
    else:
        st.warning("Colunas 'latitude' ou 'longitude' não encontradas. O mapa não pode ser exibido.")

    # ---- NOVO: Tabela de Chamados com Ação ----
    st.subheader("Lista de Chamados (Ordenado por Prioridade)")
    
    # Cria os valores formatados para exibição
    df_display = df_abertos.copy()
    df_display['Data Abertura'] = df_display[config.COLUNA_ABERTURA].dt.strftime('%d/%m/%y %H:%M') 
    df_display['Tempo Aberto (H:M:S)'] = df_display['Tempo_Decorrido_Segundos'].apply(config.formatar_hms)
    df_display['Tempo Restante SLA (H:M:S)'] = df_display['Tempo_Restante_Segundos'].apply(config.formatar_hms)
    
    # Colunas que serão configuradas e exibidas
    colunas_finais = [
        'Prioridade', config.COLUNA_ID_CLIENTE, config.COLUNA_NOME_CLIENTE, config.COLUNA_ASSUNTO, 
        config.COLUNA_STATUS, 'Data Abertura', 'Tempo Aberto (H:M:S)', 'Tempo Restante SLA (H:M:S)', 'Ação' # <--- ADICIONADO AQUI
    ]
    if config.COLUNA_TECNICO in df_display.columns:
        colunas_finais.insert(5, config.COLUNA_TECNICO) 
    
    colunas_finais = [col for col in colunas_finais if col in df_display.columns or col in ['Prioridade', 'Data Abertura', 'Tempo Aberto (H:M:S)', 'Tempo Restante SLA (H:M:S)', 'Ação']]

    # 1. Renderiza a lista usando st.data_editor para ter o botão na linha
    editor_key = 'action_editor' # Chave explícita para o data_editor
    
    st.data_editor(
        df_display[colunas_finais],
        column_config={
            "Ação": st.column_config.SelectboxColumn(
                "Concluir Atendimento?",
                help="Selecione 'Concluído' para remover o atendimento da lista.",
                width="small",
                options=['Aberto', 'Concluído'],
                required=True,
            ),
            # Corrigindo a exibição das outras colunas
            "Prioridade": st.column_config.Column("Priori.", width="small")
        },
        hide_index=True,
        use_container_width=True,
        key=editor_key
    )
    
    # 2. Lógica para remover os concluídos (Esta é a parte que registra a ação)
    if st.session_state.get(editor_key, False):
        edited_data = st.session_state[editor_key]
        if edited_data.get('edited_rows'):
            for index, row in edited_data['edited_rows'].items():
                if row.get('Ação') == 'Concluído':
                    # Pega o ID do cliente da linha original
                    cliente_id = df_display.iloc[index][config.COLUNA_ID_CLIENTE]
                    
                    if cliente_id not in st.session_state.get('concluidos_list', []):
                        st.session_state.setdefault('concluidos_list', []).append(cliente_id)
                        st.experimental_rerun() # Força a recarga para remover o item
