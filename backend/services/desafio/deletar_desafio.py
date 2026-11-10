from repositories.desafio_repository import DesafioRepository
from repositories.transacao import Transacao
from services.exclusao import remover_desafio


class DeletarDesafioService:

    def executar(self, desafio_id):
        desafio = DesafioRepository.buscar_por_id(desafio_id)
        if desafio is None:
            return False
        remover_desafio(desafio)
        Transacao.confirmar()
        return True
