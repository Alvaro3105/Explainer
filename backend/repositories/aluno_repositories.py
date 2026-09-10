from sqlalchemy import text

from models.database import db


class AlunoRepository:
    @staticmethod
    def buscar_ranking():
        banco = db.session.get_bind().dialect.name

        if banco == "mysql":
            resultado = db.session.execute(text("CALL sp_ranking_alunos()"))
            linhas = resultado.mappings().all()
            resultado.close()
            return [dict(linha) for linha in linhas]

        resultado = db.session.execute(text("""
            SELECT Ranking.classificacao, Ranking.pontos, Aluno.nome
            FROM Ranking
            JOIN Aluno ON Ranking.id_aluno = Aluno.id_aluno
            ORDER BY Ranking.pontos DESC, Ranking.classificacao ASC
        """))
        linhas = resultado.mappings().all()
        resultado.close()
        return [dict(linha) for linha in linhas]
