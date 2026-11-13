from .database import db


class Materia(db.Model):
    __tablename__ = "Materia"

    id_materia = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(80), nullable=False, unique=True)
    # Nome sem acentos e em minúsculas, usado na busca e para evitar matérias repetidas.
    nome_busca = db.Column(db.String(80), nullable=False, unique=True, index=True)
    area = db.Column(db.String(80), nullable=True)
    sinonimos = db.Column(db.Text, nullable=True)
    termos_busca = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            "id_materia": self.id_materia,
            "nome": self.nome,
            "area": self.area,
        }
