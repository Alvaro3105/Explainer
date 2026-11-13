from repositories.tema_repository import TemaRepository
from repositories.transacao import Transacao
from services.aprendizado.catalogo_service import CatalogoService
from services.atualizacao import aplicar_campos


class AtualizarTemaService:

    def executar(self, id_tema, dados):
        tema = TemaRepository.buscar_por_id(id_tema)
        if not tema:
            return None

        aplicar_campos(tema, {"materia": dados.get("materia"), "nome": dados.get("nome")})
        CatalogoService.ligar_ao_catalogo(tema)
        Transacao.confirmar()
        return tema.to_dict()
