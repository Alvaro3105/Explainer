import hmac
import re
import threading
import time
from datetime import date, datetime, timezone

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash

from models.model_aluno import VERSAO_TERMOS_ATUAL, Aluno
from repositories.aluno_repositories import AlunoRepository
from repositories.transacao import Transacao
from services.aprendizado.erros import ErroDeNegocio
from services.exclusao import remover_aluno

# Hash usado quando o e-mail não existe, para o login demorar o mesmo tempo
# e ninguém descobrir pela demora quais e-mails têm conta.
_HASH_FICTICIO = generate_password_hash("senha-ficticia-para-tempo-constante")

# Limite de tentativas de login: depois de 5 erros em 15 minutos, bloqueia por um tempo.
# A contagem é por e-mail e IP, e também só por IP. Fica na memória do servidor,
# então vale para um servidor só.
LIMITE_FALHAS_LOGIN = 5
LIMITE_FALHAS_POR_IP = 20
JANELA_FALHAS_LOGIN = 15 * 60
_falhas_login = {}
_trava_falhas = threading.Lock()


def _falhas_recentes(chave, agora):
    tentativas = [t for t in _falhas_login.get(chave, []) if agora - t < JANELA_FALHAS_LOGIN]
    if tentativas:
        _falhas_login[chave] = tentativas
    else:
        _falhas_login.pop(chave, None)
    return tentativas


def _login_bloqueado(email, ip):
    agora = time.monotonic()
    with _trava_falhas:
        espera = 0
        for chave, limite in (((email, ip), LIMITE_FALHAS_LOGIN), ((None, ip), LIMITE_FALHAS_POR_IP)):
            tentativas = _falhas_recentes(chave, agora)
            if len(tentativas) >= limite:
                espera = max(espera, JANELA_FALHAS_LOGIN - (agora - tentativas[0]))
        return int(espera) + 1 if espera else 0


def _registrar_falha_login(email, ip):
    agora = time.monotonic()
    with _trava_falhas:
        for chave in ((email, ip), (None, ip)):
            _falhas_login.setdefault(chave, []).append(agora)


def _limpar_falhas_login(email, ip):
    with _trava_falhas:
        _falhas_login.pop((email, ip), None)


def senha_confere(senha_armazenada, senha_informada):
    senha_armazenada = senha_armazenada or ""
    if senha_armazenada.startswith(("pbkdf2:", "scrypt:")):
        try:
            return check_password_hash(senha_armazenada, senha_informada)
        except (ValueError, TypeError):
            return False
    return bool(senha_armazenada) and hmac.compare_digest(senha_armazenada.encode(), senha_informada.encode())


class ContaService:

    def aluno_da_sessao(self, id_aluno):
        return AlunoRepository.buscar_por_id(id_aluno)

    def registrar(self, dados):
        nome = str(dados.get("nome") or "").strip()
        nick = str(dados.get("nick") or "").strip()
        email = str(dados.get("email") or "").strip().lower()
        senha = str(dados.get("senha") or "")
        if not nome or not email or not senha:
            raise ErroDeNegocio("Preencha nome, e-mail e senha.")
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
            raise ErroDeNegocio("Informe um e-mail válido.")
        if len(senha) < 8:
            raise ErroDeNegocio("A senha deve ter pelo menos 8 caracteres.")
        if len(nome) > 100 or len(nick or nome) > 40:
            raise ErroDeNegocio("Nome ou nick excede o limite permitido.")
        if dados.get("aceite_termos") is not True:
            raise ErroDeNegocio("Para criar a conta, é preciso aceitar os Termos de Uso e o Termo de Consentimento.")
        if AlunoRepository.buscar_por_email(email):
            raise ErroDeNegocio("Já existe uma conta com este e-mail.", 409)
        nascimento = dados.get("data_nascimento") or None
        try:
            data_nascimento = date.fromisoformat(nascimento) if nascimento else None
        except (TypeError, ValueError):
            raise ErroDeNegocio("A data de nascimento é inválida.")
        aluno = Aluno(
            nome=nome,
            nick=(nick or nome)[:40],
            email=email,
            senha=generate_password_hash(senha),
            data_nascimento=data_nascimento,
            pontos=0,
            foguinho=0,
            minutos_ativos=0,
            sequencia_atual=0,
            melhor_sequencia=0,
        )
        self._registrar_aceite(aluno)
        try:
            AlunoRepository.adicionar(aluno)
            Transacao.confirmar()
        except IntegrityError:
            Transacao.desfazer()
            raise ErroDeNegocio("Já existe uma conta com este e-mail.", 409)
        return aluno

    def entrar(self, email, senha, ip):
        email = str(email or "").strip().lower()
        senha = str(senha or "")
        ip = ip or "desconhecido"
        espera = _login_bloqueado(email, ip)
        if espera:
            minutos = max(1, round(espera / 60))
            raise ErroDeNegocio(f"Muitas tentativas de login. Tente novamente em cerca de {minutos} min.",
                                429, cabecalhos={"Retry-After": str(espera)})
        aluno = AlunoRepository.buscar_por_email(email)
        if aluno is None:
            check_password_hash(_HASH_FICTICIO, senha)  # gasta o mesmo tempo de uma conta que existe
            _registrar_falha_login(email, ip)
            raise ErroDeNegocio("E-mail ou senha incorretos.", 401)
        if not senha_confere(aluno.senha, senha):
            _registrar_falha_login(email, ip)
            raise ErroDeNegocio("E-mail ou senha incorretos.", 401)
        _limpar_falhas_login(email, ip)
        if not (aluno.senha or "").startswith(("pbkdf2:", "scrypt:")):
            aluno.senha = generate_password_hash(senha)  # senha antiga em texto puro vira hash
        Transacao.confirmar()
        return aluno

    def excluir(self, aluno, senha):
        if not senha_confere(aluno.senha, str(senha or "")):
            raise ErroDeNegocio("Senha incorreta. A conta não foi excluída.", 403)
        try:
            # Apaga primeiro tudo o que é do aluno, por causa das chaves estrangeiras.
            remover_aluno(aluno)
            Transacao.confirmar()
        except SQLAlchemyError:
            Transacao.desfazer()
            raise ErroDeNegocio("Não foi possível excluir a conta. Nenhum dado foi alterado.", 500)

    def aceitar_termos(self, aluno):
        self._registrar_aceite(aluno)
        Transacao.confirmar()
        return aluno

    @staticmethod
    def _registrar_aceite(aluno):
        # Guarda no banco quando o aluno aceitou os termos e qual versão.
        aluno.termos_aceitos_em = datetime.now(timezone.utc).replace(tzinfo=None)
        aluno.versao_termos = VERSAO_TERMOS_ATUAL

    def atualizar_nick(self, aluno, nick):
        nick = str(nick or "").strip()
        if not nick or len(nick) > 40:
            raise ErroDeNegocio("O nick deve ter entre 1 e 40 caracteres.")
        aluno.nick = nick
        Transacao.confirmar()
        return aluno
