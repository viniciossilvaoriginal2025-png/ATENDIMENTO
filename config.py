import pandas as pd
import folium 
from branca.element import Template, MacroElement

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

# --- CONFIGURAÇÃO AVANÇADA DE CORES (SEMAFORO POR CATEGORIA) ---
# Cores em formato HEX ou Nome CSS
CORES_CATEGORIA = {
    'ATIVACAO': {
        'safe': '#228B22',    # Verde Floresta (No Prazo)
        'alert': '#FFD700',   # Dourado/Amarelo (Vence em 4h)
        'overdue': '#FF4500', # Laranja Escuro (Vencido)
        'label': 'Ativação Inicial'
    },
    'MUDANCA': {
        'safe': '#1E90FF',    # Azul Dodger (No Prazo)
        'alert': '#87CEFA',   # Azul Claro (Vence em 4h)
        'overdue': '#00008B', # Azul Marinho (Vencido)
        'label': 'Mudança Endereço'
    },
    'MANUTENCAO': {
        'safe': '#B22222',    # Tijolo/Vermelho (No Prazo)
        'alert': '#F08080',   # Coral Claro (Vence em 4h)
        'overdue': '#800000', # Marrom/Vinho (Vencido)
        'label': 'Manutenção Ext.'
    },
    'SERVICOS': {
        'safe': '#9370DB',    # Roxo Médio (No Prazo)
        'alert': '#DDA0DD',   # Ameixa/Lilás (Vence em 4h)
        'overdue': '#4B0082', # Índigo/Roxo Escuro (Vencido)
        'label': 'Serviços Extras'
    },
    'DEFAULT': {
        'safe': 'gray', 
        'alert': 'lightgray', 
        'overdue': 'black',
        'label': 'Outros'
    }
}

# Mapeamento de nomes do Excel para as chaves acima
MAPA_NOMES = {
    'ATIVAÇÃO INICIAL (ADAPTER)': 'ATIVACAO',
    'ATIVACAO INICIAL (ADAPTER)': 'ATIVACAO',
    'MUDANÇA DE ENDEREÇO (ADAPTER)': 'MUDANCA',
    'MUDANCA DE ENDERECO (ADAPTER)': 'MUDANCA',
    'MANUTENÇÃO EXTERNA (ADAPTER)': 'MANUTENCAO',
    'MANUTENCAO EXTERNA (ADAPTER)': 'MANUTENCAO',
    'SERVIÇOS EXTRAS (ADAPTER)': 'SERVICOS',
    'SERVICOS EXTRAS (ADAPTER)': 'SERVICOS'
}

# ---- FUNÇÃO HELPER DE FORMATAÇÃO DE TEMPO ----
def formatar_hms(segundos_totais):
    if pd.isna(segundos_totais): return "N/A"
    segundos_totais = int(segundos_totais)
    sinal = '-' if segundos_totais < 0 else ''
    segundos_totais = abs(segundos_totais)
    horas = segundos_totais // 3600
    minutos = (segundos_totais % 3600) // 60
    segundos = segundos_totais % 60
    return f"{sinal}{horas:02}:{minutos:02}:{segundos:02}"

# ---- ESTILO DA TABELA (Mantemos simples: Vermelho/Amarelo) ----
def highlight_sla(linha):
    if linha.get('SLA_Estourado'):
        return ['background-color: #FFC7CE'] * len(linha) 
    elif linha.get('SLA_Alerta'):
        return ['background-color: #FFF3CD'] * len(linha) 
    return [''] * len(linha)

# ---- OBTER COR DO MARCADOR (NOVA LÓGICA) ----
def obter_dados_cor(row):
    # 1. Descobre a categoria
    assunto_raw = str(row[COLUNA_ASSUNTO]).strip().upper()
    chave_categoria = MAPA_NOMES.get(assunto_raw, 'DEFAULT')
    esquema = CORES_CATEGORIA.get(chave_categoria, CORES_CATEGORIA['DEFAULT'])
    
    # 2. Decide o estado (Vencido, Alerta, Safe)
    # Se não tiver dados de SLA (Visão Geral), assume Safe
    if 'SLA_Estourado' not in row:
        return esquema['safe']

    if row['SLA_Estourado']:
        return esquema['overdue']
    elif row['SLA_Alerta']:
        return esquema['alert']
    else:
        return esquema['safe']

# ---- CRIAR MAPA FOLIUM ----
def criar_mapa_folium(df_mapa):
    if df_mapa.empty:
        return folium.Map(location=[-15.788497, -47.879873], zoom_start=4)

    map_center = [df_mapa[COLUNA_LATITUDE].mean(), df_mapa[COLUNA_LONGITUDE].mean()]
    m = folium.Map(location=map_center, zoom_start=10)

    for idx, row in df_mapa.iterrows():
        cor_final = obter_dados_cor(row)
        
        tecnico = row.get(COLUNA_TECNICO, "N/A")
        if pd.isna(tecnico): tecnico = "N/A"
        
        t_aberto = formatar_hms(row.get('Tempo_Decorrido_Segundos', pd.NA))
        t_restante = ""
        if 'Tempo_Restante_Segundos' in row and pd.notna(row['Tempo_Restante_Segundos']):
            t_restante = f"<b>Restante:</b> {formatar_hms(row['Tempo_Restante_Segundos'])}<br>"

        popup_html = f"""
        <div style="font-family: sans-serif; font-size: 12px;">
            <b>ID:</b> {row[COLUNA_ID_CLIENTE]}<br>
            <b>Técnico:</b> {tecnico}<br>
            <b>Assunto:</b> {row[COLUNA_ASSUNTO]}<br>
            <hr style='margin: 4px 0;'>
            <b>Aberto há:</b> {t_aberto}<br>
            {t_restante}
        </div>
        """
        
        folium.CircleMarker(
            location=[row[COLUNA_LATITUDE], row[COLUNA_LONGITUDE]],
            radius=7,
            color='black',      # Borda preta fina para contraste
            weight=1,
            fill=True,
            fill_color=cor_final,
            fill_opacity=0.9,
            popup=folium.Popup(popup_html, max_width=300)
        ).add_to(m)

    # ---- LEGENDA TABELA HTML ----
    # Monta as linhas da tabela dinamicamente com base no config
    rows_html = ""
    # Ordem de exibição
    keys_order = ['ATIVACAO', 'MUDANCA', 'MANUTENCAO', 'SERVICOS', 'DEFAULT']
    
    for key in keys_order:
        cor = CORES_CATEGORIA[key]
        rows_html += f"""
        <tr>
            <td style="padding:3px;">{cor['label']}</td>
            <td style="text-align:center;"><span style="background:{cor['safe']}; width:12px; height:12px; display:inline-block; border-radius:50%; border:1px solid #ccc;"></span></td>
            <td style="text-align:center;"><span style="background:{cor['alert']}; width:12px; height:12px; display:inline-block; border-radius:50%; border:1px solid #ccc;"></span></td>
            <td style="text-align:center;"><span style="background:{cor['overdue']}; width:12px; height:12px; display:inline-block; border-radius:50%; border:1px solid #ccc;"></span></td>
        </tr>
        """

    template_legenda = f"""
    {{% macro html(this, kwargs) %}}
    <div style="
        position: fixed; 
        bottom: 30px; left: 30px; width: auto; height: auto; 
        z-index:9999; font-size:12px; font-family: sans-serif;
        background-color: white;
        border: 2px solid #666;
        border-radius: 8px;
        padding: 10px;
        opacity: 0.95;
        box-shadow: 3px 3px 5px rgba(0,0,0,0.3);
        ">
        <b style="font-size:14px;">Legenda de Status</b>
        <table style="width:100%; margin-top:5px;">
            <tr style="font-weight:bold; font-size:10px; color:#555;">
                <td style="text-align:left;">Categoria</td>
                <td style="padding:0 5px;">No Prazo</td>
                <td style="padding:0 5px;">Alerta 4h</td>
                <td style="padding:0 5px;">Vencido</td>
            </tr>
            {rows_html}
        </table>
    </div>
    {{% endmacro %}}
    """
    macro = MacroElement()
    macro._template = Template(template_legenda)
    m.get_root().add_child(macro)

    return m
