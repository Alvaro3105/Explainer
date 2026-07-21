from models.model_ranking import Ranking

class ListarRankingService:
    def executar(self):
        # Retorna ordenado pela classificação/pontuação
        rankings = Ranking.query.order_by(Ranking.pontos.desc()).all()
        return [r.to_dict() for r in rankings]
        