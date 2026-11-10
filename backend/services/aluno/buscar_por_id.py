from repositories.aluno_repositories import AlunoRepository


class BuscarAlunoPorIdService:

    def executar(self, aluno_id):
        aluno = AlunoRepository.buscar_por_id(aluno_id)
        return aluno.to_dict() if aluno else None
