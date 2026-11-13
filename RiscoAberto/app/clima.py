"""
Consulta das condições do tempo em um ponto de Belo Horizonte.

Fonte: Open-Meteo (https://open-meteo.com) — gratuita para uso não
comercial e sem chave de API. Os valores são estimativas de modelo
meteorológico para a coordenada informada (grade de ~1 a 11 km),
não medições de estação. Para medições oficiais, a mesma interface
pode ser trocada pela API do INMET (exige token).
"""

import time
from datetime import datetime, timedelta

import requests


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
TIMEZONE = "America/Sao_Paulo"
TIMEOUT_SEGUNDOS = 8
CACHE_SEGUNDOS = 600  # 10 minutos: o modelo não muda mais rápido que isso

# Limites aproximados do município de Belo Horizonte (WGS84),
# com uma pequena margem.
BH_LAT_MIN, BH_LAT_MAX = -20.08, -19.75
BH_LON_MIN, BH_LON_MAX = -44.08, -43.84

# Códigos WMO usados pelo Open-Meteo
DESCRICOES_WMO = {
    0: "Céu limpo",
    1: "Predominantemente limpo",
    2: "Parcialmente nublado",
    3: "Nublado",
    45: "Nevoeiro",
    48: "Nevoeiro com geada",
    51: "Garoa fraca",
    53: "Garoa moderada",
    55: "Garoa intensa",
    56: "Garoa congelante fraca",
    57: "Garoa congelante intensa",
    61: "Chuva fraca",
    63: "Chuva moderada",
    65: "Chuva forte",
    66: "Chuva congelante fraca",
    67: "Chuva congelante forte",
    71: "Neve fraca",
    73: "Neve moderada",
    75: "Neve forte",
    77: "Grãos de neve",
    80: "Pancadas de chuva fracas",
    81: "Pancadas de chuva moderadas",
    82: "Pancadas de chuva fortes",
    85: "Pancadas de neve fracas",
    86: "Pancadas de neve fortes",
    95: "Trovoada",
    96: "Trovoada com granizo fraco",
    99: "Trovoada com granizo forte",
}


class ClimaIndisponivel(Exception):
    """O serviço de clima não respondeu ou respondeu algo inesperado."""


_cache = {}


def dentro_de_bh(latitude, longitude):
    return (
        BH_LAT_MIN <= latitude <= BH_LAT_MAX
        and BH_LON_MIN <= longitude <= BH_LON_MAX
    )


def _chuva_ultimas_24h(hourly, momento_atual):
    """Soma a chuva horária das 24 h anteriores ao momento atual."""

    horas = hourly.get("time") or []
    valores = hourly.get("precipitation") or []

    inicio = momento_atual - timedelta(hours=24)
    total = 0.0

    for hora_txt, valor in zip(horas, valores):
        if valor is None:
            continue
        hora = datetime.fromisoformat(hora_txt)
        if inicio < hora <= momento_atual:
            total += float(valor)

    return round(total, 1)


def _montar_resposta(dados, latitude, longitude):
    atual = dados.get("current") or {}
    unidades = dados.get("current_units") or {}

    if "time" not in atual or "temperature_2m" not in atual:
        raise ClimaIndisponivel("Resposta do Open-Meteo sem dados atuais.")

    momento_atual = datetime.fromisoformat(atual["time"])
    codigo = atual.get("weather_code")

    return {
        "fonte": "Open-Meteo (estimativa de modelo meteorológico)",
        "fonte_url": "https://open-meteo.com",
        "latitude": round(latitude, 5),
        "longitude": round(longitude, 5),
        "atualizado_em": atual["time"],
        "fuso_horario": dados.get("timezone", TIMEZONE),
        "descricao": DESCRICOES_WMO.get(codigo, "Condição desconhecida"),
        "codigo_wmo": codigo,
        "temperatura_c": atual.get("temperature_2m"),
        "sensacao_termica_c": atual.get("apparent_temperature"),
        "umidade_relativa_pct": atual.get("relative_humidity_2m"),
        "precipitacao_mm": atual.get("precipitation"),
        "chuva_ultimas_24h_mm": _chuva_ultimas_24h(
            dados.get("hourly") or {}, momento_atual
        ),
        "vento_kmh": atual.get("wind_speed_10m"),
        "unidades": {
            "temperatura": unidades.get("temperature_2m", "°C"),
            "precipitacao": unidades.get("precipitation", "mm"),
            "vento": unidades.get("wind_speed_10m", "km/h"),
        },
    }


def obter_clima(latitude, longitude):
    """
    Retorna as condições atuais e a chuva acumulada nas últimas 24 h
    para a coordenada informada. Usa cache de 10 minutos por ponto.
    """

    chave = (round(latitude, 3), round(longitude, 3))
    agora = time.monotonic()

    em_cache = _cache.get(chave)
    if em_cache and agora - em_cache[0] < CACHE_SEGUNDOS:
        return em_cache[1]

    parametros = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ",".join([
            "temperature_2m",
            "apparent_temperature",
            "relative_humidity_2m",
            "precipitation",
            "weather_code",
            "wind_speed_10m",
        ]),
        "hourly": "precipitation",
        "past_days": 1,
        "forecast_days": 1,
        "timezone": TIMEZONE,
    }

    try:
        resposta = requests.get(
            OPEN_METEO_URL, params=parametros, timeout=TIMEOUT_SEGUNDOS
        )
        resposta.raise_for_status()
        dados = resposta.json()
    except (requests.RequestException, ValueError) as erro:
        raise ClimaIndisponivel(str(erro)) from erro

    resultado = _montar_resposta(dados, latitude, longitude)
    _cache[chave] = (agora, resultado)

    return resultado
