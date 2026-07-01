from .database import db

class Aluno(db.Model):
    __tablename__ = "alunos"

    id_aluno = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    data_nascimento = db.Column(db.Date, nullable=True)
    pontos = db.Column(db.Integer, default=0)
    foguinho = db.Column(db.Integer, default=0)

    def salvar(self):
        db.session.add(self)
        db.session.commit()

    def atualizar(self, nome=None, email=None, senha=None, data_nascimento=None, pontos=None, foguinho=None):
        if nome is not None:
            self.nome = nome

        if email is not None:
            self.email = email

        if senha is not None:
            self.senha = senha

        if data_nascimento is not None:
            self.data_nascimento = data_nascimento

    def atualizar_foguinho(self, dias=1):
        self.foguinho += dias
        db.session.commit()

    def adicionar_pontos(self, pontuacao):
        if pontuacao > 0:
            self.pontos += pontuacao
            db.session.commit()

    def deletar(self):
        db.session.delete(self)
        db.session.commit()

    def buscar_por_email(email):
        return Aluno.query.filter_by(email=email).first()

    def to_dict(self):
        return {
            "id_aluno": self.id_aluno,
            "nome": self.nome,
            "email": self.email,
            "data_nascimento": self.data_nascimento.isoformat() if self.data_nascimento else None,
            "pontos": self.pontos,
            "foguinho": self.foguinho,
        }
