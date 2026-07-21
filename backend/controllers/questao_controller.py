from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from models.database import db

from services.questao.criar_questao import CriarQuestaoService
from services.questao.listar_questao import ListarQuestoesService
from services.questao.atualizar_questao import AtualizarQuestaoService
from services.questao.deletar_questao import DeletarQuestaoService

questao_controller = Blueprint("questao_controller", __name__)

@questao_controller.post("/questoes")
def criar_questao():
    try:
        dados = request.get_json() or {}
        service = CriarQuestaoService()
        questao = service.executar(dados)
        return jsonify(questao), 201
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao salvar questão no banco de dados."}), 500

@questao_controller.get("/questoes")
def listar_questoes():
    try:
        service = ListarQuestoesService()
        return jsonify(service.executar()), 200
    except SQLAlchemyError:
        return jsonify({"erro": "Erro ao listar questões."}), 500

@questao_controller.put("/questoes/<int:id_questao>")
def atualizar_questao(id_questao):
    try:
        dados = request.get_json() or {}
        service = AtualizarQuestaoService()
        questao = service.executar(id_questao, dados)
        if not questao:
            return jsonify({"erro": "Questão não encontrada."}), 404
        return jsonify(questao), 200
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao atualizar questão."}), 500

@questao_controller.delete("/questoes/<int:id_questao>")
def deletar_questao(id_questao):
    try:
        service = DeletarQuestaoService()
        if not service.executar(id_questao):
            return jsonify({"erro": "Questão não encontrada."}), 404
        return "", 204
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao deletar questão."}), 500