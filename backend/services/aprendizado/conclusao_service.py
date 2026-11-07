"""Caso de uso: concluir a fase (bônus, fim da jornada e reprovação por excesso de erros)."""
from datetime import date

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
    BONUS_CONCLUSAO_FASE, BONUS_CONCLUSAO_JORNADA, BONUS_PERFEITO, LIMITE_ERROS_JORNADA,
    atualizar_sequencia_diaria, eh_revisao, fases_da_jornada,
)
from services.exclusao import remover_desafio


class ConclusaoService:

    def concluir(self, aluno, id_desafio):
        desafio = desafio_do_aluno(aluno, id_desafio)
        progresso = ProgressoService()
        total_questoes = DesafioQuestaoRepository.contar(id_desafio)
        respostas = RespostaRepository.listar(aluno.id_aluno, id_desafio)
        if len(respostas) < total_questoes:
            raise ErroDeNegocio("Responda todas as questões antes de concluir.")
        corretas = sum(1 for resposta in respostas if resposta.correta)
        pontos_base = sum(resposta.pontos_ganhos for resposta in respostas)
        registro = AlunoDesafioRepository.buscar(aluno.id_aluno, id_desafio)
        if registro and registro.concluido:
            # Concluir de novo não paga os bônus outra vez.
            return {
                "concluido": True,
                "ja_concluido": True,
                "questoes_corretas": corretas,
                "quantidade_questoes": total_questoes,
                "pontos_ganhos": pontos_base,
                "pontos_totais": aluno.pontos or 0,
                "bonus_perfeito": 0,
                "bonus_conclusao": 0,
                "bonus_jornada": 0,
                "progresso": progresso.progresso(aluno),
            }
        if not registro:
            registro = AlunoDesafio(id_aluno=aluno.id_aluno, id_desafio=id_desafio)
            AlunoDesafioRepository.adicionar(registro)

        # Última fase da jornada: confere o aproveitamento de TODAS as fases juntas.
        jornada_concluida = False
        aproveitamento = None
        if not eh_revisao(desafio) and (desafio.nivel_mapa or 1) == fases_da_jornada(desafio.quantidade_questoes):
            cadeia = self._cadeia_da_jornada(aluno, desafio)
            if len(cadeia) == (desafio.nivel_mapa or 1):
                todas = [r for d in cadeia for r in RespostaRepository.listar(aluno.id_aluno, d.id_desafio)]
                total = len(todas)
                erradas = sum(1 for r in todas if not r.correta)
                taxa_erro = round(erradas * 100 / total) if total else 0
                aproveitamento = 100 - taxa_erro
                if total and erradas * 100 >= LIMITE_ERROS_JORNADA * total:
                    pontos_perdidos = self._reprovar_jornada(aluno, cadeia)
                    Transacao.confirmar()
                    return {
                        "concluido": False,
                        "reprovado": True,
                        "taxa_erro": taxa_erro,
                        "aproveitamento": aproveitamento,
                        "questoes_total": total,
                        "questoes_corretas": total - erradas,
                        "pontos_perdidos": pontos_perdidos,
                        "pontos_totais": aluno.pontos or 0,
                        "progresso": progresso.progresso(aluno),
                    }
                jornada_concluida = True

        bonus_perfeito = bonus_conclusao = bonus_jornada = 0
        if not eh_revisao(desafio):
            if corretas == total_questoes and total_questoes > 0:
                bonus_perfeito = BONUS_PERFEITO
            bonus_conclusao = BONUS_CONCLUSAO_FASE
            if jornada_concluida:
                bonus_jornada = BONUS_CONCLUSAO_JORNADA
        bonus = bonus_perfeito + bonus_conclusao + bonus_jornada
        aluno.pontos = (aluno.pontos or 0) + bonus
        registro.data_realizacao = date.today()
        registro.pontuacao_obtida = pontos_base + bonus
        registro.concluido = True
        atualizar_sequencia_diaria(aluno)
        Transacao.confirmar()
        return {
            "concluido": True,
            "questoes_corretas": corretas,
            "quantidade_questoes": total_questoes,
            "pontos_ganhos": pontos_base + bonus,
            "pontos_totais": aluno.pontos or 0,
            "bonus_perfeito": bonus_perfeito,
            "bonus_conclusao": bonus_conclusao,
            "bonus_jornada": bonus_jornada,
            "jornada_concluida": jornada_concluida,
            "aproveitamento": aproveitamento,
            "progresso": progresso.progresso(aluno),
        }

    @staticmethod
    def _cadeia_da_jornada(aluno, desafio):
        """Fases da jornada que termina em `desafio` (fase 1 ... fase atual), em ordem."""
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

    @staticmethod
    def _reprovar_jornada(aluno, cadeia):
        """Desfaz a jornada inteira: apaga fases e revisões, e tira os pontos que ela havia rendido."""
        pontos_perdidos = 0
        for desafio in cadeia:
            registro = AlunoDesafioRepository.buscar(aluno.id_aluno, desafio.id_desafio)
            if registro and registro.concluido:
                pontos_perdidos += registro.pontuacao_obtida or 0
            else:  # fase atual: só os pontos das respostas
                pontos_perdidos += sum(r.pontos_ganhos for r in RespostaRepository.listar(aluno.id_aluno, desafio.id_desafio))
        ids_questoes = {id_q for d in cadeia for id_q in DesafioQuestaoRepository.ids_questoes(d.id_desafio)}
        for revisao in DesafioRepository.listar_do_aluno(aluno.id_aluno):
            if eh_revisao(revisao) and ids_questoes.intersection(DesafioQuestaoRepository.ids_questoes(revisao.id_desafio)):
                remover_desafio(revisao)
        for desafio in cadeia:
            remover_desafio(desafio)
        pontos_perdidos = max(0, pontos_perdidos)  # nunca devolve pontos por causa de penalidades acumuladas
        antes = aluno.pontos or 0
        aluno.pontos = max(0, antes - pontos_perdidos)
        return antes - aluno.pontos
