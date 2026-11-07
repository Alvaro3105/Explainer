from datetime import timezone

from .database import db

# Versão atual dos Termos de Uso e do Termo de Consentimento. Se os termos mudarem,
# aumente a versão: quem aceitou uma versão anterior precisa aceitar de novo.
VERSAO_TERMOS_ATUAL = "1.0"

class Aluno(db.Model):
    __tablename__ = "Aluno"  # Nome idêntico ao SQL

    id_aluno = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    data_nascimento = db.Column(db.Date, nullable=True)
    pontos = db.Column(db.Integer, default=0)
    foguinho = db.Column(db.Integer, default=0)
    nick = db.Column(db.String(40), nullable=True)
    minutos_ativos = db.Column(db.Integer, nullable=False, default=0)
    ultimo_dia_ativo = db.Column(db.String(10), nullable=True)
    sequencia_atual = db.Column(db.Integer, nullable=False, default=0)
    melhor_sequencia = db.Column(db.Integer, nullable=False, default=0)
    # Controle do tempo ativo: instante (epoch) do último heartbeat e segundos ainda não
    # convertidos em minuto inteiro.
    ultimo_heartbeat = db.Column(db.Float, nullable=True)
    segundos_pendentes = db.Column(db.Integer, nullable=False, default=0)
    # Registro do consentimento (LGPD): quando o aluno aceitou os termos e qual versão.
    termos_aceitos_em = db.Column(db.DateTime, nullable=True)
    versao_termos = db.Column(db.String(20), nullable=True)

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
        if pontos is not None:
            self.pontos = pontos
        if foguinho is not None:
            self.foguinho = foguinho
            
        db.session.commit()

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

    @staticmethod
    def buscar_por_email(email):
        return Aluno.query.filter_by(email=email).first()

    def to_dict(self):
        return {
            "id_aluno": self.id_aluno,
            "nome": self.nome,
            "email": self.email,
            "data_nascimento": self.data_nascimento.isoformat() if self.data_nascimento else None,
            "pontos": self.pontos,
            "foguinho": self.foguinho or 0,
            "nick": self.nick or self.nome,
            "minutos_ativos": self.minutos_ativos or 0,
            "sequencia_atual": self.sequencia_atual or self.foguinho or 0,
            "melhor_sequencia": self.melhor_sequencia or 0,
            "termos_aceitos_em": (self.termos_aceitos_em.replace(tzinfo=timezone.utc).isoformat()
                                  if self.termos_aceitos_em else None),
            "versao_termos": self.versao_termos,
            "precisa_aceitar_termos": self.versao_termos != VERSAO_TERMOS_ATUAL,
        }
