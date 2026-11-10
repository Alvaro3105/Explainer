from models.model_questao import Questao
from repositories.questao_repository import QuestaoRepository
from repositories.tema_repository import TemaRepository
from repositories.transacao import Transacao


class CriarQuestaoService:

    def executar(self, dados):
        for campo in ("enunciado", "id_tema"):
            if not dados.get(campo):
                raise ValueError(f"O campo '{campo}' é obrigatório.")
        if not TemaRepository.buscar_por_id(dados["id_tema"]):
            raise ValueError("O tema informado não existe.")

        questao = Questao(
            enunciado=dados["enunciado"],
            alternativa_correta=dados.get("alternativa_correta"),
            id_tema=dados["id_tema"],
        )
        QuestaoRepository.adicionar(questao)
        Transacao.confirmar()
        return questao.to_dict()
