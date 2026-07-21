from .database import db

class AlunoDesafio(db.Model):
    __tablename__ = "aluno_desafio"

    id_aluno = db.Column(db.Integer, db.ForeignKey("Aluno.id_aluno"), primary_key=True)
    id_desafio = db.Column(db.Integer, db.ForeignKey("desafio.id_desafio"), primary_key=True)
    data_realizacao = db.Column(db.Date, nullable=True)
    pontuacao_obtida = db.Column(db.Integer, default=0)
    concluido = db.Column(db.Boolean, default=False)

    def salvar(self):
        db.session.add(self)
        db.session.commit()

    def atualizar(self, data_realizacao=None, pontuacao_obtida=None, concluido=None):
        if data_realizacao is not None:
            self.data_realizacao = data_realizacao
        if pontuacao_obtida is not None:
            self.pontuacao_obtida = pontuacao_obtida
        if concluido is not None:
            self.concluido = concluido
        db.session.commit()

    def deletar(self):
        db.session.delete(self)
        db.session.commit()

    def to_dict(self):
        return {
            "id_aluno": self.id_aluno,
            "id_desafio": self.id_desafio,
            "data_realizacao": self.data_realizacao.isoformat() if self.data_realizacao else None,
            "pontuacao_obtida": self.pontuacao_obtida,
            "concluido": self.concluido
        }