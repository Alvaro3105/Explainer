"""Banco local de questões: todo tema do catálogo inicial precisa funcionar sem OPENAI_API_KEY."""
import ast
import importlib.util
import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ["OPENAI_API_KEY"] = ""
_SPEC = importlib.util.spec_from_file_location("gerador_questoes", ROOT / "backend" / "services" / "aprendizado" / "gerador_questoes.py")
GERADOR = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(GERADOR)


def catalogo_inicial():
    """Lê CATALOGO_INICIAL do app.py sem importar o app (importar criaria um banco)."""
    arvore = ast.parse((ROOT / "backend" / "app.py").read_text(encoding="utf-8"))
    for no in arvore.body:
        if isinstance(no, ast.Assign) and any(getattr(alvo, "id", None) == "CATALOGO_INICIAL" for alvo in no.targets):
            return ast.literal_eval(no.value)
    raise AssertionError("CATALOGO_INICIAL não encontrado em backend/app.py")


class TestBancoLocal(unittest.TestCase):
    def test_todo_tema_do_catalogo_gera_20_questoes_sem_ia(self):
        # Todo tema criado no primeiro uso precisa funcionar sem chave de IA.
        for materia, temas in catalogo_inicial().items():
            for tema in temas:
                with self.subTest(materia=materia, tema=tema):
                    questoes, origem, _ = GERADOR.gerar_questoes(materia, tema, "Normal", 20)
                    self.assertEqual(20, len(questoes))
                    self.assertEqual("banco_local", origem)
                    self.assertEqual(20, len({q["enunciado"] for q in questoes}), "enunciados repetidos no mesmo desafio")

    def test_questoes_dos_bancos_estao_bem_formadas(self):
        bancos = {**GERADOR.BANCO_LOCAL, **GERADOR.BANCO_TEMATICO}
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
            return  # recusar por falta de banco também é aceitável
        self.assertFalse(primeiro_grau & {q["enunciado"] for q in questoes})

    def test_tema_sem_banco_continua_recusando_assunto_errado(self):
        with self.assertRaises(RuntimeError):
            GERADOR.gerar_questoes("Ciências", "Astronomia avançada", "Normal", 10)


if __name__ == "__main__":
    unittest.main()
