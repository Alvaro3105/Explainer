from repositories.tema_repository import TemaRepository
from repositories.transacao import Transacao


class DeletarTemaService:

    def executar(self, id_tema):
        tema = TemaRepository.buscar_por_id(id_tema)
        if not tema:
            return False
        if TemaRepository.possui_vinculos(id_tema):
            raise ValueError("Este tema tem questões ou desafios vinculados e não pode ser excluído.")
        TemaRepository.remover(tema)
        Transacao.confirmar()
        return True
