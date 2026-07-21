from models.model_desafio_questao import DesafioQuestao
from models.model_desafio import Desafio
from models.model_questao import Questao

class AdicionarQuestaoDesafioService:
    def executar(self, id_desafio, id_questao):
        if not Desafio.buscar_por_id(id_desafio):
            raise ValueError("Desafio não encontrado.")
        if not Questao.buscar_por_id(id_questao):
            raise ValueError("Questão não encontrada.")

        relacao_existente = DesafioQuestao.query.filter_by(
            id_desafio=id_desafio, id_questao=id_questao
        ).first()

        if relacao_existente:
            raise ValueError("Esta questão já está vinculada ao desafio.")

        relacao = DesafioQuestao(id_desafio=id_desafio, id_questao=id_questao)
        relacao.salvar()
        return relacao.to_dict()