from repositories.aluno_repositories import AlunoRepository


class ListarAlunosService:

    def executar(self):
        return [aluno.to_dict() for aluno in AlunoRepository.listar()]
