from models.model_ranking import Ranking
from repositories.aluno_repositories import AlunoRepository
from repositories.ranking_repository import RankingRepository
from repositories.transacao import Transacao


class CriarRankingService:

    def executar(self, dados):
        if not dados.get("id_aluno"):
            raise ValueError("O campo 'id_aluno' é obrigatório.")
        if not AlunoRepository.buscar_por_id(dados["id_aluno"]):
            raise ValueError("O aluno informado não existe.")

        ranking = Ranking(
            id_aluno=dados["id_aluno"],
            classificacao=dados.get("classificacao"),
            pontos=dados.get("pontos", 0),
        )
        RankingRepository.adicionar(ranking)
        Transacao.confirmar()
        return ranking.to_dict()
