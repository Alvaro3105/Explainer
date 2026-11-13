from models.model_tema import Tema
from repositories.tema_repository import TemaRepository
from repositories.transacao import Transacao
from services.aprendizado.catalogo_service import CatalogoService


class CriarTemaService:

    def executar(self, dados):
        for campo in ("materia", "nome"):
            if not dados.get(campo):
                raise ValueError(f"O campo '{campo}' é obrigatório.")

        tema = Tema(materia=dados["materia"], nome=dados["nome"])
        CatalogoService.ligar_ao_catalogo(tema)
        TemaRepository.adicionar(tema)
        Transacao.confirmar()
        return tema.to_dict()
