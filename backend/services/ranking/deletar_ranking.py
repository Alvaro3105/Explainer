from repositories.ranking_repository import RankingRepository
from repositories.transacao import Transacao


class DeletarRankingService:

    def executar(self, id_ranking):
        ranking = RankingRepository.buscar_por_id(id_ranking)
        if not ranking:
            return False
        RankingRepository.remover(ranking)
        Transacao.confirmar()
        return True
