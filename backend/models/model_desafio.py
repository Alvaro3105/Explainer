from .database import db


PREFIXO_REVISAO = "[REFAZER] "


class Desafio(db.Model):
    __tablename__ = "desafio"

    id_desafio = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(100), nullable=False)
    dificuldade = db.Column(db.String(120), nullable=False)
    pontuacao = db.Column(db.Integer, nullable=False)
    quantidade_questoes = db.Column(db.Integer, nullable=True)
    data_criacao = db.Column(db.Date)
    id_tema = db.Column(db.Integer, db.ForeignKey("Tema.id_tema"), nullable=True)
    id_aluno = db.Column(db.Integer, db.ForeignKey("Aluno.id_aluno"), nullable=True)
    nivel_mapa = db.Column(db.Integer, nullable=False, default=1)
    origem_ia = db.Column(db.Boolean, nullable=False, default=False)

    def to_dict(self):
        return {
            "id_desafio": self.id_desafio,
            "nome": self.nome,
            "dificuldade": self.dificuldade,
            "pontuacao": self.pontuacao,
            "quantidade_questoes": self.quantidade_questoes,
            "data_criacao": self.data_criacao.isoformat() if self.data_criacao else None,
            "id_tema": self.id_tema,
            "id_aluno": self.id_aluno,
            "nivel_mapa": self.nivel_mapa or 1,
            "origem_ia": bool(self.origem_ia),
        }
