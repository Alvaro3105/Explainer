from models.model_tema import Tema

class ListarTemasService:
    def executar(self):
        temas = Tema.query.all()
        return [t.to_dict() for t in temas]