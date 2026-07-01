from models.model_aluno import Aluno


class CriarAlunoService:
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
            data_nascimento=dados.get("data_nascimento"),
        )
        aluno.salvar()
        return aluno.to_dict()
