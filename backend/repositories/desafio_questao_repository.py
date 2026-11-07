from sqlalchemy import text

from models.database import db
from models.model_desafio_questao import DesafioQuestao


class DesafioQuestaoRepository:
    """Vínculo entre desafios e questões (tabela desafio_questao)."""

    @staticmethod
    def listar_questoes_desafio(id_desafio):
        sql = text("""
            SELECT q.*
            FROM Questao q
            JOIN desafio_questao dq
                ON dq.id_questao = q.id_questao
            WHERE dq.id_desafio = :id_desafio
        """)

        resultado = db.session.execute(
            sql,
            {"id_desafio": id_desafio}
        )

        return [dict(linha) for linha in resultado.mappings().all()]

    @staticmethod
    def relacoes_ordenadas(id_desafio):
        """Sempre na mesma ordem (a ordem em que as questões foram criadas): bolinha 1, 2, 3..."""
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
        return DesafioQuestao.query.filter_by(id_desafio=id_desafio, id_questao=id_questao).first() is not None

    @staticmethod
    def questao_em_uso(id_questao):
        return DesafioQuestao.query.filter_by(id_questao=id_questao).first() is not None

    @staticmethod
    def vincular(id_desafio, id_questao):
        db.session.add(DesafioQuestao(id_desafio=id_desafio, id_questao=id_questao))

    @staticmethod
    def remover_do_desafio(id_desafio):
        DesafioQuestao.query.filter_by(id_desafio=id_desafio).delete(synchronize_session=False)
