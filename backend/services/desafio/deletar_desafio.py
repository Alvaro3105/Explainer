from models.model_desafio import Desafio

class DeletarDesafioService:
    def executar(self, desafio_id):
        desafio = Desafio.buscar_por_id(desafio_id)

        if desafio is None:
            return False
        desafio.deletar()

        return True
