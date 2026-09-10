import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS

import models.database as d
from controllers.aluno_controller import aluno_controller
from controllers.desafio_controller import desafio_controller
from controllers.tema_controller import tema_controller
from controllers.questao_controller import questao_controller
from controllers.ranking_controller import ranking_controller
from controllers.desafio_questao_controller import desafio_questao_controller
from controllers.aluno_desafio_controller import aluno_desafio_controller

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def create_app(test_config=None):
    frontend_path = (BASE_DIR / ".." / "frontend").resolve()
    app = Flask(__name__, static_folder=str(frontend_path), static_url_path="")

    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///explainer.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config:
        app.config.update(test_config)

    database_url = app.config["SQLALCHEMY_DATABASE_URI"]
    if database_url.startswith("sqlite"):
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "connect_args": {"check_same_thread": False}
        }

    d.db.init_app(app)

    cors_origins = os.getenv("CORS_ORIGINS", "*")
    CORS(app, resources={r"/*": {"origins": cors_origins}})

    app.register_blueprint(aluno_controller)
    app.register_blueprint(desafio_controller)
    app.register_blueprint(tema_controller)
    app.register_blueprint(questao_controller)
    app.register_blueprint(ranking_controller)
    app.register_blueprint(desafio_questao_controller)
    app.register_blueprint(aluno_desafio_controller)

    @app.get("/")
    def frontend_home():
        return app.send_static_file("index.html")

    @app.get("/api")
    def api_home():
        return jsonify({
            "mensagem": "API do ExplAIner - Sistema de Gamificação Educacional",
            "rotas": {
                "alunos": [
                    "GET /alunos",
                    "GET /alunos/<id>",
                    "POST /alunos",
                    "PUT /alunos/<id>",
                    "DELETE /alunos/<id>",
                    "GET /alunos/ranking",
                ],
                "temas": ["GET /temas", "POST /temas", "PUT /temas/<id>", "DELETE /temas/<id>"],
                "desafios": ["GET /desafio", "POST /desafio", "PUT /desafio/<id>", "DELETE /desafio/<id>"],
                "questoes": [
                    "GET /questoes",
                    "POST /questoes",
                    "PUT /questoes/<id>",
                    "DELETE /questoes/<id>",
                    "POST /questoes/<id>/verificar",
                ],
                "ranking": ["GET /ranking", "POST /ranking", "PUT /ranking/<id>", "DELETE /ranking/<id>"],
            },
        })

    with app.app_context():
        d.db.create_all()

    return app


app = create_app()


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "False").lower() in {"1", "true", "yes", "on"}
    app.run(debug=debug)
