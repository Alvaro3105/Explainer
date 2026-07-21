from models.model_questao import Questao
from models.model_tema import Tema

class CriarQuestaoService:
    def executar(self, dados):
        for campo in ["enunciado", "id_tema"]:
            if not dados.get(campo):
                raise ValueError(f"O campo '{campo}' é obrigatório.")

        if not Tema.buscar_por_id(dados["id_tema"]):
            raise ValueError("O tema informado não existe.")

        questao = Questao(
            enunciado=dados["enunciado"],
            alternativa_correta=dados.get("alternativa_correta"),
            id_tema=dados["id_tema"]
        )
        questao.salvar()
        return questao.to_dict()