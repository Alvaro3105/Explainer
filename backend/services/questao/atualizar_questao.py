from repositories.questao_repository import QuestaoRepository
from repositories.tema_repository import TemaRepository
from repositories.transacao import Transacao
from services.atualizacao import aplicar_campos


class AtualizarQuestaoService:

    def executar(self, id_questao, dados):
        questao = QuestaoRepository.buscar_por_id(id_questao)
        if not questao:
            return None

        id_tema = dados.get("id_tema")
        if id_tema and not TemaRepository.buscar_por_id(id_tema):
            raise ValueError("O tema informado não existe.")

        aplicar_campos(questao, {
            "enunciado": dados.get("enunciado"),
            "alternativa_correta": dados.get("alternativa_correta"),
            "id_tema": id_tema,
        })
        Transacao.confirmar()
        return questao.to_dict()
