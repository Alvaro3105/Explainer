from models.database import db
from models.model_geracao import GeracaoDesafio


class GeracaoRepository:

    @staticmethod
    def buscar_por_id(id_geracao):
        return db.session.get(GeracaoDesafio, id_geracao) if id_geracao else None

    @staticmethod
    def desde(id_aluno, momento):
        """Pedidos do aluno a partir de `momento`, do mais antigo para o mais novo."""
        return (GeracaoDesafio.query
                .filter(GeracaoDesafio.id_aluno == id_aluno, GeracaoDesafio.iniciada_em >= momento)
                .order_by(GeracaoDesafio.iniciada_em.asc(), GeracaoDesafio.id_geracao.asc()).all())

    @staticmethod
    def adicionar(geracao):
        db.session.add(geracao)

    @staticmethod
    def remover(geracao):
        db.session.delete(geracao)

    @staticmethod
    def remover_anteriores(id_aluno, momento):
        (GeracaoDesafio.query
         .filter(GeracaoDesafio.id_aluno == id_aluno, GeracaoDesafio.iniciada_em < momento)
         .delete(synchronize_session=False))

    @staticmethod
    def remover_do_aluno(id_aluno):
        GeracaoDesafio.query.filter_by(id_aluno=id_aluno).delete(synchronize_session=False)

    @staticmethod
    def remover_todos():
        GeracaoDesafio.query.delete(synchronize_session=False)
