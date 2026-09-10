from models.model_desafio import Desafio


class DesafioRepository:
    @staticmethod
    def buscar_por_dificuldade(dificuldade):
        return Desafio.query.filter_by(dificuldade=dificuldade).all()

    @staticmethod
    def buscar_por_id(id_desafio):
        return Desafio.buscar_por_id(id_desafio)
