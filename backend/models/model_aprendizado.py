from datetime import datetime, timezone
from .database import db


def _agora_utc():
    # datetime.utcnow() está obsoleto; aqui o valor continua em UTC, sem fuso.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RespostaDesafio(db.Model):
    __tablename__ = "resposta_desafio"
    __table_args__ = (
        db.UniqueConstraint("id_aluno", "id_desafio", "id_questao", name="uq_resposta_aluno_desafio_questao"),
    )

    id_resposta = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_aluno = db.Column(db.Integer, db.ForeignKey("Aluno.id_aluno"), nullable=False, index=True)
    id_desafio = db.Column(db.Integer, db.ForeignKey("desafio.id_desafio"), nullable=False, index=True)
    id_questao = db.Column(db.Integer, db.ForeignKey("Questao.id_questao"), nullable=False)
    alternativa_escolhida = db.Column(db.String(1), nullable=False)
    correta = db.Column(db.Boolean, nullable=False, default=False)
    pontos_ganhos = db.Column(db.Integer, nullable=False, default=0)
    segundos_gastos = db.Column(db.Integer, nullable=False, default=0)
    data_resposta = db.Column(db.DateTime, nullable=False, default=_agora_utc)

    def to_dict(self):
        return {
            "id_resposta": self.id_resposta,
            "id_aluno": self.id_aluno,
            "id_desafio": self.id_desafio,
            "id_questao": self.id_questao,
            "alternativa_escolhida": self.alternativa_escolhida,
            "correta": self.correta,
            "pontos_ganhos": self.pontos_ganhos,
            "segundos_gastos": self.segundos_gastos,
            "data_resposta": self.data_resposta.isoformat() if self.data_resposta else None,
        }
