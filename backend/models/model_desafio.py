from .database import db
from datetime import datetime

class Desafio(db.Model):
    __tablename__ = "desafio"

    id_desafio = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(100), nullable=False)
    dificuldade = db.Column(db.String(120), nullable=False) 
    pontuacao = db.Column(db.Integer, nullable=False)
    quantidade_questoes = db.Column(db.Integer, nullable=True)
    data_criacao = db.Column(db.Date)

    def salvar(self):
        db.session.add(self)
        db.session.commit()

    def atualizar(self, nome=None, dificuldade=None, quantidade_questoes=None):
        if nome is not None:
            self.nome = nome

        if dificuldade is not None:
            self.dificuldade = dificuldade

        if quantidade_questoes is not None:
            self.quantidade_questoes = quantidade_questoes

        db.session.commit()

    def deletar(self):
        db.session.delete(self)
        db.session.commit()

    @staticmethod
    def buscar_por_nome(nome):
        return Desafio.query.filter_by(nome=nome).first()
    
    @staticmethod
    def buscar_por_id(id_desafio):
        return Desafio.query.get(id_desafio)

    def to_dict(self):
        return {
            "id_desafio": self.id_desafio,
            "nome": self.nome,
            "dificuldade": self.dificuldade,
            "pontuacao": self.pontuacao,
            "quantidade_questoes": self.quantidade_questoes,
            "data_criacao": self.data_criacao.isoformat() if self.data_criacao else None,
        }
