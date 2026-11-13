"""Comportamentos de plataforma: limite de geração gravado no banco, troca de desafio,
índices, limite de cadastros, troca e redefinição de senha, rota de saúde, erros em JSON,
conferência numérica do gabarito e questões de reserva.

Nenhum teste chama a IA de verdade.
"""
import io
import json
import os
import time
import unittest
from unittest import mock

from sqlalchemy import inspect

from tests.test_api import BaseApi, app_module, tema_com_banco_local
from tests.test_protecoes import limites, questao, zerar_pedidos

import services.aprendizado.conta_service as CONTA
import services.aprendizado.gerador_questoes as GERADOR
import services.aprendizado.limite_geracao as LIMITE
from models.model_geracao import GeracaoDesafio

SENHA = "senha-segura-123"
banco = app_module.d.db


def pedir(cliente, **extra):
    corpo = {"id_tema": tema_com_banco_local(cliente), "quantidade_questoes": 5, "dificuldade": "normal", **extra}
    return cliente.post("/api/learning/challenges", json=corpo)


class TestLimiteGravadoNoBanco(BaseApi):
    def setUp(self):
        super().setUp()
        zerar_pedidos()
        self.addCleanup(zerar_pedidos)

    def pedidos(self, id_aluno):
        with app_module.app.app_context():
            return [(p.em_andamento, p.iniciada_em) for p in GeracaoDesafio.query.filter_by(id_aluno=id_aluno).all()]

    def test_cada_geracao_fica_registrada_e_o_limite_vem_do_banco(self):
        aluno = self.registrar("persistente@exemplo.com")
        with limites(INTERVALO_ENTRE_GERACOES=30):
            self.assertEqual(201, pedir(self.client).status_code)
            registros = self.pedidos(aluno["id_aluno"])
            self.assertEqual(1, len(registros))
            self.assertFalse(registros[0][0])  # terminou: não está mais "em andamento"
            # Nada do limite fica na memória do processo: um servidor recém-iniciado
            # (ou outro processo) lê os mesmos registros e recusa do mesmo jeito.
            self.assertFalse(hasattr(LIMITE, "_recentes"))
            self.assertEqual(429, pedir(self.client).status_code)

    def test_pedido_de_outro_processo_em_andamento_bloqueia_e_o_abandonado_nao(self):
        aluno = self.registrar("outro-processo@exemplo.com")
        with app_module.app.app_context():
            banco.session.add(GeracaoDesafio(id_aluno=aluno["id_aluno"], iniciada_em=time.time() - 5, em_andamento=True))
            banco.session.commit()
        with limites():
            recusado = pedir(self.client)
            self.assertEqual(429, recusado.status_code)
            self.assertIn("já está sendo preparado", recusado.get_json()["erro"])
            # O servidor caiu no meio de uma geração antiga: o registro ficou "em andamento" para sempre.
            with app_module.app.app_context():
                GeracaoDesafio.query.filter_by(id_aluno=aluno["id_aluno"]).update(
                    {"iniciada_em": time.time() - LIMITE.VALIDADE_EM_ANDAMENTO - 60})
                banco.session.commit()
            self.assertEqual(201, pedir(self.client).status_code)

    def test_registros_antigos_sao_limpos(self):
        aluno = self.registrar("limpeza@exemplo.com")
        with app_module.app.app_context():
            banco.session.add(GeracaoDesafio(id_aluno=aluno["id_aluno"], em_andamento=False,
                                             iniciada_em=time.time() - LIMITE.GUARDAR_REGISTROS_POR - 60))
            banco.session.commit()
        with limites():
            self.assertEqual(201, pedir(self.client).status_code)
        self.assertEqual(1, len(self.pedidos(aluno["id_aluno"])))

    def test_excluir_a_conta_apaga_os_registros_de_geracao(self):
        aluno = self.registrar("excluir-geracoes@exemplo.com")
        with limites():
            self.assertEqual(201, pedir(self.client).status_code)
        resposta = self.client.delete("/api/auth/delete-account", json={"senha": SENHA})
        self.assertEqual(200, resposta.status_code, resposta.get_data(as_text=True))
        self.assertEqual([], self.pedidos(aluno["id_aluno"]))


class TestTrocaDeDesafio(BaseApi):
    def ativo(self):
        return self.client.get("/api/learning/active-challenge").get_json()

    def test_falha_da_ia_nao_apaga_o_desafio_em_andamento(self):
        self.registrar("preserva@exemplo.com")
        primeiro = self.criar_desafio()["desafio"]["id_desafio"]
        with mock.patch("services.aprendizado.desafio_service.gerar_questoes", side_effect=RuntimeError("fora do ar")):
            self.assertEqual(502, pedir(self.client).status_code)
        self.assertEqual(primeiro, self.ativo()["desafio"]["id_desafio"])
        self.assertEqual(5, len(self.ativo()["questoes"]))

    def test_com_sucesso_o_desafio_sem_respostas_e_trocado_pelo_novo(self):
        aluno = self.registrar("troca-desafio2@exemplo.com")
        self.criar_desafio()
        segundo = self.criar_desafio(quantidade_questoes=10)
        ativo = self.ativo()
        self.assertEqual(segundo["desafio"]["id_desafio"], ativo["desafio"]["id_desafio"])
        self.assertEqual(10, len(ativo["questoes"]))
        # O primeiro, que não tinha respostas, saiu: sobra um desafio só, sem questões órfãs.
        from models.model_desafio import Desafio
        from models.model_questao import Questao
        with app_module.app.app_context():
            self.assertEqual(1, Desafio.query.filter_by(id_aluno=aluno["id_aluno"]).count())
            ids = {q["id_questao"] for q in ativo["questoes"]}
            self.assertEqual(10, Questao.query.filter(Questao.id_questao.in_(ids)).count())

    def test_a_leitura_do_banco_e_encerrada_antes_de_chamar_a_ia(self):
        """Durante a espera pela IA não pode haver transação aberta, senão o SQLite segura os outros alunos."""
        self.registrar("solta@exemplo.com")
        self.criar_desafio()
        vistos = []
        real = GERADOR.gerar_questoes

        def observar(*args, **kwargs):
            vistos.append(banco.session().in_transaction())
            return real(*args, **kwargs)

        with mock.patch("services.aprendizado.desafio_service.gerar_questoes", side_effect=observar):
            self.assertEqual(201, pedir(self.client).status_code)
        self.assertEqual([False], vistos)


class TestIndices(unittest.TestCase):
    def nomes(self, tabela):
        with app_module.app.app_context():
            inspetor = inspect(banco.engine)
            return ({i["name"] for i in inspetor.get_indexes(tabela)}
                    | {r["name"] for r in inspetor.get_unique_constraints(tabela)})

    def test_todos_os_indices_existem(self):
        for tabela, nome, _tipo, _colunas in app_module.INDICES:
            with self.subTest(indice=nome):
                self.assertIn(nome, self.nomes(tabela))
        self.assertIn("ix_geracao_aluno_momento", self.nomes("geracao_desafio"))

    def test_banco_antigo_ganha_os_indices_ao_iniciar_sem_perder_dados(self):
        with app_module.app.app_context():
            antes = banco.session.execute(banco.text('SELECT COUNT(*) FROM "Tema"')).scalar()
            with banco.engine.begin() as conexao:
                conexao.exec_driver_sql('DROP INDEX "ix_desafio_aluno_tema"')
                conexao.exec_driver_sql('DROP INDEX "ix_desafio_questao_id_questao"')
        self.assertNotIn("ix_desafio_aluno_tema", self.nomes("desafio"))
        with app_module.app.app_context():
            app_module._criar_indices()
            app_module._criar_indices()  # rodar de novo não dá erro
            depois = banco.session.execute(banco.text('SELECT COUNT(*) FROM "Tema"')).scalar()
        self.assertIn("ix_desafio_aluno_tema", self.nomes("desafio"))
        self.assertIn("ix_desafio_questao_id_questao", self.nomes("desafio_questao"))
        self.assertEqual(antes, depois)


class TestLimiteDeCadastros(BaseApi):
    def setUp(self):
        super().setUp()
        CONTA._cadastros_por_ip.clear()
        self.addCleanup(CONTA._cadastros_por_ip.clear)

    def cadastrar(self, email, **extra):
        cliente = app_module.app.test_client()
        return cliente.post("/api/auth/register", json={"nome": "Aluno", "nick": "Aluno", "email": email, "senha": SENHA,
                                                        "aceite_termos": True, **extra})

    def test_muitas_contas_da_mesma_rede_sao_barradas(self):
        with mock.patch.dict(os.environ, {"CADASTROS_POR_HORA_POR_IP": "3"}):
            codigos = [self.cadastrar(f"lote{n}@exemplo.com").status_code for n in range(5)]
            barrado = self.cadastrar("lote9@exemplo.com")
        self.assertEqual([201, 201, 201, 429, 429], codigos)
        self.assertIn("Retry-After", barrado.headers)
        self.assertIn("Muitas contas", barrado.get_json()["erro"])

    def test_tentativas_invalidas_nao_gastam_o_limite(self):
        with mock.patch.dict(os.environ, {"CADASTROS_POR_HORA_POR_IP": "2"}):
            self.assertEqual(201, self.cadastrar("valida1@exemplo.com").status_code)
            self.assertEqual(409, self.cadastrar("valida1@exemplo.com").status_code)       # e-mail repetido
            self.assertEqual(400, self.cadastrar("curta@exemplo.com", senha="123").status_code)
            self.assertEqual(400, self.cadastrar("sem-arroba").status_code)
            self.assertEqual(201, self.cadastrar("valida2@exemplo.com").status_code)
            self.assertEqual(429, self.cadastrar("valida3@exemplo.com").status_code)

    def test_o_padrao_comporta_uma_escola_inteira(self):
        ambiente = {k: v for k, v in os.environ.items() if k != "CADASTROS_POR_HORA_POR_IP"}
        with mock.patch.dict(os.environ, ambiente, clear=True):
            self.assertEqual(100, CONTA._limite_de_cadastros())
        with mock.patch.dict(os.environ, {"CADASTROS_POR_HORA_POR_IP": "muitos"}):
            self.assertEqual(100, CONTA._limite_de_cadastros())


class TestSenha(BaseApi):
    def setUp(self):
        super().setUp()
        CONTA._falhas_login.clear()
        self.addCleanup(CONTA._falhas_login.clear)

    def trocar(self, atual, nova, cliente=None):
        return (cliente or self.client).post("/api/auth/change-password", json={"senha_atual": atual, "senha_nova": nova})

    def entrar(self, email, senha):
        return app_module.app.test_client().post("/api/auth/login", json={"email": email, "senha": senha}).status_code

    def test_trocar_a_senha(self):
        self.registrar("troca-senha@exemplo.com")
        self.assertEqual(403, self.trocar("errada", "nova-senha-456").status_code)
        self.assertEqual(400, self.trocar(SENHA, "curta").status_code)
        self.assertEqual(400, self.trocar(SENHA, SENHA).status_code)
        self.assertEqual(400, self.trocar(SENHA, "x" * 201).status_code)
        self.assertEqual(200, self.entrar("troca-senha@exemplo.com", SENHA))  # nada mudou até aqui
        resposta = self.trocar(SENHA, "nova-senha-456")
        self.assertEqual(200, resposta.status_code)
        self.assertEqual({"ok": True}, resposta.get_json())
        self.assertEqual(401, self.entrar("troca-senha@exemplo.com", SENHA))
        self.assertEqual(200, self.entrar("troca-senha@exemplo.com", "nova-senha-456"))
        with app_module.app.app_context():
            from repositories.aluno_repositories import AlunoRepository
            gravada = AlunoRepository.buscar_por_email("troca-senha@exemplo.com").senha
        self.assertNotIn("nova-senha-456", gravada)  # só o hash vai para o banco

    def test_trocar_a_senha_exige_login(self):
        self.assertEqual(401, self.trocar(SENHA, "nova-senha-456", app_module.app.test_client()).status_code)

    def test_senha_atual_errada_varias_vezes_bloqueia(self):
        self.registrar("chute-senha@exemplo.com")
        codigos = [self.trocar("errada", "nova-senha-456").status_code for _ in range(CONTA.LIMITE_FALHAS_LOGIN + 1)]
        self.assertEqual([403] * CONTA.LIMITE_FALHAS_LOGIN + [429], codigos)
        self.assertEqual(429, self.trocar(SENHA, "nova-senha-456").status_code)

    def test_script_da_equipe_redefine_a_senha(self):
        from scripts.redefinir_senha import redefinir
        self.registrar("esqueci@exemplo.com")
        self.assertIsNone(redefinir("ninguem@exemplo.com"))
        provisoria = redefinir("  Esqueci@Exemplo.com ")
        self.assertTrue(len(provisoria) >= 10)
        self.assertEqual(401, self.entrar("esqueci@exemplo.com", SENHA))
        self.assertEqual(200, self.entrar("esqueci@exemplo.com", provisoria))


class TestSaudeEErrosEmJson(BaseApi):
    def test_rota_de_saude(self):
        resposta = self.client.get("/api/saude")
        self.assertEqual(200, resposta.status_code)
        self.assertEqual({"status": "ok", "banco": "ok"}, resposta.get_json())

    def test_saude_avisa_quando_o_banco_nao_responde(self):
        with mock.patch.object(banco.session, "execute", side_effect=RuntimeError("banco fora do ar")):
            resposta = self.client.get("/api/saude")
        self.assertEqual(503, resposta.status_code)
        self.assertEqual("erro", resposta.get_json()["status"])
        self.assertNotIn("fora do ar", resposta.get_data(as_text=True))

    def test_erros_da_api_vem_em_json(self):
        nao_existe = self.client.get("/api/nao-existe")
        self.assertEqual((404, True), (nao_existe.status_code, "erro" in (nao_existe.get_json() or {})))
        metodo = self.client.delete("/api/learning/ranking")
        self.assertEqual((405, True), (metodo.status_code, "erro" in (metodo.get_json() or {})))
        pagina = self.client.get("/pagina-que-nao-existe")
        self.assertEqual(404, pagina.status_code)
        self.assertIn("text/html", pagina.content_type)

    def test_erro_interno_nao_mostra_detalhes(self):
        self.registrar("erro-interno@exemplo.com")
        with mock.patch("services.aprendizado.progresso_service.ProgressoService.historico",
                        side_effect=Exception("detalhe interno secreto")), self.assertLogs("app", level="ERROR"):
            resposta = self.client.get("/api/learning/history")
        self.assertEqual(500, resposta.status_code)
        self.assertIn("erro", resposta.get_json())
        self.assertNotIn("detalhe interno secreto", resposta.get_data(as_text=True))


class TestConferenciaNumericaDoGabarito(unittest.TestCase):
    VALORES = ("R$ 5.600,00", "R$ 5.750,00", "R$ 5.900,00", "R$ 6.200,00")

    def aceita(self, item):
        try:
            return len(GERADOR._validar_questoes([item], 1)) == 1
        except ValueError:
            return False

    def test_letra_do_gabarito_trocada_e_recusada(self):
        explicacao = "J = 5000 * 0,015 * 8 = 600. O montante é M = 5000 + 600 = 5600."
        self.assertTrue(self.aceita(questao("Qual o montante?", self.VALORES, "A", explicacao)))
        self.assertFalse(self.aceita(questao("Qual o montante?", self.VALORES, "C", explicacao)))

    def test_porcentagem_e_decimal_sao_o_mesmo_valor(self):
        taxas = ("30%", "36%", "42%", "48%")
        self.assertTrue(self.aceita(questao("Qual a taxa anual?", taxas, "B", "i = 0,03 ao mês; em 12 meses, 0,03 * 12 = 0,36.")))
        self.assertFalse(self.aceita(questao("Qual a taxa anual?", taxas, "A", "i = 0,03 ao mês; em 12 meses, 0,03 * 12 = 0,36.")))

    def test_nao_opina_quando_nao_ha_certeza(self):
        casos = [
            questao("Figura de linguagem?", ("Metáfora", "Ironia", "Hipérbole", "Eufemismo"), "A", "É uma comparação implícita."),
            questao("Em que ano?", ("1500", "1492", "1532", "1822"), "A", "A frota chegou em abril; Colombo chegou à América em 1492."),
            questao("Qual o intervalo?", ("de 2 a 4", "de 3 a 5", "de 4 a 6", "de 5 a 7"), "A", "O resultado fica entre 3 e 5."),
            questao("Quanto tempo?", ("90 minutos", "60 minutos", "45 minutos", "30 minutos"), "A", "São 1,5 hora de viagem."),
            questao("Qual o valor?", ("10", "20", "30", "40"), "B", "Basta aplicar a regra de três."),
            questao("Qual o valor?", ("10", "20", "30", "40"), "B", "x = 40 / 2, portanto x = 20."),
        ]
        for indice, caso in enumerate(casos):
            with self.subTest(caso=indice):
                self.assertTrue(self.aceita(caso))

    def test_leitura_de_numeros_no_formato_brasileiro(self):
        self.assertEqual([1200.5, 0.015, 8.0, 5600.0], GERADOR._numeros("R$ 1.200,50 a 0,015 por 8 meses dá 5600."))
        self.assertEqual([2.5], GERADOR._numeros("2,5%"))


class TestQuestoesDeReserva(unittest.TestCase):
    QUEBRADA = questao("Quebrada", explicacao="Reavaliando, nenhuma das alternativas serve.")

    def lote(self, boas, ruins):
        return [questao(f"Pergunta {n}") for n in range(boas)] + [self.QUEBRADA] * ruins

    def test_pediu_5_e_uma_foi_rejeitada(self):
        self.assertEqual(5, len(GERADOR._validar_questoes(self.lote(5, 1), 5)))

    def test_pediu_10_e_varias_foram_rejeitadas(self):
        self.assertEqual(10, len(GERADOR._validar_questoes(self.lote(10, 2), 10)))
        with self.assertRaises(ValueError):
            GERADOR._validar_questoes(self.lote(9, 3), 10)

    def test_pediu_20_e_o_lote_nao_tem_boas_suficientes(self):
        with self.assertRaises(ValueError):
            GERADOR._validar_questoes(self.lote(19, 5), 20)

    def test_nunca_entrega_questao_invalida_para_completar(self):
        validas = GERADOR._validar_questoes([self.QUEBRADA] + self.lote(5, 0) + [self.QUEBRADA], 5)
        self.assertNotIn("Quebrada", [q["enunciado"] for q in validas])

    def test_lote_insuficiente_vira_aviso_sem_tentar_sem_parar(self):
        """Todas as reservas inválidas: o aluno é avisado e o servidor não fica chamando a IA em laço."""
        corpo = json.dumps({"candidates": [{"content": {"parts": [{"text": json.dumps(
            {"questoes": self.lote(3, 3)})}]}}]}).encode()
        chamadas = []

        def urlopen(requisicao, **_kwargs):
            chamadas.append(requisicao.full_url)
            return io.BytesIO(corpo)

        ambiente = {"GEMINI_API_KEY": "chave-de-teste", "GEMINI_MODEL": "", "OPENAI_API_KEY": ""}
        GERADOR._pausas.clear()
        with mock.patch.dict(os.environ, ambiente), mock.patch.object(GERADOR.urllib.request, "urlopen", urlopen):
            with self.assertRaises(GERADOR.ErroDeGeracao) as contexto:
                GERADOR.gerar_questoes("Matemática", "Juros", "Normal", 5)
        self.assertEqual(GERADOR.MENSAGEM_RESPOSTA, str(contexto.exception))
        self.assertEqual(GERADOR.TENTATIVAS_IA, len(chamadas))


if __name__ == "__main__":
    unittest.main()
