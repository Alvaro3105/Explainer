from models.database import db
from models.model_aluno import Aluno


class BuscarAlunoPorIdService:

    def executar(self, aluno_id):
        aluno = db.session.get(Aluno, aluno_id)
        if aluno is None:
            return None

        return aluno.to_dict()
