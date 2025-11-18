import pandas as pd
import folium 
from branca.element import Template, MacroElement # Necessário para a legenda

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
COLUNA_LATITUDE = "latitude"
COLUNA_LONGITUDE = "longitude"

# --- CONFIGURAÇÃO DE ALERTA E SLA ---
STATUS_ABERTOS = ["VISITA_AGENDADA"] 
SLA_SEGUNDOS = 24 * 60 * 60  # 24 horas
ALERTA_SEGUNDOS = 4 * 60 * 60 # 4 horas

# --- CONFIGURAÇÃO DE CORES POR CATEGORIA (ASSUNTO) ---
# Defina aqui as cores para quando o chamado estiver no prazo "Seguro" (< 20h)
# Cores suportadas pelo Folium: 
# 'red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 
# 'darkblue', 'darkgreen', 'cadetblue', 'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen', 'gray', 'black', 'lightgray'
CORES_CATEGORIA = {
    'INSTALACAO': 'green',    # Ex: Ativação/Instalação
    'ATIVACAO': 'green',
    'INTERNET LENTA': 'orange',
    'SEM CONEXAO': 'purple',
    'QUEDA DE SINAL': 'darkred',
    'MUDANCA DE ENDERECO': 'beige',
    'DEFAULT': 'gray' # Cor para assuntos não listados acima
}

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

# ---- FUNÇÃO HELPER DE ESTILO (TABELA) ----
def highlight_sla(linha):
    if linha['SLA_Estourado'] == True:
        return ['background-color: #FFC7CE'] * len(linha) # Vermelho claro (Tabela)
    elif linha['SLA_Alerta'] == True:
        return ['background-color: #E6F3FF'] * len(linha) # Azul claro (Tabela)
    else:
        return [''] * len(linha)

# ---- FUNÇÃO HELPER: OBTER COR DO MARCADOR ----
def obter_cor_marcador(row):
    # 1. Prioridade Máxima: VENCIDO (> 24h)
    if 'SLA_Estourado' in row and row['SLA_Estourado']:
        return "white"
    
    # 2. Prioridade Média: ALERTA (Faltam < 4h)
    if 'SLA_Alerta' in row and row['SLA_Alerta']:
        return "blue"
    
    # 3. Prioridade Normal: COR DA CATEGORIA
    # Pega o assunto, converte para maiúsculo e remove espaços extras
    assunto = str(row[COLUNA_ASSUNTO]).strip().upper()
    
    # Procura no dicionário, se não achar, usa DEFAULT
    return CORES_CATEGORIA.get(assunto, CORES_CATEGORIA['DEFAULT'])

# ---- FUNÇÃO HELPER PARA CRIAR O MAPA COM LEGENDA ----
def criar_mapa_folium(df_mapa):
    if df_mapa.empty:
        return folium.Map(location=[-15.788497, -47.879873], zoom_start=4)

    map_center = [df_mapa[COLUNA_LATITUDE].mean(), df_mapa[COLUNA_LONGITUDE].mean()]
    m = folium.Map(location=map_center, zoom_start=10)

    for idx, row in df_mapa.iterrows():
        
        # Define a cor usando a nova lógica
        cor_fundo = obter_cor_marcador(row)
        
        # Define a borda (preta para branco, senão igual ao fundo)
        cor_borda = "black" if cor_fundo == "white" else cor_fundo
        
        tecnico_nome = row.get(COLUNA_TECNICO, "N/A") 
        if pd.isna(tecnico_nome): tecnico_nome = "N/A"
        
        # Formatações de tempo para o popup
        tempo_aberto_str = "N/A"
        if 'Tempo_Decorrido_Segundos' in row and pd.notna(row['Tempo_Decorrido_Segundos']):
            tempo_aberto_str = formatar_hms(row['Tempo_Decorrido_Segundos'])

        tempo_restante_str = ""
        if 'Tempo_Restante_Segundos' in row and pd.notna(row['Tempo_Restante_Segundos']):
            tempo_restante_str = f"<b>Restante SLA:</b> {formatar_hms(row['Tempo_Restante_Segundos'])}<br>"
            
        popup_html = f"""
        <b>ID:</b> {row[COLUNA_ID_CLIENTE]}<br>
        <b>Técnico:</b> {tecnico_nome}<br>
        <b>Assunto:</b> {row[COLUNA_ASSUNTO]}<br>
        <hr style='margin: 3px 0;'>
        <b>Aberto há:</b> {tempo_aberto_str}<br>
        {tempo_restante_str}
        """
        
        folium.CircleMarker(
            location=[row[COLUNA_LATITUDE], row[COLUNA_LONGITUDE]],
            radius=6,
            color=cor_borda,
            fill=True,
            fill_color=cor_fundo,
            fill_opacity=0.9,
            popup=folium.Popup(popup_html, max_width=300)
        ).add_to(m)

    # ---- ADICIONAR LEGENDA FLUTUANTE ----
    template_legenda = """
    {% macro html(this, kwargs) %}
    <div style="
        position: fixed; 
        bottom: 50px; left: 50px; width: 200px; height: auto; 
        z-index:9999; font-size:14px;
        background-color: white;
        border: 2px solid grey;
        border-radius: 6px;
        padding: 10px;
        opacity: 0.9;
        ">
        <b>Legenda SLA & Categorias</b><br>
        <i style="background:white; border:1px solid black; width:10px; height:10px; display:inline-block; border-radius:50%;"></i>&nbsp; Vencido (>24h)<br>
        <i style="background:blue; width:10px; height:10px; display:inline-block; border-radius:50%;"></i>&nbsp; Alerta (< 4h)<br>
        <hr style="margin: 5px 0;">
        <small>No Prazo (< 20h):</small><br>
        <i style="background:green; width:10px; height:10px; display:inline-block; border-radius:50%;"></i>&nbsp; Instalação/Ativ.<br>
        <i style="background:orange; width:10px; height:10px; display:inline-block; border-radius:50%;"></i>&nbsp; Internet Lenta<br>
        <i style="background:purple; width:10px; height:10px; display:inline-block; border-radius:50%;"></i>&nbsp; Sem Conexão<br>
        <i style="background:darkred; width:10px; height:10px; display:inline-block; border-radius:50%;"></i>&nbsp; Queda Sinal<br>
        <i style="background:gray; width:10px; height:10px; display:inline-block; border-radius:50%;"></i>&nbsp; Outros<br>
    </div>
    {% endmacro %}
    """
    macro = MacroElement()
    macro._template = Template(template_legenda)
    m.get_root().add_child(macro)

    return m
