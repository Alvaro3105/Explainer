from repositories.aluno_repositories import AlunoRepository


class BuscarRankingAlunosService:
    def executar(self):
        return AlunoRepository.buscar_ranking()
