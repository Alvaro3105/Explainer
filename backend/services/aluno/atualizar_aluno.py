from werkzeug.security import generate_password_hash

from repositories.aluno_repositories import AlunoRepository
from repositories.transacao import Transacao
from services.atualizacao import aplicar_campos, converter_data


class AtualizarAlunoService:

    def executar(self, aluno_id, dados):
        aluno = AlunoRepository.buscar_por_id(aluno_id)
        if aluno is None:
            return None

        novo_email = str(dados.get("email") or "").strip().lower()
        if novo_email:
            existente = AlunoRepository.buscar_por_email(novo_email)
            if existente and existente.id_aluno != aluno.id_aluno:
                raise ValueError("Já existe outro aluno cadastrado com este e-mail.")

        senha = dados.get("senha")
        aplicar_campos(aluno, {
            "nome": dados.get("nome"),
            "email": novo_email or None,
            "senha": generate_password_hash(str(senha)) if senha else None,
            "data_nascimento": converter_data(dados.get("data_nascimento"), "A data de nascimento"),
            "pontos": dados.get("pontos"),
            "foguinho": dados.get("foguinho"),
        })
        Transacao.confirmar()
        return aluno.to_dict()
