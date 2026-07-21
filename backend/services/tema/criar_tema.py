from models.model_tema import Tema

class CriarTemaService:
    def executar(self, dados):
        for campo in ["materia", "nome"]:
            if not dados.get(campo):
                raise ValueError(f"O campo '{campo}' é obrigatório.")

        tema = Tema(materia=dados["materia"], nome=dados["nome"])
        tema.salvar()
        return tema.to_dict()