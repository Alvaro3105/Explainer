from models.database import db
from models.model_desafio import PREFIXO_REVISAO, Desafio
from models.model_desafio_questao import DesafioQuestao
from models.model_questao import Questao


class QuestaoRepository:

    @staticmethod
    def verificar_resposta(id_questao, alternativa):
        questao = Questao.buscar_por_id(id_questao)

        if questao is None:
            return None

        # A coluna do gabarito aceita nulo, e a alternativa pode chegar como número:
        # por isso o gabarito é verificado e os dois lados são convertidos para texto.
        if not questao.alternativa_correta:
            raise ValueError("Esta questão ainda não tem alternativa correta cadastrada.")
        return questao.alternativa_correta.strip().upper() == str(alternativa).strip().upper()

    @staticmethod
    def buscar_por_id(id_questao):
        return db.session.get(Questao, id_questao) if id_questao else None

    @staticmethod
    def adicionar(questao):
        db.session.add(questao)
        db.session.flush()  # gera o id_questao para o vínculo com o desafio

    @staticmethod
    def remover(questao):
        db.session.delete(questao)

    @staticmethod
    def enunciados_ja_vistos(id_aluno, id_tema, dificuldade):
        """Enunciados que o aluno já recebeu neste tema e dificuldade (fora das revisões)."""
        linhas = (db.session.query(Questao.enunciado)
                  .join(DesafioQuestao, DesafioQuestao.id_questao == Questao.id_questao)
                  .join(Desafio, Desafio.id_desafio == DesafioQuestao.id_desafio)
                  .filter(Desafio.id_aluno == id_aluno,
                          Desafio.id_tema == id_tema,
                          Desafio.dificuldade == dificuldade,
                          ~Desafio.nome.startswith(PREFIXO_REVISAO))
                  .distinct().all())
        return [linha[0] for linha in linhas if linha[0]]
