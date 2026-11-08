from app import app
from app.routes import register_routes

register_routes(app)

if __name__ == '__main__':
    app.run(debug=True)