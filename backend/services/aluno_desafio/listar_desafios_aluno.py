from repositories.aluno_desafio_repository import AlunoDesafioRepository


class ListarDesafiosAlunoService:

    def executar(self, id_aluno):
        return [registro.to_dict() for registro in AlunoDesafioRepository.listar_desafios_aluno(id_aluno)]
