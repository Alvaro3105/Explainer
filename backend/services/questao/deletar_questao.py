from models.model_questao import Questao

class DeletarQuestaoService:
    def executar(self, id_questao):
        questao = Questao.buscar_por_id(id_questao)
        if not questao:
            return False
        questao.deletar()
        return True