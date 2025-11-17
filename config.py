import pandas as pd

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

# --- CONFIGURAÇÃO DE ALERTA E SLA ---
# Status correto que você informou
STATUS_ABERTOS = ["VISITA_AGENDADA"] 
SLA_SEGUNDOS = 24 * 60 * 60  # 24 horas
ALERTA_SEGUNDOS = 4 * 60 * 60 # 4 horas

# ---- FUNÇÃO HELPER DE FORMATAÇÃO DE TEMPO ----
def formatar_hms(segundos_totais):
    """Converte segundos totais (float/int) para uma string 'HH:MM:SS' com horas totais."""
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
    """Define a cor de fundo da linha se o SLA estiver estourado OU em alerta."""
    if linha['SLA_Estourado'] == True:
        # Cor VERMELHA (SLA > 24h)
        return ['background-color: #FFC7CE'] * len(linha) # Vermelho (Estourado)
    elif linha['SLA_Alerta'] == True:
        # Cor AMARELA (SLA vencendo em < 4h)
        return ['background-color: #FFF3CD'] * len(linha) # Amarelo (Alerta)
    else:
        return [''] * len(linha) # Sem estilo