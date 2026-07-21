from models.model_aluno_desafio import AlunoDesafio

class ListarDesafiosAlunoService:
    def executar(self, id_aluno):
        historico = AlunoDesafio.query.filter_by(id_aluno=id_aluno).all()
        return [h.to_dict() for h in historico]