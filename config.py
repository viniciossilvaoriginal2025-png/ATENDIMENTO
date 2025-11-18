import pandas as pd
import folium 
from folium import DivIcon 
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

# --- CONFIGURAÇÃO DE SLA DINÂMICO ---
# Adicionado SLA de 7 dias (168h) para Manutenção Rural
SLAS_POR_CATEGORIA = {
    'MANUTENCAO_RURAL': {'sla_hours': 168, 'alerta_hours': 24}, # Alerta 24h antes
    'ATIVACAO': {'sla_hours': 24, 'alerta_hours': 4},
    'MUDANCA': {'sla_hours': 24, 'alerta_hours': 4},
    'MANUTENCAO': {'sla_hours': 24, 'alerta_hours': 4},
    'SERVICOS': {'sla_hours': 24, 'alerta_hours': 4},
    'DESCONEXAO': {'sla_hours': 24, 'alerta_hours': 4},
    'DEFAULT': {'sla_hours': 24, 'alerta_hours': 4} 
}

# --- CONFIGURAÇÃO DE CORES (SEMAFORO POR CATEGORIA) ---
CORES_CATEGORIA = {
    'ATIVACAO': {'safe': '#228B22', 'alert': '#FFD700', 'overdue': '#FF4500', 'label': 'Ativação Inicial'},
    'MUDANCA': {'safe': '#1E90FF', 'alert': '#87CEFA', 'overdue': '#00008B', 'label': 'Mudança Endereço'},
    'MANUTENCAO': {'safe': '#B22222', 'alert': '#F08080', 'overdue': '#800000', 'label': 'Manutenção Ext.'},
    'MANUTENCAO_RURAL': {'safe': '#006400', 'alert': '#9ACD32', 'overdue': '#4B0082', 'label': 'Manutenção Rural'},
    'SERVICOS': {'safe': '#9370DB', 'alert': '#DDA0DD', 'overdue': '#4B0082', 'label': 'Serviços Extras'},
    'DESCONEXAO': {'safe': '#008080', 'alert': '#40E0D0', 'overdue': '#004d4d', 'label': 'Desconexão/Recolh.'},
    'DEFAULT': {'safe': 'gray', 'alert': 'lightgray', 'overdue': 'black', 'label': 'Outros'}
}

MAPA_NOMES = {
    'ATIVAÇÃO INICIAL (ADAPTER)': 'ATIVACAO', 'ATIVACAO INICIAL (ADAPTER)': 'ATIVACAO',
    'MUDANÇA DE ENDEREÇO (ADAPTER)': 'MUDANCA', 'MUDANCA DE ENDERECO (ADAPTER)': 'MUDANCA',
    'MANUTENÇÃO EXTERNA (ADAPTER)': 'MANUTENCAO', 'MANUTENCAO EXTERNA (ADAPTER)': 'MANUTENCAO',
    'MANUTENÇÃO ZONA RURAL (ADAPTER)': 'MANUTENCAO_RURAL', 'MANUTENCAO ZONA RURAL (ADAPTER)': 'MANUTENCAO_RURAL',
    'SERVIÇOS EXTRAS (ADAPTER)': 'SERVICOS', 'SERVICOS EXTRAS (ADAPTER)': 'SERVICOS',
    'DESCONEXÃO/RECOLHIMENTO (ADAPTER)': 'DESCONEXAO', 'DESCONEXAO/RECOLHIMENTO (ADAPTER)': 'DESCONEXAO'
}

# ---- FUNÇÕES HELPERS ----
def obter_sla_segundos(assunto):
    assunto_upper = str(assunto).strip().upper()
    chave = MAPA_NOMES.get(assunto_upper, 'DEFAULT')
    sla_config = SLAS_POR_CATEGORIA.get(chave, SLAS_POR_CATEGORIA['DEFAULT'])
    return sla_config['sla_hours'] * 3600, sla_config['alerta_hours'] * 3600

def formatar_hms(segundos_totais):
    if pd.isna(segundos_totais): return "N/A"
    segundos_totais = int(segundos_totais)
    sinal = '-' if segundos_totais < 0 else ''
    segundos_totais = abs(segundos_totais)
    horas = segundos_totais // 3600
    minutos = (segundos_totais % 3600) // 60
    segundos = segundos_totais % 60
    return f"{sinal}{horas:02}:{minutos:02}:{segundos:02}"

def get_esquema_cor(row):
    assunto_raw = str(row.get(COLUNA_ASSUNTO, '')).strip().upper()
    chave_categoria = MAPA_NOMES.get(assunto_raw, 'DEFAULT')
    return CORES_CATEGORIA.get(chave_categoria, CORES_CATEGORIA['DEFAULT'])

def obter_dados_cor(row):
    esquema = get_esquema_cor(row)
    if 'SLA_Estourado' not in row: return esquema['safe']
    if row['SLA_Estourado']: return esquema['overdue']
    elif row['SLA_Alerta']: return esquema['alert']
    else: return esquema['safe']

def get_text_color(bg_color):
    light_colors = ['#FFD700', '#87CEFA', '#F08080', '#DDA0DD', '#40E0D0', 'lightgray', 'white', '#FFF3CD', '#9ACD32']
    return 'black' if bg_color in light_colors else 'white'

def highlight_sla(row):
    esquema = get_esquema_cor(row)
    if 'SLA_Estourado' not in row:
        bg_color, text_color = esquema['safe'], 'white'
    elif row['SLA_Estourado']:
        bg_color, text_color = esquema['overdue'], 'white' 
    elif row['SLA_Alerta']:
        bg_color, text_color = esquema['alert'], 'black' 
    else:
        bg_color, text_color = esquema['safe'], 'white' 
    return [f'background-color: {bg_color}; color: {text_color}; font-weight: bold'] * len(row)

# ---- CRIAR MAPA FOLIUM (SIMPLIFICADO) ----
def criar_mapa_folium(df_mapa):
    if df_mapa.empty:
        return folium.Map(location=[-15.788497, -47.879873], zoom_start=4)

    # NOTA: Removemos a ordenação aqui. O mapa vai respeitar a ordem que vem da Tabela.
    
    map_center = [df_mapa[COLUNA_LATITUDE].mean(), df_mapa[COLUNA_LONGITUDE].mean()]
    m = folium.Map(location=map_center, zoom_start=12)

    for idx, row in df_mapa.iterrows():
        # Usa a coluna Prioridade que criamos na página 2
        prioridade = row.get('Prioridade', idx + 1)
        
        cor_fundo = obter_dados_cor(row)
        cor_texto = get_text_color(cor_fundo)
        cor_borda = "black" if cor_fundo == "white" else cor_fundo
        
        tecnico = row.get(COLUNA_TECNICO, "N/A")
        if pd.isna(tecnico): tecnico = "N/A"
        t_aberto = formatar_hms(row.get('Tempo_Decorrido_Segundos', pd.NA))
        t_restante = ""
        if 'Tempo_Restante_Segundos' in row and pd.notna(row['Tempo_Restante_Segundos']):
            t_restante = f"<b>Restante:</b> {formatar_hms(row['Tempo_Restante_Segundos'])}<br>"

        icon_html = f"""
        <div style="
            background-color: {cor_fundo}; border: 2px solid {cor_borda}; color: {cor_texto};
            border-radius: 50%; width: 24px; height: 24px;
            display: flex; align-items: center; justify-content: center;
            font-weight: bold; font-family: sans-serif; font-size: 10pt;
            box-shadow: 2px 2px 4px rgba(0,0,0,0.4);
        ">
        {prioridade}
        </div>
        """

        popup_html = f"""
        <div style="font-family: sans-serif; font-size: 12px;">
            <b style="font-size:14px;">Prioridade #{prioridade}</b><br>
            <hr style='margin: 4px 0;'>
            <b>ID:</b> {row[COLUNA_ID_CLIENTE]}<br>
            <b>Técnico:</b> {tecnico}<br>
            <b>Assunto:</b> {row[COLUNA_ASSUNTO]}<br>
            <b>Aberto há:</b> {t_aberto}<br>
            {t_restante}
        </div>
        """
        
        folium.Marker(
            location=[row[COLUNA_LATITUDE], row[COLUNA_LONGITUDE]],
            icon=DivIcon(html=icon_html), 
            popup=folium.Popup(popup_html, max_width=300)
        ).add_to(m)

    # Legenda HTML
    rows_html = ""
    keys_order = ['ATIVACAO', 'MUDANCA', 'MANUTENCAO', 'MANUTENCAO_RURAL', 'SERVICOS', 'DESCONEXAO', 'DEFAULT']
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
        position: fixed; bottom: 30px; left: 30px; width: auto; height: auto; 
        z-index:9999; font-size:12px; font-family: sans-serif;
        background-color: white; border: 2px solid #666; border-radius: 8px;
        padding: 10px; opacity: 0.95; box-shadow: 3px 3px 5px rgba(0,0,0,0.3);
        ">
        <b style="font-size:14px;">Legenda de Status</b>
        <table style="width:100%; margin-top:5px;">
            <tr style="font-weight:bold; font-size:10px; color:#555;">
                <td style="text-align:left;">Categoria</td>
                <td style="padding:0 5px;">No Prazo</td>
                <td style="padding:0 5px;">Alerta</td>
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
