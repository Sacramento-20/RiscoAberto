"""
Testes da rota /api/clima.

Rodar a partir da pasta RiscoAberto/:
    python -m unittest discover -s tests -v

A chamada ao Open-Meteo é simulada (mock), então os testes não
dependem de internet.
"""

import unittest
from unittest import mock

import requests

from app import app
from app.routes import register_routes
from app import clima as clima_mod
from app.utils import localizar_bairro


register_routes(app)


def resposta_open_meteo():
    """Resposta no formato do Open-Meteo, reduzida."""

    horas = [f"2026-11-07T{h:02d}:00" for h in range(24)] + \
            [f"2026-11-08T{h:02d}:00" for h in range(24)]
    chuva = [0.0] * 48
    chuva[16] = 5.0   # 07/11 16:00 -> fora (janela começa 07/11 16:45)
    chuva[17] = 0.5   # 07/11 17:00 -> dentro
    chuva[30] = 2.5   # 08/11 06:00 -> dentro
    chuva[40] = 1.0   # 08/11 16:00 -> dentro (hora atual)
    chuva[41] = 9.0   # 08/11 17:00 -> futuro, não entra

    return {
        "timezone": "America/Sao_Paulo",
        "current_units": {
            "temperature_2m": "°C",
            "precipitation": "mm",
            "wind_speed_10m": "km/h",
        },
        "current": {
            "time": "2026-11-08T16:45",
            "temperature_2m": 24.3,
            "apparent_temperature": 25.1,
            "relative_humidity_2m": 71,
            "precipitation": 0.4,
            "weather_code": 80,
            "wind_speed_10m": 9.7,
        },
        "hourly": {"time": horas, "precipitation": chuva},
    }


class TesteClima(unittest.TestCase):

    def setUp(self):
        clima_mod._cache.clear()
        self.client = app.test_client()

    def _mock_get(self, payload=None, erro=None):
        resposta = mock.Mock()
        resposta.raise_for_status.return_value = None
        resposta.json.return_value = payload or resposta_open_meteo()
        if erro:
            return mock.patch.object(clima_mod.requests, "get", side_effect=erro)
        return mock.patch.object(clima_mod.requests, "get", return_value=resposta)

    def test_localiza_bairro_sem_acento_e_maiusculas(self):
        nome, lat, lon = localizar_bairro("  LINDEIA ")
        self.assertEqual(nome, "Lindéia")
        self.assertTrue(clima_mod.dentro_de_bh(lat, lon))

    def test_homonimo_por_nome_prefere_tipo_bairro(self):
        # "Califórnia" existe como Bairro (_id 217) e como Vila (_id 138)
        self.assertEqual(
            localizar_bairro("Califórnia"),
            localizar_bairro(id_bairro=217),
        )
        self.assertNotEqual(
            localizar_bairro(id_bairro=217),
            localizar_bairro(id_bairro=138),
        )

    def test_clima_por_id(self):
        with self._mock_get():
            r = self.client.get("/api/clima?id=138")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["bairro"], "Califórnia")

    def test_id_inexistente(self):
        r = self.client.get("/api/clima?id=999999")
        self.assertEqual(r.status_code, 404)

    def test_geojson_de_bairros_expoe_id(self):
        props = self.client.get("/api/bairros/geojson").get_json()["features"][0]["properties"]
        self.assertIn("_id", props)

    def test_todos_os_bairros_ficam_dentro_de_bh(self):
        from app.utils import _pontos_bairros
        for nome, lat, lon in _pontos_bairros()[0].values():
            self.assertTrue(clima_mod.dentro_de_bh(lat, lon), nome)

    def test_clima_por_bairro(self):
        with self._mock_get() as get:
            r = self.client.get("/api/clima?bairro=lindeia")

        self.assertEqual(r.status_code, 200)
        dados = r.get_json()
        self.assertEqual(dados["bairro"], "Lindéia")

        c = dados["clima"]
        self.assertEqual(c["temperatura_c"], 24.3)
        self.assertEqual(c["descricao"], "Pancadas de chuva fracas")
        # Agora = 08/11 16:45 -> entram 07/11 17:00 (0,5), 08/11 06:00 (2,5) e 16:00 (1,0)
        self.assertEqual(c["chuva_ultimas_24h_mm"], 4.0)

        # A coordenada enviada ao Open-Meteo é a do bairro
        params = get.call_args.kwargs["params"]
        self.assertAlmostEqual(params["latitude"], c["latitude"], places=4)

    def test_clima_por_coordenada(self):
        with self._mock_get():
            r = self.client.get("/api/clima?lat=-19.93&lon=-43.94")
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.get_json()["bairro"])

    def test_cache_evita_segunda_chamada(self):
        with self._mock_get() as get:
            self.client.get("/api/clima?bairro=Lindéia")
            self.client.get("/api/clima?bairro=Lindéia")
        self.assertEqual(get.call_count, 1)

    def test_bairro_inexistente(self):
        r = self.client.get("/api/clima?bairro=Bairro Que Nao Existe")
        self.assertEqual(r.status_code, 404)

    def test_coordenada_fora_de_bh(self):
        r = self.client.get("/api/clima?lat=-23.55&lon=-46.63")
        self.assertEqual(r.status_code, 400)

    def test_sem_parametros(self):
        r = self.client.get("/api/clima")
        self.assertEqual(r.status_code, 400)

    def test_coordenada_invalida(self):
        r = self.client.get("/api/clima?lat=abc&lon=-43.9")
        self.assertEqual(r.status_code, 400)

    def test_servico_fora_do_ar(self):
        with self._mock_get(erro=requests.ConnectionError("sem rede")):
            r = self.client.get("/api/clima?bairro=Lindéia")
        self.assertEqual(r.status_code, 503)

    def test_metadados_dublin_core_e_iso19115(self):
        r = self.client.get("/api/metadados")
        self.assertEqual(r.status_code, 200)
        dados = r.get_json()
        self.assertIn("dublin_core", dados)
        self.assertIn("iso_19115_mgb", dados)
        self.assertIn("gestao_arquivistica_earq", dados)

    def test_areas_sbn_geojson(self):
        r = self.client.get("/api/areas-sbn/alagamento/geojson")
        self.assertEqual(r.status_code, 200)
        dados = r.get_json()
        self.assertEqual(dados["type"], "FeatureCollection")
        self.assertGreater(len(dados["features"]), 0)

        r_invalido = self.client.get("/api/areas-sbn/inexistente/geojson")
        self.assertEqual(r_invalido.status_code, 400)

    def test_diagnostico_bairro_selecionado(self):
        r = self.client.post(
            "/api/bairros/selecionado",
            json={"nome_bairro": "Califórnia", "id_bairro": 217},
        )
        self.assertEqual(r.status_code, 200)
        dados = r.get_json()
        self.assertEqual(dados["status"], "sucesso")
        self.assertIn("diagnostico", dados)
        self.assertEqual(dados["diagnostico"]["id"], 217)


if __name__ == "__main__":
    unittest.main()
