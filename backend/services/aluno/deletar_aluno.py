from models.database import db
from models.model_aluno import Aluno
from services.exclusao import remover_aluno


class DeletarAlunoService:

    def executar(self, aluno_id):
        aluno = db.session.get(Aluno, aluno_id)

        if aluno is None:
            return False
        # Apaga também respostas, conclusões, ranking e desafios do aluno (antes ficavam órfãos).
        remover_aluno(aluno)
        db.session.commit()
        return True
