from .database import db

class Ranking(db.Model):
    __tablename__ = "Ranking"

    id_ranking = db.Column(db.Integer, primary_key=True, autoincrement=True)
    classificacao = db.Column(db.Integer, nullable=True)
    pontos = db.Column(db.Integer, nullable=True)
    id_aluno = db.Column(db.Integer, db.ForeignKey("Aluno.id_aluno"), nullable=False)

    def salvar(self):
        db.session.add(self)
        db.session.commit()

    def atualizar(self, classificacao=None, pontos=None):
        if classificacao is not None:
            self.classificacao = classificacao
        if pontos is not None:
            self.pontos = pontos
        db.session.commit()

    def deletar(self):
        db.session.delete(self)
        db.session.commit()

    @staticmethod
    def buscar_por_id(id_ranking):
        return Ranking.query.get(id_ranking)

    def to_dict(self):
        return {
            "id_ranking": self.id_ranking,
            "classificacao": self.classificacao,
            "pontos": self.pontos,
            "id_aluno": self.id_aluno,
        }