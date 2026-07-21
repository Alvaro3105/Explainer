from models.model_desafio import Desafio

class CriarDesafioService:
    def executar(self, dados):
        campos_obrigatorios = ["nome", "dificuldade", "quantidade_questoes"]

        for campo in campos_obrigatorios:
            if not dados.get(campo):
                raise ValueError(f"O campo '{campo}' é obrigatório.")

        desafio = Desafio(
            nome=dados["nome"],
            dificuldade=dados["dificuldade"],
            pontuacao=dados.get("pontuacao", 0),  # Uso seguro com .get e valor default
            quantidade_questoes=dados.get("quantidade_questoes")
        )

        desafio.salvar()
        return desafio.to_dict()
