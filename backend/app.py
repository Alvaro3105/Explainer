import os
import secrets
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from sqlalchemy import inspect
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
from models.model_tema import Tema

MODELOS_REGISTRADOS = (RespostaDesafio,)

# Temas criados no primeiro uso. Todos têm questões no banco local,
# então funcionam mesmo sem OPENAI_API_KEY.
CATALOGO_INICIAL = {
    "Matemática": ["Porcentagem e frações", "Equações do 1º grau", "Geometria básica"],
    "Português": ["Interpretação de texto", "Gramática e pontuação", "Figuras de linguagem"],
    "Ciências": ["Corpo humano", "Ecologia", "Sistema solar"],
    "História": ["Brasil Colônia", "Revolução Industrial", "História contemporânea"],
    "Geografia": ["Relevo brasileiro", "Clima e vegetação", "População e urbanização"],
    "Programação": ["Lógica de programação", "HTML, CSS e JavaScript", "Banco de dados SQL"],
}

ROTAS_LEGADAS = ("/alunos", "/questoes", "/desafio", "/desafios", "/temas", "/ranking")


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

    database_url = endereco_do_banco(os.getenv("DATABASE_URL", ""))
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if database_url.startswith("sqlite"):
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "connect_args": {"check_same_thread": False}
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

    app.register_blueprint(aluno_controller)
    app.register_blueprint(desafio_controller)
    app.register_blueprint(tema_controller)
    app.register_blueprint(questao_controller)
    app.register_blueprint(ranking_controller)
    app.register_blueprint(desafio_questao_controller)
    app.register_blueprint(aluno_desafio_controller)
    app.register_blueprint(aprendizado_controller)

    @app.get("/")
    def pagina_inicial():
        return send_from_directory(frontend_path, "estudar.html")

    @app.get("/api")
    def api_home():
        return jsonify({
            "mensagem": "API Flask + SQLAlchemy - ExplAIner",
            "autenticacao": {
                "cadastro": "POST /api/auth/register",
                "login": "POST /api/auth/login",
                "logout": "POST /api/auth/logout",
                "aceitar_termos": "POST /api/auth/accept-terms",
                "excluir_conta": "DELETE /api/auth/delete-account",
            },
            "aprendizado": {
                "minha_conta": "GET /api/learning/me",
                "perfil": "PATCH /api/learning/profile",
                "catalogo": "GET /api/learning/catalog",
                "desafio_ativo": "GET /api/learning/active-challenge",
                "criar_desafio": "POST /api/learning/challenges",
                "buscar_desafio": "GET /api/learning/challenges/<id>",
                "responder": "POST /api/learning/challenges/<id>/answer",
                "concluir": "POST /api/learning/challenges/<id>/complete",
                "tempo_ativo": "POST /api/learning/activity",
                "ranking": "GET /api/learning/ranking",
                "historico": "GET /api/learning/history",
            },
            "painel_administrativo": "CRUD em /alunos, /temas, /questoes, /desafio, /ranking (só com ENABLE_ADMIN_PANEL=1)",
        })

    with app.app_context():
        d.db.create_all()
        if d.db.engine.dialect.name == "sqlite":
            _migrar_schema_sqlite()
        _popular_catalogo_inicial()

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


def _popular_catalogo_inicial():
    if Tema.query.count():
        return
    for materia, temas in CATALOGO_INICIAL.items():
        for nome in temas:
            d.db.session.add(Tema(materia=materia, nome=nome))
    d.db.session.commit()


app = create_app()
if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "False").strip().lower() in {"1", "true", "yes"}
    app.run(debug=debug)
