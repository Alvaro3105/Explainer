from repositories.questao_repository import QuestaoRepository


class VerificarQuestaoService:
    def executar(self, id_questao, alternativa):
        if not alternativa:
            raise ValueError("A alternativa é obrigatória.")

        resultado = QuestaoRepository.verificar_resposta(id_questao, alternativa)
        if resultado is None:
            return None
        return resultado
