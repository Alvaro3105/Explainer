from repositories.questao_repository import QuestaoRepository


class ListarQuestoesService:

    def executar(self):
        return [questao.to_dict() for questao in QuestaoRepository.listar()]
