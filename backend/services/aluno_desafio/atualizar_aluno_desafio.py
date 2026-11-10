from repositories.aluno_desafio_repository import AlunoDesafioRepository
from repositories.transacao import Transacao
from services.atualizacao import aplicar_campos, converter_data


class AtualizarAlunoDesafioService:

    def executar(self, id_aluno, id_desafio, dados):
        registro = AlunoDesafioRepository.buscar(id_aluno, id_desafio)
        if not registro:
            return None

        aplicar_campos(registro, {
            "data_realizacao": converter_data(dados.get("data_realizacao"), "A data de realização"),
            "pontuacao_obtida": dados.get("pontuacao_obtida"),
            "concluido": dados.get("concluido"),
        })
        Transacao.confirmar()
        return registro.to_dict()
