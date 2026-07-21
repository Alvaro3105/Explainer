# ExplAIner

Sistema web com frontend estático e backend Flask para gestão de alunos, temas, desafios, questões e ranking.

## Funcionalidades implementadas

- Cadastro, leitura, listagem, atualização e exclusão de alunos
- Cadastro e listagem de temas
- Cadastro e listagem de desafios
- Cadastro e listagem de questões
- Cadastro e listagem de ranking
- Navegação entre páginas do frontend

## Estrutura do projeto

- backend/: API Flask, controllers, services, models e banco SQLite local
- frontend/: páginas HTML, CSS e arquivos JavaScript para consumo da API

## Rotas da API

### Alunos
- GET /alunos
- GET /alunos/<id>
- POST /alunos
- PUT /alunos/<id>
- DELETE /alunos/<id>

### Temas
- GET /temas
- POST /temas
- PUT /temas/<id>
- DELETE /temas/<id>

### Desafios
- GET /desafio
- POST /desafio
- PUT /desafio/<id>
- DELETE /desafio/<id>

### Questões
- GET /questoes
- POST /questoes
- PUT /questoes/<id>
- DELETE /questoes/<id>

### Ranking
- GET /ranking
- POST /ranking
- PUT /ranking/<id>
- DELETE /ranking/<id>

## Como executar

### 1. Backend
```bash
cd backend
pip install -r requirements.txt
python app.py
```

A API ficará disponível em:
- http://127.0.0.1:5000

### 2. Frontend
```bash
cd frontend
python -m http.server 8000
```

A interface ficará disponível em:
- http://127.0.0.1:8000/index.html

## Observações

- O projeto usa SQLite local para execução simples.
- O frontend consome a API via JavaScript usando fetch.
