from models.database import db
from models.model_aluno_desafio import AlunoDesafio
from models.model_desafio import PREFIXO_REVISAO, Desafio


class AlunoDesafioRepository:

    @staticmethod
    def buscar(id_aluno, id_desafio):
        return AlunoDesafio.query.filter_by(
            id_aluno=id_aluno,
            id_desafio=id_desafio
        ).first()

    @staticmethod
    def listar_desafios_aluno(id_aluno):
        return AlunoDesafio.query.filter_by(
            id_aluno=id_aluno
        ).all()

    @staticmethod
    def concluido(id_aluno, id_desafio):
        registro = AlunoDesafioRepository.buscar(id_aluno, id_desafio)
        return bool(registro and registro.concluido)

    @staticmethod
    def contar_concluidos(id_aluno):
        return (Desafio.query.join(AlunoDesafio, AlunoDesafio.id_desafio == Desafio.id_desafio)
                .filter(AlunoDesafio.id_aluno == id_aluno, AlunoDesafio.concluido.is_(True),
                        ~Desafio.nome.startswith(PREFIXO_REVISAO))
                .count())

    @staticmethod
    def historico(id_aluno, limite=30):
        return (AlunoDesafio.query.filter_by(id_aluno=id_aluno)
                .order_by(AlunoDesafio.data_realizacao.desc(), AlunoDesafio.id_desafio.desc())
                .limit(limite).all())

    @staticmethod
    def adicionar(registro):
        db.session.add(registro)

    @staticmethod
    def remover_do_desafio(id_desafio):
        AlunoDesafio.query.filter_by(id_desafio=id_desafio).delete(synchronize_session=False)

    @staticmethod
    def remover_do_aluno(id_aluno):
        AlunoDesafio.query.filter_by(id_aluno=id_aluno).delete(synchronize_session=False)
