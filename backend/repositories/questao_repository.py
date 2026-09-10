from models.model_questao import Questao


class QuestaoRepository:
    @staticmethod
    def verificar_resposta(id_questao, alternativa):
        questao = Questao.buscar_por_id(id_questao)
        if questao is None:
            return None
        if not questao.alternativa_correta:
            return False
        return questao.alternativa_correta.upper() == alternativa.upper()
