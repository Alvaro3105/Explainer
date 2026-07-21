from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from models.database import db

from services.ranking.criar_ranking import CriarRankingService
from services.ranking.listar_ranking import ListarRankingService
from services.ranking.atualizar_ranking import AtualizarRankingService
from services.ranking.deletar_ranking import DeletarRankingService

ranking_controller = Blueprint("ranking_controller", __name__)

@ranking_controller.post("/ranking")
def criar_ranking():
    try:
        dados = request.get_json() or {}
        service = CriarRankingService()
        ranking = service.executar(dados)
        return jsonify(ranking), 201
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao criar registro de ranking."}), 500

@ranking_controller.get("/ranking")
def listar_ranking():
    try:
        service = ListarRankingService()
        return jsonify(service.executar()), 200
    except SQLAlchemyError:
        return jsonify({"erro": "Erro ao listar ranking."}), 500

@ranking_controller.put("/ranking/<int:id_ranking>")
def atualizar_ranking(id_ranking):
    try:
        dados = request.get_json() or {}
        service = AtualizarRankingService()
        ranking = service.executar(id_ranking, dados)
        if not ranking:
            return jsonify({"erro": "Registro de ranking não encontrado."}), 404
        return jsonify(ranking), 200
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao atualizar ranking."}), 500

@ranking_controller.delete("/ranking/<int:id_ranking>")
def deletar_ranking(id_ranking):
    try:
        service = DeletarRankingService()
        if not service.executar(id_ranking):
            return jsonify({"erro": "Registro de ranking não encontrado."}), 404
        return "", 204
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao deletar registro de ranking."}), 500