from models.model_aluno_desafio import AlunoDesafio
from repositories.aluno_desafio_repository import AlunoDesafioRepository
from repositories.aluno_repositories import AlunoRepository
from repositories.desafio_repository import DesafioRepository
from repositories.transacao import Transacao
from services.aprendizado.regras import hoje


class RegistrarAlunoDesafioService:

    def executar(self, dados):
        id_aluno = dados.get("id_aluno")
        id_desafio = dados.get("id_desafio")

        if not id_aluno or not id_desafio:
            raise ValueError("Os campos 'id_aluno' e 'id_desafio' são obrigatórios.")
        if not AlunoRepository.buscar_por_id(id_aluno):
            raise ValueError("Aluno não encontrado.")
        if not DesafioRepository.buscar_por_id(id_desafio):
            raise ValueError("Desafio não encontrado.")
        if AlunoDesafioRepository.buscar(id_aluno, id_desafio):
            raise ValueError("O aluno já possui registro neste desafio.")

        registro = AlunoDesafio(
            id_aluno=id_aluno,
            id_desafio=id_desafio,
            data_realizacao=hoje(),
            pontuacao_obtida=dados.get("pontuacao_obtida", 0),
            concluido=dados.get("concluido", False),
        )
        AlunoDesafioRepository.adicionar(registro)
        Transacao.confirmar()
        return registro.to_dict()
