from .database import db


class Ranking(db.Model):
    __tablename__ = "Ranking"

    id_ranking = db.Column(db.Integer, primary_key=True, autoincrement=True)
    classificacao = db.Column(db.Integer, nullable=True)
    pontos = db.Column(db.Integer, nullable=True)
    id_aluno = db.Column(db.Integer, db.ForeignKey("Aluno.id_aluno"), nullable=False)

    def to_dict(self):
        return {
            "id_ranking": self.id_ranking,
            "classificacao": self.classificacao,
            "pontos": self.pontos,
            "id_aluno": self.id_aluno,
        }
