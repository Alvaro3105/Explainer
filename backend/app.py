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

# Importar o model registra a tabela no create_all, mesmo sem usar o nome aqui.
MODELOS_REGISTRADOS = (RespostaDesafio,)

# Temas criados no primeiro uso. Todos têm questões no banco local de demonstração,
# então funcionam mesmo sem OPENAI_API_KEY (verificado em tests/test_banco_local.py).
CATALOGO_INICIAL = {
    "Matemática": ["Porcentagem e frações", "Equações do 1º grau", "Geometria básica"],
    "Português": ["Interpretação de texto", "Gramática e pontuação", "Figuras de linguagem"],
    "Ciências": ["Corpo humano", "Ecologia", "Sistema solar"],
    "História": ["Brasil Colônia", "Revolução Industrial", "História contemporânea"],
    "Geografia": ["Relevo brasileiro", "Clima e vegetação", "População e urbanização"],
    "Programação": ["Lógica de programação", "HTML, CSS e JavaScript", "Banco de dados SQL"],
}

# Prefixos do CRUD legado do painel administrativo.
ROTAS_LEGADAS = ("/alunos", "/questoes", "/desafio", "/desafios", "/temas", "/ranking")


CHAVES_DE_EXEMPLO = ("troque", "change", "secret", "exemplo", "example", "dev-secret")


def chave_valida(chave):
    """Rejeita chaves vazias, curtas ou copiadas do .env.example."""
    texto = (chave or "").strip()
    return len(texto) >= 24 and not any(trecho in texto.lower() for trecho in CHAVES_DE_EXEMPLO)


def create_app():
    frontend_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "frontend")
    )
    app = Flask(
        __name__, static_folder=frontend_path, static_url_path=""
    )
    chave_secreta = os.getenv("FLASK_SECRET_KEY", "").strip()
    if not chave_valida(chave_secreta):
        # Sem chave, ou com a chave de exemplo do .env.example (pública), qualquer pessoa
        # poderia forjar o cookie de sessão e entrar como outro aluno. Nesses casos usa uma
        # chave aleatória por processo (as sessões expiram ao reiniciar o servidor).
        chave_secreta = secrets.token_hex(32)
        print("AVISO: FLASK_SECRET_KEY ausente, curta ou de exemplo; usando chave temporária. "
              "Gere uma com: python -c \"import secrets; print(secrets.token_hex(32))\"")
    app.secret_key = chave_secreta
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = os.getenv("COOKIE_SECURE", "0") == "1"

    database_url = os.getenv("DATABASE_URL", "sqlite:///explainer.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if database_url.startswith("sqlite"):
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "connect_args": {"check_same_thread": False}
        }

    d.db.init_app(app)

    # CORS só é habilitado para origens explicitamente configuradas (ex.: CORS_ORIGINS=http://localhost:3000).
    origens = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
    if origens:
        CORS(app, origins=origens, supports_credentials=True)

    # O CRUD legado (painel administrativo) não tem perfis de acesso: qualquer pessoa poderia
    # alterar pontos, apagar contas ou ler gabaritos. Fica desligado, salvo opt-in explícito.
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

    # Registro de todos os Blueprints
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
            "mensagem": "API Flask + SQLAlchemy - Sistema de Gamificação Educacional",
            "rotas": {
                "alunos": {
                    "listar": "GET /alunos",
                    "buscar": "GET /alunos/<id>",
                    "criar": "POST /alunos",
                    "atualizar": "PUT /alunos/<id>",
                    "deletar": "DELETE /alunos/<id>",
                    "ranking": "GET /alunos/ranking"
                },
                "desafios": {
                    "listar": "GET /desafio",
                    "buscar_por_nome": "GET /desafio/nome/<nome>",
                    "criar": "POST /desafio",
                    "atualizar": "PUT /desafio/<id>",
                    "deletar": "DELETE /desafio/<id>",
                },
                "temas": {
                    "listar": "GET /temas",
                    "criar": "POST /temas",
                    "atualizar": "PUT /temas/<id>",
                    "deletar": "DELETE /temas/<id>",
                },
                "questoes": {
                    "listar": "GET /questoes",
                    "criar": "POST /questoes",
                    "atualizar": "PUT /questoes/<id>",
                    "deletar": "DELETE /questoes/<id>",
                },
                "ranking": {
                    "listar": "GET /ranking",
                    "criar": "POST /ranking",
                    "atualizar": "PUT /ranking/<id>",
                    "deletar": "DELETE /ranking/<id>",
                },
                "desafio_questoes": {
                    "adicionar": "POST /desafios/<id_desafio>/questoes/<id_questao>",
                    "listar": "GET /desafios/<id_desafio>/questoes",
                    "remover": "DELETE /desafios/<id_desafio>/questoes/<id_questao>",
                },
                "aluno_desafios": {
                    "registrar": "POST /alunos/desafios",
                    "listar_por_aluno": "GET /alunos/<id_aluno>/desafios",
                    "atualizar": "PUT /alunos/<id_aluno>/desafios/<id_desafio>",
                },
                "autenticacao": {
                    "cadastro": "POST /api/auth/register",
                    "login": "POST /api/auth/login",
                    "logout": "POST /api/auth/logout",
                    "sessao": "GET /api/learning/me"
                },
                "aprendizado": {
                    "catalogo": "GET /api/learning/catalog",
                    "criar_desafio": "POST /api/learning/challenges",
                    "responder": "POST /api/learning/challenges/<id>/answer",
                    "concluir": "POST /api/learning/challenges/<id>/complete",
                    "ranking": "GET /api/learning/ranking",
                    "historico": "GET /api/learning/history"
                }
            }
        })

    with app.app_context():
        d.db.create_all()
        if d.db.engine.dialect.name == "sqlite":
            _migrar_schema_sqlite()
        _popular_catalogo_inicial()

    return app


def _migrar_schema_sqlite():
    """Adiciona colunas novas em bancos SQLite existentes, sem apagar dados."""
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
