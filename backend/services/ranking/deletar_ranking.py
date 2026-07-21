from models.model_ranking import Ranking

class DeletarRankingService:
    def executar(self, id_ranking):
        ranking = Ranking.buscar_por_id(id_ranking)
        if not ranking:
            return False
        ranking.deletar()
        return True