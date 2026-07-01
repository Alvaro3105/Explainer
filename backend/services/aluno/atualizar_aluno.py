from models.model_aluno import Aluno


class AtualizarAlunoService:
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
            data_nascimento=dados.get("data_nascimento"),
            pontos=dados.get("pontos"),
            foguinho=dados.get("foguinho")
        )
        return aluno.to_dict()
