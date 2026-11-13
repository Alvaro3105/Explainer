# ExplAIner

**ExplAIner** é uma plataforma de estudos gamificada para alunos do Ensino Médio. O aluno escolhe uma matéria e um tema, e a Inteligência Artificial cria questões de múltipla escolha na hora. Cada resposta é corrigida com explicação, vale pontos e faz o aluno avançar por fases, com ranking e sequência de dias de estudo.

**Repositório:** https://github.com/Alvaro3105/Explainer

## Sumário

- [O problema e a proposta](#o-problema-e-a-proposta)
- [Funcionalidades](#funcionalidades)
- [Tecnologias](#tecnologias)
- [Arquitetura](#arquitetura)
- [Estrutura de pastas](#estrutura-de-pastas)
- [Banco de dados](#banco-de-dados)
- [Catálogo de estudo e busca](#catálogo-de-estudo-e-busca)
- [Geração de questões com IA](#geração-de-questões-com-ia)
- [Pontuação, fases e progressão](#pontuação-fases-e-progressão)
- [Ranking](#ranking)
- [Segurança e privacidade](#segurança-e-privacidade)
- [Como executar](#como-executar)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Testes](#testes)
- [Rotas da API](#rotas-da-api)
- [Limitações conhecidas](#limitações-conhecidas)
- [Resolução de problemas comuns](#resolução-de-problemas-comuns)
- [Equipe](#equipe)

## O problema e a proposta

Estudar para as provas e para o ENEM com listas prontas de exercícios é repetitivo, e o aluno raramente recebe a explicação na hora em que erra. O ExplAIner propõe sessões curtas de estudo em formato de jogo:

- o aluno escolhe o que quer treinar, em um catálogo com as matérias do Ensino Médio;
- as questões são criadas pela IA para o tema e a dificuldade escolhidos, então não se repetem como em uma lista fixa;
- cada resposta tem correção e explicação imediatas;
- pontos, fases, ranking e sequência de dias dão motivo para voltar no dia seguinte.

## Funcionalidades

**Conta**
- Cadastro com nome, nick, e-mail e senha (guardada só como hash), com aceite dos Termos de Uso e do Termo de Consentimento.
- Entrar, sair, trocar a senha, alterar o nick e excluir a própria conta com todos os dados.

**Estudo**
- Busca de matéria e de tema ou subtema com sugestões enquanto o aluno digita, sem diferenciar acentos e com sinônimos.
- Catálogo em matéria › tema › subtema: 14 matérias, 301 temas e 1.075 subtemas. Cada desafio é de uma matéria só.
- Escolha da dificuldade inicial (Fácil, Médio ou Difícil) e da quantidade de questões por fase (5, 10, 15 ou 20).
- Questões de múltipla escolha geradas por IA, com correção, explicação e pontos a cada resposta.
- Mapa de questões por fase; a alternativa fica verde no acerto e vermelha no erro.
- Continuar um desafio de onde parou e refazer fases concluídas (modo revisão, sem pontos).

**Acompanhamento**
- Pontuação, bônus por fase concluída, por fase perfeita e por jornada concluída.
- Ranking com os 5 primeiros colocados, expansível até os 100 primeiros, e a posição real de quem está logado.
- Painel "Meu progresso": fases concluídas, precisão, questões respondidas, tempo ativo e histórico das 30 atividades mais recentes.
- Sequência de dias de estudo (foguinho).

**Extras**
- Tema claro e escuro.
- Minijogo "Chuva de asteroides", que abre ao clicar na logo do topo.
- Painel administrativo antigo (CRUD), desligado por padrão.

## Tecnologias

| Parte | Tecnologias |
|---|---|
| Frontend | HTML5, CSS3 e JavaScript puro (ES6+), com fontes e ícones locais |
| Backend | Python 3.12+, Flask, Flask-SQLAlchemy, Flask-CORS |
| Banco de dados | SQLite (padrão); PostgreSQL e MySQL por configuração |
| Inteligência Artificial | API do Google Gemini; a API da OpenAI é aceita como alternativa |
| Testes | pytest; Playwright (opcional) para os testes de navegador |

## Arquitetura

O frontend (`frontend/`) e a API (`backend/`) ficam separados. O frontend chama a API com `fetch` em JSON, e o próprio Flask entrega os arquivos do frontend, então basta iniciar o backend.

O backend é organizado em camadas:

| Camada | Pasta | Responsabilidade |
|---|---|---|
| Controller | `backend/controllers/` | Recebe a requisição HTTP, confere o login e devolve o JSON |
| Service | `backend/services/` | Executa o caso de uso e as regras da aplicação |
| Repository | `backend/repositories/` | Acessa o banco (ORM e as consultas SQL do ranking) |
| Model | `backend/models/` | Representa as tabelas |

As regras de negócio ficam nos Services. O navegador nunca decide pontos, fases ou gabarito: o servidor confere tudo.

## Estrutura de pastas

```text
backend/
  app.py                    inicialização do Flask, segurança e criação das tabelas
  controllers/              rotas (aprendizado_controller.py é a área do estudante)
  services/aprendizado/     conta, catálogo, desafios, respostas, conclusão, progresso,
                            gerador de questões e limite de geração
  repositories/             acesso ao banco
  models/                   tabelas
  database/catalogo/        catálogo de estudo, um arquivo .txt por matéria
  database/create_database.sql   criação das tabelas no MySQL
  scripts/redefinir_senha.py     redefinição de senha feita pela equipe
frontend/
  estudar.html / .css / .js área do estudante
  minijogo/                 minijogo da logo
  termos-de-uso.html, termo-de-consentimento.html
  index.html, listar.html…  painel administrativo antigo
tests/                      testes automatizados (tests/navegador/ é opcional)
docs/                       diagramas e apresentação
```

## Banco de dados

Por padrão o projeto usa SQLite, no arquivo `backend/instance/explainer.db`. As tabelas, as colunas novas e os índices são criados sozinhos quando o app inicia; essa atualização só acrescenta, nunca apaga dados.

| Tabela | O que guarda |
|---|---|
| `Aluno` | Conta, nick, pontos, sequência de dias, tempo ativo e aceite dos termos |
| `Materia` | Matérias do catálogo |
| `Tema` | Temas e subtemas (o subtema é um tema com `id_tema_pai`) |
| `desafio` | Cada fase gerada para um aluno: tema, dificuldade, fase da jornada |
| `Questao` | Enunciado, alternativas, gabarito e explicação |
| `desafio_questao` | Quais questões pertencem a cada desafio |
| `resposta_desafio` | Cada resposta do aluno, se acertou e os pontos |
| `aluno_desafio` | Resultado de cada fase: concluída ou reprovada, e a pontuação |
| `geracao_desafio` | Pedidos de geração de cada aluno, usados no limite de uso |
| `Ranking` | Tabela do painel administrativo antigo |

Pontos de integridade:

- Uma resposta por aluno, desafio e questão (restrição de unicidade), e um resultado por aluno e desafio.
- As chaves estrangeiras são conferidas também no SQLite, como já acontece no PostgreSQL e no MySQL.
- Há índices para as consultas reais: busca do catálogo, desafios do aluno, fases da jornada e questões de um desafio.

**Usar outro banco:** defina `DATABASE_URL` no `.env`.

```text
DATABASE_URL=postgresql://usuario:senha@servidor/banco
DATABASE_URL=mysql+pymysql://usuario:senha@localhost:3306/ExplAIner
```

No MySQL, execute antes o `backend/database/create_database.sql`.

## Catálogo de estudo e busca

O aluno escolhe **uma matéria por desafio** e, dentro dela, um tema ou subtema. As matérias são as do Ensino Médio, nas quatro áreas da BNCC: Linguagens (Língua Portuguesa, Literatura, Inglês, Espanhol, Artes e Educação Física), Matemática, Ciências da Natureza (Biologia, Física e Química) e Ciências Humanas (História, Geografia, Filosofia e Sociologia).

| | Quantidade |
|---|---|
| Matérias | 14 |
| Temas | 301 |
| Subtemas | 1.075 |
| Sinônimos de busca | 2.019 |

**Como a busca funciona**

- As sugestões aparecem enquanto o aluno digita, com o trecho digitado em destaque. Dá para usar o mouse ou o teclado (setas, Enter e Esc), e o botão × limpa o campo.
- Não diferencia maiúsculas, minúsculas nem acentos ("equacao" acha "Equação").
- Cada palavra digitada precisa ser o começo de uma palavra do nome ou de um sinônimo ("fin" acha "Matemática Financeira"; "bhaskara" acha "Equação do Segundo Grau"). Se nada for encontrado assim, vale também um trecho no meio da palavra.
- Ordem dos resultados: nome igual ao digitado, depois nomes que começam com o texto, depois trechos e sinônimos. Em cada grupo, os temas vêm antes dos subtemas.
- A busca roda no servidor e devolve uma página por vez (8 resultados por padrão, no máximo 50). O navegador nunca recebe o catálogo inteiro.
- A busca de temas só devolve temas da matéria escolhida. Trocar de matéria limpa o tema.

**Como adicionar matérias, temas e subtemas**

O catálogo fica em `backend/database/catalogo/`, um arquivo `.txt` por matéria:

```text
@ Matemática | Matemática e suas Tecnologias | mat; matematica basica
Matemática Financeira | juros; capital; montante
- Juros Simples | juro simples
- Juros Compostos | juros sobre juros
```

- A linha com `@` é a matéria: nome, área e sinônimos.
- A linha sem marcação é um tema; depois da `|` vêm os sinônimos, separados por `;`.
- A linha que começa com `-` é um subtema do tema de cima.
- Linhas com `#` são comentários.

Ao iniciar, o app importa o catálogo: cria o que falta e atualiza o que mudou, sem duplicar e sem apagar alunos, desafios, respostas ou histórico. Para tirar uma matéria, apague o arquivo dela: os temas sem uso são apagados e os que já têm histórico de algum aluno continuam no banco, mas saem da busca.

O catálogo foi montado pela equipe com os conteúdos do Ensino Médio e do ENEM. Ele não é uma lista oficial da BNCC ou do ENEM.

## Geração de questões com IA

```mermaid
flowchart TD
    A[Aluno pede um desafio] --> B{Passou do limite de geração?}
    B -- sim --> C[Aviso com o tempo de espera]
    B -- não --> D[Gemini]
    D -- falhou --> E[OpenAI, se houver chave]
    E -- falhou --> F[Banco local do tema, se existir]
    F -- não existe --> G[Aviso conforme o motivo da falha]
    D -- respondeu --> H[Validação das questões]
    E -- respondeu --> H
    F -- existe --> I[Desafio gravado e entregue]
    H -- quantidade suficiente --> I
    H -- faltaram questões boas --> G
```

**O que é enviado à IA:** matéria, tema, subtema (se houver), dificuldade, quantidade e público (Ensino Médio e ENEM), com a orientação de não misturar outras matérias, de resolver cada questão antes de escrevê-la e de conferir que só uma alternativa está correta. A chave vai no cabeçalho da requisição e nunca chega ao navegador nem aos logs.

**Ordem das fontes:** Gemini (modelo de `GEMINI_MODEL` e, se falhar, o seguinte da lista), depois OpenAI (se houver chave), depois o banco local. Sem chave de IA, só cinco temas têm questões guardadas no projeto: Corpo Humano, Sistema Solar, Equação do Primeiro Grau, Figuras de Linguagem e Brasil Colônia.

**Validação.** São descartadas as questões:

- incompletas ou fora do formato;
- com alternativas repetidas;
- com o mesmo enunciado de outra do lote;
- com texto grande demais;
- com explicação que desmente o próprio gabarito (a IA escreve que está "reavaliando" a conta ou que nenhuma alternativa serve);
- em que a conta da explicação termina no valor de outra alternativa e o valor do gabarito nem aparece (letra trocada).

**Questões de reserva.** O servidor pede uma questão a mais a cada cinco (6 para 5, 12 para 10, 18 para 15, 24 para 20) para repor as descartadas. O aluno recebe sempre a quantidade que escolheu. Se não sobrarem questões boas suficientes, nenhuma questão inválida é usada para completar: o aluno é avisado e pode tentar de novo. Não há repetição automática sem fim: cada pedido faz no máximo duas chamadas por provedor, dentro de um prazo total de 80 segundos.

**Limite de geração por aluno** (gravado no banco, então vale para todos os processos do servidor e depois de um reinício):

- uma geração por vez: clicar de novo enquanto o desafio é preparado não dispara outra chamada;
- 10 segundos entre uma geração e a próxima;
- no máximo 8 gerações a cada 10 minutos e 40 por dia;
- refazer um desafio concluído não chama a IA e não entra no limite.

Quem passa do limite recebe o status 429, com o tempo de espera na mensagem e no cabeçalho `Retry-After`.

**Quando a IA falha**

| Motivo | Status | O que o servidor faz |
|---|---|---|
| Limite de uso do provedor | 503 | Fica 30 s sem chamar o provedor (ou o tempo que ele pedir) e informa a espera |
| Chave recusada | 503 | Para na primeira tentativa e registra o problema no log, sem mostrar a chave |
| Provedor fora do ar ou lento | 502 | Tenta o próximo modelo, dentro do prazo total do pedido |
| Resposta fora do formato | 502 | Descarta o lote |

Se a geração falhar, o desafio que o aluno já tinha em andamento continua lá. Ele só é trocado depois que as questões novas chegam.

## Pontuação, fases e progressão

| Dificuldade | Acerto | Erro |
|---|---|---|
| Fácil | +10 | −3 |
| Médio | +15 | −4 |
| Difícil | +20 | −5 |

- O erro tira 25% do que valeria o acerto, e o total do aluno nunca fica negativo.
- Bônus: **+10** por fase aprovada, **+25** por fase perfeita e **+50** por jornada concluída.
- A fase só é aprovada com **60% de acertos ou mais**. Abaixo disso não há bônus, a próxima fase continua bloqueada e o aluno tenta a fase de novo, com outras questões.
- A jornada de um tema tem 5 fases de 5 questões, 4 de 10, 3 de 15 ou 2 de 20. A dificuldade sobe um nível a cada fase, até Difícil.
- As questões são respondidas em ordem, e cada uma só pode ser respondida uma vez.
- Refazer uma fase concluída (revisão) não vale pontos.
- A sequência de dias (foguinho) aumenta quando o aluno estuda em dias seguidos, no horário de Brasília.

## Ranking

- Abre com os **5 primeiros colocados**; o botão **Ver mais posições** mostra, no mesmo card, até o 100º.
- O quadro **Sua posição** mostra a colocação real de quem está logado, mesmo fora dos 100 primeiros.
- Participa quem já respondeu pelo menos uma questão.
- A ordem é por pontos. No empate, vale a ordem alfabética do nome e depois a ordem de cadastro.
- A ordem vem de uma única consulta ao banco, com o limite aplicado no próprio banco. A API só aceita `limite=5` ou `limite=100`.
- A resposta traz apenas posição, nick, pontos, sequência e tempo ativo. E-mail e nome completo nunca são enviados; quem não tem nick aparece só com o primeiro nome.

## Segurança e privacidade

**Conta e sessão**
- Senhas guardadas com hash (nunca em texto).
- Cookie de sessão com `HttpOnly` e `SameSite=Lax`; com `COOKIE_SECURE=1`, só trafega em HTTPS.
- 5 senhas erradas para a mesma conta bloqueiam novas tentativas por 15 minutos. Há também um limite de 100 erros por IP, alto de propósito, porque uma escola inteira usa o mesmo IP.
- No máximo 100 contas novas por IP por hora (`CADASTROS_POR_HORA_POR_IP`).
- Trocar a senha exige a senha atual; excluir a conta também.

**Dados dos alunos**
- Um aluno não lê, responde nem conclui o desafio de outro.
- O gabarito e a explicação só são enviados depois da resposta.
- Dados coletados: nome, nick, e-mail, senha (hash), data de nascimento (opcional), pontos e tempo de uso.
- Excluir a conta apaga os desafios, as respostas e os registros do aluno.

**Servidor**
- Cabeçalhos de segurança em todas as respostas: política de conteúdo (só scripts, fontes e imagens do próprio site), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy` e `Permissions-Policy`. Por causa dessa política, as páginas não podem usar `<script>` sem `src`, `onclick="..."` nem recursos de outros sites.
- HSTS opcional: só é enviado em HTTPS e quando `HSTS_SEGUNDOS` está definido.
- Pedidos com mais de 256 KB são recusados (413).
- Erros internos devolvem uma mensagem genérica; o detalhe fica só no log do servidor.
- O painel administrativo antigo não tem login e fica desligado (`ENABLE_ADMIN_PANEL=0`); as rotas dele respondem 403.
- O `.env` está no `.gitignore`. Nenhuma chave vai para o repositório.

**Esqueci minha senha.** O ExplAIner ainda não envia e-mails, então não há recuperação de senha pela tela. A equipe confirma por fora quem é o aluno e redefine a senha no servidor:

```powershell
.\.venv\Scripts\python.exe backend\scripts\redefinir_senha.py email-do-aluno@exemplo.com
```

O script mostra uma senha provisória uma única vez. O aluno entra com ela e troca em **Meu progresso › Trocar senha**.

## Como executar

Antes de começar, instale o **Python 3.12 ou mais novo**. Rode os comandos no PowerShell, **na pasta raiz do projeto**.

**1. Criar e ativar o ambiente virtual**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**2. Instalar as dependências**
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**3. Configurar o `.env`**
```powershell
copy .env.example .env
```
Edite o `.env`:
- `FLASK_SECRET_KEY`: gere com `python -c "import secrets; print(secrets.token_hex(32))"` e cole o resultado.
- `GEMINI_API_KEY`: a chave do Google Gemini (crie em aistudio.google.com).

**4. Iniciar**
```powershell
.\.venv\Scripts\python.exe backend\app.py
```

Acesse `http://127.0.0.1:5000`. Para conferir se o servidor e o banco estão respondendo, abra `http://127.0.0.1:5000/api/saude`.

## Variáveis de ambiente

| Variável | Para que serve | Padrão |
|---|---|---|
| `FLASK_SECRET_KEY` | Assina as sessões. Sem ela, o app usa uma chave temporária e todos são deslogados a cada reinício | — (obrigatória em produção) |
| `GEMINI_API_KEY` | Chave do Google Gemini | vazio (só o banco local funciona) |
| `GEMINI_MODEL` | Modelo do Gemini tentado primeiro | `gemini-3.1-flash-lite` no exemplo |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | Provedor alternativo | vazio, `gpt-4o-mini` |
| `DATABASE_URL` | Outro banco (PostgreSQL ou MySQL) | SQLite local |
| `COOKIE_SECURE` | `1` em produção com HTTPS | `0` |
| `TRUST_PROXY` | `1` quando o app roda atrás de um proxy, para enxergar o IP real | `0` |
| `ENABLE_ADMIN_PANEL` | Liga o painel antigo. Só em desenvolvimento | `0` |
| `CORS_ORIGINS` | Outros domínios autorizados a chamar a API | vazio |
| `INTERVALO_ENTRE_GERACOES` | Segundos entre gerações do mesmo aluno | `10` |
| `GERACOES_POR_JANELA` | Gerações por aluno a cada 10 minutos | `8` |
| `GERACOES_POR_DIA` | Gerações por aluno por dia | `40` |
| `CADASTROS_POR_HORA_POR_IP` | Contas novas por IP por hora | `100` |
| `HSTS_SEGUNDOS` | Liga o HSTS, só em HTTPS | desligado |
| `FLASK_DEBUG` | Modo de depuração. Nunca em produção | `False` |

Nos limites, o valor `0` desliga a regra.

## Testes

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Os testes usam um banco temporário e nunca chamam a IA de verdade (as respostas do provedor são simuladas), então não dependem de chave nem gastam cota.

| Arquivo | O que cobre |
|---|---|
| `tests/test_api.py` | Conta, autorização, desafios, respostas, bônus, fases, histórico e painel antigo |
| `tests/test_catalogo.py` | Importação do catálogo, busca e leitura do `.env` |
| `tests/test_ranking.py` | Top 5 e top 100, desempate e posição do aluno |
| `tests/test_banco_local.py` | Banco local de questões e troca de provedor |
| `tests/test_protecoes.py` | Limite de geração, login, validação das questões, erros da IA, cabeçalhos e concorrência |
| `tests/test_plataforma.py` | Limite gravado no banco, índices, cadastros, senha, rota de saúde e questões de reserva |
| `tests/navegador/` | Jornada completa do aluno em um navegador de verdade (opcional) |

**Testes de navegador (opcionais).** Precisam do Playwright e de um navegador (Chromium do Playwright, Edge ou Chrome). Sem eles, são pulados.

```powershell
.\.venv\Scripts\python.exe -m pip install playwright
.\.venv\Scripts\python.exe -m pytest tests\navegador -q
```

## Rotas da API

**Conta**
- `POST /api/auth/register` – cadastro (exige o aceite dos termos)
- `POST /api/auth/login` e `POST /api/auth/logout`
- `POST /api/auth/change-password` – trocar a senha (logado)
- `POST /api/auth/accept-terms` – registrar o aceite dos termos
- `DELETE /api/auth/delete-account` – excluir a própria conta

**Aprendizado**
- `GET /api/learning/me` – dados e progresso do aluno
- `PATCH /api/learning/profile` – alterar o nick
- `GET /api/learning/catalog?q=mat` – listar ou pesquisar matérias
- `GET /api/learning/catalog/<id_materia>/themes?q=fin&limite=8&pagina=1` – temas e subtemas de uma matéria
- `GET /api/learning/catalog/themes/<id_tema>/subtopics?q=juros` – subtemas de um tema
- `GET /api/learning/active-challenge` – desafio em andamento
- `POST /api/learning/challenges` – gerar desafio (ou refazer um concluído, com `refazer: true`)
- `GET /api/learning/challenges/<id>`
- `POST /api/learning/challenges/<id>/answer` – responder uma questão
- `POST /api/learning/challenges/<id>/complete` – concluir a fase
- `POST /api/learning/activity` – tempo ativo
- `GET /api/learning/ranking?limite=5` – os 5 primeiros (`?limite=100` traz os 100)
- `GET /api/learning/history` – histórico

**Outras**
- `GET /api/saude` – o servidor e o banco estão respondendo?
- `/` – área do estudante

**Painel administrativo antigo (CRUD)**, desligado por padrão: `/alunos`, `/temas`, `/desafio`, `/questoes`, `/ranking` e os relacionamentos `/alunos/<id>/desafios` e `/desafios/<id>/questoes`. Para usar no computador, defina `ENABLE_ADMIN_PANEL=1` (nunca em produção, porque o painel não tem login).

## Limitações conhecidas

- **Qualidade das questões.** A validação pega problemas de formato, repetição e contradição evidente, mas não resolve as questões. Uma questão errada com explicação confiante pode passar, e o sistema não confere se a questão é mesmo do tema pedido.
- **Dependência da IA.** Sem chave, ou com a cota do provedor esgotada, só cinco temas geram desafio.
- **Tempo de geração.** A resposta da IA leva de alguns segundos a algumas dezenas de segundos, e mais nos lotes maiores.
- **Recuperação de senha.** Depende de um serviço de e-mail que o projeto ainda não tem; por enquanto a redefinição é feita pela equipe.
- **Confirmação de e-mail.** Não existe; o cadastro aceita qualquer e-mail com formato válido.
- **Limites em memória.** Os limites de login e de cadastro ficam na memória de cada processo do servidor. O limite de geração fica no banco.
- **Sessões.** Trocar a senha não encerra as sessões já abertas em outros aparelhos.
- **PostgreSQL e MySQL.** O código aceita os dois bancos, mas a suíte de testes roda em SQLite; eles ainda não foram validados de ponta a ponta.
- **Menores de idade.** Não há verificação de idade nem consentimento do responsável. O uso com menores precisa de revisão da instituição.
- **Painel administrativo antigo.** Não tem login; por isso fica desligado.

## Resolução de problemas comuns

**"Fatal error in launcher: Unable to create process..."**
Acontece no Windows quando a pasta do projeto é movida ou sincronizada no OneDrive. Use sempre `.\.venv\Scripts\python.exe -m pip install <pacote>` em vez de `pip install`.

**O PowerShell não deixa ativar o ambiente virtual**
Rode uma vez: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

**Aviso "nenhuma chave de IA configurada" ao iniciar**
O `.env` não tem `GEMINI_API_KEY` (nem `OPENAI_API_KEY`), ou o app foi iniciado fora da pasta do projeto. Sem a chave, só os cinco temas do banco local geram desafio.

## Equipe

- Lucas Ribeiro Fontana
- Josué Fernando Silva Melo
- Weber Anjos de Souza Sodré
- Álvaro Pires de Souza
- Antônio Henrique de Paula Reis
- Henrique Saddi Meinicke
