from werkzeug.security import generate_password_hash

from models.model_aluno import Aluno
from repositories.aluno_repositories import AlunoRepository
from repositories.transacao import Transacao
from services.atualizacao import converter_data


class CriarAlunoService:

    def executar(self, dados):
        for campo in ("nome", "email", "senha"):
            if not dados.get(campo):
                raise ValueError(f"O campo '{campo}' é obrigatório.")

        nome = str(dados["nome"]).strip()
        email = str(dados["email"]).strip().lower()
        if AlunoRepository.buscar_por_email(email):
            raise ValueError("Já existe um aluno cadastrado com este e-mail.")

        aluno = Aluno(
            nome=nome,
            email=email,
            senha=generate_password_hash(str(dados["senha"])),
            data_nascimento=converter_data(dados.get("data_nascimento"), "A data de nascimento"),
            nick=str(dados.get("nick") or nome).strip()[:40],
        )
        AlunoRepository.adicionar(aluno)
        Transacao.confirmar()
        return aluno.to_dict()
