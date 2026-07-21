from models.model_ranking import Ranking
from models.model_aluno import Aluno

class CriarRankingService:
    def executar(self, dados):
        if not dados.get("id_aluno"):
            raise ValueError("O campo 'id_aluno' é obrigatório.")

        if not Aluno.query.get(dados["id_aluno"]):
            raise ValueError("O aluno informado não existe.")

        ranking = Ranking(
            id_aluno=dados["id_aluno"],
            classificacao=dados.get("classificacao"),
            pontos=dados.get("pontos", 0)
        )
        ranking.salvar()
        return ranking.to_dict()