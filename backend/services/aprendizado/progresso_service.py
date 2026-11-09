"""Casos de uso de acompanhamento: progresso, tempo ativo, ranking e histórico."""
import time

from repositories.aluno_desafio_repository import AlunoDesafioRepository
from repositories.aluno_repositories import AlunoRepository
from repositories.desafio_repository import DesafioRepository
from repositories.resposta_repository import RespostaRepository
from repositories.tema_repository import TemaRepository
from repositories.transacao import Transacao
from services.aprendizado.erros import ErroDeNegocio
from services.aprendizado.regras import atualizar_sequencia_diaria, eh_revisao


class ProgressoService:

    def progresso(self, aluno):
        total_respondidas = RespostaRepository.contar_do_aluno(aluno.id_aluno)
        total_corretas = RespostaRepository.contar_do_aluno(aluno.id_aluno, apenas_corretas=True)
        return {
            "desafios_concluidos": AlunoDesafioRepository.contar_concluidos(aluno.id_aluno),
            "questoes_respondidas": total_respondidas,
            "questoes_corretas": total_corretas,
            "precisao": round((total_corretas / total_respondidas) * 100) if total_respondidas else 0,
            "minutos_ativos": aluno.minutos_ativos or 0,
        }

    def registrar_tempo_ativo(self, aluno, segundos_informados):
        try:
            segundos = max(0, min(int(segundos_informados or 0), 120))
        except (TypeError, ValueError):
            raise ErroDeNegocio("Tempo inválido.")
        # Só credita o tempo que realmente passou desde o heartbeat anterior. Assim, chamar
        # a rota várias vezes seguidas não aumenta o tempo ativo exibido no ranking.
        # O controle fica no banco (não na sessão), porque o cookie de sessão pode ser reenviado.
        agora = time.time()
        if aluno.ultimo_heartbeat:
            segundos = min(segundos, max(0, int(agora - aluno.ultimo_heartbeat)))
        else:
            segundos = min(segundos, 60)
        aluno.ultimo_heartbeat = agora
        # Minutos inteiros no total; o resto fica guardado para o próximo heartbeat.
        pendentes = (aluno.segundos_pendentes or 0) + segundos
        aluno.minutos_ativos = (aluno.minutos_ativos or 0) + pendentes // 60
        aluno.segundos_pendentes = pendentes % 60
        atualizar_sequencia_diaria(aluno)
        Transacao.confirmar()
        return {"minutos_ativos": aluno.minutos_ativos, "sequencia_atual": aluno.sequencia_atual}

    def ranking(self, aluno_atual, limite=20):
        """Ranking global (só quem já respondeu questões). As consultas são SQL no AlunoRepository."""
        limite = max(1, min(int(limite or 20), 100))
        resultado = [{
            "posicao": posicao,
            "id_aluno": linha["id_aluno"],
            "nick": linha["nick"] or linha["nome"],
            "pontos": linha["pontos"] or 0,
            "sequencia_atual": linha["sequencia_atual"] or linha["foguinho"] or 0,
            "minutos_ativos": linha["minutos_ativos"] or 0,
        } for posicao, linha in enumerate(AlunoRepository.ranking_topo(limite), start=1)]
        posicao_atual = None
        if aluno_atual:
            posicao_atual = next((item["posicao"] for item in resultado if item["id_aluno"] == aluno_atual.id_aluno), None)
            if posicao_atual is None and AlunoRepository.participa_do_ranking(aluno_atual.id_aluno):
                # Fora do topo: conta quem vem antes do usuário, na mesma ordem do topo.
                posicao_atual = AlunoRepository.quantos_a_frente(
                    aluno_atual.pontos or 0, aluno_atual.nome, aluno_atual.id_aluno) + 1
        return {"itens": resultado, "posicao_usuario": posicao_atual,
                "total_alunos": AlunoRepository.total_participantes()}

    def historico(self, aluno):
        resultado = []
        for registro in AlunoDesafioRepository.historico(aluno.id_aluno, limite=30):
            desafio = DesafioRepository.buscar_por_id(registro.id_desafio)
            tema = TemaRepository.buscar_por_id(desafio.id_tema) if desafio and desafio.id_tema else None
            resultado.append({
                "id_desafio": registro.id_desafio,
                "id_tema": desafio.id_tema if desafio else None,
                "quantidade_questoes": desafio.quantidade_questoes if desafio else 5,
                "nivel_mapa": (desafio.nivel_mapa or 1) if desafio else 1,
                "nome": desafio.nome if desafio else "Desafio removido",
                "modo_revisao": bool(desafio and eh_revisao(desafio)),
                "materia": tema.materia if tema else "—",
                "tema": tema.nome if tema else "—",
                "dificuldade": desafio.dificuldade if desafio else "—",
                "pontuacao_obtida": registro.pontuacao_obtida or 0,
                "concluido": bool(registro.concluido),
                "data_realizacao": registro.data_realizacao.isoformat() if registro.data_realizacao else None,
            })
        return resultado
