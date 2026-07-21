from models.model_desafio_questao import DesafioQuestao

class RemoverQuestaoDesafioService:
    def executar(self, id_desafio, id_questao):
        relacao = DesafioQuestao.query.filter_by(
            id_desafio=id_desafio, id_questao=id_questao
        ).first()

        if not relacao:
            return False

        relacao.deletar()
        return True