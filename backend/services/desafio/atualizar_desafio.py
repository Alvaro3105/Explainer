from repositories.desafio_repository import DesafioRepository
from repositories.transacao import Transacao
from services.atualizacao import aplicar_campos


class AtualizarDesafioService:

    def executar(self, desafio_id, dados):
        desafio = DesafioRepository.buscar_por_id(desafio_id)
        if desafio is None:
            return None

        aplicar_campos(desafio, {
            "nome": dados.get("nome"),
            "dificuldade": dados.get("dificuldade"),
            "quantidade_questoes": dados.get("quantidade_questoes"),
        })
        Transacao.confirmar()
        return desafio.to_dict()
