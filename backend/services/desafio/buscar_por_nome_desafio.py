from models.model_desafio import Desafio

class BuscarDesafiosPorNomeService:
    def executar(self, nome):
        if not nome or not nome.strip():
            raise ValueError("O parâmetro 'nome' é obrigatório.")

        desafios = Desafio.query.filter(Desafio.nome.like(f"%{nome.strip()}%")).all()

        return [desafio.to_dict() for desafio in desafios]
