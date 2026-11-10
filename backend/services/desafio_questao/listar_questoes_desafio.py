from repositories.questao_repository import QuestaoRepository


class ListarQuestoesDesafioService:

    def executar(self, id_desafio):
        return [questao.to_dict() for questao in QuestaoRepository.listar_do_desafio(id_desafio)]
