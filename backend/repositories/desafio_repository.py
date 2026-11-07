from models.database import db
from models.model_aluno_desafio import AlunoDesafio
from models.model_desafio import PREFIXO_REVISAO, Desafio


class DesafioRepository:

    @staticmethod
    def buscar_por_dificuldade(dificuldade):
        return Desafio.query.filter_by(
            dificuldade=dificuldade
        ).all()

    @staticmethod
    def buscar_por_id(id_desafio):
        return db.session.get(Desafio, id_desafio) if id_desafio else None

    @staticmethod
    def listar_do_aluno(id_aluno, mais_recentes_primeiro=False):
        consulta = Desafio.query.filter_by(id_aluno=id_aluno)
        if mais_recentes_primeiro:
            consulta = consulta.order_by(Desafio.id_desafio.desc())
        return consulta.all()

    @staticmethod
    def anteriores_no_tema(id_aluno, id_tema, antes_de):
        """Desafios do aluno no mesmo tema criados antes de `antes_de`, do mais novo para o mais antigo."""
        return (Desafio.query.filter(Desafio.id_aluno == id_aluno, Desafio.id_tema == id_tema,
                                     Desafio.id_desafio < antes_de)
                .order_by(Desafio.id_desafio.desc()).all())

    @staticmethod
    def fase_concluida(id_aluno, id_tema, nivel):
        """A fase `nivel` desta jornada (mesmo tema, fora das revisões) já foi concluída pelo aluno?"""
        return (Desafio.query
                .join(AlunoDesafio, AlunoDesafio.id_desafio == Desafio.id_desafio)
                .filter(Desafio.id_aluno == id_aluno, Desafio.id_tema == id_tema,
                        Desafio.nivel_mapa == nivel, ~Desafio.nome.startswith(PREFIXO_REVISAO),
                        AlunoDesafio.id_aluno == id_aluno, AlunoDesafio.concluido.is_(True))
                .first()) is not None

    @staticmethod
    def adicionar(desafio):
        db.session.add(desafio)
        db.session.flush()  # gera o id_desafio para vincular as questões

    @staticmethod
    def remover(desafio):
        db.session.delete(desafio)
