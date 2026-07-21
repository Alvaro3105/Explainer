from models.model_ranking import Ranking

class AtualizarRankingService:
    def executar(self, id_ranking, dados):
        ranking = Ranking.buscar_por_id(id_ranking)
        if not ranking:
            return None

        ranking.atualizar(
            classificacao=dados.get("classificacao"),
            pontos=dados.get("pontos")
        )
        return ranking.to_dict()
        