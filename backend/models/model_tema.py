from .database import db


class Tema(db.Model):
    """Tema ou subtema de uma matéria. O subtema é um Tema com `id_tema_pai` preenchido."""
    __tablename__ = "Tema"
    __table_args__ = (
        db.UniqueConstraint("id_materia", "nome_busca", name="uq_tema_materia_nome"),
        db.Index("ix_tema_materia_nome_busca", "id_materia", "nome_busca"),
    )

    id_tema = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # Nome da matéria em texto: continua preenchido para os desafios antigos e o painel.
    materia = db.Column(db.String(60), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    id_materia = db.Column(db.Integer, db.ForeignKey("Materia.id_materia"), nullable=True, index=True)
    id_tema_pai = db.Column(db.Integer, db.ForeignKey("Tema.id_tema"), nullable=True, index=True)
    nome_busca = db.Column(db.String(160), nullable=True)
    sinonimos = db.Column(db.Text, nullable=True)
    termos_busca = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            "id_tema": self.id_tema,
            "materia": self.materia,
            "nome": self.nome,
            "id_materia": self.id_materia,
            "id_tema_pai": self.id_tema_pai,
            "tipo": "subtema" if self.id_tema_pai else "tema",
        }
