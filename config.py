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
SLAS_POR_CATEGORIA = {
    'MANUTENCAO_RURAL': {'sla_hours': 168, 'alerta_hours': 24},
    'ATIVACAO': {'sla_hours': 24, 'alerta_hours': 4},
    'MUDANCA': {'sla_hours': 24, 'alerta_hours': 4},
    'MANUTENCAO': {'sla_hours': 24, 'alerta_hours': 4},
    'SERVICOS': {'sla_hours': 24, 'alerta_hours': 4},
    'DESCONEXAO': {'sla_hours': 24, 'alerta_hours': 4},
    'DEFAULT': {'sla_hours': 24, 'alerta_hours': 4}
}

# --- CORES FIXAS DO SEMÁFORO ---
COR_SAFE = '#28a745'     # Verde (Até 20h)
COR_ALERT = '#FFD700'    # Amarelo/Dourado (4h ou menos restantes)
COR_OVERDUE = '#DC3545'  # Vermelho (Vencido)

# --- CONFIGURAÇÃO DE ALERTA ---
STATUS_ABERTOS = ["VISITA_AGENDADA"] 
ALERTA_SEGUNDOS = 4 * 60 * 60 # 4 horas

# Mapeamento de nomes do Excel
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

# ---- FUNÇÃO DE COR DO SEMÁFORO ----
def obter_dados_cor(row):
    if 'SLA_Estourado' in row and row['SLA_Estourado']:
        return COR_OVERDUE 
    elif 'SLA_Alerta' in row and row['SLA_Alerta']:
        return COR_ALERT 
    else:
        return COR_SAFE 

def get_text_color(bg_color):
    return 'black' if bg_color == COR_ALERT else 'white'

def highlight_sla(row):
    bg_color = obter_dados_cor(row)
    text_color = get_text_color(bg_color)
    return [f'background-color: {bg_color}; color: {text_color}; font-weight: bold'] * len(row)


# ---- CRIAR MAPA FOLIUM COM ROTAS ----
def criar_mapa_folium(df_mapa):
    if df_mapa.empty:
        return folium.Map(location=[-15.788497, -47.879873], zoom_start=4)

    map_center = [df_mapa[COLUNA_LATITUDE].mean(), df_mapa[COLUNA_LONGITUDE].mean()]
    m = folium.Map(location=map_center, zoom_start=12)

    # 1. Desenha os Marcadores (Pontos)
    for idx, row in df_mapa.iterrows():
        prioridade = row.get('Prioridade', idx + 1)
        cor_fundo = obter_dados_cor(row)
        cor_texto = get_text_color(cor_fundo)
        cor_borda = cor_fundo 
        
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

    # 2. Desenha as Rotas (Linhas) por Técnico
    if COLUNA_TECNICO in df_mapa.columns:
        tecnicos_unicos = df_mapa[COLUNA_TECNICO].unique()
        
        # Cores para as rotas (cíclicas para diferenciar técnicos)
        cores_rota = ['#3388ff', '#ff3388', '#88ff33', '#33ffff', '#ff9933']
        
        for i, tecnico in enumerate(tecnicos_unicos):
            if pd.isna(tecnico): continue
            
            # Filtra os pontos deste técnico, mantendo a ordem de prioridade
            df_rota = df_mapa[df_mapa[COLUNA_TECNICO] == tecnico]
            
            # Extrai coordenadas como lista de tuplas
            pontos_rota = df_rota[[COLUNA_LATITUDE, COLUNA_LONGITUDE]].values.tolist()
            
            if len(pontos_rota) > 1:
                cor_linha = cores_rota[i % len(cores_rota)]
                folium.PolyLine(
                    locations=pontos_rota,
                    color=cor_linha,
                    weight=3,
                    opacity=0.7,
                    dash_array='5, 10', # Linha tracejada para indicar sugestão
                    tooltip=f"Rota Sugerida: {tecnico}"
                ).add_to(m)

    # 3. Legenda Semáforo
    template_legenda = f"""
    {{% macro html(this, kwargs) %}}
    <div style="
        position: fixed; 
        bottom: 30px; left: 30px; width: auto; height: auto; 
        z-index:9999; font-size:13px; font-family: sans-serif;
        background-color: white; border: 2px solid #666; border-radius: 8px;
        padding: 10px; opacity: 0.95; box-shadow: 3px 3px 5px rgba(0,0,0,0.3);
        ">
        <b style="font-size:14px;">Legenda (Semáforo SLA)</b><br><hr style="margin: 5px 0;">
        <i style="background:{COR_SAFE}; width:12px; height:12px; display:inline-block; border-radius:50%; margin-right:5px;"></i> &nbsp; **Verde:** No Prazo<br>
        <i style="background:{COR_ALERT}; width:12px; height:12px; display:inline-block; border-radius:50%; margin-right:5px;"></i> &nbsp; **Amarelo:** Alerta (< 4h)<br>
        <i style="background:{COR_OVERDUE}; width:12px; height:12px; display:inline-block; border-radius:50%; margin-right:5px;"></i> &nbsp; **Vermelho:** Vencido<br>
        <hr style="margin: 5px 0;">
        <span style="border-bottom: 2px dashed grey;">---</span> &nbsp; Rota Sugerida
    </div>
    {{% endmacro %}}
    """
    macro = MacroElement()
    macro._template = Template(template_legenda)
    m.get_root().add_child(macro)

    return m
