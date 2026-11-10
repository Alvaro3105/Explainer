from models.model_desafio import Desafio


class ListarDesafiosService:
    def executar(self):
        desafios = Desafio.query.all()
        return [desafio.to_dict() for desafio in desafios]
