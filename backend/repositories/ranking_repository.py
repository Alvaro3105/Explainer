from models.database import db
from models.model_ranking import Ranking


class RankingRepository:

    @staticmethod
    def buscar_por_id(id_ranking):
        return db.session.get(Ranking, id_ranking) if id_ranking else None

    @staticmethod
    def listar():
        return Ranking.query.order_by(Ranking.pontos.desc()).all()

    @staticmethod
    def adicionar(ranking):
        db.session.add(ranking)

    @staticmethod
    def remover(ranking):
        db.session.delete(ranking)

    @staticmethod
    def remover_do_aluno(id_aluno):
        Ranking.query.filter_by(id_aluno=id_aluno).delete(synchronize_session=False)
