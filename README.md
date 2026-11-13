# RiscoAberto

## Clima por região (`/api/clima`)

Mostra as condições do tempo agora em um bairro de Belo Horizonte: descrição, temperatura, sensação térmica, umidade, vento, chuva no momento e chuva acumulada nas últimas 24 h. Na página, aparece no painel ao selecionar um bairro.

```
GET /api/clima?id=217                 # coluna _id do CSV de bairros (recomendado)
GET /api/clima?bairro=Lindéia         # nome; acentos e maiúsculas são ignorados
GET /api/clima?lat=-19.93&lon=-43.94  # coordenada dentro de BH
```

- **Fonte:** [Open-Meteo](https://open-meteo.com), gratuita para uso não comercial e sem chave. Os valores são estimativas de modelo para o ponto do bairro, não medições de estação. Para medições oficiais, dá para trocar a fonte em `app/clima.py` pela API do INMET, que exige token.
- **Ponto consultado:** um ponto interno de cada polígono (`representative_point`), calculado em EPSG:31983.
- **Nomes repetidos:** o CSV tem 20 nomes repetidos (ex.: "Califórnia" é Bairro e também Vila). A página consulta pelo `_id`; na busca por nome, prevalece o TIPO "Bairro".
- **Cache:** 10 minutos por ponto, para não repetir chamadas ao Open-Meteo.
- **Erros:** 400 (parâmetro inválido ou fora de BH), 404 (bairro não encontrado), 503 (Open-Meteo fora do ar).

Testes (simulam o Open-Meteo, não precisam de internet), rodando a partir da pasta `RiscoAberto/`:

```
python -m unittest discover -s tests -v
```
