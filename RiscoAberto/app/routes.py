from flask import jsonify, render_template
from app.utils import get_hello_message

def register_routes(app):
    @app.route('/api/hello', methods=['GET'])
    def api_hello():
        mensagem = get_hello_message()
        
        return jsonify({
            'status': 'sucesso',
            'mensagem': mensagem
        })

    @app.route('/')
    def page():
        resultado = get_hello_message()
        return render_template('page.html', saida_funcao=resultado)