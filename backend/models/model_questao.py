import json

from .database import db


class Questao(db.Model):
    __tablename__ = "Questao"

    id_questao = db.Column(db.Integer, primary_key=True, autoincrement=True)
    enunciado = db.Column(db.Text, nullable=False)
    alternativa_correta = db.Column(db.String(1), nullable=True)
    id_tema = db.Column(db.Integer, db.ForeignKey("Tema.id_tema"), nullable=False, index=True)
    alternativas_json = db.Column(db.Text, nullable=True)
    explicacao = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            "id_questao": self.id_questao,
            "enunciado": self.enunciado,
            "alternativa_correta": self.alternativa_correta,
            "id_tema": self.id_tema,
            "alternativas": json.loads(self.alternativas_json) if self.alternativas_json else {},
            "explicacao": self.explicacao,
        }
