from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from models.database import db

from services.tema.criar_tema import CriarTemaService
from services.tema.listar_tema import ListarTemasService
from services.tema.atualizar_tema import AtualizarTemaService
from services.tema.deletar_tema import DeletarTemaService

tema_controller = Blueprint("tema_controller", __name__)

@tema_controller.post("/temas")
def criar_tema():
    try:
        dados = request.get_json() or {}
        service = CriarTemaService()
        tema = service.executar(dados)
        return jsonify(tema), 201
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao salvar tema no banco de dados."}), 500

@tema_controller.get("/temas")
def listar_temas():
    try:
        service = ListarTemasService()
        return jsonify(service.executar()), 200
    except SQLAlchemyError:
        return jsonify({"erro": "Erro ao listar temas."}), 500

@tema_controller.put("/temas/<int:id_tema>")
def atualizar_tema(id_tema):
    try:
        dados = request.get_json() or {}
        service = AtualizarTemaService()
        tema = service.executar(id_tema, dados)
        if not tema:
            return jsonify({"erro": "Tema não encontrado."}), 404
        return jsonify(tema), 200
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao atualizar tema."}), 500

@tema_controller.delete("/temas/<int:id_tema>")
def deletar_tema(id_tema):
    try:
        service = DeletarTemaService()
        if not service.executar(id_tema):
            return jsonify({"erro": "Tema não encontrado."}), 404
        return "", 204
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao deletar tema."}), 500