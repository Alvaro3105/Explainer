from repositories.ranking_repository import RankingRepository
from repositories.transacao import Transacao
from services.atualizacao import aplicar_campos


class AtualizarRankingService:

    def executar(self, id_ranking, dados):
        ranking = RankingRepository.buscar_por_id(id_ranking)
        if not ranking:
            return None

        aplicar_campos(ranking, {
            "classificacao": dados.get("classificacao"),
            "pontos": dados.get("pontos"),
        })
        Transacao.confirmar()
        return ranking.to_dict()
