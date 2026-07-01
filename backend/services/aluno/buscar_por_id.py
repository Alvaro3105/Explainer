from models.model_aluno import Aluno


class BuscarAlunoPorIdService:

    def executar(self, aluno_id):
        aluno = Aluno.query.get(aluno_id)
        if aluno is None:
            return None

        return aluno.to_dict()
