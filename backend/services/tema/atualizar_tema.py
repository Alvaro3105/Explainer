from repositories.tema_repository import TemaRepository
from repositories.transacao import Transacao
from services.atualizacao import aplicar_campos


class AtualizarTemaService:

    def executar(self, id_tema, dados):
        tema = TemaRepository.buscar_por_id(id_tema)
        if not tema:
            return None

        aplicar_campos(tema, {"materia": dados.get("materia"), "nome": dados.get("nome")})
        Transacao.confirmar()
        return tema.to_dict()
