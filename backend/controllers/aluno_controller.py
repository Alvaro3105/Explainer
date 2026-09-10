from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from models.database import db
from services.aluno.atualizar_aluno import AtualizarAlunoService
from services.aluno.buscar_por_id import BuscarAlunoPorIdService
from services.aluno.criar_aluno import CriarAlunoService
from services.aluno.deletar_aluno import DeletarAlunoService
from services.aluno.listar_aluno import ListarAlunosService
from services.aluno.ranking_dos_alunos import BuscarRankingAlunosService

aluno_controller = Blueprint("aluno_controller", __name__)


@aluno_controller.post("/alunos")
def criar_aluno():
    try:
        dados = request.get_json() or {}
        return jsonify(CriarAlunoService().executar(dados)), 201
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao salvar aluno no banco de dados."}), 500


@aluno_controller.get("/alunos")
def listar_alunos():
    try:
        return jsonify(ListarAlunosService().executar()), 200
    except SQLAlchemyError:
        return jsonify({"erro": "Erro ao listar alunos do banco de dados."}), 500


@aluno_controller.get("/alunos/<int:aluno_id>")
def buscar_aluno_por_id(aluno_id):
    try:
        aluno = BuscarAlunoPorIdService().executar(aluno_id)
        if aluno is None:
            return jsonify({"erro": "Aluno não encontrado."}), 404
        return jsonify(aluno), 200
    except SQLAlchemyError:
        return jsonify({"erro": "Erro ao buscar aluno no banco de dados."}), 500


@aluno_controller.put("/alunos/<int:aluno_id>")
def atualizar_aluno(aluno_id):
    try:
        dados = request.get_json() or {}
        aluno = AtualizarAlunoService().executar(aluno_id, dados)
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
        if DeletarAlunoService().executar(aluno_id) is False:
            return jsonify({"erro": "Aluno não encontrado."}), 404
        return "", 204
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao deletar aluno no banco de dados."}), 500


@aluno_controller.get("/alunos/ranking")
def buscar_ranking_alunos():
    try:
        return jsonify(BuscarRankingAlunosService().executar()), 200
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao buscar o ranking de alunos no banco de dados."}), 500
