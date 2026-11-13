from functools import wraps

from flask import Blueprint, jsonify, request, session

from services.aprendizado.catalogo_service import CatalogoService
from services.aprendizado.conclusao_service import ConclusaoService
from services.aprendizado.conta_service import ContaService
from repositories.transacao import Transacao
from services.aprendizado.desafio_service import DesafioService
from services.aprendizado.erros import ErroDeNegocio
from services.aprendizado.progresso_service import ProgressoService
from services.aprendizado.resposta_service import RespostaService

aprendizado_controller = Blueprint("aprendizado_controller", __name__)


def aluno_logado():
    return ContaService().aluno_da_sessao(session.get("aluno_id"))


def _dados():
    dados = request.get_json(silent=True)
    return dados if isinstance(dados, dict) else {}


def _iniciar_sessao(aluno):
    session.clear()
    session["aluno_id"] = aluno.id_aluno


def rota(exige_login=True):
    """Transforma ErroDeNegocio em resposta HTTP e entrega o aluno logado para a rota (ou 401)."""
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
            except OverflowError:
                # Número grande demais para o banco (ou "Infinity" no JSON): é erro de quem enviou.
                Transacao.desfazer()
                return jsonify({"erro": "Número fora do limite permitido."}), 400
        return envolvida
    return decorador


# Rotas da conta

@aprendizado_controller.post("/api/auth/register")
@rota(exige_login=False)
def registrar_conta(_aluno):
    aluno = ContaService().registrar(_dados(), request.remote_addr)
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


@aprendizado_controller.post("/api/auth/change-password")
@rota()
def trocar_senha(aluno):
    dados = _dados()
    ContaService().trocar_senha(aluno, dados.get("senha_atual"), dados.get("senha_nova"), request.remote_addr)
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


# Rotas dos desafios

def _filtros():
    return request.args.get("q", ""), request.args.get("limite"), request.args.get("pagina", 1)


@aprendizado_controller.get("/api/learning/catalog")
@rota(exige_login=False)
def catalogo_estudo(_aluno):
    """Lista ou pesquisa as matérias (?q=mat). Os temas vêm pelas rotas abaixo, aos poucos."""
    texto, limite, pagina = _filtros()
    return jsonify(CatalogoService().materias(texto, limite, pagina))


@aprendizado_controller.get("/api/learning/catalog/<int:id_materia>/themes")
@rota(exige_login=False)
def temas_da_materia(_aluno, id_materia):
    """Pesquisa temas e subtemas de UMA matéria (?q=fin&limite=8)."""
    texto, limite, pagina = _filtros()
    return jsonify(CatalogoService().temas(id_materia, texto, limite, pagina))


@aprendizado_controller.get("/api/learning/catalog/themes/<int:id_tema>/subtopics")
@rota(exige_login=False)
def subtemas_do_tema(_aluno, id_tema):
    texto, limite, pagina = _filtros()
    return jsonify(CatalogoService().subtemas(id_tema, texto, limite, pagina))


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


# Rotas de acompanhamento

@aprendizado_controller.post("/api/learning/activity")
@rota()
def registrar_tempo_ativo(aluno):
    return jsonify(ProgressoService().registrar_tempo_ativo(aluno, _dados().get("segundos", 0)))


@aprendizado_controller.get("/api/learning/ranking")
@rota(exige_login=False)
def ranking_de_estudo(aluno):
    """?limite=5 (início) ou ?limite=100 (lista completa). Outro valor vira 5."""
    return jsonify(ProgressoService().ranking(aluno, request.args.get("limite")))


@aprendizado_controller.get("/api/learning/history")
@rota()
def historico_estudo(aluno):
    return jsonify({"historico": ProgressoService().historico(aluno)})
