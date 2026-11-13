"""Redefine a senha de um aluno que esqueceu a senha. Para uso da equipe, no servidor.

O ExplAIner ainda não envia e-mails, então não existe "esqueci minha senha" na tela.
Enquanto isso, a equipe confirma por fora quem é o aluno e roda:

    python backend/scripts/redefinir_senha.py email-do-aluno@exemplo.com

O script cria uma senha provisória, mostra uma única vez e grava só o hash.
O aluno entra com ela e troca em "Meu progresso" > "Trocar senha".
"""
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def redefinir(email):
    from werkzeug.security import generate_password_hash

    import app as aplicacao
    from repositories.aluno_repositories import AlunoRepository
    from repositories.transacao import Transacao

    with aplicacao.app.app_context():
        aluno = AlunoRepository.buscar_por_email(str(email or "").strip().lower())
        if aluno is None:
            return None
        provisoria = secrets.token_urlsafe(9)
        aluno.senha = generate_password_hash(provisoria)
        Transacao.confirmar()
        return provisoria


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python backend/scripts/redefinir_senha.py email-do-aluno@exemplo.com")
        sys.exit(2)
    senha = redefinir(sys.argv[1])
    if senha is None:
        print("Nenhuma conta encontrada com esse e-mail.")
        sys.exit(1)
    print("Senha provisória (anote agora, ela não será mostrada de novo):", senha)
    print("Peça ao aluno para trocar a senha assim que entrar.")
