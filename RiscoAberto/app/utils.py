
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

def _normalizar_nome(texto: str) -> str:
    """Ignora acentos, maiúsculas e espaços extras (igual ao frontend)."""

    import unicodedata

    texto = unicodedata.normalize("NFD", str(texto or ""))
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")

    return " ".join(texto.lower().split())


@lru_cache(maxsize=1)
def _pontos_bairros():
    """
    Ponto representativo de cada região do CSV de bairros.

    Retorna dois dicionários de (nome, latitude, longitude):
      - por_id:   chave = coluna _id (única)
      - por_nome: chave = nome normalizado

    O CSV tem nomes repetidos (ex.: "Califórnia" é Bairro e também
    Vila). Na busca por nome, prevalece o registro do TIPO "Bairro".

    O ponto é calculado no CRS projetado (EPSG:31983) e fica sempre
    dentro do polígono, ao contrário do centroide em formas irregulares.
    """

    df = pd.read_csv(CSV_PATH_BAIRROS)
    df.columns = df.columns.str.strip()

    gdf = gpd.GeoDataFrame(
        df[["_id", "TIPO", "NOME"]],
        geometry=df["GEOMETRIA"].apply(wkt.loads),
        crs="EPSG:31983"
    )

    pontos = gdf.geometry.representative_point().to_crs(epsg=4326)

    por_id = {}
    por_nome = {}

    # Registros do tipo "Bairro" por último, para sobrescreverem
    # homônimos de outros tipos no dicionário por nome.
    ordem = sorted(
        range(len(gdf)),
        key=lambda i: gdf["TIPO"].iloc[i] == "Bairro"
    )

    for i in ordem:
        nome = str(gdf["NOME"].iloc[i]).strip()
        ponto = pontos.iloc[i]
        registro = (nome, ponto.y, ponto.x)

        por_id[str(gdf["_id"].iloc[i])] = registro
        por_nome[_normalizar_nome(nome)] = registro

    return por_id, por_nome


def localizar_bairro(nome_bairro: str = None, id_bairro=None):
    """
    Retorna (nome, latitude, longitude) do bairro ou None.
    Prefira id_bairro (coluna _id): nomes podem se repetir.
    """

    por_id, por_nome = _pontos_bairros()

    if id_bairro is not None:
        return por_id.get(str(id_bairro).strip())

    return por_nome.get(_normalizar_nome(nome_bairro))


def consultar_bairro(nome_bairro: str) -> str:

    bairro = nome_bairro.strip()

    mensagem = (
        f"O bairro: {bairro} foi selecionado - Resposta Backend"
    )

    return mensagem