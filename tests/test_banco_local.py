import importlib.util
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["OPENAI_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["GEMINI_MODEL"] = ""
_SPEC = importlib.util.spec_from_file_location("gerador_questoes", ROOT / "backend" / "services" / "aprendizado" / "gerador_questoes.py")
GERADOR = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(GERADOR)


def catalogo():
    """Pares (matéria, tema principal, subtema ou None) de todo o catálogo em backend/database/catalogo/."""
    from services.aprendizado.catalogo_service import ler_catalogo
    for materia in ler_catalogo():
        for tema in materia["temas"]:
            yield materia["nome"], tema["nome"], None
            for subtema in tema["subtemas"]:
                yield materia["nome"], tema["nome"], subtema["nome"]


class TestBancoLocal(unittest.TestCase):
    def test_sem_ia_cada_tema_recebe_so_questoes_do_proprio_assunto(self):
        com_banco, problemas = set(), []
        for materia, tema, subtema in catalogo():
            nome = subtema or tema
            banco = GERADOR._banco_do_tema(nome)
            if banco is None:
                try:
                    GERADOR.gerar_questoes(materia, tema, "Normal", 5, subtema=subtema)
                    problemas.append(f"{materia} > {nome}: gerou questões sem banco local e sem IA")
                except RuntimeError:
                    pass
                continue
            com_banco.add(nome)
            questoes, origem = GERADOR.gerar_questoes(materia, tema, "Normal", 20, subtema=subtema)
            if origem != "banco_local" or len({q["enunciado"] for q in questoes}) != 20:
                problemas.append(f"{materia} > {nome}: banco local errado ou com enunciados repetidos")
            if not {q["enunciado"] for q in questoes} <= {q[0] for q in banco}:
                problemas.append(f"{materia} > {nome}: questão de fora do banco do tema")
        self.assertEqual([], problemas)
        # Só os temas com banco próprio funcionam sem IA; um nome parecido não pega questões de outro assunto.
        self.assertEqual({"Corpo Humano", "Sistema Solar", "Equação do Primeiro Grau", "Figuras de Linguagem",
                          "Brasil Colônia"}, com_banco)

    def test_falha_da_ia_vira_mensagem_amigavel(self):
        original = GERADOR._gerar_com_openai

        def ia_fora_do_ar(*_args, **_kwargs):
            raise RuntimeError("Falha ao gerar questões pela IA: HTTP Error 401")

        GERADOR._gerar_com_openai = ia_fora_do_ar
        try:
            with self.assertRaises(RuntimeError) as contexto:
                GERADOR.gerar_questoes("História", "Revolução Industrial", "Normal", 5)
            self.assertEqual(GERADOR.MENSAGEM_INDISPONIVEL, str(contexto.exception))
            questoes, origem = GERADOR.gerar_questoes("Ciências", "Sistema solar", "Normal", 5)
            self.assertEqual(("banco_local", 5), (origem, len(questoes)))
        finally:
            GERADOR._gerar_com_openai = original

    def test_questoes_dos_bancos_estao_bem_formadas(self):
        bancos = GERADOR.BANCO_TEMATICO
        for nome, questoes in bancos.items():
            with self.subTest(banco=nome):
                self.assertGreaterEqual(len(questoes), 20, "o desafio maior tem 20 questões")
                self.assertEqual(len(questoes), len({q[0] for q in questoes}), "enunciado repetido no banco")
                for enunciado, opcoes, correta, explicacao in questoes:
                    self.assertEqual(4, len(opcoes), enunciado)
                    self.assertEqual(4, len(set(opcoes)), f"alternativas repetidas: {enunciado}")
                    self.assertIn(correta, GERADOR.LETRAS, enunciado)
                    self.assertTrue(enunciado.strip() and explicacao.strip(), enunciado)

    def test_alternativa_correta_acompanha_o_embaralhamento(self):
        respostas = {q[0]: q[1][GERADOR.LETRAS.index(q[2])] for q in GERADOR.BANCO_TEMATICO["sistema solar"]}
        for _ in range(5):
            for questao in GERADOR.gerar_questoes("Ciências", "Sistema solar", "Normal", 20)[0]:
                self.assertEqual(respostas[questao["enunciado"]], questao["alternativas"][questao["alternativa_correta"]])

    def test_segundo_grau_nao_recebe_questoes_de_primeiro_grau(self):
        primeiro_grau = {q[0] for q in GERADOR.BANCO_TEMATICO["do 1º grau"]}
        try:
            questoes = GERADOR.gerar_questoes("Matemática", "Equações do 2º grau", "Normal", 5)[0]
        except RuntimeError:
            return
        self.assertFalse(primeiro_grau & {q["enunciado"] for q in questoes})

    def test_tema_sem_banco_continua_recusando_assunto_errado(self):
        with self.assertRaises(RuntimeError):
            GERADOR.gerar_questoes("Ciências", "Astronomia avançada", "Normal", 10)

    def test_ia_tenta_de_novo_quando_a_primeira_chamada_falha(self):
        import io
        import json
        from unittest import mock

        questoes = [{"enunciado": f"Pergunta {n}", "alternativas": {"A": "1", "B": "2", "C": "3", "D": "4"},
                     "alternativa_correta": "B", "explicacao": "Porque sim."} for n in range(5)]
        corpo = json.dumps({"choices": [{"message": {"content": json.dumps({"questoes": questoes})}}]}).encode()
        respostas = [OSError("conexão caiu"), io.BytesIO(corpo)]

        def falsa_urlopen(*_args, **_kwargs):
            resposta = respostas.pop(0)
            if isinstance(resposta, Exception):
                raise resposta
            return resposta

        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "chave-de-teste"}), \
                mock.patch.object(GERADOR.urllib.request, "urlopen", falsa_urlopen):
            geradas, origem = GERADOR.gerar_questoes("História", "Revolução Industrial", "Difícil", 5)
        self.assertEqual("ia", origem)
        self.assertEqual(["B"] * 5, [q["alternativa_correta"] for q in geradas])

    def test_gemini_troca_de_modelo_quando_o_primeiro_falha(self):
        import io
        import json
        from unittest import mock

        questoes = [{"enunciado": f"Pergunta {n}", "alternativas": {"A": "1", "B": "2", "C": "3", "D": "4"},
                     "alternativa_correta": "C", "explicacao": "Porque sim."} for n in range(5)]
        corpo = json.dumps({"candidates": [{"content": {"parts": [{"text": json.dumps({"questoes": questoes})}]}}]}).encode()
        chamadas = []

        def falsa_urlopen(requisicao, **_kwargs):
            chamadas.append((requisicao.full_url, requisicao.get_header("X-goog-api-key")))
            if len(chamadas) == 1:
                raise OSError("modelo indisponível")
            return io.BytesIO(corpo)

        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "chave-gemini", "GEMINI_MODEL": "", "OPENAI_API_KEY": ""}), \
                mock.patch.object(GERADOR.urllib.request, "urlopen", falsa_urlopen):
            geradas, origem = GERADOR.gerar_questoes("História", "Revolução Industrial", "Normal", 5)
        self.assertEqual("ia", origem)
        self.assertEqual(["C"] * 5, [q["alternativa_correta"] for q in geradas])
        self.assertEqual(2, len(chamadas))
        self.assertIn("gemini-flash-latest:generateContent", chamadas[0][0])
        self.assertNotEqual(chamadas[0][0], chamadas[1][0])
        self.assertEqual("chave-gemini", chamadas[1][1])

    def test_sem_chave_o_gemini_nao_e_chamado(self):
        from unittest import mock
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            self.assertIsNone(GERADOR._gerar_com_gemini("História", "Revolução Industrial", "Normal", 5))

    def test_resposta_da_ia_fora_do_formato_e_recusada(self):
        for resposta in (["texto solto"], [None], [{"enunciado": "Sem alternativas"}]):
            with self.subTest(resposta=resposta):
                with self.assertRaises(ValueError):
                    GERADOR._validar_questoes(resposta, 1)


if __name__ == "__main__":
    unittest.main()
