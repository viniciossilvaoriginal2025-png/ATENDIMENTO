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
# Filtra o dataframe principal removendo os IDs já marcados como concluídos
concluidos_list = st.session_state.get('concluidos_list', [])
if concluidos_list:
    df_processado = df_processado[~df_processado[config.COLUNA_ID_CLIENTE].isin(concluidos_list)]
    st.success(f"{len(concluidos_list)} atendimentos concluídos removidos da lista.")

# ---- CRIA FILTROS PRÓPRIOS PARA ESTA PÁGINA ----
st.sidebar.subheader("Filtros do Painel de Alertas")
df_filtrado_alertas = df_processado.copy() 
# ... (código dos filtros, removido por brevidade, mas está na versão anterior) ...

cidades_selecionadas = st.sidebar.multiselect(
    f'Filtrar por {config.COLUNA_CIDADE}',
    options=sorted(df_processado[config.COLUNA_CIDADE].dropna().unique()),
    default=[], key='alertas_cidade' 
)
# ... (demais multiselects) ...
tecnicos_selecionados = [] # [.. filtro técnico ..]
assuntos_selecionados = [] # [.. filtro assunto ..]
status_selecionados = [] # [.. filtro status ..]

# ... (Lógica de Aplicação dos Filtros) ...

if cidades_selecionadas:
    df_filtrado_alertas = df_filtrado_alertas[df_filtrado_alertas[config.COLUNA_CIDADE].isin(cidades_selecionadas)]
# ... (resto da aplicação dos filtros) ...
if config.COLUNA_STATUS in df_filtrado_alertas.columns:
    df_filtrado_alertas = df_filtrado_alertas[df_filtrado_alertas[config.COLUNA_STATUS].isin(status_selecionados)]
# --- FIM DOS FILTROS ---


df_abertos = df_filtrado_alertas.copy()

if not df_abertos.empty:
    # Cálculos de Prioridade
    df_abertos = df_abertos.sort_values(by='Tempo_Decorrido_Segundos', ascending=False).reset_index(drop=True)
    df_abertos.insert(0, 'Prioridade', df_abertos.index + 1)
    
    df_abertos['Tempo_Restante_Segundos'] = df_abertos['SLA_Total_Segundos'] - df_abertos['Tempo_Decorrido_Segundos']
    df_abertos['SLA_Estourado'] = df_abertos['Tempo_Restante_Segundos'] < 0
    df_abertos['SLA_Alerta'] = df_abertos.apply(
        lambda row: row['Tempo_Restante_Segundos'] > 0 and 
                    row['Tempo_Restante_Segundos'] <= row['SLA_Alerta_Segundos'], axis=1
    )
    
    # Adiciona a coluna para o botão de ação (Status Padrão)
    df_abertos['Ação'] = 'Aberto'


if df_abertos.empty:
    st.success("🎉 Nenhum chamado encontrado para os filtros atuais!")
else:
    # ... (KPIs, Mapas e Alertas de Hora - permanecem iguais) ...

    # ---- NOVO: Tabela de Chamados com Ação ----
    st.subheader("Lista de Chamados (Ordenado por Prioridade)")
    
    # Colunas de exibição
    colunas_finais = [
        'Prioridade', config.COLUNA_ID_CLIENTE, config.COLUNA_NOME_CLIENTE, config.COLUNA_ASSUNTO, 
        config.COLUNA_STATUS, 'Data Abertura', 'Tempo Aberto (H:M:S)', 'Tempo Restante SLA (H:M:S)', 'Ação'
    ]
    if config.COLUNA_TECNICO in df_abertos.columns:
        colunas_finais.insert(5, config.COLUNA_TECNICO) 
    
    # Cria os valores formatados para exibição
    df_display = df_abertos.copy()
    df_display['Data Abertura'] = df_display[config.COLUNA_ABERTURA].dt.strftime('%d/%m/%y %H:%M') 
    df_display['Tempo Aberto (H:M:S)'] = df_display['Tempo_Decorrido_Segundos'].apply(config.formatar_hms)
    df_display['Tempo Restante SLA (H:M:S)'] = df_display['Tempo_Restante_Segundos'].apply(config.formatar_hms)

    # Renderiza a lista usando st.data_editor para ter o botão na linha
    st.data_editor(
        df_display[colunas_finais],
        column_config={
            "Ação": st.column_config.SelectboxColumn(
                "Concluir Atendimento?",
                help="Selecione 'Concluído' para remover o atendimento da lista.",
                width="small",
                options=['Aberto', 'Concluído'],
                required=True,
            )
        },
        hide_index=True,
        use_container_width=True,
        # Aplica a cor na linha (usando df_abertos como base)
        column_order=colunas_finais
    )
    
    # Lógica para remover os concluídos (Esta é a parte que registra a ação)
    if st.session_state.get('data_editor', False):
        for index, row in st.session_state['data_editor']['edited_rows'].items():
            if row.get('Ação') == 'Concluído':
                cliente_id = df_display.iloc[index][config.COLUNA_ID_CLIENTE]
                if cliente_id not in st.session_state.get('concluidos_list', []):
                    st.session_state.setdefault('concluidos_list', []).append(cliente_id)
                    st.experimental_rerun() # Força a recarga para remover o item


    # ... (Restante do código: st.subheader, Mapa, etc. ) ...
