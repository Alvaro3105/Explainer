from models.database import db
from models.model_aprendizado import RespostaDesafio


class RespostaRepository:
    """Respostas que cada aluno deu às questões de um desafio."""

    @staticmethod
    def listar(id_aluno, id_desafio):
        return RespostaDesafio.query.filter_by(id_aluno=id_aluno, id_desafio=id_desafio).all()

    @staticmethod
    def buscar(id_aluno, id_desafio, id_questao):
        return RespostaDesafio.query.filter_by(id_aluno=id_aluno, id_desafio=id_desafio, id_questao=id_questao).first()

    @staticmethod
    def contar(id_aluno, id_desafio):
        return RespostaDesafio.query.filter_by(id_aluno=id_aluno, id_desafio=id_desafio).count()

    @staticmethod
    def contar_do_aluno(id_aluno, apenas_corretas=False):
        consulta = RespostaDesafio.query.filter_by(id_aluno=id_aluno)
        if apenas_corretas:
            consulta = consulta.filter_by(correta=True)
        return consulta.count()

    @staticmethod
    def questao_respondida(id_questao):
        return RespostaDesafio.query.filter_by(id_questao=id_questao).first() is not None

    @staticmethod
    def adicionar(resposta):
        db.session.add(resposta)

    @staticmethod
    def remover_do_desafio(id_desafio):
        RespostaDesafio.query.filter_by(id_desafio=id_desafio).delete(synchronize_session=False)

    @staticmethod
    def remover_do_aluno(id_aluno):
        RespostaDesafio.query.filter_by(id_aluno=id_aluno).delete(synchronize_session=False)
