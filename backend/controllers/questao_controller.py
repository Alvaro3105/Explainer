from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from models.database import db
from services.questao.atualizar_questao import AtualizarQuestaoService
from services.questao.criar_questao import CriarQuestaoService
from services.questao.deletar_questao import DeletarQuestaoService
from services.questao.listar_questao import ListarQuestoesService
from services.questao.verificar_questao import VerificarQuestaoService

questao_controller = Blueprint("questao_controller", __name__)


@questao_controller.post("/questoes")
def criar_questao():
    try:
        dados = request.get_json() or {}
        return jsonify(CriarQuestaoService().executar(dados)), 201
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao salvar questão no banco de dados."}), 500


@questao_controller.get("/questoes")
def listar_questoes():
    try:
        return jsonify(ListarQuestoesService().executar()), 200
    except SQLAlchemyError:
        return jsonify({"erro": "Erro ao listar questões."}), 500


@questao_controller.put("/questoes/<int:id_questao>")
def atualizar_questao(id_questao):
    try:
        dados = request.get_json() or {}
        questao = AtualizarQuestaoService().executar(id_questao, dados)
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
        if not DeletarQuestaoService().executar(id_questao):
            return jsonify({"erro": "Questão não encontrada."}), 404
        return "", 204
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao deletar questão."}), 500


@questao_controller.post("/questoes/<int:id_questao>/verificar")
def verificar_questao(id_questao):
    try:
        dados = request.get_json() or {}
        resultado = VerificarQuestaoService().executar(id_questao, dados.get("alternativa"))
        if resultado is None:
            return jsonify({"erro": "Questão não encontrada."}), 404
        return jsonify({"correta": resultado}), 200
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        return jsonify({"erro": "Erro ao verificar questão."}), 500
