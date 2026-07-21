from models.model_aluno_desafio import AlunoDesafio

class AtualizarAlunoDesafioService:
    def executar(self, id_aluno, id_desafio, dados):
        relacao = AlunoDesafio.query.filter_by(
            id_aluno=id_aluno, id_desafio=id_desafio
        ).first()

        if not relacao:
            return None

        relacao.atualizar(
            data_realizacao=dados.get("data_realizacao"),
            pontuacao_obtida=dados.get("pontuacao_obtida"),
            concluido=dados.get("concluido")
        )
        return relacao.to_dict()