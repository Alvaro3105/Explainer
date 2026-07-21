from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from models.database import db

from services.desafio_questao.adicionar_questao_desafio import AdicionarQuestaoDesafioService
from services.desafio_questao.listar_questoes_desafio import ListarQuestoesDesafioService
from services.desafio_questao.remover_questao_desafio import RemoverQuestaoDesafioService

desafio_questao_controller = Blueprint("desafio_questao_controller", __name__)

@desafio_questao_controller.post("/desafios/<int:id_desafio>/questoes/<int:id_questao>")
def adicionar_questao(id_desafio, id_questao):
    try:
        service = AdicionarQuestaoDesafioService()
        resultado = service.executar(id_desafio, id_questao)
        return jsonify(resultado), 201
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao vincular questão ao desafio."}), 500

@desafio_questao_controller.get("/desafios/<int:id_desafio>/questoes")
def listar_questoes_do_desafio(id_desafio):
    try:
        service = ListarQuestoesDesafioService()
        questoes = service.executar(id_desafio)
        return jsonify(questoes), 200
    except SQLAlchemyError:
        return jsonify({"erro": "Erro ao buscar questões do desafio."}), 500

@desafio_questao_controller.delete("/desafios/<int:id_desafio>/questoes/<int:id_questao>")
def remover_questao(id_desafio, id_questao):
    try:
        service = RemoverQuestaoDesafioService()
        if not service.executar(id_desafio, id_questao):
            return jsonify({"erro": "Vínculo não encontrado."}), 404
        return "", 204
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao desvincular questão do desafio."}), 500