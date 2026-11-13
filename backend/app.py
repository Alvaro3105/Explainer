import os
import secrets
from pathlib import Path

ARQUIVO_ENV = Path(__file__).resolve().parent.parent / ".env"


def carregar_env(arquivo=ARQUIVO_ENV):
    """Lê o .env do projeto. Variáveis já definidas no sistema têm prioridade.

    Usa o python-dotenv quando ele está instalado. Sem ele (por exemplo, quando o app é
    iniciado por um Python fora do .venv), lê as linhas NOME=valor aqui mesmo, para a
    chave da IA nunca ser ignorada em silêncio.
    """
    if not arquivo.is_file():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(arquivo)
        return
    except ImportError:
        pass
    for linha in arquivo.read_text(encoding="utf-8-sig").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        nome, valor = linha.removeprefix("export ").split("=", 1)
        nome, valor = nome.strip(), valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]
        elif " #" in valor:
            valor = valor.split(" #", 1)[0].rstrip()
        if nome and nome not in os.environ:
            os.environ[nome] = valor


carregar_env()

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from sqlalchemy import event, inspect, text
from sqlalchemy.engine import Engine
from werkzeug.middleware.proxy_fix import ProxyFix

import models.database as d
from controllers.aluno_controller import aluno_controller
from controllers.desafio_controller import desafio_controller
from controllers.tema_controller import tema_controller
from controllers.questao_controller import questao_controller
from controllers.ranking_controller import ranking_controller
from controllers.desafio_questao_controller import desafio_questao_controller
from controllers.aluno_desafio_controller import aluno_desafio_controller
from controllers.aprendizado_controller import aprendizado_controller
from models.model_aprendizado import RespostaDesafio
from models.model_geracao import GeracaoDesafio
from models.model_materia import Materia
from services.aprendizado.catalogo_service import CatalogoService

MODELOS_REGISTRADOS = (RespostaDesafio, Materia, GeracaoDesafio)

ROTAS_LEGADAS = ("/alunos", "/questoes", "/desafio", "/desafios", "/temas", "/ranking")


# Os pedidos da API são pequenos (login, resposta de uma questão). Corpo maior que isto é recusado.
TAMANHO_MAXIMO_DO_PEDIDO = 256 * 1024

# Cabeçalhos de segurança enviados em todas as respostas. As páginas só carregam scripts,
# fontes e imagens do próprio site; "unsafe-inline" vale só para estilos, que as páginas usam.
POLITICA_DE_CONTEUDO = "; ".join((
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "font-src 'self'",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
))
CABECALHOS_DE_SEGURANCA = {
    "Content-Security-Policy": POLITICA_DE_CONTEUDO,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


@event.listens_for(Engine, "connect")
def _ligar_chaves_estrangeiras_no_sqlite(conexao, _registro):
    """O SQLite só confere as chaves estrangeiras se isso for ligado em cada conexão.
    PostgreSQL e MySQL já conferem sempre; assim o banco local se comporta igual."""
    if type(conexao).__module__.startswith("sqlite3"):
        cursor = conexao.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def segundos_de_hsts():
    """HSTS é opcional (HSTS_SEGUNDOS no ambiente) e só vale em HTTPS. Fica desligado por
    padrão porque, uma vez enviado, o navegador passa a recusar o site por HTTP."""
    try:
        return max(0, int(os.getenv("HSTS_SEGUNDOS", "0").strip() or 0))
    except ValueError:
        return 0


CHAVES_DE_EXEMPLO = ("troque", "change", "secret", "exemplo", "example", "dev-secret")


def chave_valida(chave):
    texto = (chave or "").strip()
    return len(texto) >= 24 and not any(trecho in texto.lower() for trecho in CHAVES_DE_EXEMPLO)


def endereco_do_banco(url):
    url = (url or "").strip()
    if not url:
        return "sqlite:///explainer.db"
    for prefixo in ("postgres://", "postgresql://"):
        if url.startswith(prefixo):
            return "postgresql+psycopg://" + url[len(prefixo):]
    return url


def create_app():
    frontend_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "frontend")
    )
    app = Flask(
        __name__, static_folder=frontend_path, static_url_path=""
    )
    chave_secreta = os.getenv("FLASK_SECRET_KEY", "").strip()
    if not chave_valida(chave_secreta):
        # Sem chave, ou com a chave de exemplo, qualquer pessoa poderia forjar o cookie
        # de sessão e entrar como outro aluno. Nesse caso o app usa uma chave aleatória,
        # que vale até o servidor reiniciar.
        chave_secreta = secrets.token_hex(32)
        print("AVISO: FLASK_SECRET_KEY ausente, curta ou de exemplo; usando chave temporária. "
              "Gere uma com: python -c \"import secrets; print(secrets.token_hex(32))\"")
    app.secret_key = chave_secreta
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = os.getenv("COOKIE_SECURE", "0") == "1"
    app.config["MAX_CONTENT_LENGTH"] = TAMANHO_MAXIMO_DO_PEDIDO

    database_url = endereco_do_banco(os.getenv("DATABASE_URL", ""))
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if database_url.startswith("sqlite"):
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            # timeout: espera até 15 s por outra gravação em andamento, em vez de falhar logo.
            "connect_args": {"check_same_thread": False, "timeout": 15}
        }
    else:
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True, "pool_recycle": 280}

    if os.getenv("TRUST_PROXY", "0").strip() == "1":
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    d.db.init_app(app)

    # O CORS só é ligado para as origens configuradas em CORS_ORIGINS.
    origens = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
    if origens:
        CORS(app, origins=origens, supports_credentials=True)

    # O CRUD do painel administrativo não tem login: qualquer pessoa poderia alterar
    # pontos, apagar contas ou ler gabaritos. Por isso ele fica desligado por padrão.
    painel_admin_ativo = os.getenv("ENABLE_ADMIN_PANEL", "0").strip() == "1"

    @app.before_request
    def bloquear_crud_legado():
        if painel_admin_ativo:
            return None
        caminho = request.path.rstrip("/") or "/"
        for prefixo in ROTAS_LEGADAS:
            if caminho == prefixo or caminho.startswith(prefixo + "/"):
                return jsonify({"erro": "Rota administrativa desativada. Defina ENABLE_ADMIN_PANEL=1 apenas em desenvolvimento local."}), 403
        return None

    @app.before_request
    def conferir_corpo_do_painel():
        # As rotas do painel esperam um objeto JSON ({"campo": valor}); lista ou texto solto é recusado.
        caminho = request.path.rstrip("/") or "/"
        if not any(caminho == p or caminho.startswith(p + "/") for p in ROTAS_LEGADAS):
            return None
        if request.method in ("POST", "PUT", "PATCH") and request.get_data(cache=True).strip():
            dados = request.get_json(silent=True)
            if not isinstance(dados, dict):
                return jsonify({"erro": "Envie os dados em um objeto JSON."}), 400
            if any(isinstance(valor, (list, dict)) for valor in dados.values()):
                return jsonify({"erro": "Cada campo precisa ser um texto, um número ou verdadeiro/falso."}), 400
        return None

    @app.after_request
    def cabecalhos_de_seguranca(resposta):
        for nome, valor in CABECALHOS_DE_SEGURANCA.items():
            resposta.headers.setdefault(nome, valor)
        hsts = segundos_de_hsts()
        if hsts and request.is_secure:
            resposta.headers.setdefault("Strict-Transport-Security", f"max-age={hsts}")
        return resposta

    def _erro_da_api(mensagem, status):
        """Nas rotas /api a resposta de erro é JSON, que é o que a tela sabe ler. Nas páginas, fica a padrão."""
        if request.path.startswith("/api/"):
            return jsonify({"erro": mensagem}), status
        return None

    @app.errorhandler(404)
    def nao_encontrado(erro):
        return _erro_da_api("Endereço não encontrado.", 404) or erro

    @app.errorhandler(405)
    def metodo_nao_permitido(erro):
        return _erro_da_api("Operação não permitida neste endereço.", 405) or erro

    @app.errorhandler(500)
    def erro_interno(erro):
        # O detalhe do erro vai só para o log do servidor; o aluno recebe uma mensagem genérica.
        d.db.session.rollback()
        return _erro_da_api("Algo deu errado no servidor. Tente de novo em instantes.", 500) or erro

    @app.errorhandler(413)
    def pedido_grande_demais(_erro):
        return jsonify({"erro": "O pedido enviado é grande demais."}), 413

    @app.errorhandler(OverflowError)
    def numero_fora_do_limite(_erro):
        # Número grande demais para o banco (id gigante na URL, "Infinity" no JSON).
        d.db.session.rollback()
        return jsonify({"erro": "Número fora do limite permitido."}), 400

    app.register_blueprint(aluno_controller)
    app.register_blueprint(desafio_controller)
    app.register_blueprint(tema_controller)
    app.register_blueprint(questao_controller)
    app.register_blueprint(ranking_controller)
    app.register_blueprint(desafio_questao_controller)
    app.register_blueprint(aluno_desafio_controller)
    app.register_blueprint(aprendizado_controller)

    @app.get("/api/saude")
    def saude():
        """Verificação de saúde para a hospedagem: o app responde e o banco aceita consultas."""
        try:
            d.db.session.execute(text("SELECT 1"))
        except Exception:  # noqa: BLE001 - qualquer falha de banco significa "não está saudável"
            d.db.session.rollback()
            return jsonify({"status": "erro", "banco": "indisponivel"}), 503
        return jsonify({"status": "ok", "banco": "ok"})

    @app.get("/")
    def pagina_inicial():
        return send_from_directory(frontend_path, "estudar.html")

    if not (os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("OPENAI_API_KEY", "").strip()):
        print("AVISO: nenhuma chave de IA configurada (GEMINI_API_KEY ou OPENAI_API_KEY no .env). "
              "Sem ela, só os temas do banco local geram desafios.")

    with app.app_context():
        d.db.create_all()
        if d.db.engine.dialect.name == "sqlite":
            _migrar_schema_sqlite()
        _migrar_catalogo()
        # O catálogo de matérias, temas e subtemas fica em backend/database/catalogo/.
        CatalogoService().importar()
        _criar_indices()

    return app


def _migrar_schema_sqlite():
    migracoes = {
        "Aluno": {
            "nick": "VARCHAR(40)",
            "minutos_ativos": "INTEGER DEFAULT 0",
            "ultimo_dia_ativo": "VARCHAR(10)",
            "sequencia_atual": "INTEGER DEFAULT 0",
            "melhor_sequencia": "INTEGER DEFAULT 0",
            "ultimo_heartbeat": "FLOAT",
            "segundos_pendentes": "INTEGER NOT NULL DEFAULT 0",
            "termos_aceitos_em": "DATETIME",
            "versao_termos": "VARCHAR(20)",
        },
        "desafio": {
            "id_tema": "INTEGER",
            "id_aluno": "INTEGER",
            "nivel_mapa": "INTEGER DEFAULT 1",
            "origem_ia": "BOOLEAN DEFAULT 0",
        },
        "Questao": {
            "alternativas_json": "TEXT",
            "explicacao": "TEXT",
        },
    }
    with d.db.engine.begin() as conexao:
        for tabela, colunas in migracoes.items():
            existentes = {linha["name"] for linha in inspect(d.db.engine).get_columns(tabela)}
            for coluna, tipo in colunas.items():
                if coluna not in existentes:
                    conexao.exec_driver_sql(f'ALTER TABLE "{tabela}" ADD COLUMN "{coluna}" {tipo}')


def _migrar_catalogo():
    """Colunas do catálogo na tabela Tema, para bancos criados antes dele (SQLite, PostgreSQL ou MySQL)."""
    colunas = {
        "id_materia": "INTEGER",
        "id_tema_pai": "INTEGER",
        "nome_busca": "VARCHAR(160)",
        "sinonimos": "TEXT",
        "termos_busca": "TEXT",
    }
    aspas = d.db.engine.dialect.identifier_preparer.quote
    existentes = {linha["name"] for linha in inspect(d.db.engine).get_columns("Tema")}
    with d.db.engine.begin() as conexao:
        for coluna, tipo in colunas.items():
            if coluna not in existentes:
                conexao.exec_driver_sql(f"ALTER TABLE {aspas('Tema')} ADD COLUMN {aspas(coluna)} {tipo}")


# Índices criados em bancos que já existiam (nos bancos novos o create_all já cria).
# Cada um atende a uma consulta real: busca do catálogo, desafios do aluno, fases da jornada,
# questões de um desafio e limpeza de questões sem uso.
INDICES = (
    ("Tema", "uq_tema_materia_nome", "UNIQUE INDEX", "id_materia, nome_busca"),
    ("Tema", "ix_tema_materia_nome_busca", "INDEX", "id_materia, nome_busca"),
    ("Tema", "ix_Tema_id_materia", "INDEX", "id_materia"),
    ("Tema", "ix_Tema_id_tema_pai", "INDEX", "id_tema_pai"),
    ("desafio", "ix_desafio_aluno_tema", "INDEX", "id_aluno, id_tema"),
    ("desafio", "ix_desafio_id_tema", "INDEX", "id_tema"),
    ("Questao", "ix_Questao_id_tema", "INDEX", "id_tema"),
    ("desafio_questao", "ix_desafio_questao_id_questao", "INDEX", "id_questao"),
    ("aluno_desafio", "ix_aluno_desafio_id_desafio", "INDEX", "id_desafio"),
    ("resposta_desafio", "ix_resposta_desafio_id_questao", "INDEX", "id_questao"),
)


def _criar_indices():
    """Cria os índices que faltam. Só acrescenta: não apaga nem altera dados."""
    aspas = d.db.engine.dialect.identifier_preparer.quote
    inspetor = inspect(d.db.engine)
    existentes = {}
    for tabela, nome, tipo, colunas in INDICES:
        if tabela not in existentes:
            existentes[tabela] = ({indice["name"] for indice in inspetor.get_indexes(tabela)}
                                  | {restricao["name"] for restricao in inspetor.get_unique_constraints(tabela)})
        if nome in existentes[tabela]:
            continue
        lista = ", ".join(aspas(c.strip()) for c in colunas.split(","))
        try:
            with d.db.engine.begin() as conexao:
                conexao.exec_driver_sql(f"CREATE {tipo} {aspas(nome)} ON {aspas(tabela)} ({lista})")
        except Exception as erro:  # noqa: BLE001 - um índice que não pôde ser criado não impede o app de subir
            print(f"AVISO: não foi possível criar o índice {nome}: {erro}")


app = create_app()
if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "False").strip().lower() in {"1", "true", "yes"}
    app.run(debug=debug)
