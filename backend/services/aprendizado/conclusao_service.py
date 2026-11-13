from sqlalchemy.exc import IntegrityError

from models.model_aluno_desafio import AlunoDesafio
from repositories.aluno_desafio_repository import AlunoDesafioRepository
from repositories.desafio_questao_repository import DesafioQuestaoRepository
from repositories.desafio_repository import DesafioRepository
from repositories.resposta_repository import RespostaRepository
from repositories.transacao import Transacao
from services.aprendizado.desafio_service import desafio_do_aluno
from services.aprendizado.erros import ErroDeNegocio
from services.aprendizado.progresso_service import ProgressoService
from services.aprendizado.regras import (
    BONUS_CONCLUSAO_FASE, BONUS_CONCLUSAO_JORNADA, BONUS_PERFEITO, MINIMO_ACERTOS_FASE,
    atualizar_sequencia_diaria, eh_revisao, fase_aprovada, fases_da_jornada, hoje,
    nivel_de_desempenho, percentual_de_acertos,
)


class ConclusaoService:

    def concluir(self, aluno, id_desafio):
        try:
            return self._concluir(aluno, id_desafio)
        except IntegrityError:
            # Dois pedidos de conclusão chegaram juntos e o outro gravou primeiro. Este é
            # desfeito (sem pagar bônus de novo) e responde com o resultado já gravado.
            Transacao.desfazer()
            return self._concluir(aluno, id_desafio)

    def _concluir(self, aluno, id_desafio):
        desafio = desafio_do_aluno(aluno, id_desafio)
        total_questoes = DesafioQuestaoRepository.contar(id_desafio)
        respostas = RespostaRepository.listar(aluno.id_aluno, id_desafio)
        if len(respostas) < total_questoes:
            raise ErroDeNegocio("Responda todas as questões antes de concluir.")
        corretas = sum(1 for resposta in respostas if resposta.correta)
        pontos_base = sum(resposta.pontos_ganhos for resposta in respostas)
        revisao = eh_revisao(desafio)
        # A revisão não vale pontos nem libera fase, então não tem nota mínima.
        aprovada = revisao or fase_aprovada(corretas, total_questoes)
        resultado = {
            "questoes_corretas": corretas,
            "quantidade_questoes": total_questoes,
            "percentual_acertos": percentual_de_acertos(corretas, total_questoes),
            "minimo_para_avancar": MINIMO_ACERTOS_FASE,
            "desempenho": "revisao" if revisao else nivel_de_desempenho(corretas, total_questoes),
            "aprovado": aprovada,
            "bonus_perfeito": 0,
            "bonus_conclusao": 0,
            "bonus_jornada": 0,
            "jornada_concluida": False,
            "aproveitamento": None,
        }
        registro = AlunoDesafioRepository.buscar(aluno.id_aluno, id_desafio)
        if registro and registro.concluido:
            # Fase já concluída: repetir o pedido não paga os bônus de novo.
            return self._responder(aluno, resultado, concluido=True, ja_concluido=True, pontos_ganhos=pontos_base)
        if not registro:
            registro = AlunoDesafio(id_aluno=aluno.id_aluno, id_desafio=id_desafio)
            AlunoDesafioRepository.adicionar(registro)
        registro.data_realizacao = hoje()

        if not aprovada:
            # Abaixo da nota mínima: a tentativa fica no histórico, sem bônus,
            # e a próxima fase continua bloqueada.
            registro.pontuacao_obtida = pontos_base
            registro.concluido = False
            Transacao.confirmar()
            return self._responder(aluno, resultado, concluido=False, reprovado=True, pontos_ganhos=pontos_base)

        bonus = 0
        if not revisao:
            resultado["bonus_conclusao"] = BONUS_CONCLUSAO_FASE
            if corretas == total_questoes:
                resultado["bonus_perfeito"] = BONUS_PERFEITO
            if (desafio.nivel_mapa or 1) == fases_da_jornada(desafio.quantidade_questoes):
                cadeia = self._cadeia_da_jornada(aluno, desafio)
                if len(cadeia) == (desafio.nivel_mapa or 1):
                    # Última fase, com todas as anteriores aprovadas: a jornada terminou.
                    todas = [r for d in cadeia for r in RespostaRepository.listar(aluno.id_aluno, d.id_desafio)]
                    resultado["jornada_concluida"] = True
                    resultado["aproveitamento"] = percentual_de_acertos(sum(1 for r in todas if r.correta), len(todas))
                    resultado["bonus_jornada"] = BONUS_CONCLUSAO_JORNADA
            bonus = resultado["bonus_conclusao"] + resultado["bonus_perfeito"] + resultado["bonus_jornada"]
        aluno.pontos = (aluno.pontos or 0) + bonus
        registro.pontuacao_obtida = pontos_base + bonus
        registro.concluido = True
        atualizar_sequencia_diaria(aluno)
        Transacao.confirmar()
        return self._responder(aluno, resultado, concluido=True, pontos_ganhos=pontos_base + bonus)

    @staticmethod
    def _responder(aluno, resultado, **campos):
        return {**resultado, **campos, "pontos_totais": aluno.pontos or 0,
                "progresso": ProgressoService().progresso(aluno)}

    @staticmethod
    def _cadeia_da_jornada(aluno, desafio):
        """Fases da jornada que termina em `desafio`, da fase 1 até a atual."""
        cadeia = [desafio]
        esperado = (desafio.nivel_mapa or 1) - 1
        for anterior in DesafioRepository.anteriores_no_tema(aluno.id_aluno, desafio.id_tema, desafio.id_desafio):
            if esperado < 1:
                break
            if eh_revisao(anterior) or (anterior.nivel_mapa or 1) != esperado:
                continue
            if AlunoDesafioRepository.concluido(aluno.id_aluno, anterior.id_desafio):
                cadeia.append(anterior)
                esperado -= 1
        return list(reversed(cadeia))
