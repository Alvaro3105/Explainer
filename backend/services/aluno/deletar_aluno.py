from models.model_aluno import Aluno

class DeletarAlunoService:

    def executar(self, aluno_id):
        aluno = Aluno.query.get(aluno_id)

        if aluno is None:
            return False
        aluno.deletar()
        return True
