from repositories.desafio_repository import DesafioRepository


class ListarDesafiosService:

    def executar(self):
        return [desafio.to_dict() for desafio in DesafioRepository.listar()]
