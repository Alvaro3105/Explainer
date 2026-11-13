import json

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
from services.aprendizado.limite_geracao import vaga_de_geracao
from services.aprendizado.regras import (
    PONTOS_POR_DIFICULDADE, QUANTIDADES_PERMITIDAS, dificuldade_da_fase, eh_revisao,
    fases_da_jornada, hoje, normalizar_dificuldade,
)
from services.exclusao import remover_desafio


def serializar_questao_para_jogo(questao):
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
    """Devolve dois dicionários das respostas já dadas: a alternativa escolhida e se acertou."""
    respostas = RespostaRepository.listar(aluno.id_aluno, id_desafio)
    escolhidas = {str(r.id_questao): r.alternativa_escolhida for r in respostas}
    acertos = {str(r.id_questao): bool(r.correta) for r in respostas}
    return escolhidas, acertos


class DesafioService:

    def desafio_ativo(self, aluno):
        for desafio in DesafioRepository.listar_do_aluno(aluno.id_aluno, mais_recentes_primeiro=True):
            # Revisão não conta como desafio em andamento.
            if eh_revisao(desafio) or AlunoDesafioRepository.buscar(aluno.id_aluno, desafio.id_desafio):
                continue
            total = DesafioQuestaoRepository.contar(desafio.id_desafio)
            # Fase com tudo respondido mas não concluída também volta,
            # para a pessoa conseguir concluir depois.
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
                "concluido": AlunoDesafioRepository.concluido(aluno.id_aluno, id_desafio),
                "reprovado": AlunoDesafioRepository.reprovado(aluno.id_aluno, id_desafio)}

    def criar(self, aluno, dados):
        if dados.get("refazer"):
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
        if not tema.id_materia:
            # Tema de matéria que saiu do catálogo: fica só no histórico.
            raise ErroDeNegocio("Este tema não está mais disponível para novos desafios.", 404)
        # O desafio é de UMA matéria: o tema escolhido precisa ser da matéria selecionada.
        id_materia = dados.get("id_materia")
        if id_materia not in (None, "") and str(tema.id_materia) != str(id_materia):
            raise ErroDeNegocio("Este tema não pertence à matéria selecionada.")
        # Subtema: o pedido à IA leva o tema principal e o subtema escolhido.
        pai = TemaRepository.buscar_por_id(tema.id_tema_pai) if tema.id_tema_pai else None
        # A fase vem do navegador, mas o servidor confere: só vale se a fase anterior
        # do mesmo tema já foi aprovada. Se não foi, desce até a fase liberada.
        fase = min(fase_jornada, fases_da_jornada(quantidade))
        while fase > 1 and not DesafioRepository.fase_concluida(aluno.id_aluno, tema.id_tema, fase - 1):
            fase -= 1
        # A dificuldade sobe um nível por fase, até "Difícil". O servidor recalcula a
        # dificuldade da fase que vai gravar, para bater com as questões e os pontos.
        dificuldade_base = normalizar_dificuldade(dados.get("dificuldade_base"))
        if dificuldade_base:
            dificuldade = dificuldade_da_fase(dificuldade_base, fase)
        # Limite por aluno: uma geração por vez, com intervalo e teto por janela e por dia.
        with vaga_de_geracao(aluno.id_aluno):
            desafio, origem = self._gerar_e_gravar(aluno, tema, pai, fase, dificuldade, quantidade)
        return {
            "desafio": desafio.to_dict(),
            "tema": tema.to_dict(),
            "origem_questoes": origem,
            "questoes": questoes_do_desafio(desafio.id_desafio),
        }

    def _gerar_e_gravar(self, aluno, tema, pai, fase, dificuldade, quantidade):
        """Pede as questões ao gerador e grava o desafio. Em qualquer falha, nada fica gravado."""
        try:
            enunciados_anteriores = QuestaoRepository.enunciados_ja_vistos(aluno.id_aluno, tema.id_tema, dificuldade)
            pedido = (tema.materia, pai.nome if pai else tema.nome, dificuldade, quantidade)
            subtema = tema.nome if pai else None
            # A IA pode demorar: a leitura é encerrada antes, para não prender o banco.
            Transacao.soltar()
            questoes_geradas, origem = gerar_questoes(*pedido, excluir_enunciados=enunciados_anteriores, subtema=subtema)
            # Só com as questões novas na mão o desafio antigo sem respostas é trocado.
            # Se a geração falhar, ele continua lá.
            self._apagar_desafios_em_andamento(aluno)
            desafio = Desafio(
                nome=f"{tema.nome[:85]} · Fase {fase}",  # o nome do desafio tem até 100 letras
                dificuldade=dificuldade,
                pontuacao=quantidade * PONTOS_POR_DIFICULDADE[dificuldade],
                quantidade_questoes=quantidade,
                data_criacao=hoje(),
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
            return desafio, origem
        except RuntimeError as erro:
            Transacao.desfazer()
            # O gerador diz o motivo (cota, chave recusada, fora do ar) no status e na espera sugerida.
            espera = getattr(erro, "espera", None)
            raise ErroDeNegocio(str(erro), getattr(erro, "status", 502),
                                cabecalhos={"Retry-After": str(espera)} if espera else None)
        except (SQLAlchemyError, KeyError, ValueError):
            Transacao.desfazer()
            raise ErroDeNegocio("Não foi possível criar o desafio. Verifique a configuração e tente novamente.", 500)

    def _criar_revisao(self, aluno, refazer_de):
        """Refazer: usa as mesmas questões, na mesma ordem, de um desafio já concluído."""
        try:
            origem = DesafioRepository.buscar_por_id(int(refazer_de))
        except (TypeError, ValueError):
            origem = None
        if (not origem or origem.id_aluno != aluno.id_aluno or eh_revisao(origem)
                or not AlunoDesafioRepository.concluido(aluno.id_aluno, origem.id_desafio)):
            raise ErroDeNegocio("Só é possível refazer um desafio que você já concluiu.", 404)
        tema_origem = TemaRepository.buscar_por_id(origem.id_tema)
        if not tema_origem:
            raise ErroDeNegocio("O tema deste desafio não existe mais.", 404)
        try:
            revisao = Desafio(
                nome=f"{PREFIXO_REVISAO}{tema_origem.nome[:78]} · Tentativa", dificuldade=origem.dificuldade, pontuacao=0,
                quantidade_questoes=origem.quantidade_questoes, data_criacao=hoje(), id_tema=origem.id_tema,
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
            "desafio": revisao.to_dict(), "tema": tema_origem.to_dict(), "origem_questoes": "salvas",
            "questoes": questoes_do_desafio(revisao.id_desafio),
        }

    @staticmethod
    def _apagar_desafios_em_andamento(aluno):
        for desafio in DesafioRepository.listar_do_aluno(aluno.id_aluno):
            if eh_revisao(desafio) or AlunoDesafioRepository.concluido(aluno.id_aluno, desafio.id_desafio):
                continue
            if RespostaRepository.contar(aluno.id_aluno, desafio.id_desafio):
                continue
            remover_desafio(desafio)
