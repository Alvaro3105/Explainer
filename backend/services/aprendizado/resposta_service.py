"""Caso de uso: responder uma questão do desafio (correção, pontos e sequência diária)."""
from sqlalchemy.exc import IntegrityError

from models.model_aprendizado import RespostaDesafio
from repositories.desafio_questao_repository import DesafioQuestaoRepository
from repositories.desafio_repository import DesafioRepository
from repositories.questao_repository import QuestaoRepository
from repositories.resposta_repository import RespostaRepository
from repositories.transacao import Transacao
from services.aprendizado.erros import ErroDeNegocio
from services.aprendizado.regras import (
    PONTOS_POR_DIFICULDADE, atualizar_sequencia_diaria, eh_revisao, penalidade_por_erro,
)

EXPLICACAO_PADRAO = "Revise o enunciado e compare as alternativas."


class RespostaService:

    def responder(self, aluno, id_desafio, dados):
        try:
            id_questao = int(dados.get("id_questao", 0))
            segundos = max(0, min(int(dados.get("segundos_gastos", 0)), 3600))
        except (TypeError, ValueError):
            raise ErroDeNegocio("Resposta ou tempo inválido.")
        alternativa = str(dados.get("alternativa", "")).strip().upper()
        if alternativa not in {"A", "B", "C", "D"}:
            raise ErroDeNegocio("Selecione uma alternativa válida.")
        desafio = DesafioRepository.buscar_por_id(id_desafio)
        questao = QuestaoRepository.buscar_por_id(id_questao)
        if (not desafio or desafio.id_aluno != aluno.id_aluno or not questao
                or not DesafioQuestaoRepository.pertence(id_desafio, id_questao)):
            raise ErroDeNegocio("Questão não pertence a um desafio desta conta.", 404)
        explicacao = questao.explicacao or EXPLICACAO_PADRAO
        existente = RespostaRepository.buscar(aluno.id_aluno, id_desafio, id_questao)
        if existente:
            return {
                "ja_respondida": True,
                "correta": existente.correta,
                "alternativa_correta": questao.alternativa_correta,
                "explicacao": explicacao,
                "pontos_ganhos": existente.pontos_ganhos,
                "pontos_totais": aluno.pontos or 0,
            }
        # As questões precisam ser respondidas na sequência (1, 2, 3...).
        ids_em_ordem = DesafioQuestaoRepository.ids_questoes(id_desafio)
        ja_respondidas = {r.id_questao for r in RespostaRepository.listar(aluno.id_aluno, id_desafio)}
        anteriores = ids_em_ordem[:ids_em_ordem.index(id_questao)] if id_questao in ids_em_ordem else []
        if any(anterior not in ja_respondidas for anterior in anteriores):
            raise ErroDeNegocio("Responda as questões na ordem, começando pela primeira disponível.", 409)
        correta = alternativa == str(questao.alternativa_correta or "").upper()
        ganho = PONTOS_POR_DIFICULDADE.get(desafio.dificuldade, 10)
        # Errar tira 25% do que valeria o acerto, sem deixar o total negativo; revisão não vale pontos.
        pontos = ganho if correta else -min(penalidade_por_erro(ganho), aluno.pontos or 0)
        if eh_revisao(desafio):
            pontos = 0
        RespostaRepository.adicionar(RespostaDesafio(
            id_aluno=aluno.id_aluno,
            id_desafio=id_desafio,
            id_questao=id_questao,
            alternativa_escolhida=alternativa,
            correta=correta,
            pontos_ganhos=pontos,
            segundos_gastos=segundos,
        ))
        aluno.pontos = (aluno.pontos or 0) + pontos
        atualizar_sequencia_diaria(aluno)
        try:
            Transacao.confirmar()
        except IntegrityError:
            Transacao.desfazer()
            raise ErroDeNegocio("Esta questão já foi respondida.", 409, extra={"ja_respondida": True})
        return {
            "correta": correta,
            "alternativa_correta": questao.alternativa_correta,
            "explicacao": explicacao,
            "pontos_ganhos": pontos,
            "pontos_totais": aluno.pontos,
        }
