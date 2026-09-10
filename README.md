# ExplAIner

**ExplAIner** é um projeto acadêmico em equipe para uma plataforma de estudos gamificada. A versão atual implementa uma aplicação web com **Python, Flask, SQLAlchemy, MySQL/SQLite e JavaScript**, com gerenciamento de alunos, temas, desafios, questões e ranking.

> Este repositório é o espelho do projeto no meu GitHub. O repositório de referência da equipe é: https://github.com/lucasf0ntana/ExplAInerRepositorio

## Equipe

- Lucas Ribeiro Fontana
- Josué Fernando Silva Melo
- Weber Anjos de Souza Sodré
- Álvaro Pires de Souza
- Antônio Henrique de Paula Reis
- Henrique Saddi Meinicke

## Estado atual do projeto

A proposta do ExplAIner inclui o uso de Inteligência Artificial para auxiliar na geração de questões. **Na versão de código sincronizada neste repositório, a integração com um provedor/modelo de IA ainda não está implementada.** O que está implementado e pode ser demonstrado no código é a base de gamificação e gerenciamento de estudos.

### Funcionalidades implementadas

- cadastro, consulta, listagem, atualização e exclusão de alunos;
- cadastro e gerenciamento de temas;
- cadastro e gerenciamento de desafios;
- cadastro e gerenciamento de questões;
- verificação de alternativa de uma questão;
- gerenciamento de ranking;
- ranking de alunos por pontuação;
- relacionamentos entre alunos/desafios e desafios/questões;
- frontend servido pelo próprio Flask;
- suporte local a SQLite e configuração para MySQL.

## Arquitetura

```text
backend/
├── controllers/
├── models/
├── repositories/
├── services/
├── database/
├── tests/
├── app.py
└── requirements.txt

frontend/
├── index.html
├── ler.html
├── listar.html
├── atualizar.html
├── deletar.html
├── temas.html
├── desafios.html
├── questoes.html
├── ranking.html
├── style.css
└── *.js
```

A aplicação separa responsabilidades entre **controllers**, **services**, **repositories** e **models**.

## Stack

- Python
- Flask
- Flask-SQLAlchemy
- Flask-Cors
- SQLAlchemy
- MySQL / PyMySQL
- SQLite para desenvolvimento local
- HTML5
- CSS3
- JavaScript

## Como executar

### 1. Clone o repositório

```bash
git clone https://github.com/Alvaro3105/Explainer.git
cd Explainer/backend
```

### 2. Crie e ative o ambiente virtual

```bash
python -m venv .venv
```

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

CMD:

```cmd
.\.venv\Scripts\activate.bat
```

### 3. Instale as dependências

```bash
python -m pip install -r requirements.txt
```

### 4. Configure o ambiente

Crie `.env` a partir de `.env.example`.

PowerShell:

```powershell
Copy-Item .env.example .env
```

CMD:

```cmd
copy .env.example .env
```

Por padrão, o projeto usa SQLite:

```text
DATABASE_URL=sqlite:///explainer.db
```

Para MySQL, execute `database/create_database.sql` e ajuste a `DATABASE_URL` no `.env`.

### 5. Execute

```bash
python app.py
```

A aplicação ficará disponível em:

```text
http://127.0.0.1:5000
```

O frontend é servido pelo Flask, portanto não é necessário iniciar um segundo servidor HTTP.

## Rotas principais

### Aplicação e documentação

- `GET /` — frontend
- `GET /api` — resumo das rotas da API

### Alunos

- `GET /alunos`
- `GET /alunos/<id>`
- `POST /alunos`
- `PUT /alunos/<id>`
- `DELETE /alunos/<id>`
- `GET /alunos/ranking`

### Temas

- `GET /temas`
- `POST /temas`
- `PUT /temas/<id>`
- `DELETE /temas/<id>`

### Desafios

- `GET /desafio`
- `GET /desafio/nome/<nome>`
- `POST /desafio`
- `PUT /desafio/<id>`
- `DELETE /desafio/<id>`

### Questões

- `GET /questoes`
- `POST /questoes`
- `PUT /questoes/<id>`
- `DELETE /questoes/<id>`
- `POST /questoes/<id>/verificar`

### Ranking

- `GET /ranking`
- `POST /ranking`
- `PUT /ranking/<id>`
- `DELETE /ranking/<id>`

## Testes

```bash
cd backend
python -m unittest discover -s tests
```

Os testes utilizam SQLite em memória para não depender do banco local.

## Observações de segurança e organização

- arquivos `__pycache__`, `.pyc`, `.env` e bancos SQLite locais não são versionados;
- senhas de novos alunos são armazenadas usando hash do Werkzeug;
- dados sensíveis de ambiente ficam fora do repositório;
- o README diferencia funcionalidades implementadas de objetivos futuros do projeto.

## Contexto

Projeto desenvolvido em grupo durante a formação técnica em TI no COTEMIG.

**Álvaro Pires de Souza**  
GitHub: https://github.com/Alvaro3105  
LinkedIn: https://www.linkedin.com/in/alvaro-pires-de-souza/
