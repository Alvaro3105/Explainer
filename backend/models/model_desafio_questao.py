from .database import db

class DesafioQuestao(db.Model):
    __tablename__ = "desafio_questao"

    id_desafio = db.Column(db.Integer, db.ForeignKey("desafio.id_desafio"), primary_key=True)
    id_questao = db.Column(db.Integer, db.ForeignKey("Questao.id_questao"), primary_key=True)

    def salvar(self):
        db.session.add(self)
        db.session.commit()

    def deletar(self):
        db.session.delete(self)
        db.session.commit()

    def to_dict(self):
        return {
            "id_desafio": self.id_desafio,
            "id_questao": self.id_questao
        }