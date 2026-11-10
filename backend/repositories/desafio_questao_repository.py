from models.database import db
from models.model_desafio_questao import DesafioQuestao


class DesafioQuestaoRepository:

    @staticmethod
    def buscar(id_desafio, id_questao):
        return DesafioQuestao.query.filter_by(id_desafio=id_desafio, id_questao=id_questao).first()

    @staticmethod
    def relacoes_ordenadas(id_desafio):
        """Sempre na ordem em que as questões foram criadas (bolinha 1, 2, 3)."""
        return (DesafioQuestao.query.filter_by(id_desafio=id_desafio)
                .order_by(DesafioQuestao.id_questao.asc()).all())

    @staticmethod
    def ids_questoes(id_desafio):
        return [relacao.id_questao for relacao in DesafioQuestaoRepository.relacoes_ordenadas(id_desafio)]

    @staticmethod
    def contar(id_desafio):
        return DesafioQuestao.query.filter_by(id_desafio=id_desafio).count()

    @staticmethod
    def pertence(id_desafio, id_questao):
        return DesafioQuestaoRepository.buscar(id_desafio, id_questao) is not None

    @staticmethod
    def questao_em_uso(id_questao):
        return DesafioQuestao.query.filter_by(id_questao=id_questao).first() is not None

    @staticmethod
    def vincular(id_desafio, id_questao):
        relacao = DesafioQuestao(id_desafio=id_desafio, id_questao=id_questao)
        db.session.add(relacao)
        return relacao

    @staticmethod
    def remover(relacao):
        db.session.delete(relacao)

    @staticmethod
    def remover_do_desafio(id_desafio):
        DesafioQuestao.query.filter_by(id_desafio=id_desafio).delete(synchronize_session=False)
