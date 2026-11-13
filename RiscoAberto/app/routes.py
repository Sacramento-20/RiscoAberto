from flask import jsonify, render_template, request
from app.utils import (
    get_bairros_geojson,
    get_areas_inundacao_geojson,
    consultar_bairro,
    localizar_bairro,
)
from app.clima import obter_clima, dentro_de_bh, ClimaIndisponivel

def register_routes(app):

    @app.route("/api/clima", methods=["GET"])
    def api_clima():
        """
        Condições do tempo agora em uma região de BH.

        Uso (um dos três):
            /api/clima?id=217              (coluna _id do CSV; recomendado)
            /api/clima?bairro=Califórnia   (nome; homônimos -> TIPO Bairro)
            /api/clima?lat=-19.93&lon=-43.94
        """

        id_bairro = (request.args.get("id") or "").strip()
        nome_bairro = (request.args.get("bairro") or "").strip()
        lat_txt = request.args.get("lat")
        lon_txt = request.args.get("lon")

        bairro = None

        if id_bairro or nome_bairro:

            if id_bairro:
                encontrado = localizar_bairro(id_bairro=id_bairro)
            else:
                encontrado = localizar_bairro(nome_bairro)

            if encontrado is None:
                return jsonify({
                    "status": "erro",
                    "mensagem": f"Bairro não encontrado: {id_bairro or nome_bairro}"
                }), 404

            bairro, latitude, longitude = encontrado

        elif lat_txt is not None and lon_txt is not None:

            try:
                latitude = float(lat_txt)
                longitude = float(lon_txt)
            except ValueError:
                return jsonify({
                    "status": "erro",
                    "mensagem": "lat e lon devem ser números."
                }), 400

            if not dentro_de_bh(latitude, longitude):
                return jsonify({
                    "status": "erro",
                    "mensagem": "Coordenada fora de Belo Horizonte."
                }), 400

        else:
            return jsonify({
                "status": "erro",
                "mensagem": "Informe ?id=<_id>, ?bairro=<nome> ou ?lat=<lat>&lon=<lon>."
            }), 400

        try:
            clima = obter_clima(latitude, longitude)
        except ClimaIndisponivel:
            return jsonify({
                "status": "erro",
                "mensagem": "Serviço de clima indisponível no momento."
            }), 503

        return jsonify({
            "status": "sucesso",
            "bairro": bairro,
            "clima": clima
        }), 200

    @app.route("/")
    def page():
        return render_template("pagina.html")

    @app.route("/api/bairros/geojson", methods=["GET"])
    def api_bairros_geojson():

        geojson = get_bairros_geojson()

        return jsonify(geojson)

    @app.route("/api/areas-inundacao/geojson", methods=["GET"])
    def api_areas_inundacao_geojson():

        geojson = get_areas_inundacao_geojson()

        return jsonify(geojson)

    @app.route("/api/bairros/selecionado", methods=["POST"])
    def api_bairro_selecionado():

        # Recebe os dados enviados pelo frontend
        dados = request.get_json(silent=True) or {}

        nome_bairro = dados.get("nome_bairro")

        # Validação da entrada
        if not isinstance(nome_bairro, str) or not nome_bairro.strip():

            return jsonify({
                "status": "erro",
                "mensagem": "Nome do bairro não informado."
            }), 400

        # Chama a função responsável pelo processamento
        nome_bairro = nome_bairro.strip()

        mensagem = consultar_bairro(nome_bairro)

        # Retorna a resposta para o frontend
        return jsonify({
            "status": "sucesso",
            "nome_bairro": nome_bairro,
            "mensagem": mensagem
        }), 200

    @app.route("/api/bairros/selecionado", methods=["GET"])
    def api_bairro_selecionado_get():

        nome_bairro = request.args.get("nome_bairro")

        if not nome_bairro or not nome_bairro.strip():
            return jsonify({
                "status": "erro",
                "mensagem": "Nome do bairro não informado."
            }), 400

        nome_bairro = nome_bairro.strip()

        mensagem = consultar_bairro(nome_bairro)

        return jsonify({
            "status": "sucesso",
            "nome_bairro": nome_bairro,
            "mensagem": mensagem
        }), 200