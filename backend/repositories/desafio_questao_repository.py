from sqlalchemy import text

from models.database import db


class DesafioQuestaoRepository:
    @staticmethod
    def listar_questoes_desafio(id_desafio):
        resultado = db.session.execute(text("""
            SELECT q.*
            FROM Questao q
            JOIN desafio_questao dq ON dq.id_questao = q.id_questao
            WHERE dq.id_desafio = :id_desafio
        """), {"id_desafio": id_desafio})
        return [dict(linha) for linha in resultado.mappings().all()]
