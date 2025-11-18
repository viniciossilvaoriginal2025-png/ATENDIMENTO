import pandas as pd
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from tqdm import tqdm # Para a barra de progresso
import time
import os

# --- Nomes das colunas do seu arquivo (Linha 2) ---
# ATENÇÃO: Verifique se os nomes abaixo batem EXATAMENTE
# com os cabeçalhos da sua Linha 2 (especialmente "Cidade" e "UF")

COL_LOGRADOURO = "Logradouro"       # Coluna F2
COL_NUMERO = "Numero Endereco"  # Coluna G2
COL_BAIRRO = "Bairro"           # Coluna I2
COL_CIDADE = "Cidade"           # Coluna J2 (Confirme que não tem espaço, ex: " Cidade")
COL_UF = "UF"               # Coluna K2 (Confirme que é "UF" e não "F")
# --- Colunas novas que vamos criar ---
COL_LATITUDE = "latitude"
COL_LONGITUDE = "longitude"

def geocode_address(geolocator, address, attempts=3):
    """Tenta encontrar a coordenada de um endereço, com retentativas."""
    try:
        location = geolocator.geocode(address, timeout=10)
        if location:
            return location.latitude, location.longitude
        else:
            return None, None
    except GeocoderTimedOut:
        time.sleep(1)
        if attempts > 0:
            return geocode_address(geolocator, address, attempts - 1)
        return None, None
    except GeocoderUnavailable:
        time.sleep(5) 
        if attempts > 0:
            return geocode_address(geolocator, address, attempts - 1)
        return None, None
    except Exception:
        return None, None

def main():
    print("--- Script de Preparação de Mapa ---")
    
    input_file = input("Por favor, arraste seu arquivo Excel original para esta janela e aperte Enter: ")
    input_file = input_file.strip().strip('"') 

    if not os.path.exists(input_file):
        print(f"Erro: Arquivo não encontrado em '{input_file}'")
        return

    output_file = "relatorio_com_mapa.xlsx"
    print(f"Lendo o arquivo: {input_file}")
    
    # --- CORREÇÃO AQUI ---
    # Adicionado 'header=1' para ler os cabeçalhos da Linha 2
    try:
        df = pd.read_excel(input_file, header=1)
    except Exception as e:
        print(f"Erro ao ler o arquivo Excel: {e}")
        return
    
    # Verifica se as colunas de endereço existem
    colunas_endereco_necessarias = [COL_LOGRADOURO, COL_NUMERO, COL_BAIRRO, COL_CIDADE, COL_UF]
    colunas_faltando = [col for col in colunas_endereco_necessarias if col not in df.columns]
    
    if colunas_faltando:
        print("\n--- ERRO ---")
        print("Não consegui encontrar as seguintes colunas de endereço no seu arquivo:")
        print(f"{', '.join(colunas_faltando)}")
        print("Por favor, abra o 'geocode.py' e corrija os nomes das colunas (ex: COL_CIDADE) no topo do script.")
        print("Lembre-se de verificar espaços e maiúsculas/minúsculas.")
        return

    if COL_LATITUDE not in df.columns or COL_LONGITUDE not in df.columns:
        df[COL_LATITUDE] = pd.NA
        df[COL_LONGITUDE] = pd.NA
    else:
        print("Colunas de mapa já existem. Preenchendo apenas as vazias...")

    geolocator = Nominatim(user_agent="meu_dashboard_streamlit_app")
    print("Iniciando a busca por coordenadas (Isso pode demorar vários minutos)...")
    
    tqdm.pandas(desc="Geocodificando endereços")
    
    df_para_processar = df[df[COL_LATITUDE].isna()].copy()

    if df_para_processar.empty:
        print("Nenhuma coordenada faltando. Arquivo já está completo.")
        # Mesmo assim, salva o arquivo para garantir que está no formato correto
    else:
        def processar_linha(linha):
            address_parts = [
                str(linha[COL_LOGRADOURO]),
                str(linha[COL_NUMERO]),
                str(linha[COL_BAIRRO]),
                str(linha[COL_CIDADE]),
                str(linha[COL_UF]),
                "Brasil"
            ]
            full_address = ", ".join(part for part in address_parts if pd.notna(part) and str(part) != 'nan')
            
            lat, lon = geocode_address(geolocator, full_address)
            return lat, lon

        coords = df_para_processar.progress_apply(processar_linha, axis=1)
        
        df.loc[df[COL_LATITUDE].isna(), COL_LATITUDE] = [c[0] for c in coords]
        df.loc[df[COL_LONGITUDE].isna(), COL_LONGITUDE] = [c[1] for c in coords]

    try:
        df.to_excel(output_file, index=False)
        print(f"\nSucesso! Seu novo arquivo está salvo como: '{output_file}'")
        print("Use ESTE NOVO ARQUIVO para subir no seu dashboard.")
    except Exception as e:
        print(f"\nErro ao salvar o arquivo: {e}")
        print("Verifique se você fechou o arquivo 'relatorio_com_mapa.xlsx' antes de rodar o script.")

if __name__ == "__main__":
    main()
