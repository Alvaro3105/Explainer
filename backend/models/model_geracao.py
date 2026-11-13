from .database import db


class GeracaoDesafio(db.Model):
    """Registro de cada pedido de geração de desafio, usado no limite por aluno.

    Fica no banco (e não na memória) para o limite valer em todos os processos
    do servidor e continuar valendo depois de um reinício.
    """
    __tablename__ = "geracao_desafio"
    __table_args__ = (
        db.Index("ix_geracao_aluno_momento", "id_aluno", "iniciada_em"),
    )

    id_geracao = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_aluno = db.Column(db.Integer, db.ForeignKey("Aluno.id_aluno"), nullable=False)
    # Hora do pedido, em segundos desde 1970 (time.time()).
    iniciada_em = db.Column(db.Float, nullable=False)
    # Verdadeiro enquanto as questões estão sendo preparadas.
    em_andamento = db.Column(db.Boolean, nullable=False, default=True)
