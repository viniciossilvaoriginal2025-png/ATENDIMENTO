import streamlit as st
import pandas as pd
import config # <-- Importa o arquivo de configuração
from streamlit_folium import st_folium # <-- Importa o componente Folium
from datetime import datetime

st.set_page_config(layout="wide")
st.title("🚨 Painel de Alertas e Pendências (SLA Dinâmico)")

# --- Inicialização de Variáveis ---
editor_key = 'action_editor' 

# Verifica se o DF PROCESSADO existe
if 'df_processado' not in st.session_state or st.session_state['df_processado'].empty:
    st.error("Por favor, carregue um arquivo na página 'Visão Geral' primeiro.")
    st.stop()

# Busca o DF PROCESSADO COMPLETO
df_processado = st.session_state['df_processado']

# --- Inicialização do Estado de Ação ---
if 'status_map' not in st.session_state:
    st.session_state['status_map'] = {}
if 'log_contato' not in st.session_state:
    st.session_state['log_contato'] = {}
if 'show_contact_form' not in st.session_state:
    st.session_state['show_contact_form'] = False

# Filtra removendo 'Concluído'
status_map = st.session_state['status_map']
concluidos_ids = [id for id, status in status_map.items() if status == 'Concluído']

if concluidos_ids:
    df_processado = df_processado[~df_processado[config.COLUNA_ID_CLIENTE].isin(concluidos_ids)]
    st.success(f"✅ {len(concluidos_ids)} atendimentos concluídos removidos da lista.")


# =============================================================================
# ---- LÓGICA DE FILTROS EM CASCATA (DINÂMICOS) ----
# =============================================================================
st.sidebar.subheader("Filtros do Painel de Alertas")

# Vamos usar uma variável temporária que vai sendo filtrada passo a passo
df_cascade = df_processado.copy()

# 1. FILTRO DE CIDADE (Nível 1)
# As opções vêm de todo o dataframe
opcoes_cidades = sorted(df_processado[config.COLUNA_CIDADE].dropna().unique())
cidades_selecionadas = st.sidebar.multiselect(
    f'Filtrar por {config.COLUNA_CIDADE}',
    options=opcoes_cidades,
    default=[],
    key='alertas_cidade' 
)

# Aplica o filtro de cidade imediatamente na variável temporária
if cidades_selecionadas:
    df_cascade = df_cascade[df_cascade[config.COLUNA_CIDADE].isin(cidades_selecionadas)]

# 2. FILTRO DE TÉCNICO (Nível 2 - Depende da Cidade)
tecnicos_selecionados = []
if config.COLUNA_TECNICO in df_processado.columns:
    # MUDANÇA: As opções vêm de 'df_cascade' (já filtrado por cidade)
    opcoes_tecnicos = sorted(df_cascade[config.COLUNA_TECNICO].dropna().unique())
    
    tecnicos_selecionados = st.sidebar.multiselect(
        f'Filtrar por {config.COLUNA_TECNICO}',
        options=opcoes_tecnicos,
        default=[],
        key='alertas_tecnico' 
    )
    
    # Aplica o filtro de técnico na variável temporária
    if tecnicos_selecionados:
        df_cascade = df_cascade[df_cascade[config.COLUNA_TECNICO].isin(tecnicos_selecionados)]

# 3. FILTRO DE ASSUNTO (Nível 3 - Depende de Cidade + Técnico)
assuntos_selecionados = []
if config.COLUNA_ASSUNTO in df_processado.columns:
    # MUDANÇA: As opções vêm de 'df_cascade' (já filtrado por cidade e técnico)
    opcoes_assuntos = sorted(df_cascade[config.COLUNA_ASSUNTO].dropna().unique())
    
    assuntos_selecionados = st.sidebar.multiselect(
        f'Filtrar por {config.COLUNA_ASSUNTO}',
        options=opcoes_assuntos,
        default=[],
        key='alertas_assunto' 
    )
    
    # Aplica o filtro
    if assuntos_selecionados:
        df_cascade = df_cascade[df_cascade[config.COLUNA_ASSUNTO].isin(assuntos_selecionados)]

# 4. FILTRO DE STATUS (Flags)
status_selecionados = []
if config.COLUNA_STATUS in df_processado.columns:
    st.sidebar.subheader(f"Filtrar por {config.COLUNA_STATUS}")
    opcoes_status = sorted(df_processado[config.COLUNA_STATUS].dropna().unique())
    for status in opcoes_status:
        is_default = (status == config.STATUS_ABERTOS[0])
        if st.sidebar.checkbox(status, value=is_default, key=f"alertas_status_{status}"):
            status_selecionados.append(status)
    
    # Aplica o filtro
    df_cascade = df_cascade[df_cascade[config.COLUNA_STATUS].isin(status_selecionados)]

# =============================================================================
# FIM DOS FILTROS
# =============================================================================

# O df_filtrado_alertas final é o resultado da cascata
df_filtrado_alertas = df_cascade


# ---- Lógica da Página ----
df_abertos = df_filtrado_alertas.copy()

if not df_abertos.empty:
    # 1. ORDENAÇÃO E NUMERAÇÃO
    df_abertos = df_abertos.sort_values(
        by='Tempo_Decorrido_Segundos', 
        ascending=False, 
        na_position='last'
    ).reset_index(drop=True)
    df_abertos.insert(0, 'Prioridade', df_abertos.index + 1)
    
    # Cálculos de SLA
    df_abertos['Tempo_Restante_Segundos'] = df_abertos['SLA_Total_Segundos'] - df_abertos['Tempo_Decorrido_Segundos']
    df_abertos['SLA_Estourado'] = df_abertos['Tempo_Restante_Segundos'] < 0
    df_abertos['SLA_Alerta'] = df_abertos.apply(
        lambda row: row['Tempo_Restante_Segundos'] > 0 and 
                    row['Tempo_Restante_Segundos'] <= row['SLA_Alerta_Segundos'], axis=1
    )
    
    # 2. CARREGA O STATUS PERSISTENTE NA COLUNA 'Ação'
    df_abertos['Ação'] = df_abertos[config.COLUNA_ID_CLIENTE].apply(lambda id: status_map.get(id, 'Aberto'))


if df_abertos.empty:
    st.success("🎉 Nenhum chamado encontrado para os filtros atuais!")
else:
    # --- BOTÃO GATILHO ---
    st.markdown("---")
    if not st.session_state.get('show_contact_form', False):
        if st.button("📝 Abrir Formulário de Contato Detalhado", key="open_form_btn"):
            st.session_state['show_contact_form'] = True
            st.rerun() 

    # --- FORMULÁRIO DE REGISTRO DE TRATATIVA ---
    if st.session_state.get('show_contact_form', False):
        st.markdown("---")
        
        col_header, col_close = st.columns([4, 1])
        col_header.header("📋 Registro de Contato")
        
        if col_close.button("❌ Fechar Formulário"):
            st.session_state['show_contact_form'] = False
            st.rerun()

        # 1. Filtra a lista para APENAS 'Em Tratativa' para o selectbox
        df_em_tratativa = df_abertos[df_abertos['Ação'] == 'Em Tratativa'].copy()

        if df_em_tratativa.empty:
            st.warning("⚠️ Nenhuma atendimento marcado como 'Em Tratativa'. Marque um atendimento na lista abaixo para registrar o contato.")
        else:
            
            # Mapeia IDs para Prioridades para exibir no Selectbox
            id_to_priority = {
                row[config.COLUNA_ID_CLIENTE]: f"#{row['Prioridade']} (ID: {row[config.COLUNA_ID_CLIENTE]}) - {row[config.COLUNA_ASSUNTO]}"
                for index, row in df_em_tratativa.iterrows() 
            }
            
            priority_options = list(id_to_priority.values())
            
            # Lógica de Retenção do Selectbox
            selected_option_str = st.session_state.get("selected_ticket_for_log")
            
            try:
                initial_index = priority_options.index(selected_option_str)
            except (ValueError, TypeError):
                initial_index = 0
            
            selected_option = st.selectbox(
                "Selecione o Atendimento para Registrar Log:",
                options=priority_options,
                index=initial_index,
                key="selected_ticket_for_log"
            )
            
            # Extrai o ID do cliente selecionado
            selected_id = selected_option.split('ID: ')[-1].split(')')[0]
            
            # --- BUSCA SEGURA ---
            # Verifica se o ID ainda existe na lista filtrada
            if selected_id in df_em_tratativa[config.COLUNA_ID_CLIENTE].values:
                active_item = df_em_tratativa[df_em_tratativa[config.COLUNA_ID_CLIENTE] == selected_id].iloc[0]
            else:
                active_item = df_em_tratativa.iloc[0]
                selected_id = active_item[config.COLUNA_ID_CLIENTE]


            if active_item is not None:
                primeira_prioridade = active_item['Prioridade']
                current_status = status_map.get(selected_id, 'Aberto')
                
                # Encontra o índice atual para o selectbox
                status_options = ['Aberto', 'Em Tratativa', 'Concluído']
                try:
                    idx_status = status_options.index(current_status)
                except ValueError:
                    idx_status = 0
                
                st.markdown(f"**Tratando Prioridade #{primeira_prioridade}** (ID: `{selected_id}` | Assunto: `{active_item[config.COLUNA_ASSUNTO]}`)")
                st.info(f"Status Atual: **{current_status}**")
                
                with st.form("contact_form_details", clear_on_submit=True):
                    
                    # SELETOR DE STATUS (Fonte de verdade)
                    st.subheader("1. Atualizar Status")
                    novo_status_form = st.selectbox("Novo Status:", status_options, index=idx_status)

                    st.markdown("---")
                    st.subheader("2. Registrar Contato")

                    col_c1, col_c2 = st.columns(2)
                    input_contato1 = col_c1.text_input("Opção de Contato 1", key="input_contato1")
                    input_contato2 = col_c2.text_input("Opção de Contato 2", key="input_contato2")
                    
                    st.write("**Meio de Contato Realizado:**")
                    col_check1, col_check2, col_check3, col_check4 = st.columns(4)
                    check_call = col_check1.checkbox("📞 Ligação")
                    check_msg = col_check2.checkbox("📱 Mensagem SMS")
                    check_wapp = col_check3.checkbox("📞 WhatsApp (Ligação)")
                    check_wapp_msg = col_check4.checkbox("💬 WhatsApp (Mensagem)")
                    
                    notes = st.text_area("Observações da Tentativa/Próximos Passos", max_chars=500)
                    
                    submitted = st.form_submit_button("✅ Salvar Status e Log")

                    if submitted:
                        if novo_status_form != 'Aberto' and not (check_call or check_msg or check_wapp or check_wapp_msg or notes):
                             st.warning("Atenção: Você mudou o status mas não registrou nenhum detalhe de contato/observação.")
                        
                        # 1. Salva LOG
                        log_entry = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "cliente_id": selected_id,
                            "novo_status": novo_status_form, 
                            "contato_op1": input_contato1,
                            "contato_op2": input_contato2,
                            "meio": [
                                m for m, checked in [
                                    ("Ligação", check_call), ("SMS", check_msg), 
                                    ("WhatsApp Ligação", check_wapp), ("WhatsApp Mensagem", check_wapp_msg)
                                ] if checked
                            ],
                            "observacoes": notes
                        }
                        st.session_state.setdefault('log_contato', {}).setdefault(selected_id, []).append(log_entry)
                        
                        # 2. ATUALIZA O STATUS NA MEMÓRIA (PERSISTÊNCIA)
                        st.session_state['status_map'][selected_id] = novo_status_form
                        
                        st.success(f"Sucesso! Status alterado para '{novo_status_form}'.")
                        
                        if novo_status_form == 'Concluído':
                            st.session_state['show_contact_form'] = False
                        
                        st.rerun()

            st.button("❌ Fechar Formulário", on_click=lambda: st.session_state.update(show_contact_form=False), key="close_form_out")
    
    st.markdown("---")
    
    # ---- KPIs Principais ----
    st.subheader("KPIs dos Chamados Selecionados")
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    
    total_abertos = len(df_abertos)
    total_fora_sla = df_abertos['SLA_Estourado'].sum()
    total_em_alerta = df_abertos['SLA_Alerta'].sum()
    
    col_kpi1.metric("Total de Chamados na Lista", total_abertos)
    col_kpi2.metric("Total Fora do SLA (Estourado)", f"{total_fora_sla} 🚨")
    col_kpi3.metric("Total em Alerta (Regra de 4h)", f"{total_em_alerta} ⚠️")

    # ---- KPIs de Alerta por Hora de Abertura ----
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

    # ---- Tabela de Chamados com Ação ----
    st.subheader("Lista de Chamados (Ordenado por Prioridade)")
    
    # Cria os valores formatados para exibição
    df_display = df_abertos.copy()
    df_display['Data Abertura'] = df_display[config.COLUNA_ABERTURA].dt.strftime('%d/%m/%y %H:%M') 
    df_display['Tempo Aberto'] = df_display['Tempo_Decorrido_Segundos'].apply(config.formatar_hms)
    df_display['Restante SLA'] = df_display['Tempo_Restante_Segundos'].apply(config.formatar_hms)
    
    # Colunas que serão exibidas (Read-Only)
    colunas_finais = [
        'Ação', 
        'Prioridade', config.COLUNA_ID_CLIENTE, config.COLUNA_NOME_CLIENTE, config.COLUNA_ASSUNTO, 
        config.COLUNA_STATUS, 'Data Abertura', 'Tempo Aberto', 'Restante SLA', 
    ]
    if config.COLUNA_TECNICO in df_display.columns:
        colunas_finais.insert(5, config.COLUNA_TECNICO) 
    
    # Colunas visíveis
    cols_visual = [col for col in colunas_finais if col in df_display.columns or col in ['Prioridade', 'Data Abertura', 'Tempo Aberto', 'Restante SLA', 'Ação']]
    
    # Colunas auxiliares para estilo (que serão escondidas)
    cols_aux = [
        'Tempo_Decorrido_Segundos', 'Tempo_Restante_Segundos', 
        'SLA_Estourado', 'SLA_Alerta'
    ]
    cols_aux = [c for c in cols_aux if c in df_display.columns]
    
    # Combina visual + auxiliar para passar ao Styler
    cols_total = cols_visual + [c for c in cols_aux if c not in cols_visual]

    # MUDANÇA FINAL: Tabela de leitura com estilos
    st.dataframe(
        df_display[cols_total].style.apply(config.highlight_sla, axis=1)
                         .hide(axis="columns", subset=cols_aux),
        use_container_width=True,
        hide_index=True
    )
    
    # Lógica para registrar o status na memória
    if st.session_state.get(editor_key, False):
        edited_data = st.session_state[editor_key]
        if edited_data.get('edited_rows'):
            for index, row in edited_data['edited_rows'].items():
                if row.get('Ação'):
                    cliente_id = df_display.iloc[index][config.COLUNA_ID_CLIENTE]
                    novo_status = row.get('Ação')
                    
                    st.session_state['status_map'][cliente_id] = novo_status
                    
                    if novo_status == 'Concluído':
                        st.rerun()
