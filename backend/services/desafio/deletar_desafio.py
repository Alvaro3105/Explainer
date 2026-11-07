from models.database import db
from models.model_desafio import Desafio
from services.exclusao import remover_desafio


class DeletarDesafioService:
    def executar(self, desafio_id):
        desafio = Desafio.buscar_por_id(desafio_id)

        if desafio is None:
            return False
        # Apaga também respostas, conclusões e vínculos com questões (antes ficavam órfãos).
        remover_desafio(desafio)
        db.session.commit()
        return True
