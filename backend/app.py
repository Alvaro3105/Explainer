import os
#from dotenv import load_dotenv
from flask import Flask, jsonify
#from flask_cors import CORS

import models.database as d
from controllers.aluno_controller import aluno_controller


def create_app():
    #load_dotenv()

    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "mysql+pymysql://root:@localhost/explainer")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    d.db.init_app(app)

    # Registra todos os controllers
    app.register_blueprint(aluno_controller)

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
                    "historico": "GET /alunos/<id>/historico"
                },
                "desafios": {
                    "listar": "GET /desafios",
                    "buscar": "GET /desafios/<id>",
                    "criar": "POST /desafios",
                    "atualizar": "PUT /desafios/<id>",
                    "deletar": "DELETE /desafios/<id>"
                },
                "temas": {
                    "listar_por_materia": "GET /temas?materia=<materia>",
                    "buscar": "GET /temas/<id>",
                    "criar": "POST /temas",
                    "deletar": "DELETE /temas/<id>"
                },
                "questoes": {
                    "listar_por_tema": "GET /questoes?id_tema=<id>",
                    "buscar": "GET /questoes/<id>",
                    "criar": "POST /questoes"
                },
                "ranking": {
                    "listar": "GET /ranking?limite=<n>",
                    "recalcular": "POST /ranking/recalcular"
                },
                "aluno_desafio": {
                    "concluir": "POST /alunos-desafios"
                }
            }
        })

    with app.app_context():
        # Cria as tabelas automaticamente
        d.db.create_all()

    return app


app = create_app()


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "True") == "True"
    app.run(debug=debug)