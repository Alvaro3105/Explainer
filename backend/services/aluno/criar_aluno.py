from datetime import date

from models.model_aluno import Aluno


class CriarAlunoService:
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

    def executar(self, dados):
        campos_obrigatorios = ["nome", "email", "senha", "data_nascimento"]

        for campo in campos_obrigatorios:
            if not dados.get(campo):
                raise ValueError(f"O campo '{campo}' é obrigatório.")

        aluno_existente = Aluno.buscar_por_email(dados["email"])
        if aluno_existente:
            raise ValueError("Já existe um aluno cadastrado com este e-mail.")

        aluno = Aluno(
            nome=dados["nome"],
            email=dados["email"],
            senha=dados["senha"],
            data_nascimento=self._normalizar_data_nascimento(dados.get("data_nascimento")),
        )
        aluno.salvar()
        return aluno.to_dict()
