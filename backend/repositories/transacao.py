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
