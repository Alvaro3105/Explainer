from sqlalchemy import text

from models.database import db
from models.model_aluno import Aluno

PARTICIPANTES = "SELECT DISTINCT r.id_aluno FROM resposta_desafio r"


def consulta(sql):
    nome = db.session.get_bind().dialect.identifier_preparer.quote
    return text(sql.format(aluno=nome("Aluno"), ranking=nome("Ranking"), participantes=PARTICIPANTES))


class AlunoRepository:
    # Consultas pelo ORM
    @staticmethod
    def buscar_por_id(id_aluno):
        return db.session.get(Aluno, id_aluno) if id_aluno else None

    @staticmethod
    def buscar_por_email(email):
        return Aluno.query.filter_by(email=email).first()

    @staticmethod
    def listar():
        return Aluno.query.all()

    @staticmethod
    def adicionar(aluno):
        db.session.add(aluno)

    @staticmethod
    def remover(aluno):
        db.session.delete(aluno)

    @staticmethod
    def ranking_topo(limite):
        sql = consulta("""
            SELECT a.id_aluno, a.nome, a.nick, COALESCE(a.pontos, 0) AS pontos,
                   a.sequencia_atual, a.foguinho, a.minutos_ativos
            FROM {aluno} a
            WHERE a.id_aluno IN ({participantes})
            ORDER BY COALESCE(a.pontos, 0) DESC, a.nome ASC, a.id_aluno ASC
            LIMIT :limite
        """)
        return [dict(linha) for linha in db.session.execute(sql, {"limite": limite}).mappings().all()]

    @staticmethod
    def total_participantes():
        sql = consulta("SELECT COUNT(*) FROM {aluno} a WHERE a.id_aluno IN ({participantes})")
        return db.session.execute(sql).scalar() or 0

    @staticmethod
    def participa_do_ranking(id_aluno):
        sql = consulta("SELECT 1 FROM resposta_desafio WHERE id_aluno = :id LIMIT 1")
        return db.session.execute(sql, {"id": id_aluno}).first() is not None

    @staticmethod
    def quantos_a_frente(pontos, nome, id_aluno):
        sql = consulta("""
            SELECT COUNT(*) FROM {aluno} a
            WHERE a.id_aluno IN ({participantes})
              AND (COALESCE(a.pontos, 0) > :pontos
                   OR (COALESCE(a.pontos, 0) = :pontos AND a.nome < :nome)
                   OR (COALESCE(a.pontos, 0) = :pontos AND a.nome = :nome AND a.id_aluno < :id))
        """)
        return db.session.execute(sql, {"pontos": pontos, "nome": nome, "id": id_aluno}).scalar() or 0

    # Ranking antigo (tabela Ranking, usada pelo painel administrativo)
    @staticmethod
    def buscar_ranking():
        if db.session.get_bind().dialect.name == "mysql":
            sql = text("CALL sp_ranking_alunos()")
        else:
            sql = consulta("""
                SELECT r.classificacao, r.pontos, a.nome
                FROM {ranking} r
                JOIN {aluno} a ON r.id_aluno = a.id_aluno
                ORDER BY r.pontos DESC, r.classificacao DESC
            """)
        resultado = db.session.execute(sql)
        linhas = resultado.mappings().all()
        resultado.close()
        return [dict(linha) for linha in linhas]
