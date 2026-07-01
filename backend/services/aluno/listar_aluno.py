from models.model_aluno import Aluno

class ListarAlunosService:

    def executar(self):
        alunos = Aluno.query.all()
        
        return [aluno.to_dict() for aluno in alunos]
