from models.model_aprendizado import RespostaDesafio
from models.model_desafio_questao import DesafioQuestao
from models.model_questao import Questao


class DeletarQuestaoService:
    def executar(self, id_questao):
        questao = Questao.buscar_por_id(id_questao)
        if not questao:
            return False
        # Uma questão usada em desafio ou já respondida faz parte do histórico de alguém.
        if (DesafioQuestao.query.filter_by(id_questao=id_questao).first()
                or RespostaDesafio.query.filter_by(id_questao=id_questao).first()):
            raise ValueError("Esta questão faz parte de um desafio e não pode ser excluída. Remova-a do desafio primeiro.")
        questao.deletar()
        return True
