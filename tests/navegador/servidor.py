"""Sobe o ExplAIner para os testes de navegador: banco temporário e nenhuma chamada à IA.

Uso: python tests/navegador/servidor.py PORTA CAMINHO_DO_BANCO
"""
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
porta, banco = int(sys.argv[1]), Path(sys.argv[2])

os.environ["DATABASE_URL"] = "sqlite:///" + banco.as_posix()
# Sem chaves: as questões vêm do banco local e nenhum teste gasta cota da IA.
os.environ["GEMINI_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["FLASK_SECRET_KEY"] = "chave-so-para-os-testes-de-navegador-0123456789"
os.environ["COOKIE_SECURE"] = "0"
os.environ["ENABLE_ADMIN_PANEL"] = "0"
os.environ["INTERVALO_ENTRE_GERACOES"] = "0"   # o robô clica mais rápido que um aluno
sys.path.insert(0, str(RAIZ / "backend"))

import app as aplicacao  # noqa: E402

aplicacao.app.run(port=porta, debug=False, use_reloader=False)
