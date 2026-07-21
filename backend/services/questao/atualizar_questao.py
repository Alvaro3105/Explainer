from models.model_questao import Questao
from models.model_tema import Tema

class AtualizarQuestaoService:
    def executar(self, id_questao, dados):
        questao = Questao.buscar_por_id(id_questao)
        if not questao:
            return None

        id_tema = dados.get("id_tema")
        if id_tema and not Tema.buscar_por_id(id_tema):
            raise ValueError("O tema informado não existe.")

        questao.atualizar(
            enunciado=dados.get("enunciado"),
            alternativa_correta=dados.get("alternativa_correta"),
            id_tema=id_tema
        )
        return questao.to_dict()