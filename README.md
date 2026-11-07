# ExplAIner v16.1 — correções de segurança, retomada e banco local

## Alterações desta versão
- **Segurança:** o painel administrativo legado (CRUD sem login) fica desligado por padrão (`ENABLE_ADMIN_PANEL=1` liga, só em desenvolvimento); CORS só para origens em `CORS_ORIGINS`; chaves de sessão vazias, curtas ou de exemplo são recusadas; login com limite de tentativas (5 erros por e-mail/IP em 15 min → 429); tempo ativo só conta o tempo que realmente passou; exclusão de conta pede a senha num campo mascarado; páginas do painel escapam o HTML vindo do servidor.
- **Jogo:** dificuldade sobe um nível por fase (Fácil → Médio → Difícil) e o servidor recalcula a dificuldade da fase que grava; "Normal" aparece como **Médio** (o valor interno continua `Normal`).
- **Retomada:** "Continuar desafio" volta na fase e na questão certas; uma fase com tudo respondido mas não concluída pode ser concluída depois; após concluir uma fase e sair, o painel oferece "Continuar jornada" (funciona após recarregar e em outro dispositivo).
- **Mapa:** trilha refeita em HTML/CSS (sem SVG), mais grossa, com o trecho percorrido em violeta.
- **Botão Voltar** ao lado da marca em todas as páginas (`frontend/voltar.js`).
- **Banco local:** todos os 18 temas do catálogo inicial funcionam sem `OPENAI_API_KEY` (novos bancos para Equações do 1º grau, Figuras de linguagem, Sistema solar e Brasil Colônia).
- **Dados:** excluir aluno, desafio, tema ou questão não deixa mais registros órfãos; `create_database.sql` atualizado para espelhar os models.

# ExplAIner v16 — refazer fiel, fases corretas e aproveitamento

## Alterações desta versão
- **Refazer com as mesmas questões:** a revisão reutiliza as questões salvas do desafio concluído, na mesma ordem (mesma bolinha = mesma pergunta).
- **Fase gravada no servidor:** um desafio novo é sempre Fase 1 da jornada; "Continuar" volta na fase certa. A cor do espaço agora depende da fase (fase 1 = cor original), inclusive ao refazer e no mapa pequeno da tela inicial.
- **Pontos por erro:** acertar dá o ponto normal (10/15/20); errar tira 25% disso (ex.: 100 → -25), sem deixar o total abaixo de 0. Na revisão não há ganho nem perda.
- **Aproveitamento da jornada:** ao terminar a última fase, se o aluno errou 70% ou mais de todas as questões da jornada, ela é reprovada: sem elogio, sem bônus, todos os pontos da jornada são descontados e fases e revisões são apagadas (como se nunca tivesse feito). O botão "Recomeçar jornada" gera tudo de novo com perguntas novas.
- A decisão de fim de jornada e de reprovação é feita no servidor.

# ExplAIner v15 — correções do mapa e novos elogios

## Alterações desta versão
- **Mapa do desafio em tela cheia:** o mapa agora ocupa sempre toda a largura e altura visíveis (mesmo com 5 questões) e só cria rolagem horizontal quando há muitas questões. Redesenha ao redimensionar a janela.
- **Sequência obrigatória:** só a primeira questão não respondida fica liberada; as demais aparecem bloqueadas (cadeado). O servidor também recusa respostas fora de ordem.
- **Gerar novo desafio:** se já existe um desafio em andamento, aparece uma janela perguntando se deseja excluí-lo (Sim/Não). Ao confirmar, o desafio antigo é apagado no servidor e o botão "Continuar desafio" passa a abrir o novo. O estado do desafio é zerado por inteiro a cada início (corrige o vazamento de progresso/modo revisão entre desafios).
- **Continuar** volta na fase certa da jornada (fase/dificuldade salvas no navegador).
- **Refazer:** o botão começa pelo **desafio 1**. Ao terminar, só avança para o desafio 2 se ele já foi concluído no progresso normal; caso contrário aparece o aviso "Conclua o desafio 2 no seu progresso normal para conseguir refazê-lo".
- **Elogios:** desafio concluído → emojis 👍 subindo + janela de elogio com X e fechamento automático; 5 desafios seguidos → janela + som "Uhul!" (sem emojis); jornada completa → confetes + janela de festa.
- **XP extra:** +10 XP por desafio concluído e +50 XP ao concluir a jornada (não vale no modo Refazer).
- **Mapa pequeno da tela inicial** usa o mesmo fundo espacial (com a cor do desafio atual).

# ExplAIner v14 — novo visual (front-end Figma)

## Alterações desta versão
- Todo o front-end foi adaptado ao novo design: tema escuro `#1E2C32` com lime `#D1DC5A`, Montserrat, ícones Font Awesome, cartões `#45444E`, bolinhas com sombra e botões em relevo. O modo claro continua disponível em **Configurações** (o padrão agora é escuro).
- Login/cadastro com painel espacial e astronauta, rótulos flutuantes e abas Entrar / Criar conta.
- Painel "Aprender" no estilo do novo layout (cabeçalho fixo com XP, sequência e ranking; barra lateral com ícones; cartões de estatísticas). Nenhuma função foi removida.
- Mapa do desafio continua **horizontal**, com a **trilha** ligando cada bolinha; bolinhas no novo formato (lime / turquesa / roxo quando concluída).
- O fundo do mapa mantém astronauta e estrelas, mas **muda de cor a cada desafio criado** (8 tons escolhidos pelo id do desafio; ver `PALETAS_ESPACO` em `estudar.js`).
- Janela da questão com alternativas lime/turquesa; acerto em verde e erro em vermelho.
- Páginas administrativas (`index.html`, `listar.html`, `temas.html` etc.) com o mesmo tema via `style.css`.
- Novos arquivos visuais em `frontend/assets/`.

---

# ExplAIner v13 — navegação aprimorada e revisão isolada

## Alterações desta versão
- Barra superior redesenhada com navegação mais clara, indicadores e botão de continuar destacado.
- Barra lateral com estados ativos/hover, ícones e área de conta refinados.
- Revisões marcadas como `[REFAZER]` não são tratadas como desafios ativos da jornada normal.
- O histórico e o botão de refazer ignoram sessões de revisão para evitar encadeamento de revisões.
- A geração local prioriza perguntas que o aluno ainda não viu no mesmo tema e dificuldade, evitando repetições até esgotar o banco local disponível.
- A geração por IA recebe os enunciados anteriores como contexto para reduzir repetição.

## Limites importantes
O banco local é demonstrativo e finito. Ele não consegue garantir diversidade ilimitada nem uma separação pedagógica perfeita entre Fácil, Médio e Difícil. Para uma variedade muito maior e questões novas contextualizadas, configure `OPENAI_API_KEY` no arquivo `.env`. Se o banco local não tiver questões suficientes para a quantidade solicitada, o sistema informa o limite em vez de inventar questões de outro tema.

## Executar
1. Crie e ative um ambiente virtual Python.
2. Execute `pip install -r requirements.txt`.
3. Copie `.env.example` para `.env` se necessário e configure as variáveis.
4. Execute `python backend/app.py`.
5. Abra `http://127.0.0.1:5000`.

## Testes
Instale as dependências de desenvolvimento com `pip install -r requirements-dev.txt` e execute `python -m pytest tests -q` (ou, sem pytest, `python -m unittest discover -s tests -v`).

O projeto é organizado com `backend/`, `frontend/` e `tests/` diretamente na raiz; não é necessário abrir uma pasta de versão aninhada.

---

# ExplAIner — aprendizagem gamificada

Aplicação web de estudo construída com Flask, SQLite, HTML, CSS e JavaScript. A nova área do estudante fica na rota `/`; as páginas de administração CRUD que já existiam continuam disponíveis pelos arquivos HTML originais.

## Ajustes da versão 12 — ações do desafio, mapa e conta

- O botão verde do topo agora aparece somente quando existe um desafio em andamento e serve para continuar o desafio salvo.
- O botão grande de continuar foi removido da área de configuração. O botão inferior fica maior e é identificado como “Gerar desafio” ou “Criar um novo desafio”, conforme exista um desafio ativo.
- O minimapa de conquistas ganha borda, trilha e detalhes coloridos conforme matéria, tema e fase selecionados.
- O menu da conta oferece “Sair do site”, “Utilizar outra conta” e “Excluir minha conta”.
- A exclusão da conta solicita confirmação e senha e remove os registros pessoais de respostas, histórico, ranking e desafios próprios associados à conta.
- A estrutura do ZIP foi organizada para que `backend/`, `frontend/` e `tests/` fiquem diretamente na raiz, sem uma pasta `explv9/` adicional.

## Funcionalidades adicionadas

- Cadastro e login com sessão de servidor e senha armazenada como hash.
- Nick público, perfil e alteração do nick.
- Catálogo organizado por matéria e tema, com temas iniciais inseridos automaticamente quando o catálogo está vazio.
- Desafios com 5, 10, 15 ou 20 questões e níveis Fácil, Médio e Difícil. A jornada mostra quantos desafios terá: 5 questões → 5 desafios; 10 → 4; 15 → 3; 20 → 2.
- Questões de múltipla escolha, validação da resposta no backend, explicação da resposta e pontos por acerto.
- Bônus de 25 pontos por concluir um desafio com 100% de acertos.
- Ranking por pontos, sequência de atividade diária, tempo ativo, precisão e quantidade de desafios concluídos.
- Mapa espacial de desafios em tela cheia, adaptado às referências visuais exportadas do Figma, com uma bolinha por questão; tocar/clicar na bolinha abre a questão correspondente.
- Progresso visual das bolinhas respondidas, trilha conectada e quatro variações de mapa, que se alternam conforme a fase avança. Tema claro por padrão, com opção de tema escuro.
- Histórico de desafios e registro de respostas individuais, com opção para refazer atividades anteriores.
- Elogio após cada resposta correta, mensagem especial a cada cinco acertos consecutivos e mensagens separadas ao concluir uma fase ou acertar tudo.
- A jornada termina após o número de desafios planejado para a quantidade de questões escolhida; o estudante pode iniciar uma nova jornada depois.
- Layout responsivo para desktop e celular.
- Login e cadastro por e-mail/senha, com senha armazenada em hash e telas de acesso separadas.
- Integração opcional com a API da OpenAI para gerar questões alinhadas à matéria, ao tema, à dificuldade e à quantidade selecionada.
- Modo local de demonstração quando não existe chave de API configurada.


### Ajustes visuais v8 — mapa horizontal e mundos temáticos

- O mapa de cada desafio foi redesenhado para desktop em formato horizontal, com progressão da esquerda para a direita e rolagem lateral quando há muitas questões.
- As bolinhas ficam conectadas por uma trilha curva; questões concluídas ganham estado visual próprio e os rótulos ficam visíveis em telas maiores.
- O minimapa do painel inicial também usa uma trilha horizontal e ocupa menos espaço vertical.
- Os cenários variam conforme a matéria/tema (matemática, ciências, história, geografia, idiomas ou outros) e também recebem uma variação pela fase. Os cenários são feitos com gradientes e camadas CSS locais, sem dependência de imagens externas ou carregamento do Google.
- Mantidos o fluxo de perguntas, o histórico, o ranking, o sistema de pontos e o modo claro/escuro.

## Requisitos

- Python 3.10 ou superior.
- Pacotes descritos em `requirements.txt`.
- Opcional: chave de API da OpenAI para geração dinâmica de questões. O uso da API pode gerar custos na conta associada à chave.

## Executar no Windows

Abra o terminal na pasta raiz deste projeto e execute:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
cd backend
py app.py
```

Acesse `http://127.0.0.1:5000/` no navegador. Não abra `estudar.html` diretamente pelo explorador de arquivos: a interface usa a API Flask e a sessão HTTP.

Se o PowerShell bloquear a ativação do ambiente virtual, use o terminal CMD e rode `.venv\Scripts\activate.bat`.

## Configurar geração por IA

Sem a chave, o aplicativo usa um banco local demonstrativo. Para gerar questões com a API da OpenAI, defina as variáveis de ambiente **antes de iniciar o backend**. No PowerShell:

```powershell
$env:OPENAI_API_KEY="sua-chave-de-api"
$env:OPENAI_MODEL="gpt-4o-mini"
$env:FLASK_SECRET_KEY="uma-chave-longa-e-aleatoria"
cd backend
py app.py
```

A variável `OPENAI_API_KEY` deve permanecer apenas no backend; não a coloque em `estudar.js`, no HTML nem em arquivos publicados. `OPENAI_MODEL` é opcional. A geração dinâmica depende de conectividade e de uma conta de API habilitada. Se uma solicitação de geração falhar, o sistema retorna ao banco local de demonstração e identifica essa origem na resposta.

Para produção, configure uma `FLASK_SECRET_KEY` forte (gere com `python -c "import secrets; print(secrets.token_hex(32))"`), use HTTPS e defina `COOKIE_SECURE=1`. Se a chave estiver vazia, curta ou for a do `.env.example`, o app a recusa e usa uma chave temporária, que derruba as sessões a cada reinício.

## Notas sobre dados existentes

Na inicialização, o aplicativo adiciona as colunas novas ao banco SQLite existente sem eliminar os registros anteriores. Senhas legadas em texto puro são convertidas para hash quando o usuário entra com sucesso; novas senhas já são armazenadas como hash. Faça uma cópia de `backend/instance/explainer.db` antes de usar o projeto sobre uma base importante.

O modo local foi pensado para testar a navegação e a mecânica de gamificação sem chave de IA. Ele seleciona questões de demonstração por área de conhecimento e não equivale à geração personalizada por IA para cada tema. Para conteúdo escolar específico, configure a API e valide as questões geradas antes de uso avaliativo.

## API principal

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/learning/me`
- `GET /api/learning/catalog`
- `POST /api/learning/challenges`
- `GET /api/learning/active-challenge`
- `GET /api/learning/challenges/<id>`
- `POST /api/learning/challenges/<id>/answer`
- `POST /api/learning/challenges/<id>/complete`
- `POST /api/learning/activity`
- `GET /api/learning/ranking`
- `GET /api/learning/history`
- `PATCH /api/learning/profile`
- `DELETE /api/auth/delete-account`

A interface de estudante foi reorganizada em um painel compacto, com configuração do desafio e mapa de conquistas lado a lado, indicadores resumidos e histórico/ranking em blocos menores. O mapa do desafio abre depois da criação, cada bolinha abre uma questão e, depois da resposta, o estudante volta ao mapa. A reprodução usa as referências visuais exportadas do Figma e não sincroniza automaticamente com o arquivo Figma original.

### Limite importante do painel administrativo legado

As rotas CRUD antigas (`/alunos`, `/questoes`, `/temas`, `/desafio`, `/ranking` e rotas associadas) não têm autorização por perfil. Por isso elas respondem **403 por padrão**; para usar as telas administrativas em desenvolvimento local, defina `ENABLE_ADMIN_PANEL=1` no `.env`. Não ligue essa opção num servidor publicado: antes, seria preciso proteger essas rotas com autenticação administrativa. O novo fluxo de estudante usa sessão, hash de senha e validação de respostas no servidor, mas isso não substitui a proteção das rotas administrativas antigas.


## Ajustes para desktop
A interface recebeu overrides responsivos para monitores: modal de questao ampliado, tipografia maior, feedback de resposta com contraste alto e estados correto/incorreto claramente identificados.

## Autenticação (e-mail e senha)

- O login e o cadastro usam as rotas `/api/auth/login` e `/api/auth/register`, com senha armazenada em hash.
- A tela apresenta dois modos exclusivos: **Entrar** e **Criar conta**. O formulário inativo fica removido do layout; erros como e-mail já cadastrado levam ao modo de login e mantêm o e-mail preenchido.
- Não há botão, rota ou dependência de autenticação Google nesta versão.
- A confirmação de novas contas por código de e-mail ou SMS não está ativa; isso exige configurar um provedor de envio e implementar a validação do token.

## Atualizações v9 — continuidade e variedade
- O botão verde de **Continuar desafio** é a ação principal quando há um desafio incompleto salvo na conta.
- O botão inferior passa a indicar **Criar um novo desafio** quando existe um desafio em andamento; um novo desafio passa a ser o ativo mais recente.
- O botão **Refazer último desafio** aparece após existir pelo menos um desafio concluído. Tentativas de refazer não concedem pontos nem bônus de desafio perfeito.
- O servidor expõe o desafio ativo da conta, incluindo questões respondidas, para restaurar o progresso após sair e entrar novamente.
- A geração por IA pede maior diversidade entre enunciados e separação mais clara entre níveis. O banco local demonstrativo ainda tem uma variedade limitada; para grande diversidade real por tema, configure `OPENAI_API_KEY`.

## Ajustes desta versão
- O modo de refazer abre novamente o mapa de revisão, permite sair de qualquer questão e não habilita avanço de fase.
- Tentativas marcadas como `[REFAZER]` não contam para calcular a próxima fase normal.
- O gerador local não usa perguntas genéricas de outra matéria quando não reconhece o tema; nesse caso, configure `OPENAI_API_KEY` para solicitar geração contextualizada.
- O mapa usa uma ilustração 2D local e não depende de imagens externas.
