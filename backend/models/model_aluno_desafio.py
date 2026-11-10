from .database import db


class AlunoDesafio(db.Model):
    __tablename__ = "aluno_desafio"

    id_aluno = db.Column(db.Integer, db.ForeignKey("Aluno.id_aluno"), primary_key=True)
    id_desafio = db.Column(db.Integer, db.ForeignKey("desafio.id_desafio"), primary_key=True)
    data_realizacao = db.Column(db.Date, nullable=True)
    pontuacao_obtida = db.Column(db.Integer, default=0)
    concluido = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "id_aluno": self.id_aluno,
            "id_desafio": self.id_desafio,
            "data_realizacao": self.data_realizacao.isoformat() if self.data_realizacao else None,
            "pontuacao_obtida": self.pontuacao_obtida,
            "concluido": self.concluido
        }
