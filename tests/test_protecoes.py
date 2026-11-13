"""Proteções de uso: limite de geração por aluno, bloqueio de login, nome no ranking,
validação das questões da IA e tratamento dos erros do provedor.

Nenhum teste chama a IA de verdade: as respostas do provedor são simuladas.
"""
import io
import json
import os
import unittest
import urllib.error
from unittest import mock

from tests.test_api import BaseApi, app_module, tema_com_banco_local

import services.aprendizado.conta_service as CONTA
import services.aprendizado.gerador_questoes as GERADOR
import services.aprendizado.limite_geracao as LIMITE
from services.aprendizado.regras import nome_publico

SEM_LIMITES = {"INTERVALO_ENTRE_GERACOES": "0", "GERACOES_POR_JANELA": "0", "GERACOES_POR_DIA": "0"}


def zerar_pedidos():
    with app_module.app.app_context():
        LIMITE.esquecer_tudo()


def limites(**valores):
    return mock.patch.dict(os.environ, {**SEM_LIMITES, **{nome: str(valor) for nome, valor in valores.items()}})


class TestLimiteDeGeracao(BaseApi):
    def setUp(self):
        super().setUp()
        zerar_pedidos()
        self.addCleanup(zerar_pedidos)

    def pedir(self, cliente=None, **extra):
        cliente = cliente or self.client
        corpo = {"id_tema": tema_com_banco_local(cliente), "quantidade_questoes": 5, "dificuldade": "normal", **extra}
        return cliente.post("/api/learning/challenges", json=corpo)

    def test_intervalo_entre_uma_geracao_e_a_proxima(self):
        self.registrar("intervalo@exemplo.com")
        with limites(INTERVALO_ENTRE_GERACOES=30):
            self.assertEqual(201, self.pedir().status_code)
            segunda = self.pedir()
        self.assertEqual(429, segunda.status_code)
        dados = segunda.get_json()
        self.assertIn("Aguarde", dados["erro"])
        self.assertTrue(dados["limite_de_geracao"])
        self.assertTrue(1 <= dados["aguarde_segundos"] <= 30)
        self.assertEqual(str(dados["aguarde_segundos"]), segunda.headers["Retry-After"])

    def test_teto_de_geracoes_na_janela(self):
        self.registrar("janela@exemplo.com")
        with limites(GERACOES_POR_JANELA=3):
            codigos = [self.pedir().status_code for _ in range(5)]
            mensagem = self.pedir().get_json()["erro"]
        self.assertEqual([201, 201, 201, 429, 429], codigos)
        self.assertIn("muitos desafios em pouco tempo", mensagem)

    def test_teto_por_dia_nao_impede_refazer(self):
        self.registrar("dia@exemplo.com")
        with limites(GERACOES_POR_DIA=2):
            primeiro = self.pedir().get_json()
            self.responder_todas(primeiro)
            id_desafio = primeiro["desafio"]["id_desafio"]
            self.assertEqual(200, self.client.post(f"/api/learning/challenges/{id_desafio}/complete").status_code)
            self.assertEqual(201, self.pedir().status_code)
            terceiro = self.pedir()
            self.assertEqual(429, terceiro.status_code)
            self.assertIn("por hoje", terceiro.get_json()["erro"])
            # Refazer usa as questões salvas, não chama a IA e por isso continua liberado.
            refazer = self.client.post("/api/learning/challenges", json={"refazer": True, "refazer_de": id_desafio})
        self.assertEqual(201, refazer.status_code)

    def test_o_limite_de_um_aluno_nao_afeta_o_outro(self):
        self.registrar("um@exemplo.com")
        outro = app_module.app.test_client()
        outro.post("/api/auth/register", json={"nome": "Outro", "email": "outro-limite@exemplo.com",
                                               "senha": "senha-segura-123", "aceite_termos": True})
        with limites(GERACOES_POR_JANELA=1):
            self.assertEqual(201, self.pedir().status_code)
            self.assertEqual(429, self.pedir().status_code)
            self.assertEqual(201, self.pedir(outro).status_code)

    def test_pedido_repetido_enquanto_o_desafio_e_preparado(self):
        aluno = self.registrar("clique-repetido@exemplo.com")
        with limites():
            with app_module.app.app_context(), LIMITE.vaga_de_geracao(aluno["id_aluno"]):  # geração em curso
                repetido = self.pedir()
            depois = self.pedir()
        self.assertEqual(429, repetido.status_code)
        self.assertIn("já está sendo preparado", repetido.get_json()["erro"])
        self.assertEqual(201, depois.status_code)

    def test_falha_da_ia_conta_a_tentativa_e_libera_o_aluno(self):
        aluno = self.registrar("falha@exemplo.com")
        with limites(INTERVALO_ENTRE_GERACOES=30), \
                mock.patch("services.aprendizado.desafio_service.gerar_questoes", side_effect=RuntimeError("fora do ar")):
            self.assertEqual(502, self.pedir().status_code)
            with app_module.app.app_context():
                self.assertFalse(LIMITE.em_andamento(aluno["id_aluno"]))
            self.assertEqual(429, self.pedir().status_code)

    def test_pedido_invalido_nao_gasta_o_limite(self):
        self.registrar("invalido@exemplo.com")
        with limites(GERACOES_POR_JANELA=1):
            for _ in range(3):
                resposta = self.client.post("/api/learning/challenges", json={"id_tema": 999999, "quantidade_questoes": 5})
                self.assertEqual(404, resposta.status_code)
            self.assertEqual(400, self.pedir(quantidade_questoes=7).status_code)
            self.assertEqual(201, self.pedir().status_code)

    def test_limite_mal_configurado_usa_o_padrao(self):
        with mock.patch.dict(os.environ, {"GERACOES_POR_DIA": "muitas", "INTERVALO_ENTRE_GERACOES": ""}):
            self.assertEqual(LIMITE.PADROES["GERACOES_POR_DIA"], LIMITE._limite("GERACOES_POR_DIA"))
            self.assertEqual(LIMITE.PADROES["INTERVALO_ENTRE_GERACOES"], LIMITE._limite("INTERVALO_ENTRE_GERACOES"))

    def test_sem_configuracao_o_limite_fica_ligado(self):
        self.registrar("padrao@exemplo.com")
        ambiente = {nome: valor for nome, valor in os.environ.items() if nome not in SEM_LIMITES}
        with mock.patch.dict(os.environ, ambiente, clear=True):
            self.assertEqual(201, self.pedir().status_code)
            self.assertEqual(429, self.pedir().status_code)


class TestBloqueioDeLogin(BaseApi):
    def setUp(self):
        super().setUp()
        CONTA._falhas_login.clear()
        self.addCleanup(CONTA._falhas_login.clear)

    def test_senhas_erradas_da_turma_nao_travam_o_login_dos_colegas(self):
        """Uma escola inteira usa o mesmo IP: 25 erros somados não podem bloquear quem acerta a senha."""
        self.registrar("colega@exemplo.com")
        for indice in range(25):
            resposta = self.client.post("/api/auth/login", json={"email": f"turma{indice}@exemplo.com", "senha": "errada"})
            self.assertEqual(401, resposta.status_code)
        certo = self.client.post("/api/auth/login", json={"email": "colega@exemplo.com", "senha": "senha-segura-123"})
        self.assertEqual(200, certo.status_code)

    def test_a_conta_atacada_continua_protegida(self):
        self.registrar("alvo@exemplo.com")
        codigos = [self.client.post("/api/auth/login", json={"email": "alvo@exemplo.com", "senha": "errada"}).status_code
                   for _ in range(CONTA.LIMITE_FALHAS_LOGIN + 1)]
        self.assertEqual([401] * CONTA.LIMITE_FALHAS_LOGIN + [429], codigos)

    def test_o_limite_por_ip_continua_existindo(self):
        for indice in range(CONTA.LIMITE_FALHAS_POR_IP):
            self.client.post("/api/auth/login", json={"email": f"robo{indice}@exemplo.com", "senha": "errada"})
        bloqueado = self.client.post("/api/auth/login", json={"email": "novo@exemplo.com", "senha": "errada"})
        self.assertEqual(429, bloqueado.status_code)
        self.assertIn("Retry-After", bloqueado.headers)


class TestNomeNoRanking(BaseApi):
    def test_sem_nick_o_ranking_mostra_so_o_primeiro_nome(self):
        resposta = self.client.post("/api/auth/register", json={
            "nome": "Mariazinha Sobrenomelongo Deteste", "email": "primeironome@exemplo.com",
            "senha": "senha-segura-123", "aceite_termos": True})
        self.assertEqual(201, resposta.status_code)
        self.assertEqual("Mariazinha", resposta.get_json()["aluno"]["nick"])
        desafio = self.criar_desafio()
        questao = desafio["questoes"][0]["id_questao"]
        self.client.post(f"/api/learning/challenges/{desafio['desafio']['id_desafio']}/answer",
                         json={"id_questao": questao, "alternativa": self.gabarito(questao)})
        publico = app_module.app.test_client().get("/api/learning/ranking?limite=100")
        texto = publico.get_data(as_text=True)
        self.assertIn("Mariazinha", [item["nick"] for item in publico.get_json()["itens"]])
        self.assertNotIn("Sobrenomelongo", texto)
        self.assertNotIn("primeironome@exemplo.com", texto)

    def test_nome_publico(self):
        self.assertEqual("Lia", nome_publico("Lia", "Maria Lia Souza"))
        self.assertEqual("Maria", nome_publico(None, "Maria Lia Souza"))
        self.assertEqual("Maria", nome_publico("   ", "  Maria   Lia "))
        self.assertEqual("Estudante", nome_publico("", ""))


def questao(enunciado, alternativas=("1", "2", "3", "4"), correta="B", explicacao="Porque sim."):
    return {"enunciado": enunciado, "alternativas": dict(zip("ABCD", alternativas)),
            "alternativa_correta": correta, "explicacao": explicacao}


class TestValidacaoDasQuestoes(unittest.TestCase):
    def test_alternativas_repetidas_sao_recusadas(self):
        with self.assertRaises(ValueError):
            GERADOR._validar_questoes([questao("Capital da França?", ["Paris"] * 4)], 1)
        with self.assertRaises(ValueError):
            GERADOR._validar_questoes([questao("Capital da França?", ["Paris", " paris ", "Roma", "Lima"])], 1)

    def test_sinais_e_numeros_diferentes_nao_sao_repeticao(self):
        lote = [questao("Resolva: x + 7 = 15.", ["2", "−2", "8", "-8"]), questao("Resolva: x − 7 = 15.", ["22", "−22", "8", "2"])]
        validas = GERADOR._validar_questoes(lote, 2)
        self.assertEqual(2, len(validas))
        self.assertEqual("−2", validas[0]["alternativas"]["B"])

    def test_enunciado_repetido_no_lote_e_descartado(self):
        repetidas = [questao("Mesma pergunta?")] * 5
        with self.assertRaises(ValueError):
            GERADOR._validar_questoes(repetidas, 5)
        # Com questões de sobra, as boas são aproveitadas.
        lote = [questao("Pergunta 1"), questao("pergunta   1"), questao("Pergunta 2"), {"enunciado": "quebrada"}, questao("Pergunta 3")]
        validas = GERADOR._validar_questoes(lote, 3)
        self.assertEqual(["Pergunta 1", "Pergunta 2", "Pergunta 3"], [q["enunciado"] for q in validas])

    def test_textos_grandes_demais(self):
        with self.assertRaises(ValueError):
            GERADOR._validar_questoes([questao("X" * (GERADOR.LIMITE_ENUNCIADO + 1))], 1)
        with self.assertRaises(ValueError):
            GERADOR._validar_questoes([questao("Pergunta", ["a", "b", "c", "d" * (GERADOR.LIMITE_ALTERNATIVA + 1)])], 1)
        longa = GERADOR._validar_questoes([questao("Pergunta", explicacao="e" * 5000)], 1)[0]
        self.assertEqual(GERADOR.LIMITE_EXPLICACAO, len(longa["explicacao"]))

    def test_explicacao_vazia_ganha_texto_padrao(self):
        valida = GERADOR._validar_questoes([questao("Pergunta", explicacao="  ")], 1)[0]
        self.assertTrue(valida["explicacao"])

    def test_o_banco_local_passa_na_mesma_validacao(self):
        for nome, banco in GERADOR.BANCO_TEMATICO.items():
            lote = [questao(enunciado, opcoes, correta, explicacao) for enunciado, opcoes, correta, explicacao in banco]
            with self.subTest(banco=nome):
                self.assertEqual(len(banco), len(GERADOR._validar_questoes(lote, len(banco))))


def erro_http(codigo, corpo=b"{}", cabecalhos=None):
    def urlopen(requisicao, **_kwargs):
        urlopen.chamadas.append(requisicao.full_url)
        raise urllib.error.HTTPError(requisicao.full_url, codigo, "erro", cabecalhos or {}, io.BytesIO(corpo))
    urlopen.chamadas = []
    return urlopen


class TestErrosDoProvedor(unittest.TestCase):
    GEMINI = {"GEMINI_API_KEY": "chave-secreta-do-teste", "GEMINI_MODEL": "", "OPENAI_API_KEY": ""}
    OPENAI = {"GEMINI_API_KEY": "", "OPENAI_API_KEY": "chave-secreta-do-teste"}

    def setUp(self):
        GERADOR._pausas.clear()
        self.addCleanup(GERADOR._pausas.clear)

    def gerar(self, ambiente, urlopen):
        with mock.patch.dict(os.environ, ambiente), mock.patch.object(GERADOR.urllib.request, "urlopen", urlopen):
            with self.assertRaises(GERADOR.ErroDeGeracao) as contexto:
                GERADOR.gerar_questoes("História", "Revolução Industrial", "Normal", 5)
        return contexto.exception

    def test_limite_de_uso_tem_mensagem_propria_e_pausa_o_provedor(self):
        urlopen = erro_http(429)
        erro = self.gerar(self.GEMINI, urlopen)
        self.assertEqual((GERADOR.MENSAGEM_COTA, 503), (str(erro), erro.status))
        self.assertTrue(erro.espera)
        self.assertEqual(2, len(urlopen.chamadas))          # um modelo, depois o outro
        self.assertNotEqual(*urlopen.chamadas)
        # Logo em seguida o provedor está em pausa: nenhum pedido novo sai do servidor.
        erro = self.gerar(self.GEMINI, urlopen)
        self.assertEqual(GERADOR.MENSAGEM_COTA, str(erro))
        self.assertEqual(2, len(urlopen.chamadas))

    def test_a_pausa_respeita_o_tempo_pedido_pelo_provedor(self):
        erro = self.gerar(self.OPENAI, erro_http(429, cabecalhos={"Retry-After": "7"}))
        self.assertEqual(7, erro.espera)
        restante = GERADOR._pausas["openai"] - GERADOR.time.monotonic()
        self.assertTrue(5 < restante <= 7)

    def test_openai_nao_insiste_quando_o_limite_foi_atingido(self):
        urlopen = erro_http(429)
        self.gerar(self.OPENAI, urlopen)
        self.assertEqual(1, len(urlopen.chamadas))

    def test_chave_recusada_para_na_primeira_tentativa(self):
        for codigo, corpo in ((401, b"{}"), (403, b"{}"), (400, b'{"error":{"status":"INVALID_ARGUMENT","details":[{"reason":"API_KEY_INVALID"}]}}')):
            with self.subTest(codigo=codigo):
                urlopen = erro_http(codigo, corpo)
                erro = self.gerar(self.GEMINI, urlopen)
                self.assertEqual((GERADOR.MENSAGEM_CHAVE, 503), (str(erro), erro.status))
                self.assertEqual(1, len(urlopen.chamadas))

    def test_provedor_fora_do_ar(self):
        for codigo in (400, 404, 500, 503):
            with self.subTest(codigo=codigo):
                urlopen = erro_http(codigo)
                erro = self.gerar(self.GEMINI, urlopen)
                self.assertEqual((GERADOR.MENSAGEM_INDISPONIVEL, 502), (str(erro), erro.status))
                self.assertEqual(2, len(urlopen.chamadas))

    def test_resposta_fora_do_formato(self):
        corpo = json.dumps({"candidates": [{"content": {"parts": [{"text": json.dumps({"questoes": [questao("Só uma")]})}]}}]}).encode()
        erro = self.gerar(self.GEMINI, lambda *_a, **_k: io.BytesIO(corpo))
        self.assertEqual((GERADOR.MENSAGEM_RESPOSTA, 502), (str(erro), erro.status))

    def test_prazo_total_do_pedido(self):
        urlopen = erro_http(500)
        with mock.patch.object(GERADOR, "PRAZO_TOTAL_IA", 0):
            erro = self.gerar(self.GEMINI, urlopen)
        self.assertEqual(GERADOR.MENSAGEM_INDISPONIVEL, str(erro))
        self.assertEqual([], urlopen.chamadas)

    def test_tempo_limite_de_cada_chamada_cabe_no_prazo(self):
        tempos = []

        def urlopen(_requisicao, timeout=None):
            tempos.append(timeout)
            raise OSError("sem rede")

        with mock.patch.object(GERADOR, "PRAZO_TOTAL_IA", 20):
            self.gerar(self.GEMINI, urlopen)
        self.assertTrue(tempos and all(0 < tempo <= 20 for tempo in tempos))

    def test_a_chave_nunca_vai_para_o_log(self):
        with self.assertLogs(GERADOR.registro, level="WARNING") as registros:
            self.gerar(self.GEMINI, erro_http(401, b'{"error":"chave-secreta-do-teste recusada"}'))
        self.assertNotIn("chave-secreta-do-teste", "\n".join(registros.output))

    def test_sem_ia_configurada_a_mensagem_continua_a_mesma(self):
        erro = self.gerar({"GEMINI_API_KEY": "", "OPENAI_API_KEY": ""}, erro_http(500))
        self.assertEqual((GERADOR.MENSAGEM_INDISPONIVEL, 502), (str(erro), erro.status))

    def test_com_banco_local_o_aluno_nem_percebe_a_falha_da_ia(self):
        with mock.patch.dict(os.environ, self.GEMINI), mock.patch.object(GERADOR.urllib.request, "urlopen", erro_http(429)):
            questoes, origem = GERADOR.gerar_questoes("Física", "Sistema Solar", "Normal", 5)
        self.assertEqual(("banco_local", 5), (origem, len(questoes)))


class TestErroDaIaNaApi(BaseApi):
    def setUp(self):
        super().setUp()
        zerar_pedidos()

    def test_limite_do_provedor_chega_ao_aluno_com_tempo_de_espera(self):
        self.registrar("cota@exemplo.com")
        falha = GERADOR.ErroDeGeracao(GERADOR.MENSAGEM_COTA, 503, espera=42)
        with mock.patch("services.aprendizado.desafio_service.gerar_questoes", side_effect=falha):
            resposta = self.client.post("/api/learning/challenges", json={
                "id_tema": tema_com_banco_local(self.client), "quantidade_questoes": 5, "dificuldade": "normal"})
        self.assertEqual(503, resposta.status_code)
        self.assertEqual(GERADOR.MENSAGEM_COTA, resposta.get_json()["erro"])
        self.assertEqual("42", resposta.headers["Retry-After"])
        # Nada ficou gravado pela metade.
        self.assertFalse(self.client.get("/api/learning/active-challenge").get_json()["ativo"])


class TestCabecalhosDeSeguranca(BaseApi):
    CABECALHOS = ("Content-Security-Policy", "X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy", "Permissions-Policy")

    def test_todas_as_respostas_levam_os_cabecalhos(self):
        for caminho in ("/", "/estudar.js", "/api/learning/catalog", "/api/learning/me", "/alunos", "/nao-existe"):
            resposta = self.client.get(caminho)
            with self.subTest(caminho=caminho, status=resposta.status_code):
                for nome in self.CABECALHOS:
                    self.assertTrue(resposta.headers.get(nome), nome)
                self.assertEqual("nosniff", resposta.headers["X-Content-Type-Options"])
                self.assertEqual("DENY", resposta.headers["X-Frame-Options"])

    def test_a_politica_so_aceita_scripts_do_proprio_site(self):
        cabecalho = self.client.get("/").headers["Content-Security-Policy"]
        politica = dict(parte.strip().split(" ", 1) for parte in cabecalho.split(";"))
        self.assertEqual("'self'", politica["script-src"])
        self.assertEqual("'none'", politica["object-src"])
        self.assertEqual("'none'", politica["frame-ancestors"])
        self.assertNotIn("unsafe-eval", cabecalho)

    def test_as_paginas_nao_dependem_de_script_embutido_nem_de_site_externo(self):
        """A política acima bloquearia <script> sem src, onclick="..." e recursos de outros sites."""
        import re
        from tests.test_api import ROOT
        problemas = []
        for arquivo in sorted((ROOT / "frontend").glob("*.html")):
            html = arquivo.read_text(encoding="utf-8")
            if re.search(r"<script(?![^>]*\bsrc=)[^>]*>", html):
                problemas.append(f"{arquivo.name}: <script> sem src")
            if re.search(r"""\son[a-z]+\s*=\s*["']""", html):
                problemas.append(f"{arquivo.name}: evento embutido (onclick=...)")
            if re.search(r"""<(script|link|img)[^>]+(src|href)=["']https?://""", html):
                problemas.append(f"{arquivo.name}: recurso de outro site")
        self.assertEqual([], problemas)

    def test_hsts_so_com_configuracao_e_em_https(self):
        self.assertNotIn("Strict-Transport-Security", self.client.get("/", base_url="https://localhost").headers)
        with mock.patch.dict(os.environ, {"HSTS_SEGUNDOS": "600"}):
            self.assertNotIn("Strict-Transport-Security", self.client.get("/", base_url="http://localhost").headers)
            self.assertEqual("max-age=600", self.client.get("/", base_url="https://localhost").headers["Strict-Transport-Security"])
        with mock.patch.dict(os.environ, {"HSTS_SEGUNDOS": "sempre"}):
            self.assertNotIn("Strict-Transport-Security", self.client.get("/", base_url="https://localhost").headers)


class TestTamanhoDoPedido(BaseApi):
    def test_corpo_grande_demais_e_recusado(self):
        grande = b"{" + b" " * (app_module.TAMANHO_MAXIMO_DO_PEDIDO + 10) + b"}"
        for caminho in ("/api/auth/login", "/api/auth/register"):
            resposta = self.client.post(caminho, data=grande, content_type="application/json")
            with self.subTest(caminho=caminho):
                self.assertEqual(413, resposta.status_code)
                self.assertIn("grande demais", resposta.get_json()["erro"])

    def test_pedido_normal_continua_passando(self):
        resposta = self.client.post("/api/auth/login", json={"email": "ninguem@exemplo.com", "senha": "x" * 200})
        self.assertEqual(401, resposta.status_code)


class TestChavesEstrangeirasNoSqlite(BaseApi):
    def setUp(self):
        super().setUp()
        with app_module.app.app_context():
            if app_module.d.db.engine.dialect.name != "sqlite":
                self.skipTest("Só se aplica ao SQLite; os outros bancos já conferem as chaves.")

    def test_o_banco_recusa_resposta_de_aluno_que_nao_existe(self):
        from sqlalchemy import text
        from sqlalchemy.exc import IntegrityError
        with app_module.app.app_context():
            sessao = app_module.d.db.session
            self.assertEqual(1, sessao.execute(text("PRAGMA foreign_keys")).scalar())
            with self.assertRaises(IntegrityError):
                sessao.execute(text(
                    "INSERT INTO resposta_desafio (id_aluno, id_desafio, id_questao, alternativa_escolhida, correta, "
                    "pontos_ganhos, segundos_gastos, data_resposta) VALUES (987654, 987654, 987654, 'A', 0, 0, 0, '2026-01-01')"))
                sessao.flush()
            sessao.rollback()

    def test_excluir_a_conta_continua_funcionando_com_as_chaves_ligadas(self):
        self.registrar("fk-excluir@exemplo.com")
        desafio = self.criar_desafio()
        self.responder_todas(desafio)
        self.client.post(f"/api/learning/challenges/{desafio['desafio']['id_desafio']}/complete")
        self.criar_desafio()  # um segundo desafio, sem respostas
        resposta = self.client.delete("/api/auth/delete-account", json={"senha": "senha-segura-123"})
        self.assertEqual(200, resposta.status_code, resposta.get_data(as_text=True))
        self.assertEqual(401, self.client.post("/api/auth/login", json={
            "email": "fk-excluir@exemplo.com", "senha": "senha-segura-123"}).status_code)


class TestConclusaoEmParalelo(BaseApi):
    def pontos(self):
        return self.client.get("/api/learning/me").get_json()["aluno"]["pontos"]

    def test_varios_pedidos_juntos_pagam_o_bonus_uma_vez_e_nenhum_da_erro(self):
        import threading
        self.registrar("paralelo@exemplo.com")
        desafio = self.criar_desafio()
        self.responder_todas(desafio)
        id_desafio = desafio["desafio"]["id_desafio"]
        antes = self.pontos()
        sessao = self.client.get_cookie("session").value
        resultados = []

        def concluir():
            cliente = app_module.app.test_client()
            cliente.set_cookie("session", sessao)
            resposta = cliente.post(f"/api/learning/challenges/{id_desafio}/complete")
            resultados.append((resposta.status_code, (resposta.get_json() or {}).get("concluido")))

        pedidos = [threading.Thread(target=concluir) for _ in range(8)]
        for pedido in pedidos:
            pedido.start()
        for pedido in pedidos:
            pedido.join()
        self.assertEqual([(200, True)] * 8, resultados)
        self.assertEqual(35, self.pontos() - antes)  # 10 da fase + 25 do desafio perfeito, uma única vez

    def test_gravacao_repetida_vira_resposta_de_fase_ja_concluida(self):
        """Simula o outro pedido gravando primeiro: o banco recusa a segunda gravação."""
        from sqlalchemy.exc import IntegrityError
        from services.aprendizado.conclusao_service import ConclusaoService
        self.registrar("corrida@exemplo.com")
        desafio = self.criar_desafio()
        self.responder_todas(desafio)
        id_desafio = desafio["desafio"]["id_desafio"]
        antes = self.pontos()
        sessao = self.client.get_cookie("session").value
        original = ConclusaoService._concluir
        chamadas = []

        def primeira_perde_a_corrida(servico, aluno, id_do_desafio):
            chamadas.append(id_do_desafio)
            if len(chamadas) == 1:
                outro = app_module.app.test_client()
                outro.set_cookie("session", sessao)
                with mock.patch.object(ConclusaoService, "_concluir", original):
                    self.assertEqual(200, outro.post(f"/api/learning/challenges/{id_do_desafio}/complete").status_code)
                raise IntegrityError("INSERT", {}, Exception("registro duplicado"))
            return original(servico, aluno, id_do_desafio)

        with mock.patch.object(ConclusaoService, "_concluir", primeira_perde_a_corrida):
            resposta = self.client.post(f"/api/learning/challenges/{id_desafio}/complete")
        self.assertEqual(200, resposta.status_code)
        self.assertTrue(resposta.get_json()["ja_concluido"])
        self.assertEqual(2, len(chamadas))
        self.assertEqual(35, self.pontos() - antes)


class TestQuestaoComExplicacaoContraditoria(unittest.TestCase):
    # Explicação que o Gemini devolveu de verdade num teste: a conta não fecha com nenhuma alternativa.
    QUEBRADA = ("Igualando os juros: 2000 * 0,04 * t = 3000 * 0,02 * t. Isso implica 80t = 60t. Como o tempo deve ser "
                "igual para ambos, a igualdade ocorre apenas se t=0, porém, analisando a taxa de rendimento, o primeiro "
                "capital supera o segundo em juros após 6 meses. Reavaliando: J1 = 80t, J2 = 60t. Caso a questão peça o "
                "tempo para o montante ser igual: t = 50 meses. Ajustando para uma questão de comparação, t=6 meses.")

    def test_questao_que_a_propria_ia_desmente_e_descartada(self):
        with self.assertRaises(ValueError):
            GERADOR._validar_questoes([questao("Após quantos meses os juros serão iguais?", explicacao=self.QUEBRADA)], 1)
        for trecho in ("Nenhuma das alternativas está correta, mas a mais próxima é B.", "Recalculando, o valor é 12.",
                       "Há um erro no enunciado; considere 10%.", "Não há alternativa correta."):
            with self.subTest(trecho=trecho):
                with self.assertRaises(ValueError):
                    GERADOR._validar_questoes([questao("Pergunta", explicacao=trecho)], 1)

    def test_explicacao_normal_continua_aceita(self):
        for texto in ("J = C * i * t = 5000 * 0,015 * 8 = 600. O montante é 5600.",
                      "Ajustando a equação e isolando x, temos x = 8.",
                      "Avaliando as alternativas, só a B traz uma metáfora."):
            with self.subTest(texto=texto):
                self.assertEqual(1, len(GERADOR._validar_questoes([questao("Pergunta", explicacao=texto)], 1)))

    def test_a_reserva_repoe_a_questao_descartada(self):
        lote = [questao(f"Pergunta {n}") for n in range(1, 5)] + [questao("Quebrada", explicacao=self.QUEBRADA), questao("Reserva")]
        validas = GERADOR._validar_questoes(lote, 5)
        self.assertEqual(["Pergunta 1", "Pergunta 2", "Pergunta 3", "Pergunta 4", "Reserva"], [q["enunciado"] for q in validas])

    def test_quantidade_de_reserva(self):
        self.assertEqual([1, 2, 3, 4], [GERADOR.questoes_de_reserva(n) for n in (5, 10, 15, 20)])

    def test_o_pedido_manda_resolver_antes_e_pede_questoes_de_reserva(self):
        texto = GERADOR._montar_prompt("Matemática", "Juros", "Normal", 5)
        self.assertIn("resolva-a por completo", texto)
        self.assertIn("exatamente uma alternativa está correta", texto)
        corpos = []
        resposta = json.dumps({"candidates": [{"content": {"parts": [{"text": json.dumps(
            {"questoes": [questao(f"Pergunta {n}") for n in range(6)]})}]}}]}).encode()

        def urlopen(requisicao, **_kwargs):
            corpos.append(json.loads(requisicao.data))
            return io.BytesIO(resposta)

        ambiente = {"GEMINI_API_KEY": "chave-de-teste", "GEMINI_MODEL": "", "OPENAI_API_KEY": ""}
        GERADOR._pausas.clear()
        with mock.patch.dict(os.environ, ambiente), mock.patch.object(GERADOR.urllib.request, "urlopen", urlopen):
            questoes, origem = GERADOR.gerar_questoes("Matemática", "Juros", "Normal", 5)
        self.assertEqual(("ia", 5), (origem, len(questoes)))          # o aluno recebe as 5 que pediu
        self.assertIn("exatamente 6 questões", corpos[0]["contents"][0]["parts"][0]["text"])  # 5 + 1 de reserva


if __name__ == "__main__":
    unittest.main()
