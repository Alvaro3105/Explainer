from models.database import db


class Transacao:
    """Controle da transação do banco, usado pelos Services ao final de cada caso de uso."""

    @staticmethod
    def confirmar():
        db.session.commit()

    @staticmethod
    def desfazer():
        db.session.rollback()

    @staticmethod
    def enviar():
        """Envia as alterações pendentes ao banco sem confirmar (gera ids e valida restrições)."""
        db.session.flush()
