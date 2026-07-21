from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from models.database import db

from services.aluno_desafio.registrar_aluno_desafio import RegistrarAlunoDesafioService
from services.aluno_desafio.atualizar_aluno_desafio import AtualizarAlunoDesafioService
from services.aluno_desafio.listar_desafios_aluno import ListarDesafiosAlunoService

aluno_desafio_controller = Blueprint("aluno_desafio_controller", __name__)

@aluno_desafio_controller.post("/alunos/desafios")
def registrar_desafio():
    try:
        dados = request.get_json() or {}
        service = RegistrarAlunoDesafioService()
        resultado = service.executar(dados)
        return jsonify(resultado), 201
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao registrar desafio para o aluno."}), 500

@aluno_desafio_controller.get("/alunos/<int:id_aluno>/desafios")
def listar_desafios_do_aluno(id_aluno):
    try:
        service = ListarDesafiosAlunoService()
        historico = service.executar(id_aluno)
        return jsonify(historico), 200
    except SQLAlchemyError:
        return jsonify({"erro": "Erro ao buscar histórico de desafios do aluno."}), 500

@aluno_desafio_controller.put("/alunos/<int:id_aluno>/desafios/<int:id_desafio>")
def atualizar_progresso(id_aluno, id_desafio):
    try:
        dados = request.get_json() or {}
        service = AtualizarAlunoDesafioService()
        resultado = service.executar(id_aluno, id_desafio, dados)
        if not resultado:
            return jsonify({"erro": "Registro de desafio do aluno não encontrado."}), 404
        return jsonify(resultado), 200
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"erro": "Erro ao atualizar progresso do desafio."}), 500