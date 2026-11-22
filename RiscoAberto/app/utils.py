
import json
from pathlib import Path
from functools import lru_cache

import pandas as pd
import geopandas as gpd
from shapely import wkt


# Diretório raiz do projeto (RiscoAberto/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Caminhos dos arquivos CSV
CSV_PATH_BAIRROS = (
    BASE_DIR / "data" / "bairros" / "bairros_bh.csv"
)

CSV_INUNDACAO_PATH = (
    BASE_DIR / "data" / "registros_clima" / "AREA_RISCO_INUNDACAO.csv"
)

# Bases de Áreas Prioritárias para Soluções Baseadas na Natureza (SBN)
TIPOS_SBN = {
    "alagamento": {
        "arquivo": "ALAGAMENTO_AREA_PRIORITARIA_SBN.csv",
        "rotulo": "Alagamento",
        "col_exp": "EXP_ALAG",
        "col_vul": "VUL_ALAG",
        "col_ac": "AC_ALAG",
        "col_sbn": "SBN_ALAG",
        "classe_pcd": "213",
    },
    "deslizamento": {
        "arquivo": "DESLIZAMENTO_TERRA_AREA_PRIORITARIA_SBN.csv",
        "rotulo": "Deslizamento de Terra",
        "col_exp": "EXP_DESL",
        "col_vul": "VUL_DESL",
        "col_ac": "AC_DESL",
        "col_sbn": "SBN_DESL",
        "classe_pcd": "221",
    },
    "inundacao": {
        "arquivo": "INUNDACAO_AREA_PRIORITARIA_SBN.csv",
        "rotulo": "Inundação (SBN)",
        "col_exp": "EXP_INUN",
        "col_vul": "VUL_INUN",
        "col_ac": "AC_INUN",
        "col_sbn": "SBN_INUN",
        "classe_pcd": "212",
    },
    "ondas_calor": {
        "arquivo": "ONDAS_CALOR_AREA_PRIORITARIA_SBN.csv",
        "rotulo": "Ondas de Calor",
        "col_exp": "EXP_ONDA",
        "col_vul": "VUL_ONDA",
        "col_ac": "AC_ONDA",
        "col_sbn": "SBN_ONDA",
        "classe_pcd": "231",
    },
}


def classificar_indice_sbn(valor: float) -> str:
    """
    Traduz o índice numérico SBN (escala 0 a 5) para um termo
    controlado de criticidade (Taxonomia de Criticidade).
    """
    if valor is None or pd.isna(valor) or valor <= 0:
        return "Sem registro"
    if valor >= 2.2:
        return "Muito Alto"
    if valor >= 1.7:
        return "Alto"
    if valor >= 1.2:
        return "Médio"
    return "Baixo"


@lru_cache(maxsize=1)
def _gdf_bairros_projetado():
    """Retorna o GeoDataFrame de bairros em EPSG:31983 (SIRGAS 2000 / UTM 23S)."""
    df = pd.read_csv(CSV_PATH_BAIRROS)
    df.columns = df.columns.str.strip()

    df_bairros = df.copy()
    if df_bairros.empty:
        raise ValueError("Nenhum bairro encontrado no CSV.")

    df_bairros["geometry"] = df_bairros["GEOMETRIA"].apply(wkt.loads)

    gdf_bairros = gpd.GeoDataFrame(
        df_bairros.drop(columns=["GEOMETRIA"]),
        geometry="geometry",
        crs="EPSG:31983",
    )

    for coluna in ["AREA_KM2", "PERIMETR_M"]:
        gdf_bairros[coluna] = pd.to_numeric(
            gdf_bairros[coluna],
            errors="coerce",
        )

    return gdf_bairros


@lru_cache(maxsize=1)
def _gdf_inundacao_projetado():
    """Retorna o GeoDataFrame de áreas de inundação em EPSG:31983."""
    df = pd.read_csv(CSV_INUNDACAO_PATH)
    df.columns = df.columns.str.strip()

    colunas_obrigatorias = [
        "FID",
        "ID_ARG",
        "RISCO_GEOLOGICO",
        "GEOMETRIA",
    ]

    faltantes = [
        coluna for coluna in colunas_obrigatorias
        if coluna not in df.columns
    ]

    if faltantes:
        raise ValueError(f"Colunas ausentes no CSV: {faltantes}")

    df = df.dropna(subset=["GEOMETRIA"]).copy()
    df["geometry"] = df["GEOMETRIA"].apply(wkt.loads)

    return gpd.GeoDataFrame(
        df[["FID", "ID_ARG", "RISCO_GEOLOGICO"]],
        geometry=df["geometry"],
        crs="EPSG:31983",
    )


@lru_cache(maxsize=4)
def _gdf_sbn_projetado(tipo: str):
    """
    Carrega a malha de áreas prioritárias SBN em EPSG:31983 para o tipo
    solicitado, filtrando registros que possuem índice SBN ativo (> 0).
    """
    if tipo not in TIPOS_SBN:
        raise ValueError(f"Tipo SBN inválido: {tipo}")

    cfg = TIPOS_SBN[tipo]
    caminho = BASE_DIR / "data" / "registros_clima" / cfg["arquivo"]

    df = pd.read_csv(caminho)
    df.columns = df.columns.str.strip()
    df = df.dropna(subset=["GEOMETRIA"]).copy()

    col_exp = cfg["col_exp"]
    col_vul = cfg["col_vul"]
    col_ac = cfg["col_ac"]
    col_sbn = cfg["col_sbn"]

    for col in ["AREA_M2", col_exp, col_vul, col_ac, col_sbn]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[df[col_sbn].fillna(0) > 0].copy()
    df["geometry"] = df["GEOMETRIA"].apply(wkt.loads)

    df_out = pd.DataFrame({
        "FID": df["FID"],
        "ID_SBN": df["ID_AREAS_PRIORITARIAS_SBN_2022"],
        "TIPO_RISCO": cfg["rotulo"],
        "AREA_M2": df["AREA_M2"].round(1),
        "INDICE_EXPOSICAO": df[col_exp].round(2),
        "INDICE_VULNERABILIDADE": df[col_vul].round(2),
        "INDICE_PRIORIDADE_SBN": df[col_sbn].round(2),
        "NIVEL_CRITICIDADE": df[col_sbn].apply(classificar_indice_sbn),
    })

    return gpd.GeoDataFrame(
        df_out,
        geometry=df["geometry"],
        crs="EPSG:31983",
    )


@lru_cache(maxsize=1)
def _contagem_inundacao_por_bairro():
    """
    Cruza espacialmente (EPSG:31983) os bairros com as manchas de risco
    de inundação para indexação espacial de cada unidade territorial.
    """
    gdf_bairros = _gdf_bairros_projetado()
    gdf_inund = _gdf_inundacao_projetado()

    contagem = {}
    for _, row in gdf_bairros.iterrows():
        bid = str(row["_id"])
        geom = row.geometry
        n = int(gdf_inund.geometry.intersects(geom).sum())
        contagem[bid] = n

    return contagem


@lru_cache(maxsize=1)
def get_bairros_geojson():
    gdf_bairros = _gdf_bairros_projetado().copy()
    contagem_inund = _contagem_inundacao_por_bairro()

    # Identifica nomes homônimos para controle de vocabulário na interface
    contagem_nomes = gdf_bairros["NOME"].str.strip().value_counts()

    gdf_bairros["HOMONIMO"] = gdf_bairros["NOME"].str.strip().map(
        lambda n: bool(contagem_nomes.get(n, 0) > 1)
    )
    gdf_bairros["ROTULO_CONTROLADO"] = gdf_bairros.apply(
        lambda r: (
            f"{str(r['NOME']).strip()} ({str(r['TIPO']).strip()})"
            if r["HOMONIMO"]
            else str(r["NOME"]).strip()
        ),
        axis=1,
    )
    gdf_bairros["AREAS_INUNDACAO"] = gdf_bairros["_id"].astype(str).map(
        lambda bid: contagem_inund.get(bid, 0)
    )
    gdf_bairros["TEM_RISCO_INUNDACAO"] = gdf_bairros["AREAS_INUNDACAO"] > 0

    gdf_wgs84 = gdf_bairros.to_crs(epsg=4326)

    return json.loads(gdf_wgs84.to_json(drop_id=True))


@lru_cache(maxsize=1)
def get_areas_inundacao_geojson():
    gdf = _gdf_inundacao_projetado().to_crs(epsg=4326)
    return json.loads(gdf.to_json(drop_id=True))


@lru_cache(maxsize=4)
def get_areas_sbn_geojson(tipo: str, limite: int = 800):
    """
    Retorna em GeoJSON (EPSG:4326) as microáreas prioritárias SBN
    ordenadas pelas de maior índice de prioridade SBN.
    """
    gdf = _gdf_sbn_projetado(tipo).sort_values(
        by="INDICE_PRIORIDADE_SBN",
        ascending=False,
    )
    if limite and len(gdf) > limite:
        gdf = gdf.head(limite)

    gdf_wgs84 = gdf.to_crs(epsg=4326)
    return json.loads(gdf_wgs84.to_json(drop_id=True))


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


def consultar_bairro(nome_bairro: str, id_bairro=None) -> str:
    """
    Cruza espacialmente o polígono do bairro selecionado com as manchas
    de inundação e as microáreas SBN, gerando um boletim preventivo em
    linguagem cidadã acessível.
    """
    diag = diagnosticar_bairro(nome_bairro=nome_bairro, id_bairro=id_bairro)
    return diag["mensagem"]


@lru_cache(maxsize=64)
def diagnosticar_bairro(nome_bairro: str = None, id_bairro=None) -> dict:
    """
    Retorna diagnóstico estruturado e boletim cidadão do bairro (cruzando
    Bairros + Inundação + 4 dimensões SBN em EPSG:31983).
    """
    gdf_bairros = _gdf_bairros_projetado()

    registro = None
    if id_bairro is not None and str(id_bairro).strip():
        filtro = gdf_bairros[
            gdf_bairros["_id"].astype(str) == str(id_bairro).strip()
        ]
        if not filtro.empty:
            registro = filtro.iloc[0]

    if registro is None and nome_bairro:
        alvo = _normalizar_nome(nome_bairro)
        candidatos = gdf_bairros[
            gdf_bairros["NOME"].apply(_normalizar_nome) == alvo
        ]
        if not candidatos.empty:
            # Prefere TIPO == "Bairro" em caso de homônimos
            bairros_oficiais = candidatos[candidatos["TIPO"] == "Bairro"]
            registro = (
                bairros_oficiais.iloc[0]
                if not bairros_oficiais.empty
                else candidatos.iloc[0]
            )

    if registro is None:
        nome_limpo = (nome_bairro or "").strip() or "Selecionado"
        return {
            "nome": nome_limpo,
            "tipo": "Unidade Territorial",
            "manchas_inundacao": 0,
            "riscos_sbn": {},
            "nivel_geral": "Indefinido",
            "mensagem": f"Unidade territorial {nome_limpo}: sem geometria associada para cruzamento espacial.",
        }

    geom = registro.geometry
    nome_oficial = str(registro["NOME"]).strip()
    tipo_local = str(registro["TIPO"]).strip()
    bid = str(registro["_id"])

    # 1. Contagem de manchas de risco de inundação (Defesa Civil)
    manchas_inund = _contagem_inundacao_por_bairro().get(bid, 0)

    # 2. Índices médios e máximos de prioridade SBN dentro do bairro
    riscos_sbn = {}
    alertas = []

    for chave, cfg in TIPOS_SBN.items():
        gdf_sbn = _gdf_sbn_projetado(chave)
        inter = gdf_sbn[gdf_sbn.geometry.intersects(geom)]
        if not inter.empty:
            max_sbn = float(inter["INDICE_PRIORIDADE_SBN"].max())
            media_sbn = float(inter["INDICE_PRIORIDADE_SBN"].mean())
            nivel = classificar_indice_sbn(max_sbn)
            riscos_sbn[chave] = {
                "rotulo": cfg["rotulo"],
                "microareas_afetadas": int(len(inter)),
                "indice_maximo_sbn": round(max_sbn, 2),
                "indice_medio_sbn": round(media_sbn, 2),
                "criticidade": nivel,
            }
            if nivel in ("Alto", "Muito Alto"):
                alertas.append(f"{cfg['rotulo']} ({nivel}: máx. {max_sbn:.2f})")

    # 3. Geração do boletim preventivo em linguagem cidadã acessível
    if manchas_inund > 0:
        texto_inund = (
            f"Possui {manchas_inund} mancha(s) oficial(is) de risco de inundação mapeada(s) pela Defesa Civil."
        )
    else:
        texto_inund = (
            "Não possui manchas diretas de inundação fluvial na base de áreas de risco geológico."
        )

    linhas = [f"[{tipo_local} {nome_oficial}] {texto_inund}"]

    if alertas:
        linhas.append("Principais vulnerabilidades socioambientais (SBN):")
        for alerta in alertas:
            linhas.append(f"• {alerta}")
    else:
        linhas.append(
            "Apresenta criticidade baixa a moderada nas bases de vulnerabilidade climática (SBN)."
        )

    if manchas_inund > 0 or any("Alagamento" in a or "Inundação" in a for a in alertas):
        linhas.append(
            "Recomendação preventiva: em caso de chuva acumulada superior a 20 mm em 24h, evite trafegar em fundos de vale e vias marginais. Emergência: Defesa Civil (199)."
        )
    elif any("Deslizamento" in a for a in alertas):
        linhas.append(
            "Recomendação preventiva: observe sinais de trincas, inclinação de árvores/postes ou água barrenta em encostas durante períodos chuvosos. Emergência: Defesa Civil (199)."
        )
    else:
        linhas.append(
            "Recomendação preventiva: acompanhe os boletins meteorológicos e contribua para a arborização e permeabilidade do solo no bairro."
        )

    nivel_geral = (
        "Alto"
        if (manchas_inund > 0 or len(alertas) >= 2)
        else ("Médio" if len(alertas) == 1 else "Baixo")
    )

    return {
        "id": int(registro["_id"]),
        "nome": nome_oficial,
        "tipo": tipo_local,
        "manchas_inundacao": manchas_inund,
        "riscos_sbn": riscos_sbn,
        "nivel_geral": nivel_geral,
        "mensagem": "\n".join(linhas),
    }


def get_metadados_catalogo() -> dict:
    """
    Retorna os metadados descritivos (Dublin Core + ISO 19115 / MGB 2.0),
    o controle de vocabulário (Tesauro/Taxonomia) e os instrumentos de
    gestão arquivística (e-ARQ Brasil: PCD e Tabela de Temporalidade).
    """
    return {
        "padroes_adotados": [
            "Dublin Core (ISO 15836 / ANSI/NISO Z39.85)",
            "ISO 19115:2014 / Perfil MGB 2.0 (Metadados Geoespaciais do Brasil - INDE)",
            "e-ARQ Brasil (CONARQ - Gestão Arquivística de Documentos Digitais)",
            "ANSI/NISO Z39.19 (Diretrizes para Construção de Vocabulários Controlados)",
        ],
        "dublin_core": {
            "dc:title": "RiscoAberto — Plataforma Geoespacial de Riscos Hidrogeológicos e Climáticos de Belo Horizonte",
            "dc:creator": [
                "Prefeitura Municipal de Belo Horizonte (PRODABEL / BHGeo / DataBH)",
                "Subsecretaria de Proteção e Defesa Civil de Belo Horizonte",
                "Secretaria Municipal de Meio Ambiente (SMMA) / SUPLAN",
            ],
            "dc:subject": [
                "Inundação",
                "Alagamento",
                "Deslizamento de Terra",
                "Onda de Calor",
                "Soluções Baseadas na Natureza (SBN)",
                "Vulnerabilidade Socioambiental",
                "Defesa Civil",
                "Belo Horizonte",
            ],
            "dc:description": (
                "Conjunto integrado de dados geoespaciais e meteorológicos normalizados "
                "para prevenção de desastres socioambientais e inovação cívica no município de Belo Horizonte."
            ),
            "dc:publisher": "Projeto RiscoAberto — UFMG / ECI / Sistemas de Informação (OTI071)",
            "dc:date": "2026-11-15",
            "dc:type": "Dataset / InteractiveResource / Service",
            "dc:format": ["application/geo+json", "application/json", "text/csv"],
            "dc:identifier": "urn:ufmg:oti071:riscoaberto:bh:2026",
            "dc:source": [
                "https://dados.pbh.gov.br/",
                "https://api.open-meteo.com/v1/forecast",
            ],
            "dc:language": "pt-BR",
            "dc:coverage": "Belo Horizonte, Minas Gerais, Brasil",
            "dc:rights": "Creative Commons Attribution 4.0 International (CC-BY 4.0) / Dados Abertos Governamentais",
        },
        "iso_19115_mgb": {
            "gmd:referenceSystemInfo": {
                "crs_origem": "EPSG:31983 (SIRGAS 2000 / UTM zone 23S)",
                "crs_publicacao": "EPSG:4326 (WGS 84 - RFC 7946 GeoJSON)",
            },
            "gmd:spatialRepresentationType": "vector (Polygon, MultiPolygon, Point)",
            "gmd:EX_GeographicBoundingBox": {
                "westBoundLongitude": -44.08,
                "southBoundLatitude": -20.08,
                "eastBoundLongitude": -43.84,
                "northBoundLatitude": -19.75,
            },
            "gmd:LI_Lineage": (
                "Ingestão de arquivos CSV/WKT do Portal CKAN da PBH -> Limpeza de cabeçalhos e "
                "registros órfãos -> Conversão WKT para geometrias Shapely em EPSG:31983 -> "
                "Cálculo de ponto representativo interno (representative_point) -> Cruzamento "
                "espacial (intersects) -> Reprojeção geodésica para WGS84 (EPSG:4326)."
            ),
        },
        "controle_vocabulario_tesauro": {
            "teoria_classificacao": "Classificação Facetada PMEST (Ranganathan) + Taxonomia COBRADE",
            "desambiguacao_homonimos": (
                "Qualificador parentético (TIPO: Bairro | Vila | Conjunto) e identificador canônico (_id) "
                "para os 20 termos topográficos homônimos de Belo Horizonte."
            ),
            "termos_preferidos": [
                {
                    "descritor": "Inundação",
                    "termo_generico_TG": "Desastres Hidrológicos",
                    "usado_para_UP": ["Enchente", "Cheia fluvial", "Transbordamento de córrego"],
                    "termos_relacionados_TR": ["Alagamento", "Soluções Baseadas na Natureza (SBN)"],
                },
                {
                    "descritor": "Alagamento",
                    "termo_generico_TG": "Desastres Hidrológicos",
                    "usado_para_UP": ["Enxurrada urbana", "Acúmulo de água na via"],
                    "termos_relacionados_TR": ["Inundação", "Drenagem Urbana"],
                },
                {
                    "descritor": "Deslizamento de Terra",
                    "termo_generico_TG": "Desastres Geológicos",
                    "usado_para_UP": ["Escorregamento de encosta", "Desbarrancamento", "Queda de barreira"],
                    "termos_relacionados_TR": ["Declividade", "Precipitação Acumulada 24h"],
                },
                {
                    "descritor": "Onda de Calor",
                    "termo_generico_TG": "Desastres Climatológicos",
                    "usado_para_UP": ["Ilha de calor urbana", "Calor extremo"],
                    "termos_relacionados_TR": ["Arborização Urbana", "Condição Antrópica"],
                },
            ],
        },
        "gestao_arquivistica_earq": {
            "plano_classificacao_pcd": [
                {"codigo": "110", "serie": "Malha Oficial de Bairros, Vilas e Conjuntos de BH", "guarda": "Permanente"},
                {"codigo": "211", "serie": "Mapeamento de Áreas de Risco de Inundação (Defesa Civil)", "guarda": "Permanente"},
                {"codigo": "212", "serie": "Áreas Prioritárias SBN — Inundação", "guarda": "Permanente"},
                {"codigo": "213", "serie": "Áreas Prioritárias SBN — Alagamento", "guarda": "Permanente"},
                {"codigo": "221", "serie": "Áreas Prioritárias SBN — Deslizamento de Terra", "guarda": "Permanente"},
                {"codigo": "231", "serie": "Áreas Prioritárias SBN — Ondas de Calor", "guarda": "Permanente"},
                {"codigo": "310", "serie": "Coletas Meteorológicas Instantâneas em Cache (Open-Meteo)", "guarda": "Eliminação após 10 min (TTL = 600s)"},
            ]
        },
    }
