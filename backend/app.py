import os
from flask import Flask, jsonify

import models.database as d
from controllers.aluno_controller import aluno_controller
from controllers.desafio_controller import desafio_controller
from controllers.tema_controller import tema_controller
from controllers.questao_controller import questao_controller
from controllers.ranking_controller import ranking_controller
from controllers.desafio_questao_controller import desafio_questao_controller
from controllers.aluno_desafio_controller import aluno_desafio_controller


def create_app():
    app = Flask(__name__)

    database_url = os.getenv("DATABASE_URL", "sqlite:///explainer.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if database_url.startswith("sqlite"):
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "connect_args": {"check_same_thread": False}
        }

    d.db.init_app(app)

    @app.after_request
    def adicionar_cors(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    # Registro de todos os Blueprints
    app.register_blueprint(aluno_controller)
    app.register_blueprint(desafio_controller)
    app.register_blueprint(tema_controller)
    app.register_blueprint(questao_controller)
    app.register_blueprint(ranking_controller)
    app.register_blueprint(desafio_questao_controller)
    app.register_blueprint(aluno_desafio_controller)

    @app.get("/")
    def home():
        return jsonify({
            "mensagem": "API Flask + SQLAlchemy - Sistema de Gamificação Educacional",
            "rotas": {
                "alunos": {
                    "listar": "GET /alunos",
                    "buscar": "GET /alunos/<id>",
                    "criar": "POST /alunos",
                    "atualizar": "PUT /alunos/<id>",
                    "deletar": "DELETE /alunos/<id>",
                },
                "desafios": {
                    "listar": "GET /desafio",
                    "buscar_por_nome": "GET /desafio/nome/<nome>",
                    "criar": "POST /desafio",
                    "atualizar": "PUT /desafio/<id>",
                    "deletar": "DELETE /desafio/<id>",
                },
                "temas": {
                    "listar": "GET /temas",
                    "criar": "POST /temas",
                    "atualizar": "PUT /temas/<id>",
                    "deletar": "DELETE /temas/<id>",
                },
                "questoes": {
                    "listar": "GET /questoes",
                    "criar": "POST /questoes",
                    "atualizar": "PUT /questoes/<id>",
                    "deletar": "DELETE /questoes/<id>",
                },
                "ranking": {
                    "listar": "GET /ranking",
                    "criar": "POST /ranking",
                    "atualizar": "PUT /ranking/<id>",
                    "deletar": "DELETE /ranking/<id>",
                },
                "desafio_questoes": {
                    "adicionar": "POST /desafios/<id_desafio>/questoes/<id_questao>",
                    "listar": "GET /desafios/<id_desafio>/questoes",
                    "remover": "DELETE /desafios/<id_desafio>/questoes/<id_questao>",
                },
                "aluno_desafios": {
                    "registrar": "POST /alunos/desafios",
                    "listar_por_aluno": "GET /alunos/<id_aluno>/desafios",
                    "atualizar": "PUT /alunos/<id_aluno>/desafios/<id_desafio>",
                }
            }
        })

    with app.app_context():
        d.db.create_all()

    return app


app = create_app()


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "True") == "True"
    app.run(debug=debug)