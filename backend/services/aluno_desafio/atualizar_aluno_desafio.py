from datetime import date

from models.model_aluno_desafio import AlunoDesafio


def _converter_data(valor):
    """O JSON traz a data como texto, mas a coluna Date só aceita objetos date."""
    if valor in (None, ""):
        return None
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor))
    except ValueError as erro:
        raise ValueError("A data de realização deve estar no formato AAAA-MM-DD.") from erro


class AtualizarAlunoDesafioService:
    def executar(self, id_aluno, id_desafio, dados):
        relacao = AlunoDesafio.query.filter_by(
            id_aluno=id_aluno, id_desafio=id_desafio
        ).first()

        if not relacao:
            return None

        relacao.atualizar(
            data_realizacao=_converter_data(dados.get("data_realizacao")),
            pontuacao_obtida=dados.get("pontuacao_obtida"),
            concluido=dados.get("concluido")
        )
        return relacao.to_dict()
