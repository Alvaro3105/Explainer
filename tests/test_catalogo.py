"""Catálogo de matérias, temas e subtemas: importação, busca e uso na geração do desafio."""
import unittest
from unittest import mock

from sqlalchemy.exc import IntegrityError

from tests.test_api import BaseApi, app_module


def ids_de(lista):
    return [item["id_tema"] for item in lista]


class BaseCatalogo(BaseApi):

    def materia(self, nome):
        materias = self.client.get(f"/api/learning/catalog?q={nome}&limite=50").get_json()["materias"]
        return next(m for m in materias if m["nome"] == nome)

    def temas(self, nome_materia, busca="", **extras):
        materia = self.materia(nome_materia)
        parametros = "&".join([f"q={busca}"] + [f"{chave}={valor}" for chave, valor in extras.items()])
        resposta = self.client.get(f"/api/learning/catalog/{materia['id_materia']}/themes?{parametros}")
        self.assertEqual(200, resposta.status_code, resposta.get_data(as_text=True))
        return resposta.get_json()

    def nomes(self, nome_materia, busca, **extras):
        return [t["nome"] for t in self.temas(nome_materia, busca, **extras)["temas"]]


class TestImportacaoDoCatalogo(BaseCatalogo):

    def test_banco_tem_tudo_o_que_esta_nos_arquivos(self):
        from services.aprendizado.catalogo_service import CatalogoService, ler_catalogo, normalizar
        arquivos = ler_catalogo()
        with app_module.app.app_context():
            from models.model_materia import Materia
            from models.model_tema import Tema
            for materia in arquivos:
                registro = Materia.query.filter_by(nome_busca=normalizar(materia["nome"])).one()
                temas = Tema.query.filter_by(id_materia=registro.id_materia, id_tema_pai=None).all()
                nomes_temas = {t.nome for t in temas}
                for tema in materia["temas"]:
                    self.assertIn(tema["nome"], nomes_temas)
                    pai = next(t for t in temas if t.nome == tema["nome"])
                    filhos = {t.nome for t in Tema.query.filter_by(id_tema_pai=pai.id_tema)}
                    self.assertTrue({s["nome"] for s in tema["subtemas"]} <= filhos, tema["nome"])
            resumo = CatalogoService.resumo()
        self.assertGreaterEqual(resumo["materias"], len(arquivos))
        self.assertGreaterEqual(resumo["temas"], sum(len(m["temas"]) for m in arquivos))
        self.assertGreaterEqual(resumo["subtemas"], sum(len(t["subtemas"]) for m in arquivos for t in m["temas"]))

    def test_arquivos_nao_tem_nome_repetido_na_mesma_materia(self):
        from services.aprendizado.catalogo_service import ler_catalogo, normalizar
        for materia in ler_catalogo():
            nomes = [normalizar(item["nome"]) for tema in materia["temas"] for item in [tema] + tema["subtemas"]]
            repetidos = {nome for nome in nomes if nomes.count(nome) > 1}
            self.assertEqual(set(), repetidos, materia["nome"])

    def test_subtema_fica_na_mesma_materia_do_tema(self):
        with app_module.app.app_context():
            from models.model_tema import Tema
            subtemas = Tema.query.filter(Tema.id_tema_pai.isnot(None)).all()
            pais = {t.id_tema: t for t in Tema.query.filter(Tema.id_tema.in_({s.id_tema_pai for s in subtemas}))}
            for subtema in subtemas:
                pai = pais[subtema.id_tema_pai]
                self.assertEqual(pai.id_materia, subtema.id_materia, subtema.nome)
                self.assertIsNone(pai.id_tema_pai, "subtema de subtema")
                self.assertIn(pai.nome_busca, subtema.termos_busca)  # buscar o tema também acha os subtemas

    def test_importar_de_novo_nao_duplica_nem_apaga(self):
        from services.aprendizado.catalogo_service import CatalogoService
        self.registrar("reimportar@exemplo.com")
        desafio = self.criar_desafio()
        with app_module.app.app_context():
            from models.model_desafio import Desafio
            from models.model_tema import Tema
            antes = (Tema.query.count(), Desafio.query.count())
            resultado = CatalogoService().importar()
            self.assertEqual((0, 0), (resultado["materias_novas"], resultado["temas_novos"]))
            self.assertEqual(antes, (Tema.query.count(), Desafio.query.count()))
            self.assertIsNotNone(app_module.d.db.session.get(Desafio, desafio["desafio"]["id_desafio"]))

    def test_nome_repetido_na_mesma_materia_e_barrado_pelo_banco(self):
        with app_module.app.app_context():
            from models.model_tema import Tema
            existente = Tema.query.filter(Tema.id_materia.isnot(None)).first()
            app_module.d.db.session.add(Tema(materia=existente.materia, nome=existente.nome,
                                             id_materia=existente.id_materia, nome_busca=existente.nome_busca))
            with self.assertRaises(IntegrityError):
                app_module.d.db.session.commit()
            app_module.d.db.session.rollback()

    def test_temas_antigos_sao_ligados_sem_perder_o_id(self):
        from services.aprendizado.catalogo_service import CatalogoService
        with app_module.app.app_context():
            from models.model_materia import Materia
            from models.model_tema import Tema
            antigo = Tema(materia="Português", nome="Leitura de Bulas e Rótulos")
            sem_materia = Tema(materia="Robótica Educacional", nome="Sensores")
            app_module.d.db.session.add_all([antigo, sem_materia])
            app_module.d.db.session.commit()
            ids = (antigo.id_tema, sem_materia.id_tema)
            CatalogoService().importar()
            antigo, sem_materia = (app_module.d.db.session.get(Tema, i) for i in ids)
            portugues = Materia.query.filter_by(nome_busca="lingua portuguesa").one()
            self.assertEqual(portugues.id_materia, antigo.id_materia)
            self.assertEqual("Língua Portuguesa", antigo.materia)
            # Matéria fora do catálogo não é criada: o tema antigo continua no banco, fora da busca.
            self.assertIsNone(sem_materia.id_materia)
            self.assertIsNone(Materia.query.filter_by(nome_busca="robotica educacional").first())

    def test_materia_fora_do_catalogo_sai_da_busca_sem_apagar_historico(self):
        from services.aprendizado.catalogo_service import CatalogoService
        with app_module.app.app_context():
            from models.model_desafio import Desafio
            from models.model_materia import Materia
            from models.model_tema import Tema
            sessao = app_module.d.db.session
            antiga = Materia(nome="Programação", nome_busca="programacao")
            sessao.add(antiga)
            sessao.flush()
            com_historico = Tema(materia="Programação", nome="Python", id_materia=antiga.id_materia, nome_busca="python")
            sem_historico = Tema(materia="Programação", nome="Laços", id_materia=antiga.id_materia, nome_busca="lacos")
            sessao.add_all([com_historico, sem_historico])
            sessao.flush()
            subtema = Tema(materia="Programação", nome="For", id_materia=antiga.id_materia, nome_busca="for",
                           id_tema_pai=sem_historico.id_tema)
            sessao.add(subtema)
            sessao.flush()
            desafio = Desafio(nome="Desafio antigo", dificuldade="Normal", pontuacao=0, id_tema=com_historico.id_tema)
            sessao.add(desafio)
            sessao.commit()
            ids = (com_historico.id_tema, sem_historico.id_tema, subtema.id_tema, desafio.id_desafio)

            resumo = CatalogoService().importar()

            self.assertEqual((1, 2, 1), (resumo["materias_removidas"], resumo["temas_removidos"], resumo["temas_fora_da_busca"]))
            self.assertIsNone(Materia.query.filter_by(nome_busca="programacao").first())
            mantido = sessao.get(Tema, ids[0])
            self.assertIsNotNone(mantido)
            self.assertIsNone(mantido.id_materia)
            self.assertIsNone(sessao.get(Tema, ids[1]))
            self.assertIsNone(sessao.get(Tema, ids[2]))
            self.assertEqual(ids[0], sessao.get(Desafio, ids[3]).id_tema)
            # Na próxima vez nada muda.
            resumo = CatalogoService().importar()
            self.assertEqual((0, 0, 0), (resumo["materias_removidas"], resumo["temas_removidos"], resumo["temas_fora_da_busca"]))


class TestBuscaDeMaterias(BaseCatalogo):

    def test_lista_e_pesquisa(self):
        todas = self.client.get("/api/learning/catalog").get_json()["materias"]
        self.assertEqual(14, len(todas))
        self.assertTrue(all({"id_materia", "nome", "area", "quantidade_temas"} <= set(m) for m in todas))
        self.assertEqual("Matemática", self.client.get("/api/learning/catalog?q=mat").get_json()["materias"][0]["nome"])
        self.assertEqual("Língua Portuguesa", self.client.get("/api/learning/catalog?q=portugues").get_json()["materias"][0]["nome"])
        self.assertEqual("Física", self.client.get("/api/learning/catalog?q=fisica").get_json()["materias"][0]["nome"])
        for tecnica in ("programacao", "banco de dados", "inteligencia artificial", "desenvolvimento", "infraestrutura"):
            self.assertEqual([], self.client.get(f"/api/learning/catalog?q={tecnica}").get_json()["materias"], tecnica)
        self.assertEqual([], self.client.get("/api/learning/catalog?q=zzzz").get_json()["materias"])

    def test_sem_acento_e_sem_diferenca_de_maiusculas(self):
        for busca in ("FISICA", "física", "Fisica"):
            with self.subTest(busca=busca):
                self.assertEqual("Física", self.client.get(f"/api/learning/catalog?q={busca}").get_json()["materias"][0]["nome"])


class TestBuscaDeTemas(BaseCatalogo):

    def test_busca_exata_e_parcial(self):
        self.assertEqual("Matemática Financeira", self.nomes("Matemática", "Matemática Financeira")[0])
        self.assertIn("Equação do Primeiro Grau", self.nomes("Matemática", "equ"))
        self.assertIn("Equação do Segundo Grau", self.nomes("Matemática", "equ"))

    def test_sem_acento(self):
        self.assertEqual("Equação do Primeiro Grau", self.nomes("Matemática", "equacao primeiro grau")[0])
        self.assertIn("Teorema de Pitágoras", self.nomes("Matemática", "PITAGORAS"))

    def test_sinonimo_encontra_o_tema(self):
        temas = self.temas("Matemática", "bhaskara")["temas"]
        segundo_grau = next(t for t in temas if t["nome"] == "Equação do Segundo Grau")
        self.assertEqual("bhaskara", segundo_grau["termo_relacionado"])
        self.assertIn("Matemática Financeira", self.nomes("Matemática", "montante"))

    def test_ordem_de_relevancia(self):
        self.assertEqual("Matemática Financeira", self.nomes("Matemática", "fin")[0])
        resultado = self.temas("Matemática", "equ")["temas"]
        primeiros_subtemas = next(i for i, t in enumerate(resultado) if t["tipo"] == "subtema")
        self.assertTrue(all(t["tipo"] == "tema" for t in resultado[:primeiros_subtemas]))
        self.assertEqual("Matemática para o ENEM", self.nomes("Matemática", "enem")[0])

    def test_subtema_mostra_tema_e_materia(self):
        juros = next(t for t in self.temas("Matemática", "juros compostos")["temas"] if t["nome"] == "Juros Compostos")
        self.assertEqual("subtema", juros["tipo"])
        self.assertEqual("Matemática Financeira", juros["tema_pai"]["nome"])
        self.assertEqual("Matemática", juros["materia"])

    def test_so_aparecem_temas_da_materia_escolhida(self):
        biologia = self.materia("Biologia")
        resultado = self.temas("Biologia", "equ")["temas"]
        self.assertTrue(all(t["id_materia"] == biologia["id_materia"] for t in resultado))
        self.assertNotIn("Equação do Primeiro Grau", [t["nome"] for t in resultado])

    def test_resultado_vazio(self):
        resultado = self.temas("Matemática", "xyzwq")
        self.assertEqual([], resultado["temas"])
        self.assertFalse(resultado["tem_mais"])

    def test_limite_e_paginacao(self):
        tres = self.temas("Matemática", "", limite=3)
        self.assertEqual(3, len(tres["temas"]))
        self.assertTrue(tres["tem_mais"])
        self.assertLessEqual(len(self.temas("Matemática", "a", limite=999)["temas"]), 50)
        pagina1 = ids_de(self.temas("Matemática", "", limite=5, pagina=1)["temas"])
        pagina2 = ids_de(self.temas("Matemática", "", limite=5, pagina=2)["temas"])
        self.assertEqual(5, len(pagina2))
        self.assertFalse(set(pagina1) & set(pagina2))
        self.assertEqual(400, self.client.get(f"/api/learning/catalog/{self.materia('Matemática')['id_materia']}/themes?limite=x").status_code)

    def test_sem_busca_lista_so_temas_principais(self):
        resultado = self.temas("Matemática", "", limite=50)["temas"]
        self.assertTrue(all(t["tipo"] == "tema" for t in resultado))

    def test_subtemas_de_um_tema(self):
        financeira = next(t for t in self.temas("Matemática", "Matemática Financeira")["temas"] if t["nome"] == "Matemática Financeira")
        self.assertGreater(financeira["quantidade_subtemas"], 5)
        subtemas = self.client.get(f"/api/learning/catalog/themes/{financeira['id_tema']}/subtopics?limite=50").get_json()["temas"]
        self.assertEqual(financeira["quantidade_subtemas"], len(subtemas))
        self.assertTrue(all(s["tema_pai"]["id_tema"] == financeira["id_tema"] for s in subtemas))
        filtrados = self.client.get(f"/api/learning/catalog/themes/{financeira['id_tema']}/subtopics?q=jur").get_json()["temas"]
        self.assertEqual(["Juros Simples", "Juros Compostos"], [s["nome"] for s in filtrados][:2])
        juros = filtrados[0]["id_tema"]
        self.assertEqual(400, self.client.get(f"/api/learning/catalog/themes/{juros}/subtopics").status_code)
        self.assertEqual(404, self.client.get("/api/learning/catalog/999999/themes").status_code)
        self.assertEqual(404, self.client.get("/api/learning/catalog/themes/999999/subtopics").status_code)


class TestCatalogoNaGeracao(BaseCatalogo):

    QUESTOES = [{"enunciado": f"Questão {n} de juros compostos", "alternativas": {"A": "1", "B": "2", "C": "3", "D": "4"},
                 "alternativa_correta": "A", "explicacao": "Explicação."} for n in range(5)]

    def test_subtema_vai_para_a_ia_com_materia_e_tema(self):
        self.registrar("subtema@exemplo.com")
        juros = next(t for t in self.temas("Matemática", "juros compostos")["temas"] if t["nome"] == "Juros Compostos")
        with mock.patch("services.aprendizado.desafio_service.gerar_questoes", return_value=(self.QUESTOES, "ia")) as gerar:
            resposta = self.client.post("/api/learning/challenges", json={
                "id_tema": juros["id_tema"], "id_materia": juros["id_materia"], "quantidade_questoes": 5, "dificuldade": "normal"})
        self.assertEqual(201, resposta.status_code, resposta.get_data(as_text=True))
        argumentos, nomeados = gerar.call_args
        self.assertEqual(("Matemática", "Matemática Financeira"), argumentos[:2])
        self.assertEqual("Juros Compostos", nomeados["subtema"])
        dados = resposta.get_json()
        self.assertEqual(juros["id_tema"], dados["desafio"]["id_tema"])
        self.assertEqual("subtema", dados["tema"]["tipo"])

    def test_tema_principal_vai_sem_subtema(self):
        self.registrar("principal@exemplo.com")
        financeira = next(t for t in self.temas("Matemática", "Matemática Financeira")["temas"] if t["nome"] == "Matemática Financeira")
        with mock.patch("services.aprendizado.desafio_service.gerar_questoes", return_value=(self.QUESTOES, "ia")) as gerar:
            self.client.post("/api/learning/challenges", json={"id_tema": financeira["id_tema"], "quantidade_questoes": 5})
        self.assertEqual(("Matemática", "Matemática Financeira"), gerar.call_args[0][:2])
        self.assertIsNone(gerar.call_args[1]["subtema"])

    def test_tema_de_outra_materia_e_recusado(self):
        self.registrar("outra@exemplo.com")
        juros = next(t for t in self.temas("Matemática", "juros compostos")["temas"] if t["nome"] == "Juros Compostos")
        biologia = self.materia("Biologia")
        with mock.patch("services.aprendizado.desafio_service.gerar_questoes", return_value=(self.QUESTOES, "ia")) as gerar:
            resposta = self.client.post("/api/learning/challenges", json={
                "id_tema": juros["id_tema"], "id_materia": biologia["id_materia"], "quantidade_questoes": 5})
        self.assertEqual(400, resposta.status_code)
        gerar.assert_not_called()

    def test_sem_ia_e_sem_banco_local_o_aluno_e_avisado(self):
        self.registrar("semia@exemplo.com")
        juros = next(t for t in self.temas("Matemática", "juros compostos")["temas"] if t["nome"] == "Juros Compostos")
        resposta = self.client.post("/api/learning/challenges", json={"id_tema": juros["id_tema"], "quantidade_questoes": 5})
        self.assertEqual(502, resposta.status_code)
        self.assertIn("Não foi possível gerar", resposta.get_json()["erro"])

    def test_pedido_para_a_ia_leva_materia_tema_e_subtema(self):
        from services.aprendizado.gerador_questoes import _montar_prompt
        texto = _montar_prompt("Matemática", "Matemática Financeira", "Normal", 10, subtema="Juros Compostos")
        for trecho in ("Matéria: Matemática", "Tema: Matemática Financeira", "Subtema: Juros Compostos",
                       "Dificuldade: Médio", "Ensino Médio", "português brasileiro", "exatamente 10 questões"):
            self.assertIn(trecho, texto)


class TestCatalogoNoPainel(BaseCatalogo):

    def test_tema_criado_pelo_painel_entra_na_busca(self):
        from services.tema.criar_tema import CriarTemaService
        with app_module.app.app_context():
            CriarTemaService().executar({"materia": "Matemática", "nome": "Frações Contínuas"})
            with self.assertRaises(ValueError):
                CriarTemaService().executar({"materia": "Matemática", "nome": "FRAÇÕES contínuas"})
        self.assertIn("Frações Contínuas", self.nomes("Matemática", "continuas"))

    def test_painel_nao_cria_materia_fora_do_catalogo(self):
        from services.tema.criar_tema import CriarTemaService
        with app_module.app.app_context():
            with self.assertRaisesRegex(ValueError, "fora do catálogo"):
                CriarTemaService().executar({"materia": "Programação", "nome": "Python"})
        self.assertEqual([], self.client.get("/api/learning/catalog?q=programacao").get_json()["materias"])


class TestEntradasForaDoLimite(BaseCatalogo):
    """Números gigantes e "Infinity" são erro de quem enviou (400 ou 404), nunca erro 500."""

    GIGANTE = 10 ** 30

    def test_pagina_e_ids_gigantes_na_busca(self):
        materia = self.materia("Matemática")["id_materia"]
        resposta = self.client.get(f"/api/learning/catalog/{materia}/themes?q=a&pagina={self.GIGANTE}")
        self.assertEqual((200, []), (resposta.status_code, resposta.get_json()["temas"]))
        self.assertEqual(200, self.client.get(f"/api/learning/catalog?pagina={self.GIGANTE}").status_code)
        for rota in (f"/api/learning/catalog/{self.GIGANTE}/themes", f"/api/learning/catalog/themes/{self.GIGANTE}/subtopics"):
            self.assertIn(self.client.get(rota).status_code, (400, 404), rota)

    def test_numeros_gigantes_ou_infinitos_no_desafio(self):
        self.registrar("limites@example.com")
        desafio = self.criar_desafio()
        id_desafio = desafio["desafio"]["id_desafio"]
        id_questao = desafio["questoes"][0]["id_questao"]
        pedidos = [
            ("get", f"/api/learning/challenges/{self.GIGANTE}", None),
            ("post", f"/api/learning/challenges/{self.GIGANTE}/complete", None),
            ("post", "/api/learning/challenges", '{"id_tema": %d, "quantidade_questoes": 5}' % self.GIGANTE),
            ("post", "/api/learning/challenges", '{"id_tema": 1, "quantidade_questoes": 5, "fase_jornada": Infinity}'),
            ("post", "/api/learning/challenges", '{"refazer": true, "refazer_de": %d}' % self.GIGANTE),
            ("post", f"/api/learning/challenges/{id_desafio}/answer", '{"id_questao": Infinity, "alternativa": "A"}'),
            ("post", f"/api/learning/challenges/{id_desafio}/answer",
             '{"id_questao": %d, "alternativa": "A", "segundos_gastos": Infinity}' % id_questao),
            ("post", "/api/learning/activity", '{"segundos": Infinity}'),
        ]
        for metodo, rota, corpo in pedidos:
            resposta = getattr(self.client, metodo)(rota, data=corpo, content_type="application/json")
            self.assertIn(resposta.status_code, (400, 404), f"{rota} {corpo}: {resposta.status_code}")
            self.assertIn("erro", resposta.get_json())
        # Depois dos pedidos recusados, a conta continua funcionando.
        self.assertEqual(200, self.client.get("/api/learning/me").status_code)

    def test_tema_sem_materia_nao_gera_desafio_novo(self):
        self.registrar("fora-do-catalogo@example.com")
        with app_module.app.app_context():
            from models.model_tema import Tema
            antigo = Tema(materia="Programação", nome="Tema Guardado Só no Histórico")
            app_module.d.db.session.add(antigo)
            app_module.d.db.session.commit()
            id_tema = antigo.id_tema
        resposta = self.client.post("/api/learning/challenges", json={"id_tema": id_tema, "quantidade_questoes": 5})
        self.assertEqual(404, resposta.status_code)
        self.assertIn("não está mais disponível", resposta.get_json()["erro"])


class TestSemPaginaDaApi(BaseCatalogo):

    def test_nao_existe_pagina_com_a_lista_de_rotas(self):
        self.assertEqual(404, self.client.get("/api").status_code)
        pagina = self.client.get("/").get_data(as_text=True)
        self.assertNotIn('href="/api"', pagina)


class TestLeituraDoEnv(unittest.TestCase):
    """Sem o python-dotenv (Python fora do .venv), o app ainda precisa ler a chave da IA do .env."""

    def test_le_o_env_sem_python_dotenv(self):
        import os
        import sys
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta, ".env")
            arquivo.write_bytes("﻿# comentário\r\nTESTE_ENV_CHAVE=valor-123\r\nTESTE_ENV_ASPAS=\"com espaço\"\r\n"
                                "TESTE_ENV_JA_EXISTE=do-arquivo\r\nTESTE_ENV_COMENTARIO=abc # nota\r\n".encode("utf-8"))
            nomes = ("TESTE_ENV_CHAVE", "TESTE_ENV_ASPAS", "TESTE_ENV_JA_EXISTE", "TESTE_ENV_COMENTARIO")
            with mock.patch.dict(os.environ, {"TESTE_ENV_JA_EXISTE": "do-sistema"}), \
                    mock.patch.dict(sys.modules, {"dotenv": None}):
                app_module.carregar_env(arquivo)
                self.assertEqual(("valor-123", "com espaço", "do-sistema", "abc"),
                                 tuple(os.environ[nome] for nome in nomes))


if __name__ == "__main__":
    unittest.main()
