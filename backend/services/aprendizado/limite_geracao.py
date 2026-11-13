"""Limite de geração de desafios por aluno.

Cada desafio novo pode virar uma chamada à IA, que tem cota e pode demorar. Sem limite,
um único aluno (ou um script) esgotaria a cota de todos. As regras ficam aqui, no servidor:

* uma geração por vez por aluno (clique repetido não dispara duas chamadas);
* um intervalo mínimo entre uma geração e a próxima;
* um teto por janela de 10 minutos e um teto por dia.

Cada pedido é gravado na tabela `geracao_desafio`. Por isso o limite vale para todos os
processos do servidor e continua valendo depois de um reinício.
"""
import os
import threading
import time
from contextlib import contextmanager
from datetime import datetime, time as hora

from sqlalchemy.exc import SQLAlchemyError

from models.model_geracao import GeracaoDesafio
from repositories.geracao_repository import GeracaoRepository
from repositories.transacao import Transacao
from services.aprendizado.erros import ErroDeNegocio
from services.aprendizado.regras import FUSO_BRASILIA, hoje

JANELA_GERACOES = 10 * 60
# Um pedido "em andamento" há mais tempo que isto ficou para trás (o servidor caiu no meio):
# deixa de bloquear o aluno. É maior que o prazo total que o gerador dá à IA.
VALIDADE_EM_ANDAMENTO = 180
GUARDAR_REGISTROS_POR = 2 * 24 * 3600
PADROES = {
    "INTERVALO_ENTRE_GERACOES": 10,   # segundos entre uma geração e a próxima
    "GERACOES_POR_JANELA": 8,         # gerações a cada 10 minutos
    "GERACOES_POR_DIA": 40,           # gerações por dia (horário de Brasília)
}

# Dentro do mesmo processo, a conferência e a gravação de um pedido acontecem uma de cada vez.
_trava = threading.Lock()


def _limite(nome):
    """Lê o limite do ambiente (0 desliga aquela regra); valor inválido usa o padrão."""
    try:
        return max(0, int(os.getenv(nome, "").strip() or PADROES[nome]))
    except ValueError:
        return PADROES[nome]


def _espera(segundos):
    segundos = max(1, int(segundos + 0.999))
    if segundos < 60:
        return f"{segundos} s", segundos
    return f"cerca de {max(1, round(segundos / 60))} min", segundos


def _recusar(mensagem, segundos=None):
    cabecalhos = {"Retry-After": str(segundos)} if segundos else {}
    extra = {"limite_de_geracao": True, **({"aguarde_segundos": segundos} if segundos else {})}
    raise ErroDeNegocio(mensagem, 429, extra=extra, cabecalhos=cabecalhos)


def _inicio_do_dia():
    return datetime.combine(hoje(), hora.min, tzinfo=FUSO_BRASILIA).timestamp()


def _preparando(pedido, agora):
    return bool(pedido.em_andamento) and agora - pedido.iniciada_em < VALIDADE_EM_ANDAMENTO


def _conferir(pedidos, agora, inicio_do_dia):
    """Recusa (ErroDeNegocio 429) se os pedidos anteriores do aluno já atingiram algum limite."""
    if any(_preparando(pedido, agora) for pedido in pedidos):
        _recusar("Seu desafio já está sendo preparado. Aguarde ele ficar pronto.")
    recentes = [pedido.iniciada_em for pedido in pedidos if agora - pedido.iniciada_em < JANELA_GERACOES]

    intervalo = _limite("INTERVALO_ENTRE_GERACOES")
    if intervalo and recentes and agora - recentes[-1] < intervalo:
        texto, segundos = _espera(intervalo - (agora - recentes[-1]))
        _recusar(f"Aguarde {texto} para gerar outro desafio.", segundos)

    por_janela = _limite("GERACOES_POR_JANELA")
    if por_janela and len(recentes) >= por_janela:
        texto, segundos = _espera(JANELA_GERACOES - (agora - recentes[0]))
        _recusar(f"Você gerou muitos desafios em pouco tempo. Tente de novo em {texto}.", segundos)

    por_dia = _limite("GERACOES_POR_DIA")
    if por_dia and sum(1 for pedido in pedidos if pedido.iniciada_em >= inicio_do_dia) >= por_dia:
        _recusar(f"Você chegou ao limite de {por_dia} desafios novos por hoje. "
                 "Amanhã tem mais! Enquanto isso, dá para refazer os desafios concluídos.")


def _registrar_pedido(id_aluno):
    """Confere os limites e grava o pedido. Devolve o id do registro."""
    agora = time.time()
    inicio_do_dia = _inicio_do_dia()
    with _trava:
        GeracaoRepository.remover_anteriores(id_aluno, agora - GUARDAR_REGISTROS_POR)
        pedidos = GeracaoRepository.desde(id_aluno, min(inicio_do_dia, agora - JANELA_GERACOES))
        try:
            _conferir(pedidos, agora, inicio_do_dia)
        except ErroDeNegocio:
            Transacao.desfazer()
            raise
        pedido = GeracaoDesafio(id_aluno=id_aluno, iniciada_em=agora, em_andamento=True)
        GeracaoRepository.adicionar(pedido)
        Transacao.confirmar()   # grava já: os outros processos precisam enxergar este pedido
        id_pedido = pedido.id_geracao
    # Outro processo pode ter gravado um pedido do mesmo aluno no mesmo instante. Se houver
    # um pedido em andamento mais antigo que este, este é desfeito e o aluno espera o primeiro.
    outros = [p for p in GeracaoRepository.desde(id_aluno, agora - VALIDADE_EM_ANDAMENTO)
              if p.id_geracao < id_pedido and _preparando(p, agora)]
    if outros:
        GeracaoRepository.remover(GeracaoRepository.buscar_por_id(id_pedido))
        Transacao.confirmar()
        _recusar("Seu desafio já está sendo preparado. Aguarde ele ficar pronto.")
    return id_pedido


@contextmanager
def vaga_de_geracao(id_aluno):
    """Use em volta da geração: confere os limites, conta a tentativa e libera o aluno no fim.

    A tentativa conta mesmo se a IA falhar, porque a chamada foi feita e gastou cota.
    Na saída, o que ainda estiver pendente na sessão do banco é desfeito: quem chama
    precisa confirmar a própria gravação antes de sair do bloco.
    """
    id_pedido = _registrar_pedido(id_aluno)
    try:
        yield
    finally:
        try:
            Transacao.desfazer()
            pedido = GeracaoRepository.buscar_por_id(id_pedido)
            if pedido is not None:
                pedido.em_andamento = False
                Transacao.confirmar()
        except SQLAlchemyError:
            # O banco falhou ao marcar o fim do pedido. O erro original (se houver) segue adiante;
            # o registro deixa de bloquear o aluno sozinho, depois de VALIDADE_EM_ANDAMENTO.
            Transacao.desfazer()


def em_andamento(id_aluno):
    """O aluno tem uma geração sendo preparada agora?"""
    agora = time.time()
    return any(_preparando(pedido, agora) for pedido in GeracaoRepository.desde(id_aluno, agora - VALIDADE_EM_ANDAMENTO))


def esquecer_tudo():
    """Apaga todos os registros de pedidos (usado nos testes)."""
    GeracaoRepository.remover_todos()
    Transacao.confirmar()
