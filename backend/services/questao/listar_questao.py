from models.model_questao import Questao

class ListarQuestoesService:
    def executar(self):
        questoes = Questao.query.all()
        return [q.to_dict() for q in questoes]