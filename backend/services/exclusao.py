from repositories.aluno_desafio_repository import AlunoDesafioRepository
from repositories.aluno_repositories import AlunoRepository
from repositories.desafio_questao_repository import DesafioQuestaoRepository
from repositories.desafio_repository import DesafioRepository
from repositories.geracao_repository import GeracaoRepository
from repositories.questao_repository import QuestaoRepository
from repositories.ranking_repository import RankingRepository
from repositories.resposta_repository import RespostaRepository
from repositories.transacao import Transacao


def _apagar_questoes_sem_uso(ids_questoes):
    for id_questao in set(ids_questoes):
        if DesafioQuestaoRepository.questao_em_uso(id_questao) or RespostaRepository.questao_respondida(id_questao):
            continue
        questao = QuestaoRepository.buscar_por_id(id_questao)
        if questao:
            QuestaoRepository.remover(questao)


def remover_desafio(desafio):
    ids_questoes = DesafioQuestaoRepository.ids_questoes(desafio.id_desafio)
    RespostaRepository.remover_do_desafio(desafio.id_desafio)
    AlunoDesafioRepository.remover_do_desafio(desafio.id_desafio)
    DesafioQuestaoRepository.remover_do_desafio(desafio.id_desafio)
    DesafioRepository.remover(desafio)
    Transacao.enviar()
    _apagar_questoes_sem_uso(ids_questoes)


def remover_aluno(aluno):
    RespostaRepository.remover_do_aluno(aluno.id_aluno)
    AlunoDesafioRepository.remover_do_aluno(aluno.id_aluno)
    RankingRepository.remover_do_aluno(aluno.id_aluno)
    GeracaoRepository.remover_do_aluno(aluno.id_aluno)
    for desafio in DesafioRepository.listar_do_aluno(aluno.id_aluno):
        remover_desafio(desafio)
    AlunoRepository.remover(aluno)
    Transacao.enviar()
