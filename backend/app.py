import os

from flask import Flask, jsonify
from flask_cors import CORS
from flask_login import LoginManager

from auth import auth_bp
from config import Config
from generate import generate_bp
from models import User, db
from samples import samples_bp

FRONTEND_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")


def create_app():
    app = Flask(__name__, static_folder=FRONTEND_FOLDER, static_url_path="")
    app.config.from_object(Config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["GENERATED_FOLDER"], exist_ok=True)

    db.init_app(app)

    # CORS нужен, только если вы запускаете фронтенд отдельно от бэкенда (другой порт/домен).
    # Если фронтенд отдаётся этим же Flask-приложением (по умолчанию), CORS не требуется.
    CORS(app, supports_credentials=True)

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify(error="Требуется авторизация"), 401

    app.register_blueprint(auth_bp)
    app.register_blueprint(samples_bp)
    app.register_blueprint(generate_bp)

    with app.app_context():
        db.create_all()

    # Отдаём фронтенд (index.html и статику) с того же сервера
    @app.route("/")
    def index():
        return app.send_static_file("index.html")

    @app.errorhandler(404)
    def not_found(e):
        # для SPA: неизвестные не-API пути отдаём на index.html
        from flask import request

        if not request.path.startswith("/api/"):
            return app.send_static_file("index.html")
        return jsonify(error="Не найдено"), 404

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
