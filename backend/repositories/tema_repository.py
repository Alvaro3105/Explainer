from models.model_tema import Tema


class TemaRepository:

    @staticmethod
    def listar_por_materia(materia):
        return Tema.query.filter_by(
            materia=materia
        ).all()

    @staticmethod
    def buscar_por_id(id_tema):
        return Tema.buscar_por_id(id_tema)

    @staticmethod
    def listar_ordenados():
        """Todos os temas, agrupáveis por matéria (matéria ↑, nome ↑)."""
        return Tema.query.order_by(Tema.materia.asc(), Tema.nome.asc()).all()
