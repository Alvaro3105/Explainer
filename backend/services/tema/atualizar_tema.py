from models.model_tema import Tema

class AtualizarTemaService:
    def executar(self, id_tema, dados):
        tema = Tema.buscar_por_id(id_tema)
        if not tema:
            return None
        tema.atualizar(materia=dados.get("materia"), nome=dados.get("nome"))
        return tema.to_dict()