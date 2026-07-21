from models.model_desafio import Desafio


class AtualizarDesafioService:
    def executar(self, desafio_id, dados):
        desafio = Desafio.buscar_por_id(desafio_id)

        if desafio is None:
            return None

        desafio.atualizar(
            nome=dados.get("nome"),
            dificuldade=dados.get("dificuldade"),
            quantidade_questoes=dados.get("quantidade_questoes")
        )

        return desafio.to_dict()
