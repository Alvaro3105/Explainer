# controllers/aluno_controller.py
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from services.aluno.criar_aluno import CriarAlunoService
from services.aluno.listar_aluno import ListarAlunosService
from services.aluno.buscar_por_id import BuscarAlunoPorIdService
from services.aluno.atualizar_aluno import AtualizarAlunoService
from services.aluno.deletar_aluno import DeletarAlunoService
from models.database import db

aluno_controller = Blueprint("aluno_controller", __name__)


@aluno_controller.post("/alunos")
def criar_aluno():
    try:
        dados = request.get_json() or {}
        service = CriarAlunoService()
        aluno = service.executar(dados)
        return jsonify(aluno), 201

    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400

    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao salvar aluno no banco de dados."}), 500


@aluno_controller.get("/alunos")
def listar_alunos():
    try:
        service = ListarAlunosService()
        alunos = service.executar()
        return jsonify(alunos), 200
    except SQLAlchemyError:
        return jsonify({"erro": "Erro ao listar alunos do banco de dados."}), 500


@aluno_controller.get("/alunos/<int:aluno_id>")
def buscar_aluno_por_id(aluno_id):
    try:
        service = BuscarAlunoPorIdService()
        aluno = service.executar(aluno_id)

        if aluno is None:
            return jsonify({"erro": "Aluno não encontrado."}), 404

        return jsonify(aluno), 200
    except SQLAlchemyError:
        return jsonify({"erro": "Erro ao buscar aluno no banco de dados."}), 500


@aluno_controller.put("/alunos/<int:aluno_id>")
def atualizar_aluno(aluno_id):
    try:
        dados = request.get_json() or {}
        service = AtualizarAlunoService()
        aluno = service.executar(aluno_id, dados)

        if aluno is None:
            return jsonify({"erro": "Aluno não encontrado."}), 404

        return jsonify(aluno), 200

    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400

    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao atualizar aluno no banco de dados."}), 500


@aluno_controller.delete("/alunos/<int:aluno_id>")
def deletar_aluno(aluno_id):
    try:
        service = DeletarAlunoService()
        aluno_deletado = service.executar(aluno_id)

        if aluno_deletado is False:
            return jsonify({"erro": "Aluno não encontrado."}), 404

        return "", 204

    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao deletar aluno no banco de dados."}), 500


@aluno_controller.get("/alunos/<int:aluno_id>/historico")
def buscar_historico_aluno(aluno_id):
    try:
        service = BuscarHistoricoAlunoService()
        historico = service.executar(aluno_id)
        return jsonify(historico), 200

    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400

    except SQLAlchemyError:
        return jsonify({"erro": "Erro ao buscar histórico do aluno."}), 500