from models.model_aluno_desafio import AlunoDesafio


class AlunoDesafioRepository:
    @staticmethod
    def buscar(id_aluno, id_desafio):
        return AlunoDesafio.query.filter_by(id_aluno=id_aluno, id_desafio=id_desafio).first()

    @staticmethod
    def listar_desafios_aluno(id_aluno):
        return AlunoDesafio.query.filter_by(id_aluno=id_aluno).all()
