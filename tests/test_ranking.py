"""Ranking: top 5 inicial, expansão até o top 100, desempate e posição do aluno logado.

Estes testes usam um banco só deles (apagado a cada teste), para poder montar
rankings com quantidades exatas de participantes: 0, 1, 3, 5, 6, 20, 100 e mais de 100.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from werkzeug.security import generate_password_hash

from tests.test_api import app_module

SENHA = "senha-do-teste-de-ranking-123"
CAMPOS_PUBLICOS = {"posicao", "id_aluno", "nick", "pontos", "sequencia_atual", "minutos_ativos"}


class BaseRanking(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._pasta = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        endereco = f"sqlite:///{Path(cls._pasta.name, 'ranking.db').as_posix()}"
        with mock.patch.dict(os.environ, {"DATABASE_URL": endereco}):
            cls.app = app_module.create_app()
        cls.hash_senha = generate_password_hash(SENHA)

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            app_module.d.db.engine.dispose()
        cls._pasta.cleanup()

    def setUp(self):
        from models.model_aluno import Aluno
        from models.model_aluno_desafio import AlunoDesafio
        from models.model_aprendizado import RespostaDesafio
        from models.model_desafio import Desafio
        from models.model_desafio_questao import DesafioQuestao
        from models.model_questao import Questao
        with self.app.app_context():
            sessao = app_module.d.db.session
            for modelo in (RespostaDesafio, AlunoDesafio, DesafioQuestao, Desafio, Questao, Aluno):
                sessao.query(modelo).delete()
            sessao.commit()
        self.client = self.app.test_client()

    def criar_alunos(self, pontuacoes, sem_resposta=()):
        """Cria um aluno por pontuação. Só quem respondeu uma questão participa do ranking.

        Devolve a lista de dicionários {id_aluno, nome, email, pontos} na ordem da criação.
        """
        from models.model_aluno import VERSAO_TERMOS_ATUAL, Aluno
        from models.model_aprendizado import RespostaDesafio
        from models.model_desafio import Desafio
        from models.model_questao import Questao
        from models.model_tema import Tema
        criados = []
        with self.app.app_context():
            sessao = app_module.d.db.session
            tema = Tema.query.filter(Tema.id_materia.isnot(None)).first()
            questao = Questao(enunciado="Questão do ranking", alternativa_correta="A", id_tema=tema.id_tema)
            sessao.add(questao)
            for indice, pontos in enumerate(pontuacoes, start=1):
                aluno = Aluno(nome=f"Aluno {indice:04d}", nick=f"Nick {indice}", email=f"r{indice}@exemplo.com",
                              senha=self.hash_senha, pontos=pontos, versao_termos=VERSAO_TERMOS_ATUAL)
                sessao.add(aluno)
                sessao.flush()
                if indice - 1 not in sem_resposta:
                    desafio = Desafio(nome="Fase 1", dificuldade="Normal", pontuacao=0, quantidade_questoes=5,
                                      id_tema=tema.id_tema, id_aluno=aluno.id_aluno)
                    sessao.add(desafio)
                    sessao.flush()
                    sessao.add(RespostaDesafio(id_aluno=aluno.id_aluno, id_desafio=desafio.id_desafio,
                                               id_questao=questao.id_questao, alternativa_escolhida="A", correta=True))
                criados.append({"id_aluno": aluno.id_aluno, "nome": aluno.nome, "email": aluno.email, "pontos": pontos})
            sessao.commit()
        return criados

    def ranking(self, limite=None):
        url = "/api/learning/ranking" + (f"?limite={limite}" if limite is not None else "")
        resposta = self.client.get(url)
        self.assertEqual(200, resposta.status_code, resposta.get_data(as_text=True))
        return resposta.get_json()

    def entrar(self, aluno):
        resposta = self.client.post("/api/auth/login", json={"email": aluno["email"], "senha": SENHA})
        self.assertEqual(200, resposta.status_code, resposta.get_data(as_text=True))

    @staticmethod
    def ordem_esperada(alunos):
        """A regra do ranking: mais pontos primeiro; no empate, nome e depois id."""
        return [a["id_aluno"] for a in sorted(alunos, key=lambda a: (-a["pontos"], a["nome"], a["id_aluno"]))]


class TestQuantidadesDeParticipantes(BaseRanking):

    def conferir(self, quantidade):
        alunos = self.criar_alunos([1000 - i * 7 for i in range(quantidade)])
        topo, completo = self.ranking(5), self.ranking(100)
        esperado = self.ordem_esperada(alunos)
        self.assertEqual(esperado[:5], [i["id_aluno"] for i in topo["itens"]])
        self.assertEqual(esperado[:100], [i["id_aluno"] for i in completo["itens"]])
        for dados, limite in ((topo, 5), (completo, 100)):
            itens = dados["itens"]
            self.assertEqual(min(quantidade, limite), len(itens))
            self.assertEqual(list(range(1, len(itens) + 1)), [i["posicao"] for i in itens])  # sem buraco nem repetição
            self.assertEqual(len(itens), len({i["id_aluno"] for i in itens}))
            self.assertEqual((limite, len(itens), quantidade, quantidade > limite),
                             (dados["limite"], dados["retornados"], dados["total_participantes"], dados["tem_mais"]))
        return topo, completo

    def test_banco_sem_participantes(self):
        topo, completo = self.conferir(0)
        self.assertEqual([], topo["itens"])
        self.assertIsNone(topo["usuario_atual"])

    def test_quantidades_exatas(self):
        for quantidade in (1, 3, 5, 6, 20, 100, 101, 130):
            with self.subTest(participantes=quantidade):
                self.setUp()
                self.conferir(quantidade)

    def test_quem_nunca_respondeu_nao_aparece(self):
        alunos = self.criar_alunos([500, 9999, 300], sem_resposta={1})
        dados = self.ranking(100)
        self.assertNotIn(alunos[1]["id_aluno"], [i["id_aluno"] for i in dados["itens"]])
        self.assertEqual(2, dados["total_participantes"])


class TestDesempateEEstabilidade(BaseRanking):

    def test_empates_tem_ordem_fixa_e_igual_no_top_5_e_no_top_100(self):
        # Muitos empates, inclusive na fronteira entre a 5ª e a 6ª posição.
        alunos = self.criar_alunos([300, 200, 200, 200, 200, 200, 200, 100, 100, 50] * 3)
        esperado = self.ordem_esperada(alunos)
        primeiras = [[i["id_aluno"] for i in self.ranking(5)["itens"]] for _ in range(3)]
        completo = [i["id_aluno"] for i in self.ranking(100)["itens"]]
        self.assertTrue(all(lista == esperado[:5] for lista in primeiras))
        self.assertEqual(esperado, completo)
        self.assertEqual(completo[:5], primeiras[0])

    def test_pontos_nao_mudam_por_causa_do_empate(self):
        alunos = self.criar_alunos([200, 200, 200])
        pontos = {i["id_aluno"]: i["pontos"] for i in self.ranking(100)["itens"]}
        self.assertEqual({a["id_aluno"]: 200 for a in alunos}, pontos)


class TestPosicaoDoAlunoLogado(BaseRanking):

    def preparar(self):
        self.alunos = self.criar_alunos([5000 - i * 10 for i in range(130)] + [0], sem_resposta={130})
        self.ordem = self.ordem_esperada(self.alunos[:130])

    def posicao_real(self, aluno):
        return self.ordem.index(aluno["id_aluno"]) + 1

    def test_dentro_do_top_5(self):
        self.preparar()
        aluno = self.alunos[2]
        self.entrar(aluno)
        dados = self.ranking(5)
        self.assertEqual(3, self.posicao_real(aluno))
        self.assertEqual({"posicao": 3, "pontos": aluno["pontos"], "nick": "Nick 3", "na_lista": True}, dados["usuario_atual"])
        self.assertEqual(3, dados["posicao_usuario"])

    def test_entre_o_6_e_o_100(self):
        self.preparar()
        aluno = self.alunos[36]
        self.entrar(aluno)
        topo, completo = self.ranking(5), self.ranking(100)
        self.assertEqual(37, topo["usuario_atual"]["posicao"])
        self.assertFalse(topo["usuario_atual"]["na_lista"])
        self.assertTrue(completo["usuario_atual"]["na_lista"])
        self.assertEqual(37, next(i["posicao"] for i in completo["itens"] if i["id_aluno"] == aluno["id_aluno"]))
        # Ele não é colocado no top 5 só para aparecer.
        self.assertNotIn(aluno["id_aluno"], [i["id_aluno"] for i in topo["itens"]])

    def test_fora_do_top_100(self):
        self.preparar()
        aluno = self.alunos[119]
        self.entrar(aluno)
        for limite in (5, 100):
            dados = self.ranking(limite)
            self.assertEqual(self.posicao_real(aluno), dados["usuario_atual"]["posicao"])
            self.assertEqual(120, dados["usuario_atual"]["posicao"])
            self.assertFalse(dados["usuario_atual"]["na_lista"])

    def test_aluno_que_ainda_nao_respondeu(self):
        self.preparar()
        self.entrar(self.alunos[130])
        dados = self.ranking(5)
        self.assertIsNone(dados["usuario_atual"]["posicao"])
        self.assertIsNone(dados["posicao_usuario"])

    def test_sem_login_nao_tem_usuario_atual(self):
        self.criar_alunos([10, 20])
        self.assertIsNone(self.ranking(5)["usuario_atual"])


class TestLimiteDaApi(BaseRanking):

    def test_so_aceita_5_ou_100(self):
        self.criar_alunos([1000 - i for i in range(150)])
        casos = {"5": 5, "100": 100, None: 5, "": 5, "abc": 5, "-1": 5, "0": 5, "1": 5, "20": 5, "99": 5,
                 "101": 5, "999999": 5, str(10 ** 30): 5, "1e3": 5, "5.0": 5, " 100 ": 100}
        for valor, esperado in casos.items():
            with self.subTest(limite=valor):
                dados = self.ranking(valor)
                self.assertEqual(esperado, dados["limite"])
                self.assertEqual(esperado, len(dados["itens"]))

    def test_ranking_nao_mostra_dados_privados(self):
        alunos = self.criar_alunos([300, 200, 100])
        self.entrar(alunos[1])
        dados = self.ranking(100)
        texto = json.dumps(dados)
        for item in dados["itens"]:
            self.assertEqual(CAMPOS_PUBLICOS, set(item))
        for proibido in ("email", "senha", "scrypt:", "pbkdf2:", "exemplo.com", "Aluno 0001", "termos"):
            self.assertNotIn(proibido, texto)

    def test_erro_no_banco_vira_resposta_de_erro(self):
        self.criar_alunos([10])
        with mock.patch("repositories.aluno_repositories.AlunoRepository.ranking_topo",
                        side_effect=OverflowError("simulado")):
            resposta = self.client.get("/api/learning/ranking?limite=5")
        self.assertEqual(400, resposta.status_code)
        self.assertIn("erro", resposta.get_json())

    def test_consultas_tem_quantidade_fixa(self):
        """Top 5 ou top 100: o número de consultas não cresce com o número de alunos (sem N+1)."""
        from sqlalchemy import event
        alunos = self.criar_alunos([1000 - i for i in range(120)])
        self.entrar(alunos[110])
        contagem = {}
        with self.app.app_context():
            motor = app_module.d.db.engine

            def contar(*_):
                contagem["n"] = contagem.get("n", 0) + 1

            for limite in (5, 100):
                contagem["n"] = 0
                event.listen(motor, "before_cursor_execute", contar)
                try:
                    self.ranking(limite)
                finally:
                    event.remove(motor, "before_cursor_execute", contar)
                contagem[limite] = contagem["n"]
        self.assertEqual(contagem[5], contagem[100])
        self.assertLessEqual(contagem[100], 6)


if __name__ == "__main__":
    unittest.main()
