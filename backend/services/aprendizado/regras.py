from datetime import date, datetime, timedelta, timezone

from models.model_desafio import PREFIXO_REVISAO

QUANTIDADES_PERMITIDAS = {5, 10, 15, 20}
DIFICULDADES = {
    "facil": "Fácil", "fácil": "Fácil", "easy": "Fácil",
    "normal": "Normal", "medio": "Normal", "médio": "Normal",
    "dificil": "Difícil", "difícil": "Difícil", "hard": "Difícil",
}
ESCADA_DIFICULDADE = ["Fácil", "Normal", "Difícil"]
PONTOS_POR_DIFICULDADE = {"Fácil": 10, "Normal": 15, "Difícil": 20}
BONUS_PERFEITO = 25
BONUS_CONCLUSAO_FASE = 10
BONUS_CONCLUSAO_JORNADA = 50
LIMITE_ERROS_JORNADA = 70
FUSO_BRASILIA = timezone(timedelta(hours=-3))


def hoje():
    return datetime.now(FUSO_BRASILIA).date()


def normalizar_dificuldade(valor):
    return DIFICULDADES.get(str(valor or "").strip().casefold())


def dificuldade_da_fase(dificuldade_base, fase):
    indice = ESCADA_DIFICULDADE.index(dificuldade_base) + max(1, fase) - 1
    return ESCADA_DIFICULDADE[min(indice, len(ESCADA_DIFICULDADE) - 1)]


def penalidade_por_erro(ganho):
    """Quem acerta ganha `ganho`; quem erra perde 25% disso (se valia 100, perde 25)."""
    return (ganho + 3) // 4


def fases_da_jornada(quantidade):
    return {5: 5, 10: 4, 15: 3, 20: 2}.get(int(quantidade or 5), 5)


def eh_revisao(desafio):
    return (desafio.nome or "").startswith(PREFIXO_REVISAO)


def atualizar_sequencia_diaria(aluno, dia=None):
    dia = dia or hoje()
    hoje_iso = dia.isoformat()
    anterior = aluno.ultimo_dia_ativo
    if anterior == hoje_iso:
        return
    if anterior:
        try:
            data_anterior = date.fromisoformat(anterior)
            continua = data_anterior == dia - timedelta(days=1)
            aluno.sequencia_atual = (aluno.sequencia_atual or aluno.foguinho or 0) + 1 if continua else 1
        except ValueError:
            aluno.sequencia_atual = 1
    else:
        aluno.sequencia_atual = 1
    aluno.ultimo_dia_ativo = hoje_iso
    aluno.foguinho = aluno.sequencia_atual
    aluno.melhor_sequencia = max(aluno.melhor_sequencia or 0, aluno.sequencia_atual)
