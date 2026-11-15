# RiscoAberto

Plataforma geoespacial aberta para monitoramento, organização da informação e prevenção de riscos hidrogeológicos e climáticos no município de Belo Horizonte (MG).

## Endpoints da API Aberta

### 1. Clima por região (`/api/clima`)

Mostra as condições do tempo agora em um bairro de Belo Horizonte: descrição (vocabulário controlado WMO), temperatura, sensação térmica, umidade, vento, chuva no momento e chuva acumulada nas últimas 24 h. Na página, aparece no painel ao selecionar um bairro.

```
GET /api/clima?id=217                 # coluna _id do CSV de bairros (recomendado)
GET /api/clima?bairro=Lindéia         # nome; acentos e maiúsculas são ignorados
GET /api/clima?lat=-19.93&lon=-43.94  # coordenada dentro de BH
```

- **Fonte:** [Open-Meteo](https://open-meteo.com), gratuita para uso não comercial e sem chave. Os valores são estimativas de modelo para o ponto do bairro, não medições de estação. Para medições oficiais, dá para trocar a fonte em `app/clima.py` pela API do INMET, que exige token.
- **Ponto consultado:** um ponto interno de cada polígono (`representative_point`), calculado em EPSG:31983.
- **Nomes repetidos (Controle de Homônimos):** o CSV tem 20 nomes repetidos (ex.: "Califórnia" é Bairro e também Vila). A página consulta pelo `_id` e exibe o qualificador parentético `ROTULO_CONTROLADO`; na busca por nome, prevalece o TIPO "Bairro".
- **Cache:** 10 minutos por ponto, para não repetir chamadas ao Open-Meteo.
- **Erros:** 400 (parâmetro inválido ou fora de BH), 404 (bairro não encontrado), 503 (Open-Meteo fora do ar).

### 2. Camadas Geoespaciais (`GeoJSON` — `EPSG:4326`)

```
GET /api/bairros/geojson                      # Malha de bairros, vilas e conjuntos + contagem de manchas de inundação
GET /api/areas-inundacao/geojson              # Áreas de risco de inundação (Defesa Civil)
GET /api/areas-sbn/alagamento/geojson         # Áreas prioritárias SBN - Alagamento
GET /api/areas-sbn/deslizamento/geojson       # Áreas prioritárias SBN - Deslizamento de Terra
GET /api/areas-sbn/inundacao/geojson          # Áreas prioritárias SBN - Inundação
GET /api/areas-sbn/ondas_calor/geojson        # Áreas prioritárias SBN - Ondas de Calor
```

### 3. Diagnóstico Territorial e Boletim Cidadão (`/api/bairros/selecionado`)

Cruza espacialmente o polígono do bairro (`EPSG:31983`) com as manchas de inundação da Defesa Civil e as 4 bases de Soluções Baseadas na Natureza (SBN), gerando um boletim preventivo em linguagem acessível:

```
GET  /api/bairros/selecionado?id=217
POST /api/bairros/selecionado   {"nome_bairro": "Califórnia", "id_bairro": 217}
```

### 4. Catálogo de Metadados e Gestão Arquivística (`/api/metadados`)

Retorna os descritores **Dublin Core (ISO 15836)**, **ISO 19115 / Perfil MGB 2.0**, o **Tesauro Funcional** e o **Plano de Classificação / Tabela de Temporalidade (e-ARQ Brasil / CONARQ)**:

```
GET /api/metadados
```

## Recuperação da Informação na Interface (`pagina.html`)

- **Operadores Lógicos Booleanos:** suporte a `AND` (ou `E`), `OR` (ou `OU`) e `NOT` (ou `NAO` / `-termo`). Exemplos: `Barreiro OR Lindeia`, `California NOT Vila`.
- **Filtros Facetados:** filtragem combinada por `TIPO` (`Bairro`, `Vila`, `Todos`) e presença de `Risco de Inundação`.

## Testes

Testes (simulam o Open-Meteo, não precisam de internet), rodando a partir da pasta `RiscoAberto/`:

```
python -m unittest discover -s tests -v
```
