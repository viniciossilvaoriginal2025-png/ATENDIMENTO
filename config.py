import pandas as pd
import folium # Nova biblioteca

# ---- Nomes das Colunas ----
COLUNA_ID_CLIENTE = "ID Cliente"
COLUNA_NOME_CLIENTE = "Nome Cliente"
COLUNA_CIDADE = "Cidade"
COLUNA_STATUS = "Status Atendimento"
COLUNA_ABERTURA = "Abertura"
COLUNA_ASSUNTO = "Assunto"
COLUNA_ENCAMINHAMENTO = "Encaminhamento Operacional"
COLUNA_AGENDAMENTO = "Agendamento Visita"
COLUNA_TECNICO = "Tecnico Visita"
# --- NOVAS COLUNAS DO MAPA ---
COLUNA_LATITUDE = "latitude"
COLUNA_LONGITUDE = "longitude"

# --- CONFIGURAÇÃO DE ALERTA E SLA ---
STATUS_ABERTOS = ["VISITA_AGENDADA"] 
SLA_SEGUNDOS = 24 * 60 * 60  # 24 horas
ALERTA_SEGUNDOS = 4 * 60 * 60 # 4 horas

# ---- FUNÇÃO HELPER DE FORMATAÇÃO DE TEMPO ----
def formatar_hms(segundos_totais):
    if pd.isna(segundos_totais):
        return "N/A"
    segundos_totais = int(segundos_totais)
    sinal = ''
    if segundos_totais < 0:
        sinal = '-'
        segundos_totais = abs(segundos_totais)
    horas = segundos_totais // 3600
    minutos_restantes = segundos_totais % 3600
    minutos = minutos_restantes // 60
    segundos = minutos_restantes % 60
    return f"{sinal}{horas:02}:{minutos:02}:{segundos:02}"

# ---- FUNÇÃO HELPER DE ESTILO (PARA O ALERTA VERMELHO E AMARELO) ----
def highlight_sla(linha):
    if linha['SLA_Estourado'] == True:
        return ['background-color: #FFC7CE'] * len(linha) 
    elif linha['SLA_Alerta'] == True:
        return ['background-color: #FFF3CD'] * len(linha) 
    else:
        return [''] * len(linha)

# ---- (FUNÇÃO DO MAPA ALTERADA) ----
def criar_mapa_folium(df_mapa):
    """
    Cria um mapa Folium com popups e cores de SLA (Verde/Vermelho/Branco).
    """
    if df_mapa.empty:
        return folium.Map(location=[-15.788497, -47.879873], zoom_start=4) # Centraliza no Brasil

    # Calcula o centro do mapa
    map_center = [df_mapa[COLUNA_LATITUDE].mean(), df_mapa[COLUNA_LONGITUDE].mean()]
    m = folium.Map(location=map_center, zoom_start=10)

    # Adiciona os pontos (bolinhas)
    for idx, row in df_mapa.iterrows():
        
        # Lógica de Cor (Verde/Vermelho/Branco/Azul)
        cor_borda = "black"
        cor_fundo = "blue" # Padrão para "Visão Geral"

        if 'SLA_Estourado' in row and 'SLA_Alerta' in row:
            # Lógica de SLA (Verde/Vermelho/Branco) para o Painel de Alertas
            if row['SLA_Estourado']:
                cor_borda = "black"
                cor_fundo = "white" # VENCIDO = Branco
            elif row['SLA_Alerta']:
                cor_borda = "red"
                cor_fundo = "red"   # FALTANDO < 4H = Vermelho
            else:
                cor_borda = "green"
                cor_fundo = "green" # SEGURO (< 20h aberto) = Verde
        
        tecnico_nome = row.get(COLUNA_TECNICO, "N/A") 
        if pd.isna(tecnico_nome):
            tecnico_nome = "N/A"
        
        # --- MUDANÇA AQUI: Adiciona os tempos ao Popup ---
        
        # 1. Formata o Tempo Aberto (sempre existe)
        tempo_aberto_str = "N/A"
        if 'Tempo_Decorrido_Segundos' in row and pd.notna(row['Tempo_Decorrido_Segundos']):
            tempo_aberto_str = formatar_hms(row['Tempo_Decorrido_Segundos'])

        # 2. Formata o Tempo Restante (só existe no Painel de Alertas)
        tempo_restante_str = "" # Começa vazio
        if 'Tempo_Restante_Segundos' in row and pd.notna(row['Tempo_Restante_Segundos']):
            tempo_restante_str = f"<b>Tempo Restante SLA:</b> {formatar_hms(row['Tempo_Restante_Segundos'])}<br>"
        # --- FIM DA MUDANÇA ---
            
        popup_html = f"""
        <b>ID Cliente:</b> {row[COLUNA_ID_CLIENTE]}<br>
        <b>Técnico:</b> {tecnico_nome}<br>
        <b>Assunto:</b> {row[COLUNA_ASSUNTO]}<br>
        <b>Status:</b> {row[COLUNA_STATUS]}<br>
        <hr style='margin: 3px 0;'>
        <b>Tempo Aberto:</b> {tempo_aberto_str}<br>
        {tempo_restante_str}
        """
        
        folium.CircleMarker(
            location=[row[COLUNA_LATITUDE], row[COLUNA_LONGITUDE]],
            radius=5,
            color=cor_borda, # Cor da borda
            fill=True,
            fill_color=cor_fundo, # Cor do preenchimento
            fill_opacity=0.8,
            popup=folium.Popup(popup_html, max_width=300)
        ).add_to(m)

    return m
