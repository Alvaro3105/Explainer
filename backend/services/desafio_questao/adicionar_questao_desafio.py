from repositories.desafio_questao_repository import DesafioQuestaoRepository
from repositories.desafio_repository import DesafioRepository
from repositories.questao_repository import QuestaoRepository
from repositories.transacao import Transacao


class AdicionarQuestaoDesafioService:

    def executar(self, id_desafio, id_questao):
        if not DesafioRepository.buscar_por_id(id_desafio):
            raise ValueError("Desafio não encontrado.")
        if not QuestaoRepository.buscar_por_id(id_questao):
            raise ValueError("Questão não encontrada.")
        if DesafioQuestaoRepository.pertence(id_desafio, id_questao):
            raise ValueError("Esta questão já está vinculada ao desafio.")

        relacao = DesafioQuestaoRepository.vincular(id_desafio, id_questao)
        Transacao.confirmar()
        return relacao.to_dict()
