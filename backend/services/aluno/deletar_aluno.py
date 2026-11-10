from repositories.aluno_repositories import AlunoRepository
from repositories.transacao import Transacao
from services.exclusao import remover_aluno


class DeletarAlunoService:

    def executar(self, aluno_id):
        aluno = AlunoRepository.buscar_por_id(aluno_id)
        if aluno is None:
            return False
        remover_aluno(aluno)
        Transacao.confirmar()
        return True
