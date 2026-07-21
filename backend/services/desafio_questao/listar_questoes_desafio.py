from models.model_desafio_questao import DesafioQuestao
from models.model_questao import Questao

class ListarQuestoesDesafioService:
    def executar(self, id_desafio):
        relacoes = DesafioQuestao.query.filter_by(id_desafio=id_desafio).all()
        ids_questoes = [r.id_questao for r in relacoes]

        questoes = Questao.query.filter(Questao.id_questao.in_(ids_questoes)).all()
        return [q.to_dict() for q in questoes]