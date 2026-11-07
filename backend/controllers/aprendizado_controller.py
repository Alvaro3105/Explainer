"""Rotas da área do estudante.

O Controller só cuida do HTTP: lê a requisição, pega o aluno da sessão, chama o Service do
caso de uso e devolve JSON. Regras de negócio ficam nos Services; consultas, nos Repositories.
"""
from functools import wraps

from flask import Blueprint, jsonify, request, session

from repositories.aluno_repositories import AlunoRepository
from services.aprendizado.conclusao_service import ConclusaoService
from services.aprendizado.conta_service import ContaService
from services.aprendizado.desafio_service import DesafioService
from services.aprendizado.erros import ErroDeNegocio
from services.aprendizado.progresso_service import ProgressoService
from services.aprendizado.resposta_service import RespostaService

aprendizado_controller = Blueprint("aprendizado_controller", __name__)


def aluno_logado():
    return AlunoRepository.buscar_por_id(session.get("aluno_id"))


def _dados():
    return request.get_json(silent=True) or {}


def _iniciar_sessao(aluno):
    session.clear()
    session["aluno_id"] = aluno.id_aluno


def rota(exige_login=True):
    """Converte ErroDeNegocio em resposta HTTP e, se pedido, injeta o aluno logado (ou 401)."""
    def decorador(funcao):
        @wraps(funcao)
        def envolvida(*args, **kwargs):
            aluno = aluno_logado()
            if exige_login and not aluno:
                return jsonify({"erro": "Entre na sua conta para continuar."}), 401
            try:
                return funcao(aluno, *args, **kwargs)
            except ErroDeNegocio as erro:
                resposta = jsonify({"erro": erro.mensagem, **erro.extra})
                for nome, valor in erro.cabecalhos.items():
                    resposta.headers[nome] = valor
                return resposta, erro.status
        return envolvida
    return decorador


# ---------- conta ----------

@aprendizado_controller.post("/api/auth/register")
@rota(exige_login=False)
def registrar_conta(_aluno):
    aluno = ContaService().registrar(_dados())
    _iniciar_sessao(aluno)
    return jsonify({"aluno": aluno.to_dict()}), 201


@aprendizado_controller.post("/api/auth/login")
@rota(exige_login=False)
def entrar_conta(_aluno):
    dados = _dados()
    aluno = ContaService().entrar(dados.get("email"), dados.get("senha"), request.remote_addr)
    _iniciar_sessao(aluno)
    return jsonify({"aluno": aluno.to_dict(), "progresso": ProgressoService().progresso(aluno)})


@aprendizado_controller.post("/api/auth/logout")
def sair_conta():
    session.clear()
    return jsonify({"ok": True})


@aprendizado_controller.delete("/api/auth/delete-account")
@rota()
def excluir_propria_conta(aluno):
    ContaService().excluir(aluno, _dados().get("senha"))
    session.clear()
    return jsonify({"ok": True})


@aprendizado_controller.post("/api/auth/accept-terms")
@rota()
def aceitar_termos(aluno):
    aluno = ContaService().aceitar_termos(aluno)
    return jsonify({"aluno": aluno.to_dict()})


@aprendizado_controller.get("/api/learning/me")
@rota()
def minha_conta(aluno):
    return jsonify({"aluno": aluno.to_dict(), "progresso": ProgressoService().progresso(aluno)})


@aprendizado_controller.patch("/api/learning/profile")
@rota()
def atualizar_perfil(aluno):
    aluno = ContaService().atualizar_nick(aluno, _dados().get("nick"))
    return jsonify({"aluno": aluno.to_dict()})


# ---------- desafios ----------

@aprendizado_controller.get("/api/learning/catalog")
@rota(exige_login=False)
def catalogo_estudo(_aluno):
    return jsonify({"materias": DesafioService().catalogo()})


@aprendizado_controller.get("/api/learning/active-challenge")
@rota()
def desafio_em_andamento(aluno):
    return jsonify(DesafioService().desafio_ativo(aluno))


@aprendizado_controller.post("/api/learning/challenges")
@rota()
def criar_desafio_jogavel(aluno):
    return jsonify(DesafioService().criar(aluno, _dados())), 201


@aprendizado_controller.get("/api/learning/challenges/<int:id_desafio>")
@rota()
def buscar_desafio_jogavel(aluno, id_desafio):
    return jsonify(DesafioService().buscar(aluno, id_desafio))


@aprendizado_controller.post("/api/learning/challenges/<int:id_desafio>/answer")
@rota()
def responder_questao(aluno, id_desafio):
    return jsonify(RespostaService().responder(aluno, id_desafio, _dados()))


@aprendizado_controller.post("/api/learning/challenges/<int:id_desafio>/complete")
@rota()
def concluir_desafio(aluno, id_desafio):
    return jsonify(ConclusaoService().concluir(aluno, id_desafio))


# ---------- acompanhamento ----------

@aprendizado_controller.post("/api/learning/activity")
@rota()
def registrar_tempo_ativo(aluno):
    return jsonify(ProgressoService().registrar_tempo_ativo(aluno, _dados().get("segundos", 0)))


@aprendizado_controller.get("/api/learning/ranking")
@rota(exige_login=False)
def ranking_de_estudo(aluno):
    limite = request.args.get("limite", default=20, type=int)
    return jsonify(ProgressoService().ranking(aluno, limite))


@aprendizado_controller.get("/api/learning/history")
@rota()
def historico_estudo(aluno):
    return jsonify({"historico": ProgressoService().historico(aluno)})
