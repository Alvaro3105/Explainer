from models.database import db
from models.model_desafio import Desafio
from models.model_questao import Questao
from models.model_tema import Tema


class TemaRepository:

    @staticmethod
    def buscar_por_id(id_tema):
        return db.session.get(Tema, id_tema) if id_tema else None

    @staticmethod
    def listar():
        return Tema.query.all()

    @staticmethod
    def listar_ordenados():
        return Tema.query.order_by(Tema.materia.asc(), Tema.nome.asc()).all()

    @staticmethod
    def possui_vinculos(id_tema):
        tem_questao = Questao.query.filter_by(id_tema=id_tema).first() is not None
        tem_desafio = Desafio.query.filter_by(id_tema=id_tema).first() is not None
        return tem_questao or tem_desafio

    @staticmethod
    def adicionar(tema):
        db.session.add(tema)

    @staticmethod
    def remover(tema):
        db.session.delete(tema)
