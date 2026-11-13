from models.database import db


class Transacao:

    @staticmethod
    def confirmar():
        db.session.commit()

    @staticmethod
    def desfazer():
        db.session.rollback()

    @staticmethod
    def enviar():
        db.session.flush()

    @staticmethod
    def soltar():
        """Encerra a leitura em curso sem gravar nada. Use antes de uma espera longa (chamada à IA),
        para a conexão não ficar presa e o SQLite não segurar as gravações dos outros alunos."""
        db.session.rollback()
