"""Regras do jogo, sem acesso ao banco: dificuldade, pontuação, fases e sequência diária.

Ficam separadas para que os Services as usem e para que possam ser testadas sozinhas.
"""
from datetime import date, timedelta

from models.model_desafio import PREFIXO_REVISAO

QUANTIDADES_PERMITIDAS = {5, 10, 15, 20}
DIFICULDADES = {
    "facil": "Fácil", "fácil": "Fácil", "easy": "Fácil",
    "normal": "Normal", "medio": "Normal", "médio": "Normal",
    "dificil": "Difícil", "difícil": "Difícil", "hard": "Difícil",
}
# Ordem da progressão de dificuldade ao longo das fases da jornada.
# "Normal" é o valor interno exibido como "Médio" na interface.
ESCADA_DIFICULDADE = ["Fácil", "Normal", "Difícil"]
PONTOS_POR_DIFICULDADE = {"Fácil": 10, "Normal": 15, "Difícil": 20}
BONUS_PERFEITO = 25            # XP extra por acertar todas as questões da fase
BONUS_CONCLUSAO_FASE = 10      # XP extra ao concluir qualquer fase (fora do modo refazer)
BONUS_CONCLUSAO_JORNADA = 50   # XP extra ao concluir a última fase da jornada
LIMITE_ERROS_JORNADA = 70      # % de erros (somando todas as fases) a partir do qual a jornada é reprovada


def normalizar_dificuldade(valor):
    """Aceita 'facil', 'Médio', 'hard'... e devolve o valor interno ('Fácil', 'Normal', 'Difícil') ou None."""
    return DIFICULDADES.get(str(valor or "").strip().casefold())


def dificuldade_da_fase(dificuldade_base, fase):
    """Sobe um nível por fase concluída, com teto em 'Difícil'."""
    indice = ESCADA_DIFICULDADE.index(dificuldade_base) + max(1, fase) - 1
    return ESCADA_DIFICULDADE[min(indice, len(ESCADA_DIFICULDADE) - 1)]


def penalidade_por_erro(ganho):
    """Quem acerta ganha `ganho`; quem erra perde 25% disso (100 -> -25)."""
    return (ganho + 3) // 4


def fases_da_jornada(quantidade):
    return {5: 5, 10: 4, 15: 3, 20: 2}.get(int(quantidade or 5), 5)


def eh_revisao(desafio):
    return (desafio.nome or "").startswith(PREFIXO_REVISAO)


def atualizar_sequencia_diaria(aluno, hoje=None):
    """Foguinho: +1 se estudou ontem, volta para 1 se pulou um dia, não muda se já contou hoje."""
    hoje = hoje or date.today()
    hoje_iso = hoje.isoformat()
    anterior = aluno.ultimo_dia_ativo
    if anterior == hoje_iso:
        return
    if anterior:
        try:
            data_anterior = date.fromisoformat(anterior)
            continua = data_anterior == hoje - timedelta(days=1)
            aluno.sequencia_atual = (aluno.sequencia_atual or aluno.foguinho or 0) + 1 if continua else 1
        except ValueError:
            aluno.sequencia_atual = 1
    else:
        aluno.sequencia_atual = 1
    aluno.ultimo_dia_ativo = hoje_iso
    aluno.foguinho = aluno.sequencia_atual
    aluno.melhor_sequencia = max(aluno.melhor_sequencia or 0, aluno.sequencia_atual)
