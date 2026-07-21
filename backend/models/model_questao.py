from .database import db

class Questao(db.Model):
    __tablename__ = "Questao"

    id_questao = db.Column(db.Integer, primary_key=True, autoincrement=True)
    enunciado = db.Column(db.Text, nullable=False)
    alternativa_correta = db.Column(db.String(1), nullable=True)
    id_tema = db.Column(db.Integer, db.ForeignKey("Tema.id_tema"), nullable=False)

    def salvar(self):
        db.session.add(self)
        db.session.commit()

    def atualizar(self, enunciado=None, alternativa_correta=None, id_tema=None):
        if enunciado is not None:
            self.enunciado = enunciado
        if alternativa_correta is not None:
            self.alternativa_correta = alternativa_correta
        if id_tema is not None:
            self.id_tema = id_tema
        db.session.commit()

    def deletar(self):
        db.session.delete(self)
        db.session.commit()

    @staticmethod
    def buscar_por_id(id_questao):
        return Questao.query.get(id_questao)

    def to_dict(self):
        return {
            "id_questao": self.id_questao,
            "enunciado": self.enunciado,
            "alternativa_correta": self.alternativa_correta,
            "id_tema": self.id_tema,
        }