import pandas as pd
import folium 
from folium import DivIcon 
from branca.element import Template, MacroElement
import streamlit as st # <-- Importado para usar o st.session_state

# ... (Restante das constantes e cores) ...

# --- CONFIGURAÇÃO DE ALERTA E SLA ---
STATUS_ABERTOS = ["VISITA_AGENDADA"] 
SLA_SEGUNDOS = 24 * 60 * 60  # 24 horas
ALERTA_SEGUNDOS = 4 * 60 * 60 # 4 horas

# ... (funções formatar_hms e highlight_sla permanecem) ...

# ---- NOVA FUNÇÃO: AÇÃO DE LINHA ----
def render_action_button(df_abertos, key_prefix):
    """
    Renderiza um botão de ação 'Concluir' no final do dataframe.
    Retorna o ID do cliente que foi concluído.
    """
    
    # Adiciona a coluna de botões ao dataframe (necessário para a lógica)
    df_abertos['Ação'] = False 
    
    # Cria uma lista de dicionários para passar ao st.data_editor
    action_data = []
    
    for idx, row in df_abertos.iterrows():
        id_cliente = row[COLUNA_ID_CLIENTE]
        
        # Cria um valor booleano no session state para cada botão
        if st.session_state.get(f'{key_prefix}_concluir_{id_cliente}', False):
            # Se já foi clicado nesta sessão, mostra como concluído
            action_data.append({'ID': id_cliente, 'Ação': True, 'Status': 'CONCLUÍDO'})
        else:
            # Renderiza o botão e verifica o clique
            if st.button('✅ Concluir', key=f'{key_prefix}_btn_{id_cliente}'):
                # Ao clicar, atualiza o session state e a lista de concluídos
                st.session_state[f'{key_prefix}_concluir_{id_cliente}'] = True
                st.session_state.setdefault('concluidos_list', []).append(id_cliente)
                st.experimental_rerun() # Força o recálculo para a linha sumir
                return id_cliente
            
            action_data.append({'ID': id_cliente, 'Ação': False, 'Status': 'PENDENTE'})

    return None

# ---- CÓDIGO DO MAPA (cria_mapa_folium) ADICIONADO AQUI ----
# A função é muito longa para ser incluída aqui, mas ela permanece a mesma que enviei antes.
# Por favor, garanta que ela esteja no seu config.py.
# Vou adaptar apenas a lógica do popup para que ele mostre o ID do cliente no topo do mapa.
# Note: Não é possível adicionar o botão dentro do popup do Folium.
