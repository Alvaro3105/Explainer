from sqlalchemy import text

from models.database import db
from models.model_aluno import Aluno

# Só entram no ranking os alunos que já responderam ao menos uma questão.
_PARTICIPANTES = "SELECT DISTINCT r.id_aluno FROM resposta_desafio r"


class AlunoRepository:
    # ---------- consultas pelo ORM ----------
    @staticmethod
    def buscar_por_id(id_aluno):
        return db.session.get(Aluno, id_aluno) if id_aluno else None

    @staticmethod
    def buscar_por_email(email):
        return Aluno.query.filter_by(email=email).first()

    @staticmethod
    def adicionar(aluno):
        db.session.add(aluno)

    @staticmethod
    def remover(aluno):
        db.session.delete(aluno)

    # ---------- ranking do jogo, em SQL ----------
    @staticmethod
    def ranking_topo(limite):
        """Os `limite` primeiros do ranking: pontos ↓, nome ↑ e id ↑ para desempatar."""
        sql = text(f"""
            SELECT a.id_aluno, a.nome, a.nick, COALESCE(a.pontos, 0) AS pontos,
                   a.sequencia_atual, a.foguinho, a.minutos_ativos
            FROM Aluno a
            WHERE a.id_aluno IN ({_PARTICIPANTES})
            ORDER BY COALESCE(a.pontos, 0) DESC, a.nome ASC, a.id_aluno ASC
            LIMIT :limite
        """)
        return [dict(linha) for linha in db.session.execute(sql, {"limite": limite}).mappings().all()]

    @staticmethod
    def total_participantes():
        sql = text(f"SELECT COUNT(*) FROM Aluno a WHERE a.id_aluno IN ({_PARTICIPANTES})")
        return db.session.execute(sql).scalar() or 0

    @staticmethod
    def participa_do_ranking(id_aluno):
        sql = text("SELECT 1 FROM resposta_desafio WHERE id_aluno = :id LIMIT 1")
        return db.session.execute(sql, {"id": id_aluno}).first() is not None

    @staticmethod
    def quantos_a_frente(pontos, nome, id_aluno):
        """Quantos participantes vêm antes deste aluno, na mesma ordem de ranking_topo."""
        sql = text(f"""
            SELECT COUNT(*) FROM Aluno a
            WHERE a.id_aluno IN ({_PARTICIPANTES})
              AND (COALESCE(a.pontos, 0) > :pontos
                   OR (COALESCE(a.pontos, 0) = :pontos AND a.nome < :nome)
                   OR (COALESCE(a.pontos, 0) = :pontos AND a.nome = :nome AND a.id_aluno < :id))
        """)
        return db.session.execute(sql, {"pontos": pontos, "nome": nome, "id": id_aluno}).scalar() or 0

    # ---------- ranking legado (tabela Ranking, usada pelo painel administrativo) ----------
    @staticmethod
    def buscar_ranking():
        banco = db.session.get_bind().dialect.name

        if banco == "mysql":
            sql = text("CALL sp_ranking_alunos()")
            resultado = db.session.execute(sql)
            linhas = resultado.mappings().all()
            resultado.close()
            return [dict(linha) for linha in linhas]

        sql_sqlite = text("""
            SELECT Ranking.classificacao, Ranking.pontos, Aluno.nome
            FROM Ranking
            JOIN Aluno ON Ranking.id_aluno = Aluno.id_aluno
            ORDER BY Ranking.pontos DESC, Ranking.classificacao DESC
        """)

        resultado = db.session.execute(sql_sqlite)
        linhas = resultado.mappings().all()
        resultado.close()

        return [dict(linha) for linha in linhas]
