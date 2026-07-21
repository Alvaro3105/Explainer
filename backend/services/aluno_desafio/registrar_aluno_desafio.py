from datetime import datetime
from models.model_aluno_desafio import AlunoDesafio
from models.model_aluno import Aluno
from models.model_desafio import Desafio

class RegistrarAlunoDesafioService:
    def executar(self, dados):
        id_aluno = dados.get("id_aluno")
        id_desafio = dados.get("id_desafio")

        if not id_aluno or not id_desafio:
            raise ValueError("Os campos 'id_aluno' e 'id_desafio' são obrigatórios.")

        if not Aluno.query.get(id_aluno):
            raise ValueError("Aluno não encontrado.")
        if not Desafio.buscar_por_id(id_desafio):
            raise ValueError("Desafio não encontrado.")

        relacao = AlunoDesafio.query.filter_by(
            id_aluno=id_aluno, id_desafio=id_desafio
        ).first()

        if relacao:
            raise ValueError("O aluno já possui registro neste desafio.")

        novo_registro = AlunoDesafio(
            id_aluno=id_aluno,
            id_desafio=id_desafio,
            data_realizacao=datetime.now().date(),
            pontuacao_obtida=dados.get("pontuacao_obtida", 0),
            concluido=dados.get("concluido", False)
        )
        novo_registro.salvar()
        return novo_registro.to_dict()