"""Jornada de um aluno num navegador de verdade: cadastro, busca, desafio, respostas,
conclusão, ranking, histórico, troca de senha, saída, nova entrada e sessão encerrada.

É opcional. Precisa do Playwright e de um navegador (Chromium do Playwright, Edge ou Chrome):

    pip install playwright
    python -m pytest tests/navegador -q

Sem o Playwright ou sem navegador, os testes são pulados (não falham).
O servidor de teste usa banco temporário e não chama a IA.
"""
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api", reason="Playwright não instalado: pip install playwright")

AQUI = Path(__file__).resolve().parent
SENHA = "Senha-De-Teste-123"
NOVA_SENHA = "Outra-Senha-456"


def porta_livre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def servidor():
    pasta = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    banco = Path(pasta.name, "navegador.db")
    porta = porta_livre()
    processo = subprocess.Popen([sys.executable, str(AQUI / "servidor.py"), str(porta), str(banco)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{porta}"
    try:
        for _ in range(120):
            try:
                urllib.request.urlopen(base + "/api/saude", timeout=1)
                break
            except Exception:
                if processo.poll() is not None:
                    pytest.fail("O servidor de teste não iniciou.")
                time.sleep(0.5)
        else:
            pytest.fail("O servidor de teste não respondeu a tempo.")
        yield base, banco
    finally:
        processo.terminate()
        processo.wait(timeout=10)
        pasta.cleanup()


@pytest.fixture(scope="module")
def navegador():
    with playwright.sync_playwright() as p:
        ultimo_erro = None
        for opcoes in ({}, {"channel": "msedge"}, {"channel": "chrome"}):
            try:
                instancia = p.chromium.launch(headless=True, **opcoes)
                break
            except Exception as erro:  # noqa: BLE001 - tenta o próximo navegador instalado
                ultimo_erro = erro
        else:
            pytest.skip(f"Nenhum navegador disponível para o Playwright: {ultimo_erro}")
        yield instancia
        instancia.close()


def gabarito(banco, enunciado):
    conexao = sqlite3.connect(f"file:{banco.as_posix()}?mode=ro", uri=True)
    try:
        return conexao.execute('SELECT alternativa_correta FROM "Questao" WHERE enunciado = ? ORDER BY id_questao DESC',
                               (enunciado,)).fetchone()[0]
    finally:
        conexao.close()


def test_jornada_completa_do_aluno(servidor, navegador):
    base, banco = servidor
    contexto = navegador.new_context(viewport={"width": 1366, "height": 800}, locale="pt-BR")
    pg = contexto.new_page()
    problemas = []
    pg.on("pageerror", lambda erro: problemas.append(f"erro de JavaScript: {erro}"))
    # 401 é esperado em três momentos: antes do login, na senha errada e na sessão encerrada.
    pg.on("console", lambda m: problemas.append(f"console: {m.text}") if m.type == "error" and "401" not in m.text else None)
    pg.on("response", lambda r: problemas.append(f"HTTP {r.status} em {r.url}") if r.status >= 500 or r.status == 404 else None)

    def visivel(seletor):
        return pg.evaluate("s => { const e = document.querySelector(s); return !!e && !e.hidden && e.getClientRects().length > 0; }", seletor)

    def texto(seletor):
        return pg.evaluate("s => (document.querySelector(s)?.innerText || '').trim()", seletor)

    def clicar(seletor):
        pg.wait_for_selector(seletor, state="attached", timeout=10000)
        pg.evaluate("s => document.querySelector(s).click()", seletor)

    # --- cadastro ---
    pg.goto(base + "/")
    pg.wait_for_selector("#tela-acesso:not([hidden])", timeout=15000)
    clicar("#aba-acesso-cadastro")
    cadastro = "#formulario-cadastro"
    pg.fill(cadastro + " input[name=nome]", "Aluna do Teste de Navegador")
    pg.fill(cadastro + " input[name=nick]", "navegante")
    pg.fill(cadastro + " input[name=email]", "navegante@exemplo.com")
    pg.fill(cadastro + " input[name=senha]", SENHA)
    pg.check(cadastro + " input[name=aceite_termos]")
    clicar(cadastro + " button[type=submit]")
    pg.wait_for_selector("#estrutura-app:not([hidden])", timeout=15000)
    assert texto("#nick-lateral") == "navegante"

    # --- busca de matéria e de tema (vem do servidor, sem acento) ---
    # Enter logo depois de digitar, sem esperar as sugestões: tem de valer o texto digitado
    # ("fis" -> Física), e não o primeiro item da lista que já estava aberta (Artes).
    pg.click("#entrada-materia")
    pg.wait_for_selector("#busca-materia [role=option]", timeout=8000)
    pg.type("#entrada-materia", "fis", delay=10)
    pg.keyboard.press("Enter")
    pg.wait_for_function("() => document.querySelector('#entrada-materia').value === 'Física'", timeout=8000)
    pg.wait_for_function("() => !document.querySelector('#entrada-tema').disabled", timeout=8000)
    pg.click("#entrada-tema")
    pg.type("#entrada-tema", "sistema solar", delay=30)
    pg.wait_for_function("() => [...document.querySelectorAll('#busca-tema [role=option]')].some(o => o.innerText.includes('Sistema Solar'))", timeout=8000)
    pg.keyboard.press("Enter")
    assert pg.input_value("#entrada-tema") == "Sistema Solar"

    # --- gerar o desafio e responder as 5 questões ---
    clicar("input[name=quantidade][value='5']")
    clicar("#botao-criar-desafio")
    pg.wait_for_selector("#tela-mapa-desafio:not([hidden])", timeout=20000)
    pg.wait_for_function("() => document.querySelectorAll('.bolinha-mapa').length === 5", timeout=8000)
    for indice in range(5):
        pg.evaluate("i => document.querySelectorAll('.bolinha-mapa')[i].click()", indice)
        pg.wait_for_selector("#janela-quiz:not([hidden])", timeout=8000)
        pg.wait_for_function("() => document.querySelector('#titulo-questao-quiz').innerText.trim().length > 0", timeout=8000)
        certa = gabarito(banco, texto("#titulo-questao-quiz"))
        clicar(f".opcao-resposta[data-resposta='{certa}']")
        clicar("#proxima-questao")                      # confirma a resposta
        pg.wait_for_function("() => /correta!/.test(document.querySelector('#titulo-retorno')?.innerText || '')", timeout=8000)
        pg.wait_for_function("() => !document.querySelector('#proxima-questao').disabled", timeout=8000)
        pg.wait_for_timeout(400)                        # a tela termina de mostrar a correção
        clicar("#proxima-questao")                      # volta ao mapa (ou conclui, na última)
        if indice < 4:
            pg.wait_for_function("i => (document.querySelectorAll('.bolinha-mapa')[i].getAttribute('aria-label') || '').includes('acertou')",
                                 arg=indice, timeout=8000)

    # --- conclusão, pontos, ranking e histórico ---
    pg.wait_for_selector("#resultado-quiz:not([hidden])", timeout=15000)
    assert texto("#resultado-corretas") == "5/5"
    assert texto("#precisao-resultado") == "100%"
    clicar("#finalizar-quiz")
    pg.wait_for_timeout(600)
    if visivel("#tela-mapa-desafio"):
        clicar("#fechar-mapa-rodape")
    pg.wait_for_function("() => document.querySelector('#pontos-topo').innerText.trim() !== '0'", timeout=10000)
    clicar(".item-nav[data-visao='ranking']")
    pg.wait_for_function("() => (document.querySelector('[data-ranking=pagina]')?.innerText || '').includes('navegante')", timeout=10000)
    assert "Aluna do Teste" not in texto("[data-ranking=pagina]")      # o nome completo não aparece
    clicar(".item-nav[data-visao='progresso']")
    pg.wait_for_function("() => document.querySelector('#corpo-tabela-historico').innerText.includes('Sistema Solar')", timeout=10000)

    # --- trocar a senha, sair e entrar com a nova ---
    pg.fill("#senha-atual", SENHA)
    pg.fill("#senha-nova", NOVA_SENHA)
    clicar("#formulario-senha button[type=submit]")
    pg.wait_for_function("() => /Senha trocada/.test(document.querySelector('#mensagem-senha')?.innerText || '')", timeout=8000)
    clicar("#botao-conta")
    clicar("[data-acao-conta='sair']")
    pg.wait_for_selector("#tela-acesso:not([hidden])", timeout=10000)
    pg.fill("#formulario-login input[name=email]", "navegante@exemplo.com")
    pg.fill("#formulario-login input[name=senha]", SENHA)
    clicar("#formulario-login button[type=submit]")
    pg.wait_for_function("() => /incorretos/.test(document.querySelector('#mensagem-acesso')?.innerText || '')", timeout=8000)
    pg.fill("#formulario-login input[name=senha]", NOVA_SENHA)
    clicar("#formulario-login button[type=submit]")
    pg.wait_for_selector("#estrutura-app:not([hidden])", timeout=15000)

    # --- sessão encerrada no meio do uso: volta para o login com aviso ---
    contexto.clear_cookies()
    clicar(".item-nav[data-visao='ranking']")
    clicar(".item-nav[data-visao='progresso']")
    pg.wait_for_selector("#tela-acesso:not([hidden])", timeout=10000)
    assert "sessão terminou" in texto("#mensagem-acesso")

    contexto.close()
    assert problemas == []


def test_no_celular_nao_ha_rolagem_lateral(servidor, navegador):
    base, _banco = servidor
    contexto = navegador.new_context(viewport={"width": 360, "height": 740}, locale="pt-BR")
    pg = contexto.new_page()
    pg.goto(base + "/")
    pg.wait_for_selector("#tela-acesso:not([hidden])", timeout=15000)
    assert pg.evaluate("() => document.documentElement.scrollWidth") <= 360
    pg.evaluate("() => document.querySelector('#aba-acesso-cadastro').click()")
    cadastro = "#formulario-cadastro"
    pg.fill(cadastro + " input[name=nome]", "Aluno do Celular")
    pg.fill(cadastro + " input[name=nick]", "celular")
    pg.fill(cadastro + " input[name=email]", "celular@exemplo.com")
    pg.fill(cadastro + " input[name=senha]", SENHA)
    pg.check(cadastro + " input[name=aceite_termos]")
    pg.evaluate("s => document.querySelector(s).click()", cadastro + " button[type=submit]")
    pg.wait_for_selector("#estrutura-app:not([hidden])", timeout=15000)
    pg.wait_for_timeout(800)
    assert pg.evaluate("() => document.documentElement.scrollWidth") <= 360
    contexto.close()
