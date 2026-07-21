from models.model_tema import Tema

class DeletarTemaService:
    def executar(self, id_tema):
        tema = Tema.buscar_por_id(id_tema)
        if not tema:
            return False
        tema.deletar()
        return True