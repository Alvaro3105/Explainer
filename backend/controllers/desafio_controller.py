from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from services.desafio.criar_desafio import CriarDesafioService
from services.desafio.buscar_por_nome_desafio import BuscarDesafiosPorNomeService
from models.model_desafio import Desafio
from services.desafio.atualizar_desafio import AtualizarDesafioService
from services.desafio.deletar_desafio import DeletarDesafioService
from models.database import db

desafio_controller = Blueprint("desafio_controller", __name__)


@desafio_controller.post("/desafio")
def criar_desafio():
    try:
        dados = request.get_json() or {}
        service = CriarDesafioService()
        desafio = service.executar(dados)
        return jsonify(desafio), 201

    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400

    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao salvar desafio no banco de dados."}), 500


@desafio_controller.get("/desafio")
def listar_desafios():
    try:
        nome = request.args.get("nome")
        if nome:
            service = BuscarDesafiosPorNomeService()
            desafios = service.executar(nome)
            return jsonify(desafios), 200
            
        desafios = Desafio.query.all()
        return jsonify([desafio.to_dict() for desafio in desafios]), 200
        
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        return jsonify({"erro": "Erro ao listar desafios do banco de dados."}), 500


@desafio_controller.get("/desafio/nome/<string:nome>")
def buscar_desafio_por_nome(nome):
    try:
        service = BuscarDesafiosPorNomeService()
        desafios = service.executar(nome)
        if not desafios:
            return jsonify({"erro": "Nenhum desafio encontrado com este nome."}), 404

        return jsonify(desafios), 200

    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
        
    except SQLAlchemyError:
        return jsonify({"erro": "Erro ao buscar desafio no banco de dados."}), 500


@desafio_controller.put("/desafio/<int:desafio_id>")
def atualizar_desafio(desafio_id):
    try:
        dados = request.get_json() or {}
        service = AtualizarDesafioService()
        desafio = service.executar(desafio_id, dados)

        if desafio is None:
            return jsonify({"erro": "Desafio não encontrado."}), 404

        return jsonify(desafio), 200

    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400

    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao atualizar desafio no banco de dados."}), 500


@desafio_controller.delete("/desafio/<int:desafio_id>")
def deletar_desafio(desafio_id):
    try:
        service = DeletarDesafioService()
        desafio_deletado = service.executar(desafio_id)

        if desafio_deletado is False:
            return jsonify({"erro": "Desafio não encontrado."}), 404

        return "", 204

    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao deletar desafio no banco de dados."}), 500
