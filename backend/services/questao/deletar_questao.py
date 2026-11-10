from repositories.desafio_questao_repository import DesafioQuestaoRepository
from repositories.questao_repository import QuestaoRepository
from repositories.resposta_repository import RespostaRepository
from repositories.transacao import Transacao


class DeletarQuestaoService:

    def executar(self, id_questao):
        questao = QuestaoRepository.buscar_por_id(id_questao)
        if not questao:
            return False
        if DesafioQuestaoRepository.questao_em_uso(id_questao) or RespostaRepository.questao_respondida(id_questao):
            raise ValueError("Esta questão faz parte de um desafio e não pode ser excluída. Remova-a do desafio primeiro.")
        QuestaoRepository.remover(questao)
        Transacao.confirmar()
        return True
