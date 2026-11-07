"""Casos de uso dos desafios: catálogo, desafio em andamento, gerar desafio e refazer."""
import json
from datetime import date

from sqlalchemy.exc import SQLAlchemyError

from models.model_desafio import PREFIXO_REVISAO, Desafio
from models.model_questao import Questao
from repositories.aluno_desafio_repository import AlunoDesafioRepository
from repositories.desafio_questao_repository import DesafioQuestaoRepository
from repositories.desafio_repository import DesafioRepository
from repositories.questao_repository import QuestaoRepository
from repositories.resposta_repository import RespostaRepository
from repositories.tema_repository import TemaRepository
from repositories.transacao import Transacao
from services.aprendizado.erros import ErroDeNegocio
from services.aprendizado.gerador_questoes import gerar_questoes
from services.aprendizado.regras import (
    PONTOS_POR_DIFICULDADE, QUANTIDADES_PERMITIDAS, dificuldade_da_fase, eh_revisao,
    fases_da_jornada, normalizar_dificuldade,
)
from services.exclusao import remover_desafio


def serializar_questao_para_jogo(questao):
    """Questão como o jogo recebe: nunca expõe a alternativa correta antes da resposta."""
    alternativas = {}
    if questao.alternativas_json:
        try:
            alternativas = json.loads(questao.alternativas_json)
        except json.JSONDecodeError:
            alternativas = {}
    return {
        "id_questao": questao.id_questao,
        "enunciado": questao.enunciado,
        "alternativas": alternativas,
    }


def questoes_do_desafio(id_desafio):
    return [serializar_questao_para_jogo(QuestaoRepository.buscar_por_id(id_questao))
            for id_questao in DesafioQuestaoRepository.ids_questoes(id_desafio)]


def desafio_do_aluno(aluno, id_desafio):
    desafio = DesafioRepository.buscar_por_id(id_desafio)
    if not desafio or desafio.id_aluno != aluno.id_aluno:
        raise ErroDeNegocio("Desafio não encontrado para esta conta.", 404)
    return desafio


def resultado_das_respostas(aluno, id_desafio):
    """Mapas {id_questao: alternativa escolhida} e {id_questao: acertou?} das respostas já dadas."""
    respostas = RespostaRepository.listar(aluno.id_aluno, id_desafio)
    escolhidas = {str(r.id_questao): r.alternativa_escolhida for r in respostas}
    acertos = {str(r.id_questao): bool(r.correta) for r in respostas}
    return escolhidas, acertos


class DesafioService:

    def catalogo(self):
        materias = {}
        for tema in TemaRepository.listar_ordenados():
            materias.setdefault(tema.materia, []).append({"id_tema": tema.id_tema, "nome": tema.nome})
        return [{"nome": nome, "temas": temas} for nome, temas in materias.items()]

    def desafio_ativo(self, aluno):
        """O desafio normal (não revisão) mais recente que ainda não foi concluído, ou None."""
        for desafio in DesafioRepository.listar_do_aluno(aluno.id_aluno, mais_recentes_primeiro=True):
            # Revisões são sessões independentes e nunca devem substituir a jornada normal.
            if eh_revisao(desafio) or AlunoDesafioRepository.concluido(aluno.id_aluno, desafio.id_desafio):
                continue
            total = DesafioQuestaoRepository.contar(desafio.id_desafio)
            # Também devolve a fase com todas as questões respondidas mas ainda não concluída
            # (a pessoa saiu antes de clicar em "Concluir fase"); senão ela ficaria presa.
            if total:
                tema = TemaRepository.buscar_por_id(desafio.id_tema)
                escolhidas, acertos = resultado_das_respostas(aluno, desafio.id_desafio)
                return {"ativo": True, "desafio": desafio.to_dict(), "tema": tema.to_dict() if tema else None,
                        "questoes": questoes_do_desafio(desafio.id_desafio), "respondidas": escolhidas,
                        "acertos": acertos, "todas_respondidas": len(escolhidas) >= total}
        return {"ativo": False}

    def buscar(self, aluno, id_desafio):
        desafio = desafio_do_aluno(aluno, id_desafio)
        escolhidas, acertos = resultado_das_respostas(aluno, id_desafio)
        return {"desafio": desafio.to_dict(), "questoes": questoes_do_desafio(id_desafio),
                "respondidas": escolhidas, "acertos": acertos,
                "concluido": AlunoDesafioRepository.concluido(aluno.id_aluno, id_desafio)}

    def criar(self, aluno, dados):
        refazer = bool(dados.get("refazer", False))
        if refazer and dados.get("refazer_de"):
            return self._criar_revisao(aluno, dados.get("refazer_de"))
        try:
            fase_jornada = max(1, min(int(dados.get("fase_jornada", 1)), 20))
        except (TypeError, ValueError):
            fase_jornada = 1
        try:
            id_tema = int(dados.get("id_tema", 0))
            quantidade = int(dados.get("quantidade_questoes", 5))
        except (TypeError, ValueError):
            raise ErroDeNegocio("Tema e quantidade precisam ser válidos.")
        dificuldade = normalizar_dificuldade(dados.get("dificuldade", "normal"))
        if quantidade not in QUANTIDADES_PERMITIDAS:
            raise ErroDeNegocio("Escolha 5, 10, 15 ou 20 questões.")
        if not dificuldade:
            raise ErroDeNegocio("Escolha Fácil, Médio ou Difícil.")
        tema = TemaRepository.buscar_por_id(id_tema)
        if not tema:
            raise ErroDeNegocio("O tema selecionado não existe.", 404)
        # A fase vem do front, mas o servidor não confia nela: só vale se a fase anterior desta
        # jornada (mesmo tema) já foi concluída por este aluno; caso contrário recomeça na fase 1.
        fase = min(fase_jornada, fases_da_jornada(quantidade))
        if fase > 1 and not DesafioRepository.fase_concluida(aluno.id_aluno, tema.id_tema, fase - 1):
            fase = 1
        # A dificuldade sobe um nível por fase concluída, com teto em "Difícil". Quando o front
        # informa a dificuldade inicial, o servidor recalcula a da fase que realmente vai gravar,
        # para que questões e pontuação nunca divirjam da fase e da dificuldade exibidas.
        dificuldade_base = normalizar_dificuldade(dados.get("dificuldade_base"))
        if dificuldade_base and not refazer:
            dificuldade = dificuldade_da_fase(dificuldade_base, fase)
        try:
            # Evita repetir enunciados que este aluno já viu para o mesmo tema e dificuldade.
            enunciados_anteriores = []
            if not refazer:
                enunciados_anteriores = QuestaoRepository.enunciados_ja_vistos(aluno.id_aluno, tema.id_tema, dificuldade)
                # Gerar um desafio novo descarta o desafio em andamento (o front já pediu confirmação).
                self._apagar_desafios_em_andamento(aluno)
            questoes_geradas, origem, aviso = gerar_questoes(
                tema.materia, tema.nome, dificuldade, quantidade, excluir_enunciados=enunciados_anteriores)
            desafio = Desafio(
                nome=(f"{PREFIXO_REVISAO}{tema.nome} · Tentativa" if refazer else f"{tema.nome} · Fase {fase}"),
                dificuldade=dificuldade,
                pontuacao=quantidade * PONTOS_POR_DIFICULDADE[dificuldade],
                quantidade_questoes=quantidade,
                data_criacao=date.today(),
                id_tema=tema.id_tema,
                id_aluno=aluno.id_aluno,
                nivel_mapa=fase,
                origem_ia=(origem == "ia"),
            )
            DesafioRepository.adicionar(desafio)
            for item in questoes_geradas:
                questao = Questao(
                    enunciado=item["enunciado"],
                    alternativa_correta=item["alternativa_correta"],
                    id_tema=tema.id_tema,
                    alternativas_json=json.dumps(item["alternativas"], ensure_ascii=False),
                    explicacao=item["explicacao"],
                )
                QuestaoRepository.adicionar(questao)
                DesafioQuestaoRepository.vincular(desafio.id_desafio, questao.id_questao)
            Transacao.confirmar()
        except RuntimeError as erro:
            Transacao.desfazer()
            raise ErroDeNegocio(str(erro), 502)
        except (SQLAlchemyError, KeyError, ValueError):
            Transacao.desfazer()
            raise ErroDeNegocio("Não foi possível criar o desafio. Verifique a configuração e tente novamente.", 500)
        return {
            "desafio": desafio.to_dict(),
            "tema": tema.to_dict(),
            "origem_questoes": origem,
            "aviso": aviso,
            "questoes": questoes_do_desafio(desafio.id_desafio),
        }

    def _criar_revisao(self, aluno, refazer_de):
        """Refazer: reaproveita as MESMAS questões (na mesma ordem/bolinha) de um desafio já concluído."""
        try:
            origem = DesafioRepository.buscar_por_id(int(refazer_de))
        except (TypeError, ValueError):
            origem = None
        if (not origem or origem.id_aluno != aluno.id_aluno or eh_revisao(origem)
                or not AlunoDesafioRepository.concluido(aluno.id_aluno, origem.id_desafio)):
            raise ErroDeNegocio("Só é possível refazer um desafio que você já concluiu.", 404)
        tema_origem = TemaRepository.buscar_por_id(origem.id_tema)
        try:
            revisao = Desafio(
                nome=f"{PREFIXO_REVISAO}{tema_origem.nome} · Tentativa", dificuldade=origem.dificuldade, pontuacao=0,
                quantidade_questoes=origem.quantidade_questoes, data_criacao=date.today(), id_tema=origem.id_tema,
                id_aluno=aluno.id_aluno, nivel_mapa=origem.nivel_mapa or 1, origem_ia=origem.origem_ia,
            )
            DesafioRepository.adicionar(revisao)
            for id_questao in DesafioQuestaoRepository.ids_questoes(origem.id_desafio):
                DesafioQuestaoRepository.vincular(revisao.id_desafio, id_questao)
            Transacao.confirmar()
        except SQLAlchemyError:
            Transacao.desfazer()
            raise ErroDeNegocio("Não foi possível preparar a revisão.", 500)
        return {
            "desafio": revisao.to_dict(), "tema": tema_origem.to_dict(), "origem_questoes": "salvas", "aviso": None,
            "questoes": questoes_do_desafio(revisao.id_desafio),
        }

    @staticmethod
    def _apagar_desafios_em_andamento(aluno):
        """Remove os desafios normais ainda não concluídos do aluno (substituídos por um novo)."""
        for desafio in DesafioRepository.listar_do_aluno(aluno.id_aluno):
            if eh_revisao(desafio) or AlunoDesafioRepository.concluido(aluno.id_aluno, desafio.id_desafio):
                continue
            remover_desafio(desafio)
