from models.model_ranking import Ranking


class RankingRepository:
    """Tabela Ranking legada (preenchida só pelo painel administrativo)."""

    @staticmethod
    def remover_do_aluno(id_aluno):
        Ranking.query.filter_by(id_aluno=id_aluno).delete(synchronize_session=False)
