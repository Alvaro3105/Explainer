from .database import db

class Tema(db.Model):
    __tablename__ = "Tema"

    id_tema = db.Column(db.Integer, primary_key=True, autoincrement=True)
    materia = db.Column(db.String(60), nullable=False)
    nome = db.Column(db.String(100), nullable=False)

    def salvar(self):
        db.session.add(self)
        db.session.commit()

    def atualizar(self, materia=None, nome=None):
        if materia is not None:
            self.materia = materia
        if nome is not None:
            self.nome = nome
        db.session.commit()

    def deletar(self):
        db.session.delete(self)
        db.session.commit()

    @staticmethod
    def buscar_por_id(id_tema):
        return Tema.query.get(id_tema)

    def to_dict(self):
        return {
            "id_tema": self.id_tema,
            "materia": self.materia,
            "nome": self.nome,
        }