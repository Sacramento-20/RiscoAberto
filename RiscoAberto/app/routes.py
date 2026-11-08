from flask import jsonify, render_template, request
from app.utils import get_bairros_geojson, get_areas_inundacao_geojson, consultar_bairro

def register_routes(app):

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