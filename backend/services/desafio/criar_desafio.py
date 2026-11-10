from models.model_desafio import Desafio
from repositories.desafio_repository import DesafioRepository
from repositories.transacao import Transacao


class CriarDesafioService:

    def executar(self, dados):
        for campo in ("nome", "dificuldade", "quantidade_questoes"):
            if not dados.get(campo):
                raise ValueError(f"O campo '{campo}' é obrigatório.")

        desafio = Desafio(
            nome=dados["nome"],
            dificuldade=dados["dificuldade"],
            pontuacao=dados.get("pontuacao", 0),
            quantidade_questoes=dados["quantidade_questoes"],
        )
        DesafioRepository.adicionar(desafio)
        Transacao.confirmar()
        return desafio.to_dict()
