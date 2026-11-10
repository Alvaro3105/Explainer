from .database import db


class Tema(db.Model):
    __tablename__ = "Tema"

    id_tema = db.Column(db.Integer, primary_key=True, autoincrement=True)
    materia = db.Column(db.String(60), nullable=False)
    nome = db.Column(db.String(100), nullable=False)

    def to_dict(self):
        return {
            "id_tema": self.id_tema,
            "materia": self.materia,
            "nome": self.nome,
        }
