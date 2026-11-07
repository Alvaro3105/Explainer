from models.model_desafio import Desafio
from models.model_questao import Questao
from models.model_tema import Tema


class DeletarTemaService:
    def executar(self, id_tema):
        tema = Tema.buscar_por_id(id_tema)
        if not tema:
            return False
        # Questões e desafios apontam para o tema; apagá-lo deixaria esses registros órfãos.
        if Questao.query.filter_by(id_tema=id_tema).first() or Desafio.query.filter_by(id_tema=id_tema).first():
            raise ValueError("Este tema tem questões ou desafios vinculados e não pode ser excluído.")
        tema.deletar()
        return True
