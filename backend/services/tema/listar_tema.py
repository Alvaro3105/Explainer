from repositories.tema_repository import TemaRepository


class ListarTemasService:

    def executar(self):
        return [tema.to_dict() for tema in TemaRepository.listar()]
