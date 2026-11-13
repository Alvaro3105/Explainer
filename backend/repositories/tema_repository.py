from sqlalchemy import case, func, or_

from models.database import db
from models.model_desafio import Desafio
from models.model_questao import Questao
from models.model_tema import Tema


class TemaRepository:

    @staticmethod
    def buscar_por_id(id_tema):
        return db.session.get(Tema, id_tema) if id_tema else None

    @staticmethod
    def buscar_varios(ids):
        """Vários temas de uma vez, num dicionário {id_tema: Tema} (evita uma consulta por tema)."""
        ids = {i for i in ids if i}
        return {tema.id_tema: tema for tema in Tema.query.filter(Tema.id_tema.in_(ids)).all()} if ids else {}

    @staticmethod
    def listar():
        return Tema.query.all()

    @staticmethod
    def listar_da_materia(id_materia):
        return Tema.query.filter_by(id_materia=id_materia).all()

    @staticmethod
    def buscar_por_nome(id_materia, nome_busca):
        return Tema.query.filter_by(id_materia=id_materia, nome_busca=nome_busca).first()

    @staticmethod
    def pesquisar(id_materia, palavras, frase, limite, deslocamento=0, id_tema_pai=None, no_meio=False):
        """Temas e subtemas de UMA matéria que têm todas as palavras digitadas.

        Cada palavra precisa ser o começo de uma palavra do nome ou de um sinônimo
        ("fin" acha "Matemática Financeira"). Com `no_meio`, vale também no meio da palavra.
        Ordem: nome igual à busca; nome ou palavra do nome que começa com ela; trecho do nome;
        sinônimo. Em cada grupo, os temas principais vêm antes dos subtemas.
        Sem busca, lista só os temas principais (ou os subtemas de `id_tema_pai`), em ordem alfabética.
        """
        consulta = Tema.query.filter(Tema.id_materia == id_materia)
        if id_tema_pai:
            consulta = consulta.filter(Tema.id_tema_pai == id_tema_pai)
        elif not frase:
            consulta = consulta.filter(Tema.id_tema_pai.is_(None))
        for palavra in palavras:
            if no_meio:
                consulta = consulta.filter(or_(Tema.nome_busca.like(f"%{palavra}%"),
                                               Tema.termos_busca.like(f"%{palavra}%")))
            else:
                consulta = consulta.filter(or_(Tema.nome_busca.like(f"{palavra}%"),
                                               Tema.nome_busca.like(f"% {palavra}%"),
                                               Tema.termos_busca.like(f"%|{palavra}%"),
                                               Tema.termos_busca.like(f"% {palavra}%")))
        if frase:
            grupo = case(
                (Tema.nome_busca == frase, 0),
                (or_(Tema.nome_busca.like(f"{frase}%"), Tema.nome_busca.like(f"% {frase}%")), 1),
                (Tema.nome_busca.like(f"%{frase}%"), 2),
                else_=3,
            )
            comeca_com = case((Tema.nome_busca.like(f"{frase}%"), 0), else_=1)
            consulta = consulta.order_by(grupo, Tema.id_tema_pai.isnot(None), comeca_com,
                                         func.length(Tema.nome_busca), Tema.nome_busca)
        else:
            consulta = consulta.order_by(Tema.nome_busca)
        return consulta.offset(deslocamento).limit(limite).all()

    @staticmethod
    def contar_subtemas(ids_temas):
        """Quantos subtemas cada tema tem, num dicionário {id_tema: quantidade}."""
        ids = [i for i in ids_temas if i]
        if not ids:
            return {}
        linhas = (db.session.query(Tema.id_tema_pai, func.count(Tema.id_tema))
                  .filter(Tema.id_tema_pai.in_(ids)).group_by(Tema.id_tema_pai).all())
        return dict(linhas)

    @staticmethod
    def contar_por_tipo():
        """Total de temas principais e de subtemas ligados a alguma matéria."""
        temas = Tema.query.filter(Tema.id_materia.isnot(None), Tema.id_tema_pai.is_(None)).count()
        subtemas = Tema.query.filter(Tema.id_materia.isnot(None), Tema.id_tema_pai.isnot(None)).count()
        return temas, subtemas

    @staticmethod
    def possui_vinculos(id_tema):
        tem_questao = Questao.query.filter_by(id_tema=id_tema).first() is not None
        tem_desafio = Desafio.query.filter_by(id_tema=id_tema).first() is not None
        tem_subtema = Tema.query.filter_by(id_tema_pai=id_tema).first() is not None
        return tem_questao or tem_desafio or tem_subtema

    @staticmethod
    def adicionar(tema):
        db.session.add(tema)

    @staticmethod
    def remover(tema):
        db.session.delete(tema)
