from repositories.desafio_repository import DesafioRepository


class BuscarDesafiosPorNomeService:

    def executar(self, nome):
        if not nome or not nome.strip():
            raise ValueError("O parâmetro 'nome' é obrigatório.")
        return [desafio.to_dict() for desafio in DesafioRepository.buscar_por_nome(nome.strip())]
