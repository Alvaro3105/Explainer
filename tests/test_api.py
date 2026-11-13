import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

_TMP = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL") or f"sqlite:///{Path(_TMP.name, 'teste.db').as_posix()}"
os.environ["OPENAI_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["GEMINI_MODEL"] = ""
os.environ["FLASK_SECRET_KEY"] = "chave-de-teste"
# Os testes criam vários desafios seguidos com o mesmo aluno; o limite de geração
# tem testes próprios em tests/test_protecoes.py e fica desligado nos demais.
for _limite in ("INTERVALO_ENTRE_GERACOES", "GERACOES_POR_JANELA", "GERACOES_POR_DIA", "CADASTROS_POR_HORA_POR_IP"):
    os.environ[_limite] = "0"
os.environ.pop("ENABLE_ADMIN_PANEL", None)
os.environ.pop("CORS_ORIGINS", None)
sys.path.insert(0, str(BACKEND))

import app as app_module


def tema_com_banco_local(client):
    """Física > Sistema Solar, achado pela busca do catálogo. Ele tem questões no banco local."""
    materias = client.get("/api/learning/catalog?q=fisica").get_json()["materias"]
    fisica = next(m for m in materias if m["nome"] == "Física")
    temas = client.get(f"/api/learning/catalog/{fisica['id_materia']}/themes?q=sistema solar").get_json()["temas"]
    return next(t for t in temas if t["nome"] == "Sistema Solar")["id_tema"]


class BaseApi(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()

    def registrar(self, email):
        resposta = self.client.post("/api/auth/register", json={
            "nome": "Aluno Teste", "email": email, "senha": "senha-segura-123", "aceite_termos": True})
        self.assertEqual(201, resposta.status_code, resposta.get_data(as_text=True))
        return resposta.get_json()["aluno"]

    def criar_desafio(self, **extra):
        corpo = {"id_tema": tema_com_banco_local(self.client), "quantidade_questoes": 5, "dificuldade": "normal"}
        corpo.update(extra)
        resposta = self.client.post("/api/learning/challenges", json=corpo)
        self.assertEqual(201, resposta.status_code, resposta.get_data(as_text=True))
        return resposta.get_json()

    def gabarito(self, id_questao):
        from models.model_questao import Questao
        with app_module.app.app_context():
            return app_module.d.db.session.get(Questao, id_questao).alternativa_correta

    def responder_todas(self, desafio, acertos=None):
        """Responde todas as questões, acertando as `acertos` primeiras (todas, se não informado)."""
        id_desafio = desafio["desafio"]["id_desafio"]
        total = len(desafio["questoes"])
        acertos = total if acertos is None else acertos
        for indice, questao in enumerate(desafio["questoes"]):
            certa = self.gabarito(questao["id_questao"])
            letra = certa if indice < acertos else next(x for x in "ABCD" if x != certa)
            resposta = self.client.post(f"/api/learning/challenges/{id_desafio}/answer", json={
                "id_questao": questao["id_questao"], "alternativa": letra})
            self.assertEqual(200, resposta.status_code, resposta.get_data(as_text=True))
            self.assertEqual(indice < acertos, resposta.get_json()["correta"])

    def concluir(self, desafio, acertos=None):
        """Responde tudo e conclui. Por padrão acerta todas, para a fase ser aprovada."""
        self.responder_todas(desafio, acertos)
        id_desafio = desafio["desafio"]["id_desafio"]
        conclusao = self.client.post(f"/api/learning/challenges/{id_desafio}/complete", json={})
        self.assertEqual(200, conclusao.status_code, conclusao.get_data(as_text=True))
        return conclusao.get_json()

    def pontos(self):
        return self.client.get("/api/learning/me").get_json()["aluno"]["pontos"]


class TestSeguranca(BaseApi):
    def test_crud_legado_fica_bloqueado_por_padrao(self):
        for metodo, caminho in (("get", "/alunos"), ("get", "/questoes"), ("delete", "/alunos/1"),
                                ("put", "/alunos/1"), ("get", "/temas"), ("get", "/ranking"),
                                ("get", "/desafio"), ("get", "/desafios/1/questoes"), ("post", "/alunos")):
            with self.subTest(caminho=caminho):
                self.assertEqual(403, getattr(self.client, metodo)(caminho).status_code)

    def test_sem_cabecalho_cors_curinga(self):
        resposta = self.client.get("/api/learning/catalog", headers={"Origin": "http://evil.example"})
        self.assertNotIn("Access-Control-Allow-Origin", resposta.headers)

    def test_rotas_de_jogo_exigem_login(self):
        self.assertEqual(401, self.client.get("/api/learning/me").status_code)
        self.assertEqual(401, self.client.post("/api/learning/challenges", json={}).status_code)

    def test_aluno_nao_acessa_desafio_de_outro(self):
        self.registrar("dono@exemplo.com")
        id_desafio = self.criar_desafio()["desafio"]["id_desafio"]
        self.client.post("/api/auth/logout")
        self.registrar("intruso@exemplo.com")
        self.assertEqual(404, self.client.get(f"/api/learning/challenges/{id_desafio}").status_code)


class TestContas(BaseApi):
    def test_cadastro_login_e_validacoes(self):
        self.registrar("login@exemplo.com")
        self.assertEqual(409, self.client.post("/api/auth/register", json={
            "nome": "X", "email": "login@exemplo.com", "senha": "outra-senha-123", "aceite_termos": True}).status_code)
        self.assertEqual(400, self.client.post("/api/auth/register", json={
            "nome": "X", "email": "curta@exemplo.com", "senha": "123", "aceite_termos": True}).status_code)
        self.client.post("/api/auth/logout")
        self.assertEqual(401, self.client.get("/api/learning/me").status_code)
        self.assertEqual(401, self.client.post("/api/auth/login", json={
            "email": "login@exemplo.com", "senha": "errada"}).status_code)
        self.assertEqual(200, self.client.post("/api/auth/login", json={
            "email": "login@exemplo.com", "senha": "senha-segura-123"}).status_code)
        self.assertEqual(200, self.client.get("/api/learning/me").status_code)


class TestJogo(BaseApi):
    def test_questoes_nao_vazam_o_gabarito_e_pontuacao_funciona(self):
        self.registrar("jogo@exemplo.com")
        desafio = self.criar_desafio()
        self.assertEqual(5, len(desafio["questoes"]))
        for questao in desafio["questoes"]:
            self.assertNotIn("alternativa_correta", questao)
        id_desafio = desafio["desafio"]["id_desafio"]
        primeira = desafio["questoes"][0]["id_questao"]
        fora_de_ordem = self.client.post(f"/api/learning/challenges/{id_desafio}/answer", json={
            "id_questao": desafio["questoes"][2]["id_questao"], "alternativa": "A"})
        self.assertEqual(409, fora_de_ordem.status_code)
        self.concluir(desafio)
        repetida = self.client.post(f"/api/learning/challenges/{id_desafio}/answer", json={
            "id_questao": primeira, "alternativa": "B"}).get_json()
        self.assertTrue(repetida["ja_respondida"])
        segunda = self.client.post(f"/api/learning/challenges/{id_desafio}/complete", json={}).get_json()
        self.assertTrue(segunda["ja_concluido"])
        self.assertEqual(0, segunda["bonus_conclusao"])

    def test_fase_da_jornada_forjada_volta_para_fase_1(self):
        self.registrar("fase@exemplo.com")
        desafio = self.criar_desafio(fase_jornada=4)
        self.assertEqual(1, desafio["desafio"]["nivel_mapa"])


class TestProgressaoDeDificuldade(BaseApi):

    def jornada(self, email, base, fases=3):
        self.registrar(email)
        id_tema = tema_com_banco_local(self.client)
        dificuldades = []
        for fase in range(1, fases + 1):
            desafio = self.criar_desafio(id_tema=id_tema, dificuldade=base,
                                         dificuldade_base=base, fase_jornada=fase)
            self.assertEqual(fase, desafio["desafio"]["nivel_mapa"])
            dificuldades.append(desafio["desafio"]["dificuldade"])
            self.concluir(desafio)
        return dificuldades

    def test_base_facil_sobe_um_nivel_por_fase(self):
        self.assertEqual(["Fácil", "Normal", "Difícil"], self.jornada("facil@exemplo.com", "facil"))

    def test_base_media_chega_a_dificil_na_fase_2(self):
        self.assertEqual(["Normal", "Difícil", "Difícil"], self.jornada("medio@exemplo.com", "medio"))

    def test_base_dificil_permanece_dificil(self):
        self.assertEqual(["Difícil", "Difícil", "Difícil"], self.jornada("dificil@exemplo.com", "dificil"))

    def test_fase_forjada_tambem_reverte_a_dificuldade(self):
        # Sem ter concluído a fase anterior, o servidor volta para a fase 1, e a dificuldade
        # precisa acompanhar. Senão a fase 1 valeria pontos de Difícil.
        self.registrar("forjada@exemplo.com")
        desafio = self.criar_desafio(dificuldade="dificil", dificuldade_base="facil", fase_jornada=5)
        self.assertEqual(1, desafio["desafio"]["nivel_mapa"])
        self.assertEqual("Fácil", desafio["desafio"]["dificuldade"])

    def test_refazer_mantem_a_dificuldade_do_desafio_original(self):
        self.registrar("refazer@exemplo.com")
        id_tema = tema_com_banco_local(self.client)
        original = self.criar_desafio(id_tema=id_tema, dificuldade="facil",
                                      dificuldade_base="facil", fase_jornada=1)
        self.concluir(original)
        revisao = self.criar_desafio(id_tema=id_tema, dificuldade="facil", refazer=True,
                                     refazer_de=original["desafio"]["id_desafio"])
        self.assertEqual("Fácil", revisao["desafio"]["dificuldade"])
        self.assertTrue(revisao["desafio"]["nome"].startswith("[REFAZER] "))

    def test_refazer_nao_conta_como_desafio_concluido(self):
        self.registrar("contagem@exemplo.com")
        original = self.criar_desafio()
        self.concluir(original)
        antes = self.client.get("/api/learning/me").get_json()["progresso"]["desafios_concluidos"]
        revisao = self.criar_desafio(refazer=True, refazer_de=original["desafio"]["id_desafio"])
        self.concluir(revisao)
        depois = self.client.get("/api/learning/me").get_json()["progresso"]["desafios_concluidos"]
        self.assertEqual(1, antes)
        self.assertEqual(antes, depois)

    def test_refazer_sem_desafio_de_origem_e_recusado(self):
        self.registrar("semorigem@exemplo.com")
        resposta = self.client.post("/api/learning/challenges", json={
            "id_tema": tema_com_banco_local(self.client), "quantidade_questoes": 5,
            "dificuldade": "normal", "refazer": True})
        self.assertEqual(404, resposta.status_code)

    def test_aceita_medio_com_e_sem_acento_como_normal(self):
        self.registrar("aliases@exemplo.com")
        for valor in ("medio", "médio", "normal", "Médio"):
            with self.subTest(valor=valor):
                desafio = self.criar_desafio(dificuldade=valor)
                self.assertEqual("Normal", desafio["desafio"]["dificuldade"])

    def test_dificuldade_invalida_cita_medio_na_mensagem(self):
        self.registrar("invalida@exemplo.com")
        resposta = self.client.post("/api/learning/challenges", json={
            "id_tema": tema_com_banco_local(self.client), "quantidade_questoes": 5, "dificuldade": "impossivel"})
        self.assertEqual(400, resposta.status_code)
        self.assertIn("Médio", resposta.get_json()["erro"])


class TestNotaMinimaDaFase(BaseApi):
    """A fase só é aprovada com pelo menos 60% de acertos."""

    def test_menos_de_60_por_cento_nao_aprova(self):
        self.registrar("abaixo@exemplo.com")
        for quantidade, acertos, percentual in ((5, 2, 40), (20, 11, 55), (5, 0, 0)):
            with self.subTest(quantidade=quantidade, acertos=acertos):
                resultado = self.concluir(self.criar_desafio(quantidade_questoes=quantidade), acertos=acertos)
                self.assertFalse(resultado["concluido"])
                self.assertTrue(resultado["reprovado"])
                self.assertFalse(resultado["aprovado"])
                self.assertEqual(percentual, resultado["percentual_acertos"])
                self.assertEqual("reprovado", resultado["desempenho"])
                self.assertEqual(60, resultado["minimo_para_avancar"])

    def test_exatamente_60_por_cento_aprova(self):
        self.registrar("exato@exemplo.com")
        for quantidade, acertos in ((5, 3), (20, 12)):
            with self.subTest(quantidade=quantidade):
                resultado = self.concluir(self.criar_desafio(quantidade_questoes=quantidade), acertos=acertos)
                self.assertTrue(resultado["concluido"])
                self.assertTrue(resultado["aprovado"])
                self.assertEqual(60, resultado["percentual_acertos"])
                self.assertEqual("aprovado", resultado["desempenho"])
                self.assertEqual(10, resultado["bonus_conclusao"])
                self.assertEqual(0, resultado["bonus_perfeito"])

    def test_acima_de_60_por_cento_aprova(self):
        self.registrar("acima@exemplo.com")
        for acertos, percentual, desempenho, bonus_perfeito in ((4, 80, "otimo", 0), (5, 100, "perfeito", 25)):
            with self.subTest(acertos=acertos):
                resultado = self.concluir(self.criar_desafio(), acertos=acertos)
                self.assertTrue(resultado["concluido"])
                self.assertEqual(percentual, resultado["percentual_acertos"])
                self.assertEqual(desempenho, resultado["desempenho"])
                self.assertEqual(bonus_perfeito, resultado["bonus_perfeito"])

    def test_feedback_corresponde_a_porcentagem_real(self):
        self.registrar("feedback@exemplo.com")
        esperado = {0: "reprovado", 1: "reprovado", 2: "reprovado", 3: "aprovado", 4: "otimo", 5: "perfeito"}
        for acertos, desempenho in esperado.items():
            with self.subTest(acertos=acertos):
                resultado = self.concluir(self.criar_desafio(), acertos=acertos)
                self.assertEqual(acertos, resultado["questoes_corretas"])
                self.assertEqual(5, resultado["quantidade_questoes"])
                self.assertEqual(round(acertos * 100 / 5), resultado["percentual_acertos"])
                self.assertEqual(desempenho, resultado["desempenho"])
                self.assertEqual(acertos >= 3, resultado["aprovado"])

    def test_reprovar_mantem_historico_e_pontos_das_respostas(self):
        from models.model_desafio import Desafio
        aluno = self.registrar("historico@exemplo.com")
        id_tema = tema_com_banco_local(self.client)
        fase1 = self.criar_desafio(id_tema=id_tema, dificuldade_base="facil", fase_jornada=1)
        self.assertTrue(self.concluir(fase1)["concluido"])
        fase2 = self.criar_desafio(id_tema=id_tema, dificuldade_base="facil", fase_jornada=2)
        self.assertEqual(2, fase2["desafio"]["nivel_mapa"])
        self.responder_todas(fase2, acertos=1)
        pontos_antes = self.pontos()
        resultado = self.client.post(f"/api/learning/challenges/{fase2['desafio']['id_desafio']}/complete", json={}).get_json()
        self.assertTrue(resultado["reprovado"])
        self.assertEqual(pontos_antes, resultado["pontos_totais"])
        self.assertEqual(pontos_antes, self.pontos())
        with app_module.app.app_context():
            self.assertEqual(2, Desafio.query.filter_by(id_aluno=aluno["id_aluno"]).count())
        historico = {item["id_desafio"]: item for item in self.client.get("/api/learning/history").get_json()["historico"]}
        self.assertTrue(historico[fase1["desafio"]["id_desafio"]]["concluido"])
        self.assertFalse(historico[fase2["desafio"]["id_desafio"]]["concluido"])

    def test_proxima_fase_fica_bloqueada_sem_a_nota_minima(self):
        self.registrar("bloqueio@exemplo.com")
        id_tema = tema_com_banco_local(self.client)
        fase1 = self.criar_desafio(id_tema=id_tema, dificuldade_base="facil", fase_jornada=1)
        self.assertTrue(self.concluir(fase1, acertos=2)["reprovado"])
        # Fase 1 reprovada: pedir a fase 2 (ou a 5) devolve a fase 1 de novo.
        for pedido in (2, 5):
            with self.subTest(pedido=pedido):
                nova = self.criar_desafio(id_tema=id_tema, dificuldade_base="facil", fase_jornada=pedido)
                self.assertEqual(1, nova["desafio"]["nivel_mapa"])
        self.assertTrue(self.concluir(nova)["concluido"])
        fase2 = self.criar_desafio(id_tema=id_tema, dificuldade_base="facil", fase_jornada=2)
        self.assertEqual(2, fase2["desafio"]["nivel_mapa"])
        self.assertTrue(self.concluir(fase2, acertos=1)["reprovado"])
        # Fase 2 reprovada: pedir a fase 3 devolve a fase 2, não a 3 nem a 1.
        de_novo = self.criar_desafio(id_tema=id_tema, dificuldade_base="facil", fase_jornada=3)
        self.assertEqual(2, de_novo["desafio"]["nivel_mapa"])

    def test_bonus_so_quando_a_fase_e_aprovada(self):
        self.registrar("bonus@exemplo.com")
        reprovada = self.criar_desafio()
        self.responder_todas(reprovada, acertos=2)
        antes = self.pontos()
        resultado = self.client.post(f"/api/learning/challenges/{reprovada['desafio']['id_desafio']}/complete", json={}).get_json()
        self.assertEqual((0, 0, 0), (resultado["bonus_conclusao"], resultado["bonus_perfeito"], resultado["bonus_jornada"]))
        self.assertEqual(antes, self.pontos())
        aprovada = self.criar_desafio()
        self.responder_todas(aprovada, acertos=3)
        antes = self.pontos()
        resultado = self.client.post(f"/api/learning/challenges/{aprovada['desafio']['id_desafio']}/complete", json={}).get_json()
        self.assertEqual(10, resultado["bonus_conclusao"])
        self.assertEqual(antes + 10, self.pontos())

    def test_pedidos_repetidos_nao_duplicam_bonus(self):
        self.registrar("repetido@exemplo.com")
        for acertos in (5, 1):
            with self.subTest(acertos=acertos):
                desafio = self.criar_desafio()
                primeiro = self.concluir(desafio, acertos=acertos)
                pontos = self.pontos()
                caminho = f"/api/learning/challenges/{desafio['desafio']['id_desafio']}/complete"
                for _ in range(3):
                    repetido = self.client.post(caminho, json={}).get_json()
                    self.assertEqual(primeiro["concluido"], repetido["concluido"])
                    self.assertEqual((0, 0, 0), (repetido["bonus_conclusao"], repetido["bonus_perfeito"], repetido["bonus_jornada"]))
                    self.assertEqual(pontos, self.pontos())
        historico = self.client.get("/api/learning/history").get_json()["historico"]
        self.assertEqual(2, len(historico))

    def test_fase_reprovada_sai_do_continuar_e_pode_ser_tentada_de_novo(self):
        self.registrar("tentar@exemplo.com")
        reprovada = self.criar_desafio()
        self.assertTrue(self.concluir(reprovada, acertos=1)["reprovado"])
        self.assertFalse(self.client.get("/api/learning/active-challenge").get_json()["ativo"])
        detalhe = self.client.get(f"/api/learning/challenges/{reprovada['desafio']['id_desafio']}").get_json()
        self.assertTrue(detalhe["reprovado"])
        self.assertFalse(detalhe["concluido"])
        nova = self.criar_desafio()
        self.assertNotEqual(reprovada["desafio"]["id_desafio"], nova["desafio"]["id_desafio"])
        self.assertEqual(1, nova["desafio"]["nivel_mapa"])
        self.assertTrue(self.concluir(nova, acertos=3)["concluido"])

    def test_nao_da_para_burlar_a_progressao(self):
        self.registrar("burlar@exemplo.com")
        id_tema = tema_com_banco_local(self.client)
        desafio = self.criar_desafio(id_tema=id_tema, dificuldade_base="facil", fase_jornada=1)
        id_desafio = desafio["desafio"]["id_desafio"]
        # Concluir sem responder tudo é recusado.
        self.assertEqual(400, self.client.post(f"/api/learning/challenges/{id_desafio}/complete", json={}).status_code)
        self.responder_todas(desafio, acertos=2)
        # Mandar "aprovado" ou "jornada_concluida" no corpo não muda o resultado.
        resultado = self.client.post(f"/api/learning/challenges/{id_desafio}/complete",
                                     json={"aprovado": True, "jornada_concluida": True, "percentual_acertos": 100}).get_json()
        self.assertTrue(resultado["reprovado"])
        # Responder de novo uma questão já respondida não troca a resposta.
        primeira = desafio["questoes"][3]
        repetida = self.client.post(f"/api/learning/challenges/{id_desafio}/answer", json={
            "id_questao": primeira["id_questao"], "alternativa": self.gabarito(primeira["id_questao"])}).get_json()
        self.assertTrue(repetida["ja_respondida"])
        self.assertFalse(repetida["correta"])
        self.assertTrue(self.client.post(f"/api/learning/challenges/{id_desafio}/complete", json={}).get_json()["reprovado"])
        self.assertEqual(1, self.criar_desafio(id_tema=id_tema, dificuldade_base="facil", fase_jornada=2)["desafio"]["nivel_mapa"])

    def test_revisao_nao_tem_nota_minima_nem_bonus(self):
        self.registrar("revisao60@exemplo.com")
        original = self.criar_desafio()
        self.concluir(original)
        pontos = self.pontos()
        revisao = self.client.post("/api/learning/challenges", json={
            "refazer": True, "refazer_de": original["desafio"]["id_desafio"]}).get_json()
        resultado = self.concluir(revisao, acertos=0)
        self.assertTrue(resultado["concluido"])
        self.assertEqual("revisao", resultado["desempenho"])
        self.assertEqual(pontos, self.pontos())

    def test_jornada_so_termina_com_todas_as_fases_aprovadas(self):
        self.registrar("jornada60@exemplo.com")
        id_tema = tema_com_banco_local(self.client)
        fase1 = self.criar_desafio(id_tema=id_tema, quantidade_questoes=20, dificuldade_base="facil", fase_jornada=1)
        self.assertFalse(self.concluir(fase1, acertos=12)["jornada_concluida"])
        fase2 = self.criar_desafio(id_tema=id_tema, quantidade_questoes=20, dificuldade_base="facil", fase_jornada=2)
        reprovada = self.concluir(fase2, acertos=11)
        self.assertTrue(reprovada["reprovado"])
        self.assertFalse(reprovada["jornada_concluida"])
        de_novo = self.criar_desafio(id_tema=id_tema, quantidade_questoes=20, dificuldade_base="facil", fase_jornada=2)
        self.assertEqual(2, de_novo["desafio"]["nivel_mapa"])
        final = self.concluir(de_novo, acertos=20)
        self.assertTrue(final["jornada_concluida"])
        self.assertEqual(50, final["bonus_jornada"])
        self.assertEqual(80, final["aproveitamento"])

    def test_ranking_e_progresso_continuam_depois_de_reprovar(self):
        eu = self.registrar("ranking60@exemplo.com")
        self.assertTrue(self.concluir(self.criar_desafio(), acertos=5)["concluido"])
        self.assertTrue(self.concluir(self.criar_desafio(), acertos=1)["reprovado"])
        perfil = self.client.get("/api/learning/me").get_json()
        self.assertEqual(1, perfil["progresso"]["desafios_concluidos"])
        self.assertEqual(10, perfil["progresso"]["questoes_respondidas"])
        self.assertEqual(60, perfil["progresso"]["precisao"])
        ranking = self.client.get("/api/learning/ranking?limite=100").get_json()
        meu = next(item for item in ranking["itens"] if item["id_aluno"] == eu["id_aluno"])
        self.assertEqual(perfil["aluno"]["pontos"], meu["pontos"])
        self.assertEqual(meu["posicao"], ranking["posicao_usuario"])


class TestAceiteDosTermos(BaseApi):
    """Termos de consentimento: a decisão do usuário fica registrada."""

    def test_cadastro_sem_aceite_e_recusado(self):
        for valor in (None, False, "sim", 1):
            with self.subTest(aceite=valor):
                corpo = {"nome": "Sem Aceite", "email": "sem-aceite@exemplo.com", "senha": "senha-segura-123"}
                if valor is not None:
                    corpo["aceite_termos"] = valor
                resposta = self.client.post("/api/auth/register", json=corpo)
                self.assertEqual(400, resposta.status_code)
                self.assertIn("Termos", resposta.get_json()["erro"])
        self.assertEqual(401, self.client.get("/api/learning/me").status_code)

    def test_cadastro_registra_data_e_versao_do_aceite(self):
        from models.model_aluno import VERSAO_TERMOS_ATUAL
        aluno = self.registrar("aceite@exemplo.com")
        self.assertEqual(VERSAO_TERMOS_ATUAL, aluno["versao_termos"])
        self.assertTrue(aluno["termos_aceitos_em"])
        self.assertFalse(aluno["precisa_aceitar_termos"])

    def test_conta_antiga_aceita_pelo_app(self):
        from models.model_aluno import Aluno
        aluno = self.registrar("antiga@exemplo.com")
        with app_module.app.app_context():
            registro = app_module.d.db.session.get(Aluno, aluno["id_aluno"])
            registro.termos_aceitos_em, registro.versao_termos = None, None
            app_module.d.db.session.commit()
        self.assertTrue(self.client.get("/api/learning/me").get_json()["aluno"]["precisa_aceitar_termos"])
        aceito = self.client.post("/api/auth/accept-terms", json={}).get_json()["aluno"]
        self.assertFalse(aceito["precisa_aceitar_termos"])
        self.assertTrue(aceito["termos_aceitos_em"])
        self.client.post("/api/auth/logout")
        self.assertEqual(401, self.client.post("/api/auth/accept-terms", json={}).status_code)


class TestRetomada(BaseApi):

    def responder(self, desafio, quantas):
        id_desafio = desafio["desafio"]["id_desafio"]
        for questao in desafio["questoes"][:quantas]:
            resposta = self.client.post(f"/api/learning/challenges/{id_desafio}/answer", json={
                "id_questao": questao["id_questao"], "alternativa": "A"})
            self.assertEqual(200, resposta.status_code)

    def test_desafio_pela_metade_volta_com_respostas_salvas(self):
        self.registrar("metade@exemplo.com")
        desafio = self.criar_desafio()
        self.responder(desafio, 2)
        ativo = self.client.get("/api/learning/active-challenge").get_json()
        self.assertTrue(ativo["ativo"])
        self.assertEqual(desafio["desafio"]["id_desafio"], ativo["desafio"]["id_desafio"])
        self.assertEqual(2, len(ativo["respondidas"]))
        self.assertFalse(ativo["todas_respondidas"])
        ids = [q["id_questao"] for q in ativo["questoes"]]
        self.assertEqual([q["id_questao"] for q in desafio["questoes"]], ids)
        self.assertEqual({str(i) for i in ids[:2]}, set(ativo["respondidas"]))

    def test_retomada_informa_quais_respostas_acertaram(self):
        # Ao retomar, o mapa precisa saber quais questões o aluno acertou e quais errou.
        from models.model_questao import Questao
        self.registrar("acertos@exemplo.com")
        desafio = self.criar_desafio()
        id_desafio = desafio["desafio"]["id_desafio"]
        q1, q2 = desafio["questoes"][0]["id_questao"], desafio["questoes"][1]["id_questao"]
        with app_module.app.app_context():
            certa1 = app_module.d.db.session.get(Questao, q1).alternativa_correta
            certa2 = app_module.d.db.session.get(Questao, q2).alternativa_correta
        errada2 = next(letra for letra in "ABCD" if letra != certa2)
        self.client.post(f"/api/learning/challenges/{id_desafio}/answer", json={"id_questao": q1, "alternativa": certa1})
        self.client.post(f"/api/learning/challenges/{id_desafio}/answer", json={"id_questao": q2, "alternativa": errada2})
        for dados in (self.client.get("/api/learning/active-challenge").get_json(),
                      self.client.get(f"/api/learning/challenges/{id_desafio}").get_json()):
            self.assertEqual({str(q1): True, str(q2): False}, dados["acertos"])
        for questao in self.client.get(f"/api/learning/challenges/{id_desafio}").get_json()["questoes"]:
            self.assertNotIn("alternativa_correta", questao)

    def test_tudo_respondido_sem_concluir_ainda_pode_ser_retomado(self):
        self.registrar("presa@exemplo.com")
        desafio = self.criar_desafio()
        self.responder_todas(desafio)
        ativo = self.client.get("/api/learning/active-challenge").get_json()
        self.assertTrue(ativo["ativo"])
        self.assertTrue(ativo["todas_respondidas"])
        id_desafio = desafio["desafio"]["id_desafio"]
        self.assertFalse(self.client.get(f"/api/learning/challenges/{id_desafio}").get_json()["concluido"])
        conclusao = self.client.post(f"/api/learning/challenges/{id_desafio}/complete", json={})
        self.assertTrue(conclusao.get_json()["concluido"])
        self.assertTrue(self.client.get(f"/api/learning/challenges/{id_desafio}").get_json()["concluido"])

    def test_fase_concluida_some_do_continuar_e_libera_a_proxima(self):
        self.registrar("proxima@exemplo.com")
        id_tema = tema_com_banco_local(self.client)
        fase1 = self.criar_desafio(id_tema=id_tema, dificuldade="facil", dificuldade_base="facil", fase_jornada=1)
        self.concluir(fase1)
        self.assertFalse(self.client.get("/api/learning/active-challenge").get_json()["ativo"])
        historico = self.client.get("/api/learning/history").get_json()["historico"]
        ultimo = max((h for h in historico if h["concluido"]), key=lambda h: h["id_desafio"])
        self.assertEqual((id_tema, 1, 5, "Fácil"), (ultimo["id_tema"], ultimo["nivel_mapa"],
                                                    ultimo["quantidade_questoes"], ultimo["dificuldade"]))
        fase2 = self.criar_desafio(id_tema=id_tema, dificuldade="normal", dificuldade_base="facil", fase_jornada=2)
        self.assertEqual(2, fase2["desafio"]["nivel_mapa"])
        historico = self.client.get("/api/learning/history").get_json()["historico"]
        self.assertEqual(1, sum(1 for h in historico if h["id_desafio"] == fase1["desafio"]["id_desafio"]))

    def test_retomar_nao_apaga_nem_duplica(self):
        self.registrar("estavel@exemplo.com")
        desafio = self.criar_desafio()
        self.responder(desafio, 1)
        for _ in range(3):
            ativo = self.client.get("/api/learning/active-challenge").get_json()
            self.assertEqual(desafio["desafio"]["id_desafio"], ativo["desafio"]["id_desafio"])
            self.assertEqual(1, len(ativo["respondidas"]))


class TestCorrecoesDaAuditoria(BaseApi):
    """Erros já corrigidos no projeto, cada um com o cenário que quebrava."""

    def test_chave_de_sessao_de_exemplo_e_recusada(self):
        self.assertFalse(app_module.chave_valida("troque-por-uma-chave-aleatoria-e-segura"))
        self.assertFalse(app_module.chave_valida("curta"))
        self.assertFalse(app_module.chave_valida(""))
        self.assertTrue(app_module.chave_valida("9f2c" * 16))

    def test_login_bloqueia_depois_de_muitas_tentativas(self):
        self.registrar("forca-bruta@exemplo.com")
        self.client.post("/api/auth/logout")
        for _ in range(5):
            self.assertEqual(401, self.client.post("/api/auth/login", json={
                "email": "forca-bruta@exemplo.com", "senha": "errada"}).status_code)
        bloqueado = self.client.post("/api/auth/login", json={"email": "forca-bruta@exemplo.com", "senha": "senha-segura-123"})
        self.assertEqual(429, bloqueado.status_code)
        self.assertIn("Retry-After", bloqueado.headers)

    def test_tempo_ativo_nao_infla_com_chamadas_seguidas(self):
        self.registrar("heartbeat@exemplo.com")
        for _ in range(10):
            resposta = self.client.post("/api/learning/activity", json={"segundos": 120})
            self.assertEqual(200, resposta.status_code)
        self.assertLessEqual(resposta.get_json()["minutos_ativos"], 1)

    def test_tempo_ativo_guarda_o_resto_dos_segundos(self):
        from models.model_aluno import Aluno
        aluno = self.registrar("resto@exemplo.com")
        with app_module.app.app_context():
            registro = app_module.d.db.session.get(Aluno, aluno["id_aluno"])
            registro.ultimo_heartbeat = time.time() - 1000
            app_module.d.db.session.commit()
        self.client.post("/api/learning/activity", json={"segundos": 30})
        with app_module.app.app_context():
            registro = app_module.d.db.session.get(Aluno, aluno["id_aluno"])
            registro.ultimo_heartbeat = time.time() - 1000
            app_module.d.db.session.commit()
        resposta = self.client.post("/api/learning/activity", json={"segundos": 30}).get_json()
        self.assertEqual(1, resposta["minutos_ativos"])

    def test_excluir_conta_nao_deixa_questoes_orfas(self):
        from models.model_questao import Questao
        from models.model_aprendizado import RespostaDesafio
        self.registrar("apagar@exemplo.com")
        desafio = self.criar_desafio()
        self.concluir(desafio)
        ids = [q["id_questao"] for q in desafio["questoes"]]
        resposta = self.client.delete("/api/auth/delete-account", json={"senha": "senha-segura-123"})
        self.assertEqual(200, resposta.status_code)
        with app_module.app.app_context():
            self.assertEqual(0, Questao.query.filter(Questao.id_questao.in_(ids)).count())
            self.assertEqual(0, RespostaDesafio.query.filter_by(id_desafio=desafio["desafio"]["id_desafio"]).count())

    def test_excluir_conta_exige_a_senha_certa(self):
        self.registrar("protegida@exemplo.com")
        self.assertEqual(403, self.client.delete("/api/auth/delete-account", json={"senha": "errada"}).status_code)
        self.assertEqual(200, self.client.get("/api/learning/me").status_code)

    def test_ranking_mostra_posicao_de_quem_esta_fora_do_topo(self):
        for indice in range(6):
            self.registrar(f"topo{indice}@exemplo.com")
            self.concluir(self.criar_desafio())
            self.client.post("/api/auth/logout")
        eu = self.registrar("lanterna@exemplo.com")
        desafio = self.criar_desafio()
        id_desafio = desafio["desafio"]["id_desafio"]
        self.client.post(f"/api/learning/challenges/{id_desafio}/answer",
                         json={"id_questao": desafio["questoes"][0]["id_questao"], "alternativa": "A"})
        ranking = self.client.get("/api/learning/ranking?limite=5").get_json()
        self.assertEqual(5, len(ranking["itens"]))
        self.assertNotIn(eu["id_aluno"], [item["id_aluno"] for item in ranking["itens"]])
        completo = self.client.get("/api/learning/ranking?limite=100").get_json()
        minha = next(i["posicao"] for i in completo["itens"] if i["id_aluno"] == eu["id_aluno"])
        self.assertEqual(completo["total_alunos"], ranking["total_alunos"])
        self.assertEqual(minha, ranking["posicao_usuario"])

    def test_exclusoes_do_painel_limpam_os_dependentes(self):
        from models.model_aluno_desafio import AlunoDesafio
        from models.model_aprendizado import RespostaDesafio
        from models.model_desafio import Desafio
        from services.desafio.deletar_desafio import DeletarDesafioService
        from services.questao.deletar_questao import DeletarQuestaoService
        from services.tema.deletar_tema import DeletarTemaService
        self.registrar("painel@exemplo.com")
        desafio = self.criar_desafio()
        self.concluir(desafio)
        id_desafio = desafio["desafio"]["id_desafio"]
        with app_module.app.app_context():
            with self.assertRaises(ValueError):
                DeletarQuestaoService().executar(desafio["questoes"][0]["id_questao"])
            with self.assertRaises(ValueError):
                DeletarTemaService().executar(desafio["desafio"]["id_tema"])
            self.assertTrue(DeletarDesafioService().executar(id_desafio))
            self.assertIsNone(app_module.d.db.session.get(Desafio, id_desafio))
            self.assertEqual(0, RespostaDesafio.query.filter_by(id_desafio=id_desafio).count())
            self.assertEqual(0, AlunoDesafio.query.filter_by(id_desafio=id_desafio).count())

    def test_verificar_questao_sem_gabarito_nao_quebra(self):
        from models.model_questao import Questao
        from repositories.questao_repository import QuestaoRepository
        with app_module.app.app_context():
            from models.model_tema import Tema
            tema = Tema.query.first()
            questao = Questao(enunciado="Sem gabarito", alternativa_correta=None, id_tema=tema.id_tema)
            app_module.d.db.session.add(questao)
            app_module.d.db.session.commit()
            with self.assertRaises(ValueError):
                QuestaoRepository.verificar_resposta(questao.id_questao, "A")
            questao.alternativa_correta = "b"
            app_module.d.db.session.commit()
            self.assertTrue(QuestaoRepository.verificar_resposta(questao.id_questao, " B "))

    def test_atualizar_progresso_aceita_data_em_texto(self):
        from services.aluno_desafio.atualizar_aluno_desafio import AtualizarAlunoDesafioService
        aluno = self.registrar("data@exemplo.com")
        desafio = self.criar_desafio()
        self.concluir(desafio)
        with app_module.app.app_context():
            servico = AtualizarAlunoDesafioService()
            resultado = servico.executar(aluno["id_aluno"], desafio["desafio"]["id_desafio"], {"data_realizacao": "2026-01-15"})
            self.assertEqual("2026-01-15", resultado["data_realizacao"])
            with self.assertRaises(ValueError):
                servico.executar(aluno["id_aluno"], desafio["desafio"]["id_desafio"], {"data_realizacao": "15/01/2026"})

    def test_trocar_de_desafio_mantem_pontos_e_ranking_coerentes(self):
        eu = self.registrar("troca@exemplo.com")
        desafio = self.criar_desafio()
        id_desafio = desafio["desafio"]["id_desafio"]
        resposta = self.client.post(f"/api/learning/challenges/{id_desafio}/answer",
                                    json={"id_questao": desafio["questoes"][0]["id_questao"], "alternativa": "A"}).get_json()
        self.criar_desafio()
        ultimo = self.criar_desafio()
        pontos = self.client.get("/api/learning/me").get_json()["aluno"]["pontos"]
        self.assertEqual(resposta["pontos_totais"], pontos)
        ranking = self.client.get("/api/learning/ranking?limite=100").get_json()
        self.assertIn(eu["id_aluno"], [item["id_aluno"] for item in ranking["itens"]])
        self.assertIsNotNone(ranking["posicao_usuario"])
        ativo = self.client.get("/api/learning/active-challenge").get_json()
        self.assertEqual(ultimo["desafio"]["id_desafio"], ativo["desafio"]["id_desafio"])

    def test_cadastro_com_nome_nulo_e_recusado(self):
        resposta = self.client.post("/api/auth/register", json={
            "nome": None, "email": "nulo@exemplo.com", "senha": "senha-segura-123", "aceite_termos": True})
        self.assertEqual(400, resposta.status_code)

    def test_cadastro_com_nick_nulo_usa_so_o_primeiro_nome(self):
        resposta = self.client.post("/api/auth/register", json={
            "nome": "Sem Nick", "nick": None, "email": "semnick@exemplo.com", "senha": "senha-segura-123",
            "aceite_termos": True})
        self.assertEqual(201, resposta.status_code, resposta.get_data(as_text=True))
        # Só o primeiro nome: o nome completo não pode aparecer no ranking.
        self.assertEqual("Sem", resposta.get_json()["aluno"]["nick"])

    def test_corpo_que_nao_e_objeto_nao_vira_erro_500(self):
        self.assertEqual(400, self.client.post("/api/auth/register", json=["a", "b"]).status_code)
        self.registrar("lista@exemplo.com")
        self.assertEqual(404, self.client.post("/api/learning/challenges", json=[1, 2]).status_code)

    def test_refazer_desafio_sem_tema_nao_vira_erro_500(self):
        from models.model_desafio import Desafio
        self.registrar("semtema@exemplo.com")
        desafio = self.criar_desafio()
        self.concluir(desafio)
        id_desafio = desafio["desafio"]["id_desafio"]
        with app_module.app.app_context():
            app_module.d.db.session.get(Desafio, id_desafio).id_tema = None
            app_module.d.db.session.commit()
        resposta = self.client.post("/api/learning/challenges", json={"refazer": True, "refazer_de": id_desafio})
        self.assertEqual(404, resposta.status_code, resposta.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
