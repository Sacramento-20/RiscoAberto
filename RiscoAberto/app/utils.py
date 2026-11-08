
import json
from pathlib import Path
from functools import lru_cache

import pandas as pd
import geopandas as gpd
from shapely import wkt


# Caminho do CSV
from pathlib import Path

# Diretório raiz do projeto (RiscoAberto/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Caminhos dos arquivos CSV
CSV_PATH_BAIRROS = (
    BASE_DIR / "data" / "bairros" / "bairros_bh.csv"
)

CSV_INUNDACAO_PATH = (
    BASE_DIR / "data" / "registros_clima" / "AREA_RISCO_INUNDACAO.csv"
)

@lru_cache(maxsize=1)
def get_bairros_geojson():

    # 1. Lê o CSV
    df = pd.read_csv(CSV_PATH_BAIRROS)

    # 2. Remove espaços dos nomes das colunas
    df.columns = df.columns.str.strip()

    df_bairros= df.copy()
    if df_bairros.empty:
        raise ValueError("Nenhum bairro encontrado no CSV.")

    # 3. Converte WKT para geometrias Shapely
    df_bairros["geometry"] = df_bairros["GEOMETRIA"].apply(
        wkt.loads
    )

    # 4. Cria o GeoDataFrame
    gdf_bairros = gpd.GeoDataFrame(
        df_bairros.drop(columns=["GEOMETRIA"]),
        geometry="geometry",
        crs="EPSG:31983"
    )

    # 5. Converte campos numéricos
    for coluna in ["AREA_KM2", "PERIMETR_M"]:
        gdf_bairros[coluna] = pd.to_numeric(
            gdf_bairros[coluna],
            errors="coerce"
        )

    # 6. Converte para WGS84
    gdf_bairros = gdf_bairros.to_crs(epsg=4326)

    # 7. Converte para GeoJSON
    geojson = json.loads(
        gdf_bairros.to_json(drop_id=True)
    )

    return geojson


@lru_cache(maxsize=1)
def get_areas_inundacao_geojson():

    # 1. Lê o CSV
    df = pd.read_csv(CSV_INUNDACAO_PATH)

    df.columns = df.columns.str.strip()

    # 2. Verifica as colunas necessárias
    colunas_obrigatorias = [
        "FID",
        "ID_ARG",
        "RISCO_GEOLOGICO",
        "GEOMETRIA"
    ]

    faltantes = [
        coluna for coluna in colunas_obrigatorias
        if coluna not in df.columns
    ]

    if faltantes:
        raise ValueError(
            f"Colunas ausentes no CSV: {faltantes}"
        )

    # 3. Remove registros sem geometria
    df = df.dropna(subset=["GEOMETRIA"]).copy()

    # 4. Converte WKT para geometrias Shapely
    df["geometry"] = df["GEOMETRIA"].apply(wkt.loads)

    # 5. Cria GeoDataFrame
    gdf = gpd.GeoDataFrame(
        df[[
            "FID",
            "ID_ARG",
            "RISCO_GEOLOGICO"
        ]],
        geometry=df["geometry"],
        crs="EPSG:31983"
    )

    # 6. Converte para WGS84
    gdf = gdf.to_crs(epsg=4326)

    # 7. Converte para GeoJSON
    geojson = json.loads(
        gdf.to_json(drop_id=True)
    )

    return geojson

def consultar_bairro(nome_bairro: str) -> str:

    bairro = nome_bairro.strip()

    mensagem = (
        f"O bairro: {bairro} foi selecionado - Resposta Backend"
    )

    return mensagem