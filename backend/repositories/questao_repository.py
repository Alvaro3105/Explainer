from models.database import db
from models.model_desafio import PREFIXO_REVISAO, Desafio
from models.model_desafio_questao import DesafioQuestao
from models.model_questao import Questao


class QuestaoRepository:

    @staticmethod
    def verificar_resposta(id_questao, alternativa):
        questao = QuestaoRepository.buscar_por_id(id_questao)

        if questao is None:
            return None

        # O gabarito pode estar vazio e a alternativa pode chegar como número,
        # por isso os dois lados viram texto antes de comparar.
        if not questao.alternativa_correta:
            raise ValueError("Esta questão ainda não tem alternativa correta cadastrada.")
        return questao.alternativa_correta.strip().upper() == str(alternativa).strip().upper()

    @staticmethod
    def buscar_por_id(id_questao):
        return db.session.get(Questao, id_questao) if id_questao else None

    @staticmethod
    def listar():
        return Questao.query.all()

    @staticmethod
    def listar_do_desafio(id_desafio):
        return (Questao.query
                .join(DesafioQuestao, DesafioQuestao.id_questao == Questao.id_questao)
                .filter(DesafioQuestao.id_desafio == id_desafio)
                .order_by(Questao.id_questao.asc()).all())

    @staticmethod
    def adicionar(questao):
        db.session.add(questao)
        db.session.flush()

    @staticmethod
    def remover(questao):
        db.session.delete(questao)

    @staticmethod
    def enunciados_ja_vistos(id_aluno, id_tema, dificuldade):
        linhas = (db.session.query(Questao.enunciado)
                  .join(DesafioQuestao, DesafioQuestao.id_questao == Questao.id_questao)
                  .join(Desafio, Desafio.id_desafio == DesafioQuestao.id_desafio)
                  .filter(Desafio.id_aluno == id_aluno,
                          Desafio.id_tema == id_tema,
                          Desafio.dificuldade == dificuldade,
                          ~Desafio.nome.startswith(PREFIXO_REVISAO))
                  .distinct().all())
        return [linha[0] for linha in linhas if linha[0]]
