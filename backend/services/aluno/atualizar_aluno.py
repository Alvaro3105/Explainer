from datetime import date

from models.model_aluno import Aluno


class AtualizarAlunoService:
    def _normalizar_data_nascimento(self, valor):
        if valor in (None, ""):
            return None
        if isinstance(valor, date):
            return valor
        if isinstance(valor, str):
            try:
                return date.fromisoformat(valor)
            except ValueError as erro:
                raise ValueError("A data de nascimento deve estar no formato YYYY-MM-DD.") from erro
        raise ValueError("A data de nascimento está em um formato inválido.")

    def executar(self, aluno_id, dados):
        aluno = Aluno.query.get(aluno_id)

        if aluno is None:
            return None

        novo_email = dados.get("email")
        if novo_email:
            aluno_com_email = Aluno.buscar_por_email(novo_email)

            if aluno_com_email and aluno_com_email.id_aluno != aluno.id_aluno:
                raise ValueError("Já existe outro aluno cadastrado com este e-mail.")

        aluno.atualizar(
            nome=dados.get("nome"),
            email=dados.get("email"),
            senha=dados.get("senha"),
            data_nascimento=self._normalizar_data_nascimento(dados.get("data_nascimento")),
            pontos=dados.get("pontos"),
            foguinho=dados.get("foguinho")
        )
        return aluno.to_dict()
