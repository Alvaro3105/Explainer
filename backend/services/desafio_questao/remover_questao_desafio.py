from repositories.desafio_questao_repository import DesafioQuestaoRepository
from repositories.transacao import Transacao


class RemoverQuestaoDesafioService:

    def executar(self, id_desafio, id_questao):
        relacao = DesafioQuestaoRepository.buscar(id_desafio, id_questao)
        if not relacao:
            return False
        DesafioQuestaoRepository.remover(relacao)
        Transacao.confirmar()
        return True
