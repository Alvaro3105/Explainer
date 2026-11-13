from sqlalchemy import case, func, or_

from models.database import db
from models.model_materia import Materia


class MateriaRepository:

    @staticmethod
    def buscar_por_id(id_materia):
        return db.session.get(Materia, id_materia) if id_materia else None

    @staticmethod
    def listar():
        return Materia.query.all()

    @staticmethod
    def remover(materia):
        db.session.delete(materia)

    @staticmethod
    def buscar_por_nome_busca(nome_busca):
        return Materia.query.filter_by(nome_busca=nome_busca).first()

    @staticmethod
    def pesquisar(palavras, frase, limite, deslocamento=0, no_meio=False):
        """Matérias com todas as palavras no começo de uma palavra do nome ou de um sinônimo."""
        consulta = Materia.query
        for palavra in palavras:
            if no_meio:
                consulta = consulta.filter(or_(Materia.nome_busca.like(f"%{palavra}%"),
                                               Materia.termos_busca.like(f"%{palavra}%")))
            else:
                consulta = consulta.filter(or_(Materia.nome_busca.like(f"{palavra}%"),
                                               Materia.nome_busca.like(f"% {palavra}%"),
                                               Materia.termos_busca.like(f"%|{palavra}%"),
                                               Materia.termos_busca.like(f"% {palavra}%")))
        if frase:
            relevancia = case(
                (or_(Materia.nome_busca == frase, Materia.termos_busca.like(f"%|{frase}|%")), 0),
                (Materia.nome_busca.like(f"{frase}%"), 1),
                (Materia.nome_busca.like(f"% {frase}%"), 2),
                (Materia.termos_busca.like(f"%|{frase}%"), 3),
                else_=4,
            )
            consulta = consulta.order_by(relevancia, Materia.nome_busca)
        else:
            consulta = consulta.order_by(Materia.nome_busca)
        return consulta.offset(deslocamento).limit(limite).all()

    @staticmethod
    def contar_temas_por_materia():
        """Quantidade de temas principais (sem os subtemas) de cada matéria, numa consulta só."""
        from models.model_tema import Tema
        linhas = (db.session.query(Tema.id_materia, func.count(Tema.id_tema))
                  .filter(Tema.id_materia.isnot(None), Tema.id_tema_pai.is_(None))
                  .group_by(Tema.id_materia).all())
        return dict(linhas)

    @staticmethod
    def adicionar(materia):
        db.session.add(materia)
