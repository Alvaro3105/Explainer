from repositories.ranking_repository import RankingRepository


class ListarRankingService:

    def executar(self):
        return [ranking.to_dict() for ranking in RankingRepository.listar()]
