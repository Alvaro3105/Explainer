const URL_DA_API = '';
const LETRAS = ['A', 'B', 'C', 'D'];

const estado = {
  aluno: null,
  progresso: null,
  materiaEscolhida: null, // matéria escolhida na busca (uma por desafio)
  temaEscolhido: null,    // tema ou subtema escolhido na busca
  desafio: null,
  temaAtual: null,
  questoes: [],
  indiceQuestao: 0,
  alternativaSelecionada: null,
  respostaEnviada: false,
  modoMapa: false,
  modoRevisao: false,
  questoesRespondidas: new Set(),
  resultadoQuestoes: new Map(),   // índice da questão: true se acertou, false se errou
  acertosSeguidos: 0,
  inicioQuestao: 0,
  temporizador: null,
  tempoDoAviso: null,
  configuracaoBase: null,
  revisao: null,          // lista de desafios e posição atual, quando está refazendo
  faseAtiva: 1,           // fase do desafio em andamento (muda a cor do espaço)
  faseReprovada: false,
};

const elemento = (id) => document.getElementById(id);

async function api(caminho, opcoes = {}) {
  const configuracao = {
    method: opcoes.method || 'GET',
    credentials: 'same-origin',
    headers: { ...(opcoes.body ? { 'Content-Type': 'application/json' } : {}), ...(opcoes.headers || {}) },
    ...(opcoes.body ? { body: JSON.stringify(opcoes.body) } : {}),
  };

  const resposta = await fetch(`${URL_DA_API}${caminho}`, configuracao);
  let dados = {};
  try { dados = await resposta.json(); } catch (_) { dados = {}; }
  if (!resposta.ok) {
    const erro = new Error(dados.erro || `Não foi possível concluir a solicitação (${resposta.status}).`);
    erro.status = resposta.status;
    erro.dados = dados;
    // A sessão acabou no meio do uso (expirou ou a conta saiu em outra aba): volta para o login.
    if (resposta.status === 401 && estado.aluno && !caminho.startsWith('/api/auth/')) {
      estado.aluno = null;
      estado.progresso = null;
      fecharMenuConta();
      mostrarTelaAutenticacao();
      mostrarAviso('Sua sessão terminou. Entre de novo para continuar.', 'erro');
    }
    throw erro;
  }
  return dados;
}

function mostrarAviso(mensagem, tipo = 'sucesso', destino = 'mensagem-acesso') {
  const alvo = elemento(destino);
  if (!alvo) return;
  alvo.textContent = mensagem;
  alvo.className = `recado ${tipo}`;
  alvo.hidden = false;
}

function mostrarAvisoRapido(mensagem) {
  const aviso = elemento('aviso-rapido');
  aviso.textContent = mensagem;
  aviso.hidden = false;
  clearTimeout(estado.tempoDoAviso);
  estado.tempoDoAviso = setTimeout(() => { aviso.hidden = true; }, 4400);
}

// Janela de confirmação, elogios, emojis, confetes e sons
let resolverModal = null;

// Com campoSenha a janela mostra um campo de senha e devolve o texto digitado.
// Sem ele, devolve true ou false.
function perguntar({ titulo, texto, sim = 'Sim', nao = 'Não', informativo = false, icone = null, campoSenha = false }) {
  if (resolverModal) resolverModal(false);
  const janela = elemento('janela-confirmar');
  const campo = elemento('campo-confirmar');
  const entrada = elemento('entrada-confirmar');
  elemento('titulo-confirmar').textContent = titulo;
  elemento('texto-confirmar').textContent = texto;
  elemento('confirmar-sim').textContent = sim;
  elemento('confirmar-nao').textContent = nao;
  elemento('confirmar-nao').hidden = informativo;
  campo.hidden = !campoSenha;
  entrada.value = '';
  janela.querySelector('.cartao-modal').classList.toggle('informativo', informativo);
  elemento('icone-confirmar').innerHTML = `<i class="fa-solid ${icone || (informativo ? 'fa-lock' : 'fa-triangle-exclamation')}"></i>`;
  janela.hidden = false;
  (campoSenha ? entrada : informativo ? elemento('confirmar-sim') : elemento('confirmar-nao')).focus();
  return new Promise((resolver) => {
    resolverModal = (resposta) => {
      janela.hidden = true;
      resolverModal = null;
      const valor = entrada.value;
      entrada.value = '';
      campo.hidden = true;
      resolver(campoSenha ? (resposta ? valor : null) : resposta);
    };
  });
}
elemento('entrada-confirmar').addEventListener('keydown', (evento) => {
  if (evento.key === 'Enter' && resolverModal) { evento.preventDefault(); resolverModal(true); }
});
const avisar = (titulo, texto, botao = 'Entendi') => perguntar({ titulo, texto, sim: botao, informativo: true });

elemento('confirmar-sim').addEventListener('click', () => resolverModal && resolverModal(true));
elemento('confirmar-nao').addEventListener('click', () => resolverModal && resolverModal(false));
elemento('janela-confirmar').addEventListener('click', (evento) => {
  if (evento.target === elemento('janela-confirmar') && resolverModal) resolverModal(false);
});

let tempoElogio = null;
function fecharElogio(imediato = false) {
  clearTimeout(tempoElogio);
  const janela = elemento('janela-elogio');
  const cartao = elemento('cartao-elogio');
  if (janela.hidden) return;
  if (imediato) { janela.hidden = true; return; }
  cartao.classList.add('saindo');
  setTimeout(() => { janela.hidden = true; cartao.classList.remove('saindo'); }, 280);
}

function mostrarElogio({ icone, titulo, texto, xp = 0, duracao = 6, tipo = 'normal' }) {
  clearTimeout(tempoElogio);
  const janela = elemento('janela-elogio');
  const cartao = elemento('cartao-elogio');
  cartao.className = `cartao-elogio${tipo === 'sequencia' ? ' em-sequencia' : tipo === 'festa' ? ' festa' : ''}`;
  elemento('icone-elogio').textContent = icone;
  elemento('titulo-elogio').textContent = titulo;
  elemento('texto-elogio').textContent = texto;
  const rotuloXp = elemento('xp-elogio');
  rotuloXp.hidden = !(xp > 0);
  rotuloXp.textContent = `+${formatarNumero(xp)} XP de bônus`;
  const barra = elemento('barra-tempo-elogio');
  barra.style.setProperty('--duracao', `${duracao}s`);
  barra.style.animation = 'none';
  void barra.offsetWidth; // reinicia a animação da barra de tempo
  barra.style.animation = '';
  janela.hidden = false;
  tempoElogio = setTimeout(() => fecharElogio(), duracao * 1000);
}
elemento('fechar-elogio').addEventListener('click', () => fecharElogio());

document.addEventListener('keydown', (evento) => {
  if (evento.key !== 'Escape') return;
  if (resolverModal) resolverModal(false);
  else if (!elemento('janela-elogio').hidden) fecharElogio();
});

function emojisSubindo(emoji = '👍', quantidade = 26) {
  const camada = elemento('camada-comemoracao');
  for (let i = 0; i < quantidade; i += 1) {
    const item = document.createElement('span');
    item.className = 'emoji-subindo';
    item.textContent = emoji;
    item.style.left = `${4 + Math.random() * 92}%`;
    item.style.setProperty('--tam', `${28 + Math.random() * 34}px`);
    item.style.setProperty('--duracao', `${2.6 + Math.random() * 1.8}s`);
    item.style.setProperty('--atraso', `${Math.random() * 1.1}s`);
    item.style.setProperty('--alt', `${60 + Math.random() * 35}vh`);
    item.style.setProperty('--balanco', `${(Math.random() - 0.5) * 140}px`);
    item.style.setProperty('--giro', `${(Math.random() - 0.5) * 50}deg`);
    item.addEventListener('animationend', () => item.remove());
    camada.appendChild(item);
  }
}

function confete(quantidade = 170) {
  const camada = elemento('camada-comemoracao');
  const cores = ['#D1DC5A', '#33B4BD', '#7C79FF', '#FF8918', '#FEC701', '#EA2B2B', '#F6F9FC'];
  for (let i = 0; i < quantidade; i += 1) {
    const peca = document.createElement('i');
    peca.className = `peca-confete${Math.random() < 0.3 ? ' redondo' : ''}`;
    peca.style.left = `${Math.random() * 100}%`;
    peca.style.setProperty('--cor', cores[i % cores.length]);
    peca.style.setProperty('--largura', `${7 + Math.random() * 8}px`);
    peca.style.setProperty('--altura', `${10 + Math.random() * 12}px`);
    peca.style.setProperty('--duracao', `${3 + Math.random() * 2.6}s`);
    peca.style.setProperty('--atraso', `${Math.random() * 1.2}s`);
    peca.style.setProperty('--deriva', `${(Math.random() - 0.5) * 320}px`);
    peca.style.setProperty('--giro', `${360 + Math.random() * 900}deg`);
    peca.addEventListener('animationend', () => peca.remove());
    camada.appendChild(peca);
  }
}

let contextoAudio = null;
function obterAudio() {
  try {
    contextoAudio = contextoAudio || new (window.AudioContext || window.webkitAudioContext)();
    if (contextoAudio.state === 'suspended') contextoAudio.resume();
    return contextoAudio;
  } catch (_) { return null; }
}

function tocarNota(contexto, frequencia, inicio, duracao, { tipo = 'triangle', volume = 0.16, ate = null } = {}) {
  const osc = contexto.createOscillator();
  const ganho = contexto.createGain();
  osc.type = tipo;
  osc.frequency.setValueAtTime(frequencia, contexto.currentTime + inicio);
  if (ate) osc.frequency.exponentialRampToValueAtTime(ate, contexto.currentTime + inicio + duracao * 0.8);
  ganho.gain.setValueAtTime(0.0001, contexto.currentTime + inicio);
  ganho.gain.exponentialRampToValueAtTime(volume, contexto.currentTime + inicio + 0.02);
  ganho.gain.exponentialRampToValueAtTime(0.0001, contexto.currentTime + inicio + duracao);
  osc.connect(ganho).connect(contexto.destination);
  osc.start(contexto.currentTime + inicio);
  osc.stop(contexto.currentTime + inicio + duracao + 0.05);
}

function falarUhul() {
  try {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const fala = new SpeechSynthesisUtterance('Uhul!');
    fala.lang = 'pt-BR';
    fala.pitch = 1.7;
    fala.rate = 1.05;
    window.speechSynthesis.speak(fala);
  } catch (_) { /* navegador sem voz: fica só o som */ }
}

// tipos de som: 'ok' (fase concluída), 'uhul' (5 seguidos) e 'festa' (jornada concluída)
function tocarSom(tipo) {
  const contexto = obterAudio();
  if (contexto) {
    if (tipo === 'ok') {
      [523, 659, 784].forEach((nota, i) => tocarNota(contexto, nota, i * 0.1, 0.3));
    } else if (tipo === 'uhul') {
      // som de comemoração subindo de tom
      tocarNota(contexto, 330, 0, 0.55, { tipo: 'sawtooth', volume: 0.07, ate: 820 });
      tocarNota(contexto, 660, 0.45, 0.3, { tipo: 'square', volume: 0.05, ate: 520 });
    } else {
      [523, 659, 784, 1047, 784, 1047, 1319].forEach((nota, i) => tocarNota(contexto, nota, i * 0.12, 0.35));
      tocarNota(contexto, 330, 0, 0.9, { tipo: 'sawtooth', volume: 0.05, ate: 880 });
    }
  }
  if (tipo !== 'ok') falarUhul();
}

// Guarda a configuração da jornada de cada desafio, para o "Continuar" voltar na fase certa.
const CHAVE_JORNADAS = 'explainer-jornadas-v1';
function lerJornadas() {
  try { return JSON.parse(localStorage.getItem(CHAVE_JORNADAS) || '{}') || {}; } catch (_) { return {}; }
}
function salvarJornada(idDesafio, configuracao) {
  if (!idDesafio || !configuracao) return;
  try {
    const todas = lerJornadas();
    todas[idDesafio] = configuracao;
    const ids = Object.keys(todas);
    if (ids.length > 80) delete todas[ids[0]];
    localStorage.setItem(CHAVE_JORNADAS, JSON.stringify(todas));
  } catch (_) { /* sem armazenamento local */ }
}

// Conta os desafios concluídos em sequência (elogio dos 5 seguidos).
function chaveSeguidos() { return `explainer-seguidos-v1-${estado.aluno?.id_aluno || 0}`; }
function lerSeguidos() {
  try { return Number(localStorage.getItem(chaveSeguidos())) || 0; } catch (_) { return 0; }
}
function gravarSeguidos(valor) {
  try { localStorage.setItem(chaveSeguidos(), String(valor)); } catch (_) {}
}

function trocarModoAutenticacao(modo) {
  const login = modo === 'login';
  document.querySelectorAll('[data-modo-acesso]').forEach((botao) => {
    const ativo = botao.dataset.modoAcesso === modo;
    botao.classList.toggle('ativo', ativo);
    botao.setAttribute('aria-selected', String(ativo));
  });
  elemento('formulario-login').hidden = !login;
  elemento('formulario-cadastro').hidden = login;
  elemento('titulo-acesso').textContent = login ? 'Bom ter você de volta.' : 'Sua jornada começa aqui.';
  elemento('subtitulo-acesso').textContent = login ? 'Entre para continuar sua jornada.' : 'Crie sua conta e comece a avançar por fases.';
  elemento('mensagem-acesso').hidden = true;
}

document.querySelectorAll('[data-modo-acesso]').forEach((botao) => {
  botao.addEventListener('click', () => trocarModoAutenticacao(botao.dataset.modoAcesso));
});

// Só um formulário aparece por vez: login ou cadastro.
trocarModoAutenticacao('login');

elemento('formulario-login').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  const botao = evento.currentTarget.querySelector('button[type="submit"]');
  const textoOriginal = botao.innerHTML;
  botao.disabled = true;
  botao.textContent = 'Entrando…';
  const dadosFormulario = Object.fromEntries(new FormData(evento.currentTarget));
  try {
    const dados = await api('/api/auth/login', { method: 'POST', body: dadosFormulario });
    elemento('formulario-login').reset();
    await iniciarPlataforma(dados);
  } catch (erro) {
    mostrarAviso(erro.message, 'erro');
  } finally {
    botao.disabled = false;
    botao.innerHTML = textoOriginal;
  }
});

elemento('formulario-cadastro').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  const botao = evento.currentTarget.querySelector('button[type="submit"]');
  const textoOriginal = botao.innerHTML;
  botao.disabled = true;
  botao.textContent = 'Criando conta…';
  const dadosFormulario = Object.fromEntries(new FormData(evento.currentTarget));
  if (!dadosFormulario.data_nascimento) delete dadosFormulario.data_nascimento;
  dadosFormulario.aceite_termos = Boolean(evento.currentTarget.elements.aceite_termos?.checked);
  try {
    const dados = await api('/api/auth/register', { method: 'POST', body: dadosFormulario });
    elemento('formulario-cadastro').reset();
    await iniciarPlataforma({ aluno: dados.aluno });
  } catch (erro) {
    const emailEnviado = String(dadosFormulario.email || '').trim();
    if (erro.status === 409 && /e-mail/i.test(erro.message)) {
      trocarModoAutenticacao('login');
      elemento('formulario-login').elements.email.value = emailEnviado;
      mostrarAviso('Este e-mail já possui uma conta. Entre com sua senha para continuar e manter seu progresso.', 'erro');
    } else {
      mostrarAviso(erro.message, 'erro');
    }
  } finally {
    botao.disabled = false;
    botao.innerHTML = textoOriginal;
  }
});

async function iniciarPlataforma(dados) {
  estado.aluno = dados.aluno;
  estado.progresso = dados.progresso || null;
  elemento('tela-acesso').hidden = true;
  elemento('estrutura-app').hidden = false;
  historicoVisoes.length = 0;
  visaoAtual = 'estudo';
  atualizarBotaoVoltar();
  atualizarIdentidade();
  try {
    const perfil = await api('/api/learning/me');
    estado.aluno = perfil.aluno;
    estado.progresso = perfil.progresso;
    if (estado.aluno.precisa_aceitar_termos && !(await pedirAceiteDosTermos())) {
      await encerrarSessao(false);
      mostrarAviso('Sem o aceite dos termos não é possível usar o ExplAIner. Você pode aceitá-los no próximo login.', 'erro');
      return;
    }
    atualizarPainelPerfil();
    await atualizarPainel();
    await atualizarBotoesDesafio();
    iniciarContagemDeTempo();
  } catch (erro) {
    if (erro.status === 401) mostrarTelaAutenticacao();
    else mostrarAvisoRapido(erro.message);
  }
}

// Conta antiga, criada antes dos termos, precisa aceitar para continuar.
// O aceite fica gravado no servidor.
function pedirAceiteDosTermos() {
  const janela = elemento('janela-termos');
  janela.hidden = false;
  elemento('aceitar-termos').focus();
  return new Promise((resolver) => {
    const finalizar = (aceitou) => {
      janela.hidden = true;
      elemento('aceitar-termos').onclick = null;
      elemento('recusar-termos').onclick = null;
      resolver(aceitou);
    };
    elemento('recusar-termos').onclick = () => finalizar(false);
    elemento('aceitar-termos').onclick = async () => {
      elemento('aceitar-termos').disabled = true;
      try {
        const dados = await api('/api/auth/accept-terms', { method: 'POST', body: {} });
        estado.aluno = dados.aluno;
        finalizar(true);
      } catch (erro) {
        mostrarAvisoRapido(erro.message);
      } finally {
        elemento('aceitar-termos').disabled = false;
      }
    };
  });
}

function atualizarSituacaoDosTermos() {
  const situacao = elemento('situacao-termos');
  if (!situacao || !estado.aluno) return;
  const quando = estado.aluno.termos_aceitos_em ? new Date(estado.aluno.termos_aceitos_em) : null;
  situacao.textContent = quando && !Number.isNaN(quando.getTime())
    ? `Você aceitou os termos (versão ${estado.aluno.versao_termos}) em ${quando.toLocaleDateString('pt-BR')} às ${quando.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}. Para revogar o consentimento, exclua sua conta no menu da conta.`
    : 'Você ainda não aceitou os termos.';
}

function mostrarTelaAutenticacao() {
  pararContagemDeTempo();
  // Ao sair da conta, limpa tudo o que era do desafio anterior.
  Object.assign(estado, {
    desafio: null, temaAtual: null, questoes: [], configuracaoBase: null, revisao: null,
    modoRevisao: false, faseReprovada: false, faseConcluida: false,
    proximaFasePendente: null, questoesRespondidas: new Set(), resultadoQuestoes: new Map(),
  });
  window.__historicoDesafios = [];
  limparRanking();
  campoMateria.limpar();
  elemento('ir-para-desafio').hidden = true;
  elemento('botao-refazer-ultimo').hidden = true;
  elemento('tela-acesso').hidden = false;
  elemento('estrutura-app').hidden = true;
  elemento('janela-quiz').hidden = true;
  elemento('tela-mapa-desafio').hidden = true;
  document.body.classList.remove('mapa-aberto');
}

async function restaurarSessao() {
  try {
    const dados = await api('/api/learning/me');
    await iniciarPlataforma(dados);
  } catch (erro) {
    if (erro.status !== 401) console.warn('Sessão inicial indisponível:', erro.message);
    mostrarTelaAutenticacao();
  }
}

function atualizarIdentidade() {
  if (!estado.aluno) return;
  const nick = estado.aluno.nick || estado.aluno.nome || 'Estudante';
  const inicial = nick.trim().charAt(0).toUpperCase() || 'E';
  elemento('nick-lateral').textContent = nick;
  elemento('email-lateral').textContent = estado.aluno.email || 'Minha conta';
  elemento('avatar-lateral').textContent = inicial;
  elemento('avatar-topo').textContent = inicial;
  elemento('pontos-topo').textContent = formatarNumero(estado.aluno.pontos || 0);
  elemento('indicador-pontos').textContent = formatarNumero(estado.aluno.pontos || 0);
  elemento('sequencia-topo').textContent = estado.aluno.sequencia_atual || estado.aluno.foguinho || 0;
  elemento('indicador-sequencia').textContent = estado.aluno.sequencia_atual || estado.aluno.foguinho || 0;
  elemento('sequencia-lateral').textContent = `${estado.aluno.sequencia_atual || estado.aluno.foguinho || 0} ${(estado.aluno.sequencia_atual || estado.aluno.foguinho || 0) === 1 ? 'dia' : 'dias'}`;
  elemento('indicador-minutos').textContent = formatarNumero(estado.aluno.minutos_ativos || 0);
  atualizarSequenciaSemanal();
  elemento('nick-perfil').value = nick;
  atualizarSituacaoDosTermos();
}

function atualizarSequenciaSemanal() {
  const sequencia = Number(estado.aluno?.sequencia_atual || estado.aluno?.foguinho || 0);
  const bolinhas = elemento('dias-semana');
  if (bolinhas) {
    Array.from(bolinhas.children).forEach((bolinha, indice) => {
      bolinha.classList.toggle('ativo', indice >= 7 - Math.min(sequencia, 7));
    });
  }
  const mensagem = elemento('mensagem-sequencia');
  if (mensagem) {
    mensagem.textContent = sequencia > 0
      ? `${sequencia} ${sequencia === 1 ? 'dia seguido' : 'dias seguidos'} estudando. Continue para manter seu foguinho aceso.`
      : 'Acesse diariamente para manter seu foguinho aceso.';
  }
}

function atualizarPainelPerfil() {
  if (!estado.progresso) return;
  elemento('concluidos-progresso').textContent = formatarNumero(estado.progresso.desafios_concluidos || 0);
  if (elemento('indicador-licoes')) elemento('indicador-licoes').textContent = formatarNumero(estado.progresso.desafios_concluidos || 0);
  elemento('precisao-progresso').textContent = formatarNumero(estado.progresso.precisao || 0);
  elemento('respondidas-progresso').textContent = formatarNumero(estado.progresso.questoes_respondidas || 0);
  elemento('indicador-minutos').textContent = formatarNumero(estado.progresso.minutos_ativos || estado.aluno.minutos_ativos || 0);
  atualizarSequenciaSemanal();
}

// Busca de matéria e tema: as sugestões vêm da API aos poucos, sem carregar o catálogo inteiro.

// Texto sem acentos e em minúsculas, guardando onde cada letra estava no texto original
// (serve para destacar o trecho pesquisado mesmo quando o aluno digita sem acento).
function semAcentos(texto) {
  let normalizado = '';
  const posicoes = [];
  Array.from(String(texto || '')).forEach((letra, indice) => {
    const base = letra.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('pt-BR');
    for (const parte of base) { normalizado += parte; posicoes.push(indice); }
  });
  return { normalizado, posicoes, letras: Array.from(String(texto || '')) };
}

function destacar(texto, consulta) {
  const fragmento = document.createDocumentFragment();
  const palavras = semAcentos(consulta).normalizado.split(/[^a-z0-9]+/).filter(Boolean);
  const { normalizado, posicoes, letras } = semAcentos(texto);
  const marcado = new Array(letras.length).fill(false);
  palavras.forEach((palavra) => {
    let inicio = normalizado.indexOf(palavra);
    while (inicio !== -1) {
      for (let i = inicio; i < inicio + palavra.length; i += 1) marcado[posicoes[i]] = true;
      inicio = normalizado.indexOf(palavra, inicio + palavra.length);
    }
  });
  let trecho = '';
  let emDestaque = false;
  const fechar = () => {
    if (!trecho) return;
    if (emDestaque) { const marca = document.createElement('mark'); marca.textContent = trecho; fragmento.appendChild(marca); }
    else fragmento.appendChild(document.createTextNode(trecho));
    trecho = '';
  };
  letras.forEach((letra, indice) => {
    if (marcado[indice] !== emDestaque) { fechar(); emDestaque = marcado[indice]; }
    trecho += letra;
  });
  fechar();
  return fragmento;
}

// Campo de busca com sugestões: digitar, setas, Enter, Esc, clique fora e botão de limpar.
function criarCampoBusca({ chave, buscar, montarItem, aoEscolher, aoLimpar }) {
  const entrada = elemento(`entrada-${chave}`);
  const lista = elemento(`sugestoes-${chave}`);
  const botaoLimpar = elemento(`limpar-${chave}`);
  let itens = [];
  let ativo = -1;
  let temporizador = null;
  let pedido = 0;
  let escolhido = null;
  let consultaDosItens = null;   // texto que gerou as sugestões que estão na tela
  let escolherAoChegar = false;   // Enter apertado antes de as sugestões novas chegarem

  const abrir = () => { lista.hidden = false; entrada.setAttribute('aria-expanded', 'true'); };
  const fechar = () => {
    lista.hidden = true;
    entrada.setAttribute('aria-expanded', 'false');
    entrada.removeAttribute('aria-activedescendant');
    ativo = -1;
  };
  const mensagem = (texto) => {
    const item = document.createElement('li');
    item.className = 'mensagem-busca';
    item.setAttribute('role', 'option');
    item.setAttribute('aria-disabled', 'true');
    item.textContent = texto;
    lista.replaceChildren(item);
    itens = [];
    abrir();
  };
  const marcar = (indice) => {
    ativo = indice;
    Array.from(lista.children).forEach((item, i) => item.setAttribute('aria-selected', String(i === indice)));
    const atual = lista.children[indice];
    if (atual) { entrada.setAttribute('aria-activedescendant', atual.id); atual.scrollIntoView({ block: 'nearest' }); }
  };
  const escolher = (indice) => {
    const item = itens[indice];
    if (!item) return;
    escolhido = item;
    entrada.value = item.rotulo;
    botaoLimpar.hidden = false;
    fechar();
    aoEscolher(item);
  };
  const mostrar = (consulta) => {
    if (!itens.length) {
      mensagem(consulta ? `Nada encontrado para "${consulta}".` : 'Nenhuma opção disponível.');
      return;
    }
    lista.replaceChildren(...itens.map((item, indice) => {
      const opcao = document.createElement('li');
      opcao.id = `sugestoes-${chave}-${indice}`;
      opcao.setAttribute('role', 'option');
      opcao.setAttribute('aria-selected', 'false');
      opcao.append(...montarItem(item, consulta));
      opcao.addEventListener('mousedown', (evento) => { evento.preventDefault(); escolher(indice); });
      return opcao;
    }));
    abrir();
    marcar(0);
  };
  const pesquisar = async () => {
    if (entrada.disabled) return;
    const consulta = entrada.value.trim();
    const numero = ++pedido;
    mensagem('Buscando…');
    try {
      const encontrados = await buscar(consulta);
      if (numero !== pedido) return; // chegou a resposta de uma busca mais antiga
      itens = encontrados;
      consultaDosItens = consulta;
      mostrar(consulta);
      if (escolherAoChegar) {
        escolherAoChegar = false;
        if (itens.length) escolher(0);
      }
    } catch (erro) {
      if (numero === pedido) { escolherAoChegar = false; mensagem(erro.message); }
    }
  };

  entrada.addEventListener('input', () => {
    if (escolhido) { escolhido = null; aoLimpar(); }
    escolherAoChegar = false;
    botaoLimpar.hidden = !entrada.value;
    clearTimeout(temporizador);
    temporizador = setTimeout(pesquisar, 220);
  });
  entrada.addEventListener('focus', () => { if (!escolhido) pesquisar(); });
  entrada.addEventListener('keydown', (evento) => {
    if (evento.key === 'ArrowDown' || evento.key === 'ArrowUp') {
      evento.preventDefault();
      if (lista.hidden) { pesquisar(); return; }
      if (!itens.length) return;
      const passo = evento.key === 'ArrowDown' ? 1 : -1;
      marcar((ativo + passo + itens.length) % itens.length);
    } else if (evento.key === 'Enter') {
      evento.preventDefault(); // Enter escolhe a sugestão; nunca envia o formulário
      if (escolhido) return;   // já há um item escolhido e o texto não mudou: nada a fazer
      if (entrada.value.trim() !== consultaDosItens) {
        // Quem digita rápido aperta Enter antes de as sugestões novas chegarem. As que estão
        // na tela são de outro texto: busca agora e escolhe a primeira do resultado certo.
        clearTimeout(temporizador);
        escolherAoChegar = true;
        pesquisar();
        return;
      }
      if (!lista.hidden && itens.length) escolher(Math.max(ativo, 0));
    } else if (evento.key === 'Escape' && !lista.hidden) {
      evento.stopPropagation();
      fechar();
    }
  });
  botaoLimpar.addEventListener('click', () => { limpar(); entrada.focus(); });
  document.addEventListener('mousedown', (evento) => {
    if (!elemento(`busca-${chave}`).contains(evento.target)) fechar();
  });

  function limpar() {
    const tinha = escolhido;
    escolhido = null;
    itens = [];
    entrada.value = '';
    botaoLimpar.hidden = true;
    fechar();
    if (tinha) aoLimpar();
  }

  return {
    limpar,
    habilitar(sim, marcador) {
      entrada.disabled = !sim;
      if (marcador) entrada.placeholder = marcador;
    },
    definir(item) { itens = [item]; escolher(0); },
    focar() { entrada.focus(); },
  };
}

function linhaDeTexto(conteudo, etiqueta = 'span') {
  const no = document.createElement(etiqueta);
  if (typeof conteudo === 'string') no.textContent = conteudo; else no.append(conteudo);
  return no;
}

const campoMateria = criarCampoBusca({
  chave: 'materia',
  async buscar(consulta) {
    const dados = await api(`/api/learning/catalog?q=${encodeURIComponent(consulta)}&limite=10`);
    return (dados.materias || []).map((materia) => ({ ...materia, rotulo: materia.nome }));
  },
  montarItem(materia, consulta) {
    const detalhe = [materia.area, `${formatarNumero(materia.quantidade_temas)} temas`].filter(Boolean).join(' · ');
    return [linhaDeTexto(destacar(materia.nome, consulta), 'strong'), linhaDeTexto(detalhe, 'small')];
  },
  aoEscolher(materia) {
    estado.materiaEscolhida = materia;
    campoTema.limpar();
    campoTema.habilitar(true, `Pesquisar tema de ${materia.nome}...`);
    atualizarMapaSelecionado();
    campoTema.focar();
  },
  aoLimpar() {
    // Trocar de matéria limpa o tema: um desafio é sempre de uma matéria só.
    estado.materiaEscolhida = null;
    campoTema.limpar();
    campoTema.habilitar(false, 'Escolha a matéria primeiro');
    atualizarMapaSelecionado();
  },
});

const campoTema = criarCampoBusca({
  chave: 'tema',
  async buscar(consulta) {
    if (!estado.materiaEscolhida) return [];
    const dados = await api(`/api/learning/catalog/${estado.materiaEscolhida.id_materia}/themes?q=${encodeURIComponent(consulta)}&limite=10`);
    return (dados.temas || []).map((tema) => ({ ...tema, rotulo: tema.tema_pai ? `${tema.tema_pai.nome} › ${tema.nome}` : tema.nome }));
  },
  montarItem(tema, consulta) {
    let detalhe = tema.tema_pai ? `Subtema de ${tema.tema_pai.nome}` : 'Tema';
    if (!tema.tema_pai && tema.quantidade_subtemas) detalhe += ` · ${tema.quantidade_subtemas} subtemas`;
    if (tema.termo_relacionado) detalhe += ` · também: ${tema.termo_relacionado}`;
    return [linhaDeTexto(destacar(tema.nome, consulta), 'strong'), linhaDeTexto(detalhe, 'small')];
  },
  aoEscolher(tema) {
    estado.temaEscolhido = tema;
    atualizarMapaSelecionado();
    mostrarSubtemas(tema);
  },
  aoLimpar() {
    estado.temaEscolhido = null;
    elemento('subtemas-sugeridos').hidden = true;
    atualizarMapaSelecionado();
  },
});

// Depois de escolher um tema principal, mostra alguns subtemas para quem quiser focar em um deles.
async function mostrarSubtemas(tema) {
  const area = elemento('subtemas-sugeridos');
  const lista = elemento('lista-subtemas');
  area.hidden = true;
  if (tema.tema_pai || !tema.quantidade_subtemas) return;
  try {
    const dados = await api(`/api/learning/catalog/themes/${tema.id_tema}/subtopics?limite=12`);
    if (estado.temaEscolhido?.id_tema !== tema.id_tema) return;
    lista.replaceChildren(...(dados.temas || []).map((subtema) => {
      const botao = document.createElement('button');
      botao.type = 'button';
      botao.className = 'chip-subtema';
      botao.textContent = subtema.nome;
      botao.addEventListener('click', () => campoTema.definir({ ...subtema, rotulo: `${tema.nome} › ${subtema.nome}` }));
      return botao;
    }));
    area.hidden = !lista.children.length;
  } catch (erro) {
    console.warn('Não foi possível carregar os subtemas:', erro.message);
  }
}

document.querySelectorAll('input[name="quantidade"], input[name="dificuldade"]').forEach((campo) => campo.addEventListener('change', atualizarPreviaPontos));
atualizarPreviaPontos();

function temaSelecionado() {
  const tema = estado.temaEscolhido;
  if (!tema || !estado.materiaEscolhida) return null;
  return { ...tema, materia: estado.materiaEscolhida.nome, id_materia: estado.materiaEscolhida.id_materia };
}

function fasesPorQuantidade(quantidade) {
  const mapa = { 5: 5, 10: 4, 15: 3, 20: 2 };
  return mapa[Number(quantidade)] || 5;
}

function atualizarMapaSelecionado() {
  const tema = temaSelecionado();
  const materia = estado.materiaEscolhida?.nome || '';
  elemento('titulo-tema-caminho').textContent = tema ? tema.nome : (materia ? 'Escolha um tema' : 'Escolha uma matéria');
  elemento('rotulo-materia-caminho').textContent = tema ? materia : 'Seu caminho será montado aqui';
  const selecionadoId = tema ? tema.id_tema : null;
  const historico = (window.__historicoDesafios || []).filter((item) => !item.modo_revisao && !String(item.nome || "").startsWith("[REFAZER] "));
  const concluidos = historico.filter((item) => item.concluido && item.tema === (tema && tema.nome) && item.materia === materia).length;
  const nivel = concluidos + 1;
  elemento('nivel-caminho').textContent = `NÍVEL ${String(nivel).padStart(2, '0')}`;
  const mapa = elemento('mapa-aprendizado');
  const materiaVisual = String(materia || '').toLocaleLowerCase('pt-BR');
  const familiaVisual = materiaVisual.includes('matem') ? 0 : materiaVisual.includes('ciên') || materiaVisual.includes('biolog') ? 1 : materiaVisual.includes('hist') || materiaVisual.includes('geo') ? 2 : 3;
  const variacao = ((familiaVisual + (selecionadoId || 1) + nivel - 1) % 3);
  mapa.classList.remove('mapa-variacao-0', 'mapa-variacao-1', 'mapa-variacao-2');
  mapa.classList.add(`mapa-variacao-${variacao}`);
  const paletas = [
    ['#8b7cf6', '#c7bfff', '#f0edff'], ['#20b99a', '#91e2d1', '#e4fbf5'],
    ['#e5a33d', '#f4d18c', '#fff5df'], ['#4c9ee8', '#a9d4ff', '#e9f4ff'],
    ['#e879a9', '#f5b8d2', '#fff0f6'], ['#8aaf4f', '#cde4a5', '#f2f9e5']
  ];
  const paleta = paletas[(Math.abs(Number(selecionadoId || 0) * 3 + nivel + familiaVisual) % paletas.length)];
  mapa.style.setProperty('--destaque-mapa', paleta[0]);
  mapa.style.setProperty('--destaque-suave-mapa', paleta[1]);
  mapa.style.setProperty('--superficie-mapa', paleta[2]);
  elemento('painel-caminho').style.setProperty('--destaque-mapa', paleta[0]);
  elemento('painel-caminho').style.setProperty('--destaque-suave-mapa', paleta[1]);
  const posicoes = [
    [{ x: '10%', y: '66%' }, { x: '34%', y: '38%' }, { x: '62%', y: '64%' }, { x: '89%', y: '30%' }],
    [{ x: '10%', y: '34%' }, { x: '34%', y: '68%' }, { x: '62%', y: '36%' }, { x: '89%', y: '62%' }],
    [{ x: '10%', y: '64%' }, { x: '34%', y: '36%' }, { x: '62%', y: '66%' }, { x: '89%', y: '32%' }],
  ];
  const caminhos = [
    'M25 145 C75 145 75 70 145 90 S220 165 285 105 S365 45 425 95 S500 145 575 55',
    'M25 70 C90 45 90 160 180 145 S245 45 330 75 S440 155 575 130',
    'M25 140 C90 170 100 50 180 75 S260 160 345 130 S455 35 575 65',
  ];
  const pontosMapa = posicoes[variacao];
  const nos = document.querySelectorAll('.fase-mapa');
  nos.forEach((no, indice) => {
    no.style.setProperty('--x', pontosMapa[indice].x);
    no.style.setProperty('--y', pontosMapa[indice].y);
    no.classList.remove('fase-mapa-concluida', 'fase-mapa-atual', 'fase-mapa-bloqueada');
    if (indice < Math.min(concluidos, 3)) no.classList.add('fase-mapa-concluida');
    else if (indice === Math.min(concluidos, 3)) no.classList.add('fase-mapa-atual');
    else no.classList.add('fase-mapa-bloqueada');
    const numero = no.querySelector('span');
    if (numero) numero.textContent = no.classList.contains('fase-mapa-concluida') ? '✓' : String(indice + 1);
  });
  const linhaMapa = mapa.querySelector('.linha-caminho-mapa path');
  if (linhaMapa) linhaMapa.setAttribute('d', caminhos[variacao]);
  const meta = mapa.querySelector('.meta-mapa');
  if (meta) { meta.style.left = posicoes[variacao][3].x; meta.style.top = posicoes[variacao][3].y; }
  if (selecionadoId && tema) {
    const rotuloFase = document.querySelector('.fase-mapa-atual small');
    if (rotuloFase) rotuloFase.textContent = `Fase ${nivel}`;
  }
  atualizarPreviaPontos();
  const quantidade = Number(document.querySelector('input[name="quantidade"]:checked')?.value || 5);
  const numeroFases = fasesPorQuantidade(quantidade);
  if (elemento('contagem-jornada-caminho')) {
    elemento('contagem-jornada-caminho').textContent = tema
      ? `Sua jornada de ${numeroFases} desafios começa com ${tema.nome}. Cada fase concluída muda o mapa.`
      : 'Escolha uma matéria e um tema para preparar sua jornada.';
  }
}

function atualizarPreviaPontos() {
  const quantidade = Number(document.querySelector('input[name="quantidade"]:checked')?.value || 5);
  const dificuldade = document.querySelector('input[name="dificuldade"]:checked')?.value || 'normal';
  const pontosPorQuestao = dificuldade === 'facil' ? 10 : dificuldade === 'dificil' ? 20 : 15;
  const fases = fasesPorQuantidade(quantidade);
  if (elemento('pontos-possiveis')) elemento('pontos-possiveis').textContent = `Até ${formatarNumero(quantidade * pontosPorQuestao)} pontos por fase`;
  if (elemento('contagem-jornada')) elemento('contagem-jornada').textContent = `${fases} ${fases === 1 ? 'desafio' : 'desafios'}`;
  if (elemento('descricao-jornada')) elemento('descricao-jornada').textContent = `${quantidade} questões por fase · ${quantidade * fases} questões na jornada`;
  if (elemento('passos-jornada')) {
    const passos = elemento('passos-jornada');
    passos.replaceChildren();
    for (let indice = 0; indice < fases; indice += 1) {
      const passo = document.createElement('i');
      if (indice === 0) passo.classList.add('atual');
      passos.appendChild(passo);
    }
    passos.setAttribute('aria-label', `${fases} desafios planejados`);
  }
  if (elemento('contagem-jornada-caminho')) {
    const tema = temaSelecionado();
    elemento('contagem-jornada-caminho').textContent = tema
      ? `Jornada planejada: ${fases} desafios de ${quantidade} questões cada.`
      : `Você terá ${fases} desafios, com ${quantidade} questões em cada fase.`;
  }
}

// Ordem das dificuldades. O "Médio" da tela é o valor 'normal' no banco e na API.
const ESCADA_DIFICULDADE = ['facil', 'normal', 'dificil'];
const ROTULOS_DIFICULDADE = { facil: 'Fácil', normal: 'Médio', dificil: 'Difícil' };

// Aceita 'normal', "Normal" e "Médio", com ou sem acento.
function chaveDificuldade(valor) {
  const texto = String(valor || '').trim().toLocaleLowerCase('pt-BR');
  if (texto === 'facil' || texto === 'fácil' || texto === 'easy') return 'facil';
  if (texto === 'dificil' || texto === 'difícil' || texto === 'hard') return 'dificil';
  return 'normal';
}

function rotuloDificuldade(valor) {
  return ROTULOS_DIFICULDADE[chaveDificuldade(valor)];
}

// A dificuldade sobe um nível a cada fase concluída, até chegar em "Difícil".
function dificuldadeDaFase(dificuldadeBase, fase) {
  const base = ESCADA_DIFICULDADE.indexOf(chaveDificuldade(dificuldadeBase));
  const avanco = Math.max(1, Number(fase) || 1) - 1;
  return ESCADA_DIFICULDADE[Math.min(base + avanco, ESCADA_DIFICULDADE.length - 1)];
}

// Descobre a dificuldade inicial a partir da dificuldade e da fase atuais,
// para quando a jornada não está salva no navegador.
function dificuldadeBaseDaFase(dificuldadeAtual, fase) {
  const atual = ESCADA_DIFICULDADE.indexOf(chaveDificuldade(dificuldadeAtual));
  const avanco = Math.max(1, Number(fase) || 1) - 1;
  return ESCADA_DIFICULDADE[Math.max(atual - avanco, 0)];
}

// Limpa o estado do desafio em um lugar só, para não sobrar nada do desafio anterior.
function iniciarEstadoDesafio(dados, { modoMapa = true, modoRevisao = false, configuracao = null, revisao = null, respondidas = null, acertos = null, concluido = false } = {}) {
  estado.faseConcluida = Boolean(concluido);
  estado.desafio = dados.desafio;
  estado.temaAtual = dados.tema || { nome: dados.desafio.nome, materia: '' };
  estado.questoes = dados.questoes || [];
  estado.indiceQuestao = 0;
  estado.alternativaSelecionada = null;
  estado.respostaEnviada = false;
  estado.modoMapa = modoMapa;
  estado.modoRevisao = modoRevisao;
  estado.revisao = revisao;
  estado.faseReprovada = false;
  estado.questoesRespondidas = new Set();
  estado.acertosSeguidos = 0;
  estado.configuracaoBase = configuracao;
  estado.resultadoQuestoes = new Map();
  if (respondidas) {
    estado.questoes.forEach((q, i) => { if (respondidas[String(q.id_questao)]) estado.questoesRespondidas.add(i); });
  }
  if (acertos) {
    // Ao retomar, o servidor diz quais respostas estavam certas e o mapa volta marcado.
    estado.questoes.forEach((q, i) => { if (String(q.id_questao) in acertos) estado.resultadoQuestoes.set(i, Boolean(acertos[String(q.id_questao)])); });
  }
  if (!modoRevisao) {
    estado.faseAtiva = estado.desafio.nivel_mapa || 1;
    salvarJornada(estado.desafio.id_desafio, configuracao);
  }
}

async function criarProximoDesafio({ idTema, quantidade, dificuldadeBase, mostrarMapa = true, fasesPlanejadas = fasesPorQuantidade(quantidade), faseNaJornada = 1, novaTentativa = false }) {
  const fase = Number(faseNaJornada);
  const dificuldade = dificuldadeDaFase(dificuldadeBase, fase);
  const dados = await api('/api/learning/challenges', { method: 'POST', body: {
    id_tema: Number(idTema), quantidade_questoes: Number(quantidade), dificuldade, fase_jornada: fase,
    dificuldade_base: chaveDificuldade(dificuldadeBase),
  }});
  iniciarEstadoDesafio(dados, {
    modoMapa: mostrarMapa,
    configuracao: { idTema: Number(idTema), quantidade: Number(quantidade), dificuldadeBase, fasesPlanejadas: Number(fasesPlanejadas), faseNaJornada: Number(dados.desafio.nivel_mapa || faseNaJornada) },
  });
  // Valem a fase e a dificuldade que o servidor gravou (ele só libera a fase com a anterior aprovada).
  const dificuldadeFinal = chaveDificuldade(dados.desafio.dificuldade || dificuldade);
  if (novaTentativa) {
    mostrarAvisoRapido(`Nova tentativa da fase ${dados.desafio.nivel_mapa || fase}. Acerte pelo menos ${NOTA_MINIMA}% para avançar.`);
  } else if (dificuldadeFinal !== chaveDificuldade(dificuldadeBase)) {
    mostrarAvisoRapido(`Nova fase desbloqueada! A dificuldade subiu para ${rotuloDificuldade(dificuldadeFinal)}.`);
  } else {
    mostrarAvisoRapido(`Fase ${dados.desafio.nivel_mapa || fase} pronta. Bora continuar?`);
  }
  if (mostrarMapa) abrirMapaDesafio(); else abrirQuiz();
}

// Desafios normais já concluídos de um tema, na ordem da jornada.
function desafiosConcluidosDoTema(idTema) {
  const concluidos = (window.__historicoDesafios || [])
    .filter((item) => item.concluido && !item.modo_revisao && !String(item.nome || '').startsWith('[REFAZER] ') && Number(item.id_tema) === Number(idTema))
    .sort((a, b) => a.id_desafio - b.id_desafio);
  // Considera só a jornada mais recente (começa no último desafio de fase 1).
  let inicio = 0;
  concluidos.forEach((item, indice) => { if ((item.nivel_mapa || 1) === 1) inicio = indice; });
  return concluidos.slice(inicio);
}

async function atualizarBotoesDesafio() {
  const continuarTopo = elemento('ir-para-desafio');
  const refazer = elemento('botao-refazer-ultimo');
  try {
    const [ativo, historico] = await Promise.all([
      api('/api/learning/active-challenge'),
      api('/api/learning/history')
    ]);
    window.__historicoDesafios = historico.historico || [];
    estado.faseAtiva = ativo.ativo ? (ativo.desafio.nivel_mapa || 1) : 0;
    // "Refazer" começa sempre pelo desafio 1 do último tema concluído.
    const ultimo = window.__historicoDesafios
      .filter((item) => item.concluido && item.id_tema && !item.modo_revisao && !String(item.nome || '').startsWith('[REFAZER] '))
      .sort((a, b) => b.id_desafio - a.id_desafio)[0];
    let primeiro = null;
    if (ativo.ativo) {
      const desafioAtivo = ativo.desafio;
      if (Number(desafioAtivo.nivel_mapa || 1) > 1) {
        primeiro = desafiosConcluidosDoTema(desafioAtivo.id_tema)
          .filter((item) => item.id_desafio < desafioAtivo.id_desafio)[0] || null;
      }
    } else if (ultimo) {
      primeiro = desafiosConcluidosDoTema(ultimo.id_tema)[0] || null;
    }
    refazer.hidden = !primeiro;
    if (primeiro) {
      refazer.dataset.idHistorico = String(primeiro.id_desafio);
      refazer.innerHTML = '<span aria-hidden="true">↻</span> Refazer desafio 1 <small>Sem ganhar pontos</small>';
    }
    // Sem desafio em andamento e com fase ainda por fazer,
    // o botão vira "Continuar jornada" e cria a próxima fase.
    estado.proximaFasePendente = ativo.ativo ? null : proximaFasePendente(window.__historicoDesafios);
    const pendente = estado.proximaFasePendente;
    continuarTopo.hidden = !ativo.ativo && !pendente;
    continuarTopo.dataset.idDesafio = ativo.ativo ? String(ativo.desafio.id_desafio) : '';
    if (ativo.ativo) {
      const rotulo = ativo.todas_respondidas ? `Concluir fase ${ativo.desafio.nivel_mapa || 1}` : 'Continuar desafio';
      continuarTopo.innerHTML = `<span aria-hidden="true">▶</span> <span>${rotulo}</span> <span aria-hidden="true">→</span>`;
    } else if (pendente) {
      continuarTopo.innerHTML = `<span aria-hidden="true">▶</span> <span>Continuar jornada · Fase ${pendente.faseNaJornada + 1}/${pendente.fasesPlanejadas}</span> <span aria-hidden="true">→</span>`;
    } else {
      continuarTopo.innerHTML = '';
    }
    elemento('botao-criar-desafio').innerHTML = ativo.ativo
      ? '<span aria-hidden="true">✦</span> Criar um novo desafio <span aria-hidden="true">→</span>'
      : '<span aria-hidden="true">✦</span> Gerar desafio <span aria-hidden="true">→</span>';
    atualizarFundoMiniMapa();
  } catch (erro) { console.warn('Não foi possível atualizar as ações de desafio:', erro.message); }
}

async function continuarDesafioSalvo(idInformado = null) {
  try {
    const id = idInformado || elemento('ir-para-desafio').dataset.idDesafio;
    const dados = await api(`/api/learning/challenges/${id}`);
    const quantidadeSalva = Number(dados.desafio.quantidade_questoes || (dados.questoes || []).length || 5);
    const salva = lerJornadas()[dados.desafio.id_desafio];
    // A fase vem do servidor, então "continuar" volta sempre na fase certa.
    const configuracao = {
      idTema: Number(dados.desafio.id_tema),
      quantidade: quantidadeSalva,
      dificuldadeBase: salva?.dificuldadeBase || dificuldadeBaseDaFase(dados.desafio.dificuldade, dados.desafio.nivel_mapa || 1),
      fasesPlanejadas: fasesPorQuantidade(quantidadeSalva),
      faseNaJornada: Number(dados.desafio.nivel_mapa || 1),
    };
    iniciarEstadoDesafio(dados, { modoMapa: true, configuracao, respondidas: dados.respondidas || {}, acertos: dados.acertos || {}, concluido: dados.concluido });
    abrirMapaDesafio();
    mostrarAvisoRapido(estado.questoesRespondidas.size >= estado.questoes.length && !estado.faseConcluida
      ? 'Desafio restaurado. Todas as questões já foram respondidas: conclua a fase para salvar o resultado.'
      : 'Desafio restaurado. Continue de onde você parou.');
  } catch (erro) { mostrarAvisoRapido(`Não foi possível continuar: ${erro.message}`); }
}

// Próxima fase da jornada, para quem concluiu uma fase e saiu antes de começar a seguinte.
// Usa o histórico do servidor, então funciona depois de recarregar ou em outro aparelho.
function proximaFasePendente(historico) {
  const ultimo = (historico || [])
    .filter((item) => item.concluido && item.id_tema && !item.modo_revisao && !String(item.nome || '').startsWith('[REFAZER] '))
    .sort((a, b) => b.id_desafio - a.id_desafio)[0];
  if (!ultimo) return null;
  const quantidade = [5, 10, 15, 20].includes(Number(ultimo.quantidade_questoes)) ? Number(ultimo.quantidade_questoes) : 5;
  const fasesPlanejadas = fasesPorQuantidade(quantidade);
  const fase = Number(ultimo.nivel_mapa || 1);
  if (fase >= fasesPlanejadas) return null; // a jornada já terminou
  const salva = lerJornadas()[ultimo.id_desafio];
  return {
    idTema: Number(ultimo.id_tema),
    quantidade,
    dificuldadeBase: salva?.dificuldadeBase || dificuldadeBaseDaFase(ultimo.dificuldade, fase),
    fasesPlanejadas,
    faseNaJornada: fase,
  };
}

elemento('ir-para-desafio').addEventListener('click', async (evento) => {
  const botao = evento.currentTarget;
  if (botao.dataset.idDesafio) {
    continuarDesafioSalvo(botao.dataset.idDesafio);
    return;
  }
  if (!estado.proximaFasePendente) return;
  botao.disabled = true;
  try {
    estado.configuracaoBase = estado.proximaFasePendente;
    await seguirParaProximaFase();
  } finally {
    botao.disabled = false;
  }
});
elemento('botao-refazer-ultimo').addEventListener('click', async () => {
  const item = (window.__historicoDesafios || []).find((registro) => String(registro.id_desafio) === elemento('botao-refazer-ultimo').dataset.idHistorico && !registro.modo_revisao && !String(registro.nome || "").startsWith("[REFAZER] "));
  if (item) await refazerDesafio(item);
});

elemento('formulario-desafio').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  const tema = temaSelecionado();
  if (!tema) {
    mostrarAvisoRapido('Pesquise e escolha uma matéria e um tema antes de gerar o desafio.');
    return;
  }
  const botao = elemento('botao-criar-desafio');
  if (botao.disabled) return;
  botao.disabled = true;
  try {
    // Se já existe um desafio em andamento, pede confirmação antes de trocar.
    let ativo = { ativo: false };
    try { ativo = await api('/api/learning/active-challenge'); } catch (erro) { if (erro.status === 401) throw erro; }
    if (ativo.ativo) {
      const confirmou = await perguntar({
        titulo: 'Gerar um novo desafio?',
        texto: 'Você tem um desafio em andamento. Se gerar um novo, o atual fica sem terminar, mas os pontos que você já fez continuam valendo. Deseja continuar?',
        sim: 'Sim, gerar novo',
        nao: 'Não, manter o atual',
      });
      if (!confirmou) return;
      gravarSeguidos(0); // largar um desafio zera a contagem de seguidos
    }
    await gerarNovoDesafio(tema);
  } catch (erro) {
    mostrarAvisoRapido(erro.message);
  } finally {
    botao.disabled = false;
  }
});

async function gerarNovoDesafio(tema) {
  const botao = elemento('botao-criar-desafio');
  const textoOriginal = botao.innerHTML;
  botao.innerHTML = '<span class="brilho-botao">✦</span> Preparando questões…';
  try {
    // Desafio novo começa sempre na fase 1.
    const quantidade = Number(document.querySelector('input[name="quantidade"]:checked').value);
    const dificuldadeBase = document.querySelector('input[name="dificuldade"]:checked').value;
    const dificuldade = dificuldadeDaFase(dificuldadeBase, 1);
    const dados = await api('/api/learning/challenges', {
      method: 'POST',
      body: {
        id_tema: tema.id_tema, id_materia: tema.id_materia, quantidade_questoes: quantidade, dificuldade, fase_jornada: 1,
        dificuldade_base: chaveDificuldade(dificuldadeBase),
      },
    });
    iniciarEstadoDesafio(dados, {
      modoMapa: true,
      configuracao: { idTema: Number(tema.id_tema), quantidade, dificuldadeBase, fasesPlanejadas: fasesPorQuantidade(quantidade), faseNaJornada: 1 },
    });
    mostrarAvisoRapido('Seu mapa de desafio está pronto. Clique na primeira bolinha para começar.');
    abrirMapaDesafio();
  } finally {
    botao.innerHTML = textoOriginal;
  }
  await atualizarBotoesDesafio();
}

function abrirMapaDesafio() {
  if (!estado.questoes.length) {
    mostrarAvisoRapido('O desafio foi criado sem questões disponíveis. Tente novamente.');
    return;
  }
  elemento('janela-quiz').hidden = true;
  elemento('tela-mapa-desafio').hidden = false;
  document.body.classList.add('mapa-aberto');
  renderizarMapaDesafio();
  elemento('rolagem-mapa-espacial').scrollTop = 0;
  window.scrollTo({ top: 0, behavior: 'auto' });
}

// Cores do espaço. O fundo original é azul e cada fase muda o tom.
const PALETAS_ESPACO = [
  { nome: 'noite', matiz: 0, saturacao: 1, brilho: 1 },
  { nome: 'violeta', matiz: 38, saturacao: 1.9, brilho: 1.1 },
  { nome: 'magenta', matiz: 72, saturacao: 2, brilho: 1.1 },
  { nome: 'carmim', matiz: 112, saturacao: 2.2, brilho: 1.1 },
  { nome: 'ambar', matiz: 160, saturacao: 2.4, brilho: 1.15 },
  { nome: 'floresta', matiz: 270, saturacao: 2.1, brilho: 1.1 },
  { nome: 'turquesa', matiz: 305, saturacao: 2, brilho: 1.1 },
  { nome: 'oceano', matiz: 338, saturacao: 1.7, brilho: 1.1 },
];
// Cada pedaço mostra uma faixa diferente da imagem do espaço.
// As faixas pulam o astronauta da imagem, porque ele é desenhado à parte.
const FAIXAS_ESPACO = [820, 1500, 2420, 3040, 640, 1900, 2700, 1100];

// A cor depende da fase, não do id: a fase 1 tem sempre a cor original.
function aplicarCorEspaco(elementoAlvo, fase) {
  const cor = PALETAS_ESPACO[(Math.max(1, Number(fase) || 1) - 1) % PALETAS_ESPACO.length];
  elementoAlvo.style.setProperty('--matiz-espaco', `${cor.matiz}deg`);
  elementoAlvo.style.setProperty('--saturacao-espaco', cor.saturacao);
  elementoAlvo.style.setProperty('--brilho-espaco', cor.brilho);
  elementoAlvo.dataset.cor = cor.nome;
}

// O mapa pequeno da tela inicial usa a mesma cor da fase atual.
function atualizarFundoMiniMapa() {
  const fundo = elemento('fundo-mapa-aprendizado');
  if (!fundo) return;
  let fase = estado.faseAtiva;
  if (!fase) {
    const ultimo = (window.__historicoDesafios || [])
      .filter((item) => item.concluido && !item.modo_revisao && !String(item.nome || '').startsWith('[REFAZER] '))
      .sort((a, b) => b.id_desafio - a.id_desafio)[0];
    fase = ultimo ? ultimo.nivel_mapa || 1 : 1;
  }
  aplicarCorEspaco(fundo, fase);
}

function montarFundoEspacial(largura, altura) {
  const camada = elemento('fundo-mapa-espacial');
  if (!camada) return;
  camada.replaceChildren();
  const larguraPedaco = 1920;
  const total = Math.ceil(largura / larguraPedaco);
  for (let i = 0; i < total; i += 1) {
    const pedaco = document.createElement('div');
    pedaco.className = 'pedaco-mapa-espacial';
    pedaco.style.left = `${i * larguraPedaco}px`;
    // Não deixa a faixa passar do fim da imagem (5400px de altura).
    const faixa = Math.min(FAIXAS_ESPACO[i % FAIXAS_ESPACO.length], Math.max(0, 5400 - (altura || 560)));
    pedaco.style.backgroundPosition = `0 -${faixa}px`;
    camada.appendChild(pedaco);
  }
}

function renderizarMapaDesafio() {
  if (!estado.desafio || !estado.temaAtual || !estado.questoes.length) return;
  const quantidade = estado.questoes.length;
  const nivel = estado.desafio.nivel_mapa || 1;
  elemento('titulo-mapa-desafio').textContent = estado.temaAtual.nome;
  const jornada = estado.configuracaoBase;
  const faseJornada = nivel;
  const totalFases = jornada?.fasesPlanejadas || fasesPorQuantidade(quantidade);
  const proximaQuestao = indiceDaProximaQuestao();
  elemento('subtitulo-mapa-desafio').textContent = estado.modoRevisao
    ? `${estado.temaAtual.materia} · Revisão do desafio ${(estado.revisao?.pos || 0) + 1} · sem pontos`
    : `${estado.temaAtual.materia} · Fase ${nivel} · Jornada ${faseJornada}/${totalFases} — ${proximaQuestao >= 0 ? `próxima: Questão ${proximaQuestao + 1}` : 'todas respondidas'}`;
  elemento('contagem-progresso-mapa').textContent = `${estado.questoesRespondidas.size}/${quantidade}`;
  elemento('total-xp-mapa').textContent = `${formatarNumero(estado.aluno?.pontos || 0)} XP`;

  const moldura = elemento('mapa-espacial');
  const textoTema = `${estado.temaAtual.materia || ''} ${estado.temaAtual.nome || ''}`.toLocaleLowerCase('pt-BR');
  const familiaClasse = /matem|álgebra|geometr|cálculo/.test(textoTema) ? 'matematica' : /ciên|biolog|quím|físic|natureza/.test(textoTema) ? 'ciencias' : /hist|antig|medieval|civiliza/.test(textoTema) ? 'historia' : /geograf|clima|relevo|mapa/.test(textoTema) ? 'geografia' : /portugu|literat|inglês|língua|gramát/.test(textoTema) ? 'linguagens' : 'padrao';
  moldura.className = `mapa-espacial mapa-materia-${familiaClasse}`;
  // Cada fase tem a sua cor de espaço.
  aplicarCorEspaco(moldura, nivel);
  // O mapa ocupa a tela toda e só ganha rolagem se as bolinhas não couberem.
  const area = elemento('rolagem-mapa-espacial');
  const largura = Math.max(area.clientWidth || window.innerWidth, quantidade * 190 + 220);
  const altura = Math.max(area.clientHeight || 560, 420);
  moldura.style.setProperty('--largura-mapa', `${largura}px`);
  moldura.style.setProperty('--altura-mapa', `${altura}px`);
  montarFundoEspacial(largura, altura);
  const containerNos = elemento('lista-bolinhas');
  containerNos.replaceChildren();

  // Bolinhas e trilha usam as mesmas coordenadas, por isso ficam alinhadas.
  // A margem evita que a primeira e a última bolinha encostem na borda.
  const margemX = Math.min(90, largura * 0.06);

  const pontos = estado.questoes.map((_, indice) => {
    const progresso = quantidade === 1 ? 0.5 : indice / (quantidade - 1);
    return { x: margemX + progresso * (largura - margemX * 2), y: altura * (0.50 + Math.sin(indice * 1.42) * 0.27 + Math.cos(indice * 0.61) * 0.08) };
  });
  desenharTrilha(elemento('trilha-mapa-espacial'), pontos);

  estado.questoes.forEach((questao, indice) => {
    const respondida = estado.questoesRespondidas.has(indice);
    // Mostra o X na questão errada e o visto na questão certa.
    const errou = respondida && estado.resultadoQuestoes.get(indice) === false;
    const bloqueada = !respondida && indice !== proximaQuestao;
    const botao = document.createElement('button');
    botao.type = 'button';
    botao.className = `bolinha-mapa ${indice % 2 === 0 ? 'bolinha-lima' : 'bolinha-turquesa'}${respondida ? ' bolinha-respondida' : ''}${errou ? ' bolinha-errada' : ''}${bloqueada ? ' bolinha-bloqueada' : ''}${indice === proximaQuestao ? ' bolinha-atual' : ''}`;
    botao.style.left = `${pontos[indice].x}px`;
    botao.style.top = `${pontos[indice].y}px`;
    const situacao = respondida ? (errou ? ', respondida: errou' : ', respondida: acertou') : bloqueada ? ', bloqueada: responda as anteriores primeiro' : ', disponível';
    botao.setAttribute('aria-label', `Questão ${indice + 1}${situacao}`);
    if (bloqueada) botao.setAttribute('aria-disabled', 'true');
    botao.title = `Questão ${indice + 1}${respondida ? (errou ? ' — errou' : ' — acertou') : bloqueada ? ' — bloqueada' : ''}`;
    botao.innerHTML = `<span class="sombra-bolinha" aria-hidden="true"></span><span class="face-bolinha" aria-hidden="true"><i class="marca-play-bolinha fa-solid ${respondida ? (errou ? 'fa-xmark' : 'fa-check') : bloqueada ? 'fa-lock' : 'fa-play'}"></i></span><span class="legenda-bolinha">Questão ${indice + 1}</span>`;
    botao.addEventListener('click', () => {
      if (respondida) {
        mostrarAvisoRapido('Esta questão já foi concluída. Siga para a próxima bolinha.');
        return;
      }
      if (indice !== indiceDaProximaQuestao()) {
        mostrarAvisoRapido(`Siga a sequência: responda primeiro a Questão ${indiceDaProximaQuestao() + 1}.`);
        botao.classList.remove('bolinha-tremer');
        void botao.offsetWidth;
        botao.classList.add('bolinha-tremer');
        return;
      }
      estado.indiceQuestao = indice;
      abrirQuestaoDoMapa();
    });
    containerNos.appendChild(botao);
  });
  atualizarAcaoDoMapa();
}

// Botão principal do rodapé do mapa:
// - respondeu tudo e ainda não concluiu: "Concluir fase";
// - já concluiu a fase: "Próxima fase".
function atualizarAcaoDoMapa() {
  const botao = elemento('proxima-acao-mapa');
  if (!botao) return;
  const todasRespondidas = estado.questoes.length > 0 && estado.questoesRespondidas.size >= estado.questoes.length;
  botao.hidden = true;
  if (!estado.desafio || !todasRespondidas) return;
  if (estado.faseReprovada) {
    botao.textContent = 'Tentar a fase de novo ↻';
    botao.hidden = false;
    return;
  }
  if (!estado.faseConcluida) {
    botao.textContent = estado.modoRevisao ? 'Concluir revisão ✓' : 'Concluir fase ✓';
    botao.hidden = false;
    return;
  }
  const configuracao = estado.configuracaoBase;
  if (estado.modoRevisao || !configuracao) return;
  const faseAtual = Number(configuracao.faseNaJornada || 1);
  const total = Number(configuracao.fasesPlanejadas || fasesPorQuantidade(configuracao.quantidade));
  if (faseAtual >= total) return;
  botao.textContent = `Próxima fase ${faseAtual + 1}/${total} →`;
  botao.hidden = false;
}

elemento('proxima-acao-mapa').addEventListener('click', async () => {
  const botao = elemento('proxima-acao-mapa');
  botao.disabled = true;
  try {
    if (estado.faseReprovada) {
      await tentarFaseDeNovo();
    } else if (!estado.faseConcluida) {
      // Usa a mesma conclusão do quiz e mostra a tela de resultado.
      elemento('resultado-quiz').hidden = true;
      elemento('conteudo-quiz').hidden = true;
      await concluirQuiz();
      if (!elemento('resultado-quiz').hidden) {
        elemento('rotulo-tema-quiz').textContent = `${estado.temaAtual.materia} · ${estado.temaAtual.nome}`;
        elemento('total-xp-quiz').textContent = formatarNumero(estado.aluno?.pontos || 0);
        elemento('janela-quiz').hidden = false;
      } else {
        elemento('conteudo-quiz').hidden = false;
      }
    } else {
      await seguirParaProximaFase();
    }
  } finally {
    botao.disabled = false;
  }
});

// Desenha a trilha com elementos HTML. Cada ligação entre duas bolinhas é uma curva
// feita de vários trechos curtos e arredondados, um por cima do outro.
// O trecho até uma questão já respondida muda de cor.
function desenharTrilha(container, pontos) {
  container.replaceChildren();
  if (pontos.length < 2) return;
  const espessura = parseFloat(getComputedStyle(container).getPropertyValue('--espessura-trilha')) || 20;
  const camadaSombra = document.createElement('div');
  camadaSombra.className = 'camada-trilha camada-trilha-sombra';
  const camadaCor = document.createElement('div');
  camadaCor.className = 'camada-trilha';

  const criarPilula = (de, ate, classe) => {
    const pilula = document.createElement('span');
    pilula.className = classe;
    // Posição do meio do trecho. A largura soma a espessura para as pontas se encontrarem.
    pilula.style.left = `${((de.x + ate.x) / 2).toFixed(1)}px`;
    pilula.style.top = `${((de.y + ate.y) / 2).toFixed(1)}px`;
    pilula.style.width = `${(Math.hypot(ate.x - de.x, ate.y - de.y) + espessura).toFixed(1)}px`;
    pilula.style.setProperty('--angulo', `${Math.atan2(ate.y - de.y, ate.x - de.x).toFixed(4)}rad`);
    return pilula;
  };

  pontos.slice(0, -1).forEach((inicio, indice) => {
    const fim = pontos[indice + 1];
    const controle = { x: (inicio.x + fim.x) / 2, y: (inicio.y + fim.y) / 2 + (indice % 2 === 0 ? -58 : 58) };
    const cor = estado.questoesRespondidas.has(indice + 1) ? 'feito' : indice % 2 === 0 ? 'lima' : 'turquesa';
    // Trecho mais longo recebe mais pedaços, para a curva ficar lisa.
    const passos = Math.max(8, Math.ceil(Math.hypot(fim.x - inicio.x, fim.y - inicio.y) / espessura));
    let anterior = inicio;
    for (let passo = 1; passo <= passos; passo += 1) {

      const t = passo / passos;
      const atual = {
        x: (1 - t) * (1 - t) * inicio.x + 2 * (1 - t) * t * controle.x + t * t * fim.x,
        y: (1 - t) * (1 - t) * inicio.y + 2 * (1 - t) * t * controle.y + t * t * fim.y,
      };
      camadaSombra.appendChild(criarPilula(anterior, atual, 'trecho-trilha'));
      camadaCor.appendChild(criarPilula(anterior, atual, `trecho-trilha ${cor}`));
      anterior = atual;
    }
  });
  container.append(camadaSombra, camadaCor);
}

// A próxima questão é sempre a primeira que ainda não foi respondida.
function indiceDaProximaQuestao() {
  for (let i = 0; i < estado.questoes.length; i += 1) {
    if (!estado.questoesRespondidas.has(i)) return i;
  }
  return -1;
}

function abrirQuestaoDoMapa() {
  if (!estado.questoes[estado.indiceQuestao] || estado.indiceQuestao !== indiceDaProximaQuestao()) return;
  elemento('janela-quiz').hidden = false;
  elemento('conteudo-quiz').hidden = false;
  elemento('resultado-quiz').hidden = true;
  elemento('rotulo-tema-quiz').textContent = `${estado.temaAtual.materia} · ${estado.temaAtual.nome}`;
  elemento('total-xp-quiz').textContent = formatarNumero(estado.aluno.pontos || 0);
  mostrarQuestaoAtual();
}

function fecharMapaDesafio() {
  elemento('janela-quiz').hidden = true;
  elemento('tela-mapa-desafio').hidden = true;
  document.body.classList.remove('mapa-aberto');
  trocarVisao('estudo');
  atualizarPainel().catch((erro) => console.warn('Não foi possível atualizar o painel:', erro.message));
  atualizarBotoesDesafio();
}

// Redesenha o mapa quando a janela muda de tamanho.
let tempoRedimensionar = null;

window.addEventListener('resize', () => {
  clearTimeout(tempoRedimensionar);
  tempoRedimensionar = setTimeout(() => {
    if (!elemento('tela-mapa-desafio').hidden) renderizarMapaDesafio();
  }, 150);
});

elemento('sair-mapa-desafio').addEventListener('click', fecharMapaDesafio);
elemento('fechar-mapa-rodape').addEventListener('click', fecharMapaDesafio);

function aplicarTema(claro) {
  document.body.classList.toggle('tema-claro', claro);
  const chave = elemento('chave-tema');
  if (chave) chave.checked = claro;
}

elemento('chave-tema').addEventListener('change', (evento) => {
  const claro = evento.target.checked;
  aplicarTema(claro);
  try { localStorage.setItem('explainer-theme-v4', claro ? 'light' : 'dark'); } catch (_) {}
});
try { aplicarTema(localStorage.getItem('explainer-theme-v4') === 'light'); } catch (_) {}

function abrirConfiguracoes(abrir) {
  elemento('painel-config').hidden = !abrir;
  document.body.classList.toggle('config-aberto', abrir);
}
elemento('abrir-config').addEventListener('click', () => { abrirConfiguracoes(true); elemento('barra-lateral').classList.remove('aberto'); });
elemento('fechar-config').addEventListener('click', () => abrirConfiguracoes(false));
document.addEventListener('keydown', (evento) => { if (evento.key === 'Escape') abrirConfiguracoes(false); });
elemento('avatar-topo').addEventListener('click', () => { abrirConfiguracoes(false); trocarVisao('progresso'); });

function abrirQuiz() {
  if (!estado.questoes.length) {
    mostrarAvisoRapido('O desafio foi criado sem questões disponíveis. Tente novamente.');
    return;
  }
  elemento('janela-quiz').hidden = false;
  elemento('conteudo-quiz').hidden = false;
  elemento('resultado-quiz').hidden = true;
  elemento('rotulo-tema-quiz').textContent = `${estado.temaAtual.materia} · ${estado.temaAtual.nome}`;
  elemento('total-xp-quiz').textContent = formatarNumero(estado.aluno.pontos || 0);
  mostrarQuestaoAtual();
}

function mostrarQuestaoAtual() {
  const questao = estado.questoes[estado.indiceQuestao];
  estado.alternativaSelecionada = null;
  estado.respostaEnviada = false;
  estado.inicioQuestao = Date.now();
  elemento('contador-quiz').textContent = `Questão ${estado.indiceQuestao + 1} de ${estado.questoes.length}`;
  elemento('numero-questao-quiz').textContent = `Questão ${estado.indiceQuestao + 1}`;
  elemento('preenchimento-progresso-quiz').style.width = `${(estado.indiceQuestao / estado.questoes.length) * 100}%`;
  elemento('titulo-questao-quiz').textContent = questao.enunciado;
  elemento('dica-acao-quiz').textContent = 'Escolha uma alternativa';
  elemento('proxima-questao').disabled = true;
  elemento('proxima-questao').innerHTML = estado.modoMapa ? 'Continuar' : 'Confirmar resposta <span>→</span>';
  elemento('retorno-resposta').hidden = true;
  elemento('retorno-resposta').classList.remove('errada');
  const lista = elemento('lista-respostas');
  lista.replaceChildren();
  LETRAS.forEach((letra) => {
    const botao = document.createElement('button');
    botao.type = 'button';
    botao.className = 'opcao-resposta';
    botao.dataset.resposta = letra;
    const marcador = document.createElement('span');
    marcador.className = 'letra-resposta';
    marcador.textContent = letra;
    const texto = document.createElement('span');
    texto.className = 'texto-resposta';
    texto.textContent = questao.alternativas[letra] || 'Alternativa indisponível';
    botao.append(marcador, texto);
    botao.addEventListener('click', () => selecionarAlternativa(letra));
    lista.appendChild(botao);
  });
}

function selecionarAlternativa(letra) {
  if (estado.respostaEnviada) return;
  estado.alternativaSelecionada = letra;
  document.querySelectorAll('.opcao-resposta').forEach((botao) => {
    botao.classList.toggle('selecionada', botao.dataset.resposta === letra);
  });
  elemento('proxima-questao').disabled = false;
  elemento('dica-acao-quiz').textContent = `Alternativa ${letra} selecionada`;
}

elemento('proxima-questao').addEventListener('click', async () => {
  if (estado.respostaEnviada) {
    if (estado.modoMapa) {
      if (estado.questoesRespondidas.size >= estado.questoes.length) {
        await concluirQuiz();
      } else {
        elemento('janela-quiz').hidden = true;
        renderizarMapaDesafio();
        mostrarAvisoRapido('Questão concluída. Escolha a próxima bolinha no mapa.');
      }
      return;
    }
    if (estado.indiceQuestao < estado.questoes.length - 1) {
      estado.indiceQuestao += 1;
      mostrarQuestaoAtual();
    } else {
      await concluirQuiz();
    }
    return;
  }
  if (!estado.alternativaSelecionada) return;
  const botaoProximo = elemento('proxima-questao');
  botaoProximo.disabled = true;
  botaoProximo.textContent = 'Verificando…';
  const questao = estado.questoes[estado.indiceQuestao];
  const segundosGastos = Math.max(0, Math.round((Date.now() - estado.inicioQuestao) / 1000));
  try {

    const resultado = await api(`/api/learning/challenges/${estado.desafio.id_desafio}/answer`, {
      method: 'POST',
      body: { id_questao: questao.id_questao, alternativa: estado.alternativaSelecionada, segundos_gastos: segundosGastos },
    });
    estado.respostaEnviada = true;
    if (estado.modoMapa) estado.questoesRespondidas.add(estado.indiceQuestao);
    estado.resultadoQuestoes.set(estado.indiceQuestao, Boolean(resultado.correta));
    estado.aluno.pontos = resultado.pontos_totais;
    estado.aluno.minutos_ativos = Math.max(estado.aluno.minutos_ativos || 0, resultado.minutos_ativos || 0);
    elemento('total-xp-quiz').textContent = formatarNumero(estado.aluno.pontos || 0);
    atualizarIdentidade();
    document.querySelectorAll('.opcao-resposta').forEach((botao) => {
      botao.disabled = true;
      if (botao.dataset.resposta === resultado.alternativa_correta) botao.classList.add('correta');
      else if (botao.dataset.resposta === estado.alternativaSelecionada && !resultado.correta) botao.classList.add('incorreta');
    });
    const retorno = elemento('retorno-resposta');
    retorno.hidden = false;
    retorno.classList.toggle('errada', !resultado.correta);
    elemento('titulo-retorno').textContent = resultado.correta ? 'Resposta correta!' : `A resposta correta é ${resultado.alternativa_correta}.`;
    elemento('texto-retorno').textContent = resultado.explicacao;
    elemento('pontos-retorno').textContent = resultado.correta
      ? (resultado.pontos_ganhos > 0 ? `+${resultado.pontos_ganhos} pontos adicionados ao seu total.` : 'Revisão: esta tentativa não altera seus pontos.')
      : (resultado.pontos_ganhos < 0 ? `${Math.abs(resultado.pontos_ganhos)} pontos perdidos por errar. Continue tentando.` : 'Nenhum ponto nesta questão. Continue tentando.');
    if (resultado.correta) {
      estado.acertosSeguidos += 1;
      const elogios = [
        'Mandou bem! Você acabou de conquistar mais um acerto.',
        'Boa leitura da questão! Seu esforço está aparecendo.',
        'Acertou! Mais um passo na sua jornada.',
        'Resposta certa! Pode comemorar essa evolução.',
        'Aí sim! Você está construindo conhecimento de verdade.'
      ];
      mostrarAvisoRapido(elogios[(estado.acertosSeguidos - 1) % elogios.length]);
    } else {
      estado.acertosSeguidos = 0;
    }
    elemento('preenchimento-progresso-quiz').style.width = `${(estado.questoesRespondidas.size / estado.questoes.length) * 100}%`;
    elemento('dica-acao-quiz').textContent = estado.modoMapa
      ? (estado.questoesRespondidas.size >= estado.questoes.length ? 'Todas as questões foram respondidas.' : 'Volte ao mapa para escolher outra bolinha.')
      : (resultado.correta ? 'Boa! Vamos continuar.' : 'Revise a explicação e siga para a próxima.');
    botaoProximo.disabled = false;
    botaoProximo.innerHTML = estado.modoMapa
      ? (estado.questoesRespondidas.size >= estado.questoes.length ? 'Concluir fase →' : 'Voltar ao mapa')
      : (estado.indiceQuestao < estado.questoes.length - 1 ? 'Próxima questão <span>→</span>' : 'Ver resultado <span>→</span>');
    if (estado.modoMapa) renderizarMapaDesafio();
  } catch (erro) {
    mostrarAvisoRapido(erro.message);
    botaoProximo.disabled = false;
    botaoProximo.innerHTML = 'Tentar novamente <span>→</span>';
    // Erro 409: a questão já foi respondida (em outra aba, por exemplo) ou está fora de ordem.
    // Recarrega o desafio salvo para o mapa ficar igual ao servidor.
    if (erro.status === 409 && estado.desafio && estado.modoMapa && !estado.modoRevisao) {
      elemento('janela-quiz').hidden = true;
      await continuarDesafioSalvo(estado.desafio.id_desafio);
    }
  }
});

// Nota mínima para a fase ser aprovada. O servidor é quem decide; este valor só aparece nas mensagens.
const NOTA_MINIMA = 60;

// Elogios para quem foi muito bem na fase (80% de acertos ou mais).
const ELOGIOS_FASE = [
  { icone: '👍', titulo: 'Parabéns!', texto: 'Você concluiu um desafio. Você é bacana demais, continue assim!' },
  { icone: '🌟', titulo: 'Mandou muito bem!', texto: 'Mais um desafio concluído. Seu esforço está aparecendo!' },
  { icone: '🚀', titulo: 'Decolou!', texto: 'Desafio concluído! Você está evoluindo rápido.' },
  { icone: '💪', titulo: 'Que orgulho!', texto: 'Mais um desafio no bolso. Seu foco é inspirador!' },
];

// Título e texto da tela de resultado, conforme a faixa de desempenho que o servidor devolve.
function textosDoDesempenho(resultado) {
  const percentual = Number(resultado.percentual_acertos ?? Math.round((resultado.questoes_corretas / Math.max(resultado.quantidade_questoes, 1)) * 100));
  const minimo = Number(resultado.minimo_para_avancar || NOTA_MINIMA);
  if (resultado.desempenho === 'perfeito') {
    return { percentual, titulo: 'Desafio perfeito!', texto: 'Você acertou todas as questões. Continue mantendo esse ritmo.' };
  }
  if (resultado.desempenho === 'otimo') {
    return { percentual, titulo: 'Mandou muito bem!', texto: `Você acertou ${percentual}% das questões e a fase foi aprovada.` };
  }
  if (resultado.desempenho === 'reprovado') {
    return { percentual, titulo: 'Ainda não foi desta vez', texto: `Você acertou ${percentual}% das questões e precisa de pelo menos ${minimo}% para avançar. Seus pontos e seu histórico continuam guardados. Revise as explicações e tente a fase de novo.` };
  }
  return { percentual, titulo: 'Fase aprovada!', texto: `Você acertou ${percentual}% das questões, acima do mínimo de ${minimo}%. Revise os erros para ir ainda melhor na próxima.` };
}

// Escolhe a comemoração: jornada completa, 5 seguidos ou desafio comum, nessa ordem.
function comemorarConclusao({ ultimaDaJornada, resultado }) {
  const xpExtra = Number(resultado.bonus_conclusao || 0) + Number(resultado.bonus_jornada || 0);
  const seguidos = lerSeguidos() + 1;
  gravarSeguidos(seguidos);
  const fezCincoSeguidos = seguidos % 5 === 0;
  if (ultimaDaJornada) {
    confete();
    tocarSom('festa');
    mostrarElogio({
      icone: '🎉',
      titulo: 'Parabéns, jornada completa!',
      texto: fezCincoSeguidos
        ? `Você concluiu todos os desafios — e ${seguidos} seguidos! Que festa, você é demais!`
        : 'Você concluiu todos os desafios da jornada. Hora de comemorar!',
      xp: xpExtra,
      duracao: 9,
      tipo: 'festa',
    });
  } else if (fezCincoSeguidos) {
    tocarSom('uhul');
    mostrarElogio({
      icone: '🔥',
      titulo: `${seguidos} desafios seguidos!`,
      texto: 'Você concluiu 5 desafios em sequência. Está imparável!',
      xp: xpExtra,
      duracao: 7,
      tipo: 'sequencia',
    });
  } else if (resultado.desempenho === 'perfeito') {
    emojisSubindo('🎯');
    tocarSom('ok');
    mostrarElogio({ icone: '🎯', titulo: 'Na mosca!', texto: 'Você acertou todas as questões da fase!', xp: xpExtra, duracao: 6 });
  } else if (resultado.desempenho === 'otimo') {
    emojisSubindo('👍');
    tocarSom('ok');
    const elogio = ELOGIOS_FASE[Math.floor(Math.random() * ELOGIOS_FASE.length)];
    mostrarElogio({ ...elogio, xp: xpExtra, duracao: 6 });
  } else {
    // Passou perto do mínimo: confirma a aprovação sem exagerar no elogio.
    tocarSom('ok');
    mostrarElogio({ icone: '✅', titulo: 'Fase aprovada!', texto: `Você passou com ${resultado.percentual_acertos}% de acertos. Dá para ir ainda melhor na próxima!`, xp: xpExtra, duracao: 6 });
  }
}

// Fase abaixo da nota mínima: não há bônus nem elogio, e a próxima fase continua bloqueada.
// O histórico e os pontos das respostas ficam como estão.
async function mostrarFaseReprovada(resultado) {
  const textos = textosDoDesempenho({ ...resultado, desempenho: 'reprovado' });
  const fase = Number(estado.desafio?.nivel_mapa || 1);
  estado.faseReprovada = true;
  gravarSeguidos(0);
  fecharElogio(true);
  atualizarAcaoDoMapa();
  elemento('conteudo-quiz').hidden = true;
  elemento('resultado-quiz').hidden = false;
  elemento('preenchimento-progresso-quiz').style.width = '100%';
  elemento('resultado-quiz').querySelector('.mini-chamada').textContent = 'FASE NÃO APROVADA';
  elemento('titulo-resultado').textContent = textos.titulo;
  elemento('descricao-resultado').textContent = textos.texto;
  elemento('resultado-corretas').textContent = `${resultado.questoes_corretas}/${resultado.quantidade_questoes}`;
  elemento('pontos-resultado').previousElementSibling.textContent = 'Pontos nas respostas';
  elemento('pontos-resultado').textContent = `${resultado.pontos_ganhos < 0 ? '−' : '+'}${formatarNumero(Math.abs(resultado.pontos_ganhos || 0))}`;
  elemento('precisao-resultado').textContent = `${textos.percentual}%`;
  elemento('bonus-resultado').hidden = true;
  mostrarResumoDaFase();
  elemento('proximo-desafio').hidden = false;
  elemento('proximo-desafio').disabled = false;
  elemento('proximo-desafio').innerHTML = `Tentar a fase ${fase} de novo <span>↻</span>`;
  elemento('finalizar-quiz').textContent = 'Voltar ao painel';
  atualizarIdentidade();
  atualizarPainelPerfil();
  elemento('total-xp-quiz').textContent = formatarNumero(estado.aluno.pontos || 0);
  await atualizarPainel();
  await atualizarBotoesDesafio();
}

// Cria uma nova tentativa da mesma fase, com outras questões.
async function tentarFaseDeNovo() {
  const configuracao = estado.configuracaoBase;
  elemento('janela-quiz').hidden = true;
  if (!configuracao) { fecharMapaDesafio(); return; }
  try {
    await criarProximoDesafio({ ...configuracao, faseNaJornada: Number(estado.desafio?.nivel_mapa || configuracao.faseNaJornada || 1), mostrarMapa: true, novaTentativa: true });
  } catch (erro) {
    mostrarAvisoRapido(`Não foi possível criar a nova tentativa: ${erro.message}`);
    fecharMapaDesafio();
    return;
  }
  await atualizarBotoesDesafio();
}

// Resumo da fase na tela de resultado: número da questão com acerto ou erro.
function mostrarResumoDaFase() {
  const lista = elemento('lista-revisao-resultado');
  lista.replaceChildren();
  estado.questoes.forEach((_, indice) => {
    if (!estado.resultadoQuestoes.has(indice)) return;
    const acertou = estado.resultadoQuestoes.get(indice);
    const item = document.createElement('li');
    item.className = acertou ? 'acertou' : 'errou';
    item.textContent = `${indice + 1} ${acertou ? '✓' : '✗'}`;
    item.setAttribute('aria-label', `Questão ${indice + 1}: ${acertou ? 'acertou' : 'errou'}`);
    lista.appendChild(item);
  });
  elemento('revisao-resultado').hidden = !lista.children.length;
}

async function concluirQuiz() {
  const botao = elemento('proxima-questao');
  botao.disabled = true;
  botao.textContent = 'Salvando resultado…';
  const ehRevisao = Boolean(estado.modoRevisao);
  const jornadaAtual = Number(estado.configuracaoBase?.faseNaJornada || 1);
  const totalJornada = Number(estado.configuracaoBase?.fasesPlanejadas || fasesPorQuantidade(estado.questoes.length));
  const ultimaDaJornada = !ehRevisao && jornadaAtual >= totalJornada;
  try {
    const resultado = await api(`/api/learning/challenges/${estado.desafio.id_desafio}/complete`, { method: 'POST', body: { jornada_concluida: ultimaDaJornada } });
    estado.progresso = resultado.progresso;
    estado.aluno.pontos = resultado.pontos_totais;
    if (resultado.reprovado) { await mostrarFaseReprovada(resultado); return; }
    estado.faseConcluida = true;
    atualizarAcaoDoMapa();
    elemento('conteudo-quiz').hidden = true;
    elemento('resultado-quiz').hidden = false;
    elemento('pontos-resultado').previousElementSibling.textContent = 'Pontos ganhos';
    elemento('resultado-quiz').querySelector('.mini-chamada').textContent = 'FASE CONCLUÍDA';
    elemento('resultado-corretas').textContent = `${resultado.questoes_corretas}/${resultado.quantidade_questoes}`;
    elemento('pontos-resultado').textContent = `${resultado.pontos_ganhos < 0 ? '−' : '+'}${formatarNumero(Math.abs(resultado.pontos_ganhos))}`;
    const textos = ehRevisao
      ? { percentual: Number(resultado.percentual_acertos || 0), titulo: 'Revisão concluída', texto: `Você acertou ${resultado.percentual_acertos}% das questões nesta revisão. Ela não vale pontos.` }
      : textosDoDesempenho(resultado);
    elemento('precisao-resultado').textContent = `${textos.percentual}%`;
    elemento('titulo-resultado').textContent = textos.titulo;
    elemento('descricao-resultado').textContent = textos.texto;
    elemento('bonus-resultado').hidden = !(resultado.bonus_perfeito > 0);
    mostrarResumoDaFase();
    elemento('preenchimento-progresso-quiz').style.width = '100%';

    elemento('proximo-desafio').disabled = false;
    if (ehRevisao) {
      const revisao = estado.revisao || { lista: [], pos: 0 };
      const proximo = revisao.lista[revisao.pos + 1] || null;
      elemento('proximo-desafio').hidden = !proximo;
      if (proximo) elemento('proximo-desafio').innerHTML = `Refazer desafio ${revisao.pos + 2} <span>→</span>`;
      elemento('finalizar-quiz').textContent = 'Voltar ao painel';
    } else {
      elemento('proximo-desafio').hidden = false;
      elemento('proximo-desafio').innerHTML = jornadaAtual >= totalJornada
        ? 'Concluir jornada <span>✓</span>'
        : `Próxima fase ${jornadaAtual + 1}/${totalJornada} <span>→</span>`;
      elemento('finalizar-quiz').textContent = 'Voltar ao mapa';
    }
    atualizarIdentidade();
    atualizarPainelPerfil();
    elemento('total-xp-quiz').textContent = formatarNumero(estado.aluno.pontos || 0);

    if (ehRevisao) {
      mostrarAvisoRapido('Revisão concluída. Esta tentativa não concede pontos.');
      const revisao = estado.revisao || { lista: [], pos: 0 };
      const numeroProximo = revisao.pos + 2;
      const totalFases = fasesPorQuantidade(estado.questoes.length);
      if (!revisao.lista[revisao.pos + 1] && numeroProximo <= totalFases) {
        avisar(`Desafio ${numeroProximo} ainda bloqueado`, `Conclua o desafio ${numeroProximo} no seu progresso normal para conseguir refazê-lo.`);
      }
    } else if (!resultado.ja_concluido) {
      comemorarConclusao({ ultimaDaJornada, resultado });
    }
    await atualizarPainel();
    await atualizarBotoesDesafio();
  } catch (erro) {
    mostrarAvisoRapido(erro.message);
    botao.disabled = false;
    botao.innerHTML = 'Tentar salvar resultado <span>→</span>';
  }
}

elemento('finalizar-quiz').addEventListener('click', async () => {
  elemento('janela-quiz').hidden = true;
  if (estado.modoRevisao || estado.faseReprovada) {
    fecharMapaDesafio();
    return;
  }
  if (estado.modoMapa && !elemento('tela-mapa-desafio').hidden) {
    renderizarMapaDesafio();
  } else {
    trocarVisao('estudo');
  }
  await atualizarPainel();
  if (estado.modoMapa && !elemento('tela-mapa-desafio').hidden) renderizarMapaDesafio();
});

elemento('fechar-quiz').addEventListener('click', () => {
  if ((estado.modoRevisao || estado.faseReprovada) && !elemento('resultado-quiz').hidden) { elemento('janela-quiz').hidden = true; fecharMapaDesafio(); return; }
  if (estado.modoRevisao) { elemento('janela-quiz').hidden = true; renderizarMapaDesafio(); return; }
  if (estado.desafio && !elemento('resultado-quiz').hidden) {
    elemento('janela-quiz').hidden = true;
    renderizarMapaDesafio();
    return;
  }
  // A resposta já está salva no servidor, então pode fechar direto.
  const confirmou = estado.respostaEnviada || window.confirm('Voltar ao mapa? A resposta desta questão só será salva quando você confirmar.');
  if (confirmou) {
    elemento('janela-quiz').hidden = true;
    renderizarMapaDesafio();
  }
});

async function atualizarPainel() {
  const tarefas = await Promise.allSettled([
    api('/api/learning/me'),
    api(`/api/learning/ranking?limite=${limiteDoRankingAtual()}`),
    api('/api/learning/history'),
  ]);
  if (tarefas[0].status === 'fulfilled') {
    estado.aluno = tarefas[0].value.aluno;
    estado.progresso = tarefas[0].value.progresso;
    atualizarIdentidade();
    atualizarPainelPerfil();
  }
  if (tarefas[1].status === 'fulfilled') renderizarRanking(tarefas[1].value);
  if (tarefas[2].status === 'fulfilled') {
    window.__historicoDesafios = tarefas[2].value.historico || [];
    renderizarHistorico(tarefas[2].value.historico || []);
    atualizarMapaSelecionado();
  }
}

// ---------- Ranking ----------
// O mesmo componente aparece na tela inicial e na tela "Ranking". Ele abre com o top 5
// (GET /api/learning/ranking?limite=5) e, no botão "Ver mais posições", busca o top 100
// (?limite=100) e mostra do 6º em diante abaixo dos cinco primeiros, no mesmo card.
const LIMITE_INICIAL_RANKING = 5;
const LIMITE_COMPLETO_RANKING = 100;
const ranking = {
  dados: null, // última resposta recebida (top 5 ou top 100)
  completo: null, // resposta do top 100; volta a null quando os dados ficam velhos
  instancias: [],
};

function montarRanking(raiz) {
  const chave = raiz.dataset.ranking;
  const idTitulo = `titulo-ranking-${chave}`;
  const idExtra = `ranking-extra-${chave}`;
  raiz.setAttribute('aria-labelledby', idTitulo);
  raiz.innerHTML = `
    <div class="cabecalho-ranking">
      <div><div class="mini-chamada"></div><h2 id="${idTitulo}"></h2><p>Os estudantes com maior pontuação</p></div>
      <span class="pilula-suave contagem-ranking" hidden></span>
    </div>
    <div class="corpo-ranking">
      <div class="coluna-lista-ranking">
        <ol class="lista-ranking lista-topo-ranking" aria-busy="true"></ol>
        <div class="expansao-ranking" id="${idExtra}" inert>
          <div class="interior-expansao">
            <ol class="lista-ranking lista-extra-ranking" start="6"></ol>
            <p class="nota-ranking" hidden></p>
          </div>
        </div>
        <p class="erro-ranking" role="alert" hidden></p>
        <button class="botao-expandir-ranking" type="button" aria-expanded="false" aria-controls="${idExtra}" hidden>
          <span class="texto-botao-ranking">Ver mais posições</span><i class="fa-solid fa-chevron-down" aria-hidden="true"></i>
        </button>
      </div>
      <aside class="sua-posicao-ranking" aria-label="Sua posição no ranking" hidden></aside>
    </div>
    <p class="so-leitor-de-tela" aria-live="polite"></p>`;
  raiz.querySelector('.mini-chamada').textContent = raiz.dataset.chamada || 'COMUNIDADE';
  raiz.querySelector('h2').textContent = raiz.dataset.titulo || 'Ranking';
  const instancia = {
    raiz,
    expandido: false,
    carregando: false,
    topo: raiz.querySelector('.lista-topo-ranking'),
    expansao: raiz.querySelector('.expansao-ranking'),
    extra: raiz.querySelector('.lista-extra-ranking'),
    nota: raiz.querySelector('.nota-ranking'),
    erro: raiz.querySelector('.erro-ranking'),
    botao: raiz.querySelector('.botao-expandir-ranking'),
    posicao: raiz.querySelector('.sua-posicao-ranking'),
    contagem: raiz.querySelector('.contagem-ranking'),
    aviso: raiz.querySelector('[aria-live]'),
  };
  mostrarEsqueletoRanking(instancia);
  instancia.botao.addEventListener('click', () => alternarRanking(instancia));
  return instancia;
}

function mostrarEsqueletoRanking(instancia) {
  instancia.topo.replaceChildren();
  for (let i = 0; i < LIMITE_INICIAL_RANKING; i += 1) {
    const item = document.createElement('li');
    item.className = 'item-ranking esqueleto';
    item.setAttribute('aria-hidden', 'true');
    item.innerHTML = '<span></span><span class="avatar-ranking"></span><span></span><span></span>';
    instancia.topo.appendChild(item);
  }
}

function criarItemRanking(item, ordem) {
  const linha = document.createElement('li');
  const souEu = Boolean(estado.aluno && item.id_aluno === estado.aluno.id_aluno);
  const podio = item.posicao <= 3;
  linha.className = `item-ranking${podio ? ` podio podio-${item.posicao}` : ''}${souEu ? ' voce' : ''}`;
  linha.style.setProperty('--ordem', ordem);

  const posicao = document.createElement('span');
  posicao.className = 'posicao-ranking';
  posicao.setAttribute('aria-label', `${item.posicao}º lugar`);
  if (podio) {
    const medalha = document.createElement('span');
    medalha.className = `medalha-ranking ${['ouro', 'prata', 'bronze'][item.posicao - 1]}`;
    medalha.textContent = item.posicao;
    medalha.setAttribute('aria-hidden', 'true');
    posicao.appendChild(medalha);
  } else {
    posicao.textContent = `${item.posicao}º`;
  }

  const avatar = document.createElement('span');
  avatar.className = 'avatar-ranking';
  avatar.setAttribute('aria-hidden', 'true');
  avatar.textContent = (item.nick || 'E').charAt(0).toUpperCase();

  const nome = document.createElement('span');
  nome.className = 'nome-item-ranking';
  const titulo = document.createElement('strong');
  if (item.posicao === 1) {
    const coroa = document.createElement('i');
    coroa.className = 'fa-solid fa-crown coroa-ranking';
    coroa.title = 'Primeiro lugar';
    coroa.setAttribute('aria-hidden', 'true');
    titulo.appendChild(coroa);
  }
  const apelido = document.createElement('span');
  apelido.textContent = item.nick || 'Estudante';
  titulo.appendChild(apelido);
  if (souEu) {
    const selo = document.createElement('em');
    selo.className = 'selo-voce';
    selo.textContent = 'Você';
    titulo.appendChild(selo);
  }
  nome.appendChild(titulo);
  if (item.posicao <= LIMITE_INICIAL_RANKING) {
    const detalhe = document.createElement('small');
    const dias = item.sequencia_atual || 0;
    detalhe.textContent = `${dias} ${dias === 1 ? 'dia' : 'dias'} de sequência`;
    nome.appendChild(detalhe);
  }

  const pontos = document.createElement('span');
  pontos.className = 'pontos-ranking';
  pontos.textContent = formatarNumero(item.pontos);
  const unidade = document.createElement('small');
  unidade.textContent = 'pts';
  pontos.appendChild(unidade);

  linha.append(posicao, avatar, nome, pontos);
  return linha;
}

// Recebe a resposta da API (top 5 ou top 100) e atualiza todos os rankings da página.
function renderizarRanking(dados) {
  ranking.dados = dados;
  ranking.completo = dados.limite === LIMITE_COMPLETO_RANKING ? dados : null;
  const posicaoUsuario = dados.posicao_usuario;
  if (elemento('indicador-posicao')) elemento('indicador-posicao').textContent = posicaoUsuario ? `#${posicaoUsuario}` : '#—';
  if (elemento('posicao-topo')) elemento('posicao-topo').textContent = posicaoUsuario ? `#${posicaoUsuario}` : '#—';
  ranking.instancias.forEach((instancia) => desenharRanking(instancia));
}

function desenharRanking(instancia) {
  const dados = ranking.dados;
  if (!dados) return;
  const itens = dados.itens || [];
  const total = dados.total_participantes ?? dados.total_alunos ?? itens.length;
  instancia.topo.removeAttribute('aria-busy');
  instancia.topo.replaceChildren();
  if (!itens.length) {
    const vazio = document.createElement('li');
    vazio.className = 'estado-vazio';
    vazio.textContent = 'Ainda não temos participantes suficientes para montar o ranking. Seja um dos primeiros a estudar!';
    instancia.topo.appendChild(vazio);
  }
  itens.slice(0, LIMITE_INICIAL_RANKING).forEach((item, indice) => instancia.topo.appendChild(criarItemRanking(item, indice)));
  instancia.contagem.hidden = !total;
  instancia.contagem.textContent = `${formatarNumero(total)} ${total === 1 ? 'participante' : 'participantes'}`;
  if (ranking.completo) preencherExtraRanking(instancia);
  desenharSuaPosicao(instancia, total);
  atualizarBotaoRanking(instancia);
}

function preencherExtraRanking(instancia) {
  const dados = ranking.completo;
  const restantes = (dados.itens || []).slice(LIMITE_INICIAL_RANKING);
  instancia.extra.replaceChildren(...restantes.map((item, indice) => criarItemRanking(item, indice)));
  const total = dados.total_participantes ?? restantes.length + LIMITE_INICIAL_RANKING;
  instancia.nota.hidden = false;
  instancia.nota.textContent = dados.tem_mais
    ? `Mostrando os ${formatarNumero(dados.retornados)} primeiros de ${formatarNumero(total)} participantes.`
    : 'Você está vendo todos os participantes disponíveis no ranking.';
}

function desenharSuaPosicao(instancia, total) {
  const usuario = ranking.dados?.usuario_atual;
  const caixa = instancia.posicao;
  caixa.hidden = !usuario;
  if (!usuario) return;
  caixa.replaceChildren();
  const chamada = document.createElement('div');
  chamada.className = 'mini-chamada';
  chamada.textContent = 'SUA POSIÇÃO';
  caixa.appendChild(chamada);
  if (!usuario.posicao) {
    const texto = document.createElement('p');
    texto.className = 'detalhe-posicao';
    texto.textContent = 'Você ainda não está no ranking. Responda sua primeira questão para aparecer aqui.';
    caixa.appendChild(texto);
    return;
  }
  const numero = document.createElement('strong');
  numero.className = 'numero-posicao';
  numero.textContent = `${usuario.posicao}º`;
  const lugar = document.createElement('small');
  lugar.textContent = 'lugar';
  numero.appendChild(lugar);
  const pontos = document.createElement('span');
  pontos.className = 'pontos-posicao';
  pontos.textContent = `${formatarNumero(usuario.pontos)} pts`;
  const detalhe = document.createElement('p');
  detalhe.className = 'detalhe-posicao';
  detalhe.textContent = usuario.posicao <= LIMITE_INICIAL_RANKING
    ? `Você está no top 5 entre ${formatarNumero(total)} participantes.`
    : `Entre ${formatarNumero(total)} participantes.`;
  caixa.append(numero, pontos, detalhe);
}

function atualizarBotaoRanking(instancia) {
  const { botao, expansao } = instancia;
  const dados = ranking.dados;
  const total = dados ? (dados.total_participantes ?? dados.total_alunos ?? 0) : 0;
  // Com 5 participantes ou menos já aparece todo mundo: não há o que expandir.
  botao.hidden = total <= LIMITE_INICIAL_RANKING;
  expansao.classList.toggle('aberta', instancia.expandido);
  expansao.inert = !instancia.expandido;
  botao.setAttribute('aria-expanded', String(instancia.expandido));
  // aria-disabled em vez de disabled: um botão desligado perde o foco do teclado.
  botao.setAttribute('aria-disabled', String(instancia.carregando));
  botao.setAttribute('aria-busy', String(instancia.carregando));
  const texto = botao.querySelector('.texto-botao-ranking');
  const icone = botao.querySelector('i');
  if (instancia.carregando) {
    texto.textContent = 'Carregando posições…';
    icone.className = 'fa-solid fa-circle-notch fa-spin';
  } else if (instancia.expandido) {
    texto.textContent = 'Ver menos posições';
    icone.className = 'fa-solid fa-chevron-up';
  } else if (!instancia.erro.hidden) {
    texto.textContent = 'Tentar novamente';
    icone.className = 'fa-solid fa-rotate-right';
  } else {
    texto.textContent = 'Ver mais posições';
    icone.className = 'fa-solid fa-chevron-down';
  }
}

async function alternarRanking(instancia) {
  if (instancia.carregando) return; // evita cliques repetidos enquanto carrega
  if (instancia.expandido) {
    instancia.expandido = false;
    atualizarBotaoRanking(instancia);
    instancia.aviso.textContent = 'Mostrando os 5 primeiros colocados.';
    return;
  }
  instancia.erro.hidden = true;
  if (!ranking.completo) {
    instancia.carregando = true;
    atualizarBotaoRanking(instancia);
    try {
      const dados = await api(`/api/learning/ranking?limite=${LIMITE_COMPLETO_RANKING}`);
      // Os cinco primeiros também são redesenhados com a resposta nova, para a lista
      // inteira vir da mesma consulta (sem posição repetida ou pulada).
      renderizarRanking(dados);
    } catch (erro) {
      instancia.carregando = false;
      instancia.erro.textContent = 'Não foi possível carregar mais posições. Verifique sua conexão e tente novamente.';
      instancia.erro.hidden = false;
      atualizarBotaoRanking(instancia);
      return;
    }
    instancia.carregando = false;
  }
  preencherExtraRanking(instancia);
  instancia.expandido = true;
  atualizarBotaoRanking(instancia);
  instancia.aviso.textContent = `Mostrando até ${LIMITE_COMPLETO_RANKING} colocados.`;
}

// Ao sair da conta, o ranking volta ao estado inicial (o próximo aluno não vê o anterior).
function limparRanking() {
  ranking.dados = null;
  ranking.completo = null;
  ranking.instancias.forEach((instancia) => {
    instancia.expandido = false;
    instancia.carregando = false;
    instancia.erro.hidden = true;
    instancia.extra.replaceChildren();
    instancia.nota.hidden = true;
    instancia.posicao.hidden = true;
    instancia.contagem.hidden = true;
    mostrarEsqueletoRanking(instancia);
    atualizarBotaoRanking(instancia);
  });
}

function limiteDoRankingAtual() {
  return ranking.instancias.some((instancia) => instancia.expandido) ? LIMITE_COMPLETO_RANKING : LIMITE_INICIAL_RANKING;
}

ranking.instancias = [...document.querySelectorAll('[data-ranking]')].map(montarRanking);

function renderizarHistorico(historico) {
  const previa = elemento('lista-previa-recentes');
  previa.replaceChildren();
  const corpo = elemento('corpo-tabela-historico');
  corpo.replaceChildren();
  if (!historico.length) {
    previa.innerHTML = '<div class="estado-vazio">Você ainda não concluiu um desafio. Seu primeiro está a um clique.</div>';
    const linha = corpo.insertRow();
    linha.insertCell().colSpan = 6;
    linha.cells[0].textContent = 'Seu histórico aparecerá aqui depois do primeiro desafio.';
    return;
  }
  historico.slice(0, 3).forEach((item) => {
    const linha = document.createElement('div');
    linha.className = 'linha-recentes';
    const icone = document.createElement('span');
    icone.className = 'icone-recentes';
    icone.textContent = item.concluido ? '✓' : '◷';
    const copia = document.createElement('span');
    copia.className = 'texto-recentes';
    const titulo = document.createElement('strong');
    titulo.textContent = item.nome;
    const subtitulo = document.createElement('span');
    subtitulo.textContent = `${item.materia} · ${rotuloDificuldade(item.dificuldade)}`;
    copia.append(titulo, subtitulo);
    const pontos = document.createElement('span');
    pontos.className = 'pontos-recentes';
    const obtidos = Number(item.pontuacao_obtida || 0);
    pontos.textContent = `${obtidos < 0 ? '−' : '+'}${formatarNumero(Math.abs(obtidos))}`;
    linha.append(icone, copia, pontos);
    previa.appendChild(linha);
  });
  historico.forEach((item) => {
    const linha = corpo.insertRow();
    const nome = linha.insertCell();
    nome.textContent = item.concluido || item.modo_revisao ? item.nome : `${item.nome} (não aprovada)`;
    const tema = linha.insertCell();
    tema.textContent = `${item.materia} · ${item.tema}`;
    const dificuldade = linha.insertCell();
    const etiqueta = document.createElement('span');
    const chave = chaveDificuldade(item.dificuldade);
    etiqueta.className = `etiqueta-dificuldade ${chave === 'dificil' ? 'dificil' : chave === 'normal' ? 'normal' : ''}`;
    etiqueta.textContent = rotuloDificuldade(item.dificuldade);
    dificuldade.appendChild(etiqueta);
    linha.insertCell().textContent = `${formatarNumero(item.pontuacao_obtida || 0)} pts`;
    linha.insertCell().textContent = formatarData(item.data_realizacao);
    const acao = linha.insertCell();
    const refazer = document.createElement('button');
    refazer.type = 'button';
    refazer.className = 'botao-refazer-historico';
    refazer.textContent = 'Refazer ↻';
    refazer.disabled = !item.id_tema || Boolean(item.modo_revisao) || !item.concluido;
    refazer.title = 'Criar uma nova tentativa com a mesma matéria, tema e dificuldade';
    refazer.addEventListener('click', () => refazerDesafio(item));
    acao.appendChild(refazer);
  });
}

async function refazerDesafio(item, lista = null, pos = null) {
  try {
    mostrarAvisoRapido('Preparando uma nova tentativa…');
    const quantidade = [5, 10, 15, 20].includes(Number(item.quantidade_questoes)) ? Number(item.quantidade_questoes) : 5;
    // Refazer usa a mesma dificuldade do desafio original.
    const dificuldadeBase = chaveDificuldade(item.dificuldade);
    const dados = await api('/api/learning/challenges', { method: 'POST', body: {
      id_tema: Number(item.id_tema), quantidade_questoes: quantidade, dificuldade: dificuldadeBase, refazer: true, refazer_de: item.id_desafio,
    }});
    // Ordem da revisão: desafio 1, 2, 3, só os que já foram concluídos.
    let sequencia = lista || desafiosConcluidosDoTema(item.id_tema);
    let posicao = pos !== null ? pos : sequencia.findIndex((registro) => registro.id_desafio === item.id_desafio);
    if (posicao < 0) { sequencia = [item]; posicao = 0; }
    iniciarEstadoDesafio(dados, {
      modoMapa: true,
      modoRevisao: true,
      revisao: { lista: sequencia, pos: posicao },
      configuracao: { idTema: Number(item.id_tema), quantidade, dificuldadeBase, fasesPlanejadas: fasesPorQuantidade(quantidade), faseNaJornada: 1 },
    });
    abrirMapaDesafio();
    mostrarAvisoRapido(`Revisão do desafio ${posicao + 1}: você pode sair a qualquer momento. Esta tentativa não altera sua jornada nem concede pontos.`);
  } catch (erro) {
    mostrarAvisoRapido(`Não foi possível refazer: ${erro.message}`);
  }
}

elemento('proximo-desafio').addEventListener('click', async () => {
  if (estado.faseReprovada) {
    await tentarFaseDeNovo();
    return;
  }
  if (estado.modoRevisao) {
    const revisao = estado.revisao;
    const proximo = revisao && revisao.lista[revisao.pos + 1];
    if (!proximo) {
      avisar(`Desafio ${(revisao?.pos || 0) + 2} ainda bloqueado`, `Conclua o desafio ${(revisao?.pos || 0) + 2} no seu progresso normal para conseguir refazê-lo.`);
      return;
    }
    elemento('janela-quiz').hidden = true;
    await refazerDesafio(proximo, revisao.lista, revisao.pos + 1);
    return;
  }
  const botao = elemento('proximo-desafio');
  botao.disabled = true;
  try {
    await seguirParaProximaFase({ aoPreparar: () => { botao.textContent = 'Preparando próxima fase…'; } });
  } finally {
    botao.disabled = false;
    const configuracaoAtual = estado.configuracaoBase;
    if (configuracaoAtual) {
      const faseAtual = Number(configuracaoAtual.faseNaJornada || 1);
      const total = Number(configuracaoAtual.fasesPlanejadas || fasesPorQuantidade(configuracaoAtual.quantidade));
      botao.innerHTML = faseAtual >= total ? 'Concluir jornada <span>✓</span>' : `Próxima fase ${faseAtual + 1}/${total} <span>→</span>`;
    }
  }
});

// Vai para a próxima fase da jornada. É usado na tela de resultado,
// no botão do mapa e no "Continuar jornada" do painel.
async function seguirParaProximaFase({ aoPreparar = null } = {}) {
  const configuracao = estado.configuracaoBase;
  if (!configuracao) {
    elemento('janela-quiz').hidden = true;
    trocarVisao('estudo');
    return;
  }
  const jornadaConcluida = Number(configuracao.faseNaJornada || 1) >= Number(configuracao.fasesPlanejadas || fasesPorQuantidade(configuracao.quantidade));
  if (jornadaConcluida) {
    elemento('janela-quiz').hidden = true;
    elemento('tela-mapa-desafio').hidden = true;
    document.body.classList.remove('mapa-aberto');
    trocarVisao('estudo');
    await atualizarPainel();
    mostrarAvisoRapido('Jornada concluída! Você terminou todas as fases planejadas. Escolha um novo tema para continuar.');
    return;
  }
  if (aoPreparar) aoPreparar();
  try {
    await criarProximoDesafio({ ...configuracao, faseNaJornada: Number(configuracao.faseNaJornada || 1) + 1, mostrarMapa: true });
  } catch (erro) {
    mostrarAvisoRapido(`Não foi possível criar a próxima fase: ${erro.message}`);
  }
  await atualizarBotoesDesafio();
}

// Telas visitadas, para o botão "Voltar" desfazer a última troca
// antes de usar o histórico do navegador (voltar.js).
const historicoVisoes = [];
let visaoAtual = 'estudo';

function atualizarBotaoVoltar() {
  const botao = elemento('botao-voltar');
  if (!botao) return;
  // Na página inicial, sem nada para desfazer, a seta some em vez de ficar parada na tela.
  const semDestino = !historicoVisoes.length && visaoAtual === 'estudo' && !window.ExplAIner?.temPaginaAnteriorDoApp?.();
  botao.hidden = semDestino;
}

// A logo do topo abre o minijogo (frontend/minijogo). Ela não recarrega a página:
// recarregar fazia a tela de login aparecer por um instante.
function aoClicarNaLogo() {
  elemento('barra-lateral').classList.remove('aberto');
  window.ExplAIner?.minijogo?.abrir();
}
elemento('marca-topo').addEventListener('click', aoClicarNaLogo);

if (window.ExplAIner) {
  window.ExplAIner.aoVoltar = () => {
    if (historicoVisoes.length) {
      trocarVisao(historicoVisoes.pop(), { registrar: false });
      return true;
    }
    if (visaoAtual !== 'estudo') {
      trocarVisao('estudo', { registrar: false });
      return true;
    }
    return false; // deixa o voltar.js usar o histórico do navegador
  };
}

function trocarVisao(visao, { registrar = true } = {}) {
  if (registrar && visao !== visaoAtual) {
    historicoVisoes.push(visaoAtual);
    if (historicoVisoes.length > 20) historicoVisoes.shift();
  }
  visaoAtual = visao;
  atualizarBotaoVoltar();
  const titulos = { estudo: 'Aprender', ranking: 'Ranking', progresso: 'Meu progresso' };
  ['estudo', 'ranking', 'progresso'].forEach((nome) => {
    elemento(`visao-${nome}`).hidden = nome !== visao;
  });
  document.querySelectorAll('.item-nav[data-visao]').forEach((botao) => botao.classList.toggle('ativo', botao.dataset.visao === visao));
  elemento('titulo-pagina').textContent = titulos[visao] || 'Aprender';
  elemento('barra-lateral').classList.remove('aberto');
  abrirConfiguracoes(false);
  if (visao !== 'estudo') atualizarPainel().catch(() => {});
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

document.querySelectorAll('.item-nav[data-visao]').forEach((botao) => botao.addEventListener('click', () => trocarVisao(botao.dataset.visao)));
document.querySelectorAll('[data-ir-visao]').forEach((botao) => botao.addEventListener('click', () => trocarVisao(botao.dataset.irVisao)));
elemento('menu-celular').addEventListener('click', () => elemento('barra-lateral').classList.toggle('aberto'));
document.addEventListener('click', (evento) => {
  const barraLateral = elemento('barra-lateral');
  if (window.innerWidth <= 720 && barraLateral.classList.contains('aberto') && !barraLateral.contains(evento.target) && !elemento('menu-celular').contains(evento.target)) barraLateral.classList.remove('aberto');
});

function fecharMenuConta() {
  elemento('menu-conta').hidden = true;
  elemento('botao-conta').setAttribute('aria-expanded', 'false');
}

async function encerrarSessao(voltarAoLogin = true) {
  try { await api('/api/auth/logout', { method: 'POST', body: {} }); } catch (erro) { console.warn(erro); }
  estado.aluno = null;
  estado.progresso = null;
  pararContagemDeTempo();
  fecharMenuConta();
  mostrarTelaAutenticacao();
  trocarModoAutenticacao('login');
  elemento('formulario-login').reset();
  if (voltarAoLogin) elemento('formulario-login').querySelector('input[name="email"]').focus();
}

elemento('botao-conta').addEventListener('click', (evento) => {
  evento.stopPropagation();
  const menu = elemento('menu-conta');
  menu.hidden = !menu.hidden;
  elemento('botao-conta').setAttribute('aria-expanded', String(!menu.hidden));
});

elemento('menu-conta').addEventListener('click', async (evento) => {
  const botao = evento.target.closest('[data-acao-conta]');
  if (!botao) return;
  const acao = botao.dataset.acaoConta;
  if (acao === 'sair') {
    fecharMenuConta();
    await encerrarSessao(false);
  } else if (acao === 'trocar') {
    fecharMenuConta();
    await encerrarSessao(true);
    mostrarAviso('Entre com outra conta ou use o mesmo e-mail para voltar ao seu perfil.', 'sucesso');
  } else if (acao === 'excluir') {
    fecharMenuConta();
    const confirmou = await perguntar({
      titulo: 'Excluir sua conta?',
      texto: 'Seu perfil, pontos e histórico serão apagados permanentemente. Esta ação não pode ser desfeita.',
      sim: 'Continuar', nao: 'Cancelar', icone: 'fa-trash',
    });
    if (!confirmou) return;
    // A senha é digitada num campo próprio da janela, para não aparecer na tela.
    const senha = await perguntar({
      titulo: 'Confirme com sua senha',
      texto: 'Por segurança, digite sua senha para excluir a conta.',
      sim: 'Excluir conta', nao: 'Cancelar', icone: 'fa-lock', campoSenha: true,
    });
    if (!senha) return;
    try {
      await api('/api/auth/delete-account', { method: 'DELETE', body: { senha } });
      estado.aluno = null;
      estado.progresso = null;
      pararContagemDeTempo();
      mostrarTelaAutenticacao();
      trocarModoAutenticacao('cadastro');
      mostrarAviso('Conta excluída com sucesso.');
    } catch (erro) { mostrarAvisoRapido(erro.message); }
  }
});
document.addEventListener('click', (evento) => {
  if (!elemento('menu-conta').hidden && !elemento('menu-conta').contains(evento.target) && !elemento('botao-conta').contains(evento.target)) fecharMenuConta();
});

elemento('formulario-perfil').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  const nick = elemento('nick-perfil').value.trim();
  const botao = evento.currentTarget.querySelector('button');
  botao.disabled = true;
  try {
    const dados = await api('/api/learning/profile', { method: 'PATCH', body: { nick } });
    estado.aluno = { ...estado.aluno, ...dados.aluno };
    atualizarIdentidade();
    mostrarAviso('Nick atualizado. Ele já aparece no seu perfil.', 'sucesso', 'mensagem-perfil');
    await atualizarPainel();
  } catch (erro) {
    mostrarAviso(erro.message, 'erro', 'mensagem-perfil');
  } finally {
    botao.disabled = false;
  }
});

elemento('formulario-senha').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  const formulario = evento.currentTarget;
  const botao = formulario.querySelector('button');
  botao.disabled = true;
  try {
    await api('/api/auth/change-password', {
      method: 'POST',
      body: { senha_atual: elemento('senha-atual').value, senha_nova: elemento('senha-nova').value },
    });
    formulario.reset();
    mostrarAviso('Senha trocada. Use a nova senha na próxima vez que entrar.', 'sucesso', 'mensagem-senha');
  } catch (erro) {
    mostrarAviso(erro.message, 'erro', 'mensagem-senha');
  } finally {
    botao.disabled = false;
  }
});

function iniciarContagemDeTempo() {
  pararContagemDeTempo();
  estado.temporizador = setInterval(async () => {
    if (document.visibilityState !== 'visible' || !estado.aluno) return;
    try {
      const dados = await api('/api/learning/activity', { method: 'POST', body: { segundos: 60 } });
      estado.aluno.minutos_ativos = dados.minutos_ativos;
      estado.aluno.sequencia_atual = dados.sequencia_atual;
      elemento('indicador-minutos').textContent = formatarNumero(dados.minutos_ativos);
      elemento('sequencia-lateral').textContent = `${dados.sequencia_atual} ${dados.sequencia_atual === 1 ? 'dia' : 'dias'}`;
      elemento('sequencia-topo').textContent = dados.sequencia_atual;
      elemento('indicador-sequencia').textContent = dados.sequencia_atual;
    } catch (erro) {
      console.warn('Não foi possível registrar o tempo ativo:', erro.message);
    }
  }, 60000);
}

function pararContagemDeTempo() {
  if (estado.temporizador) clearInterval(estado.temporizador);
  estado.temporizador = null;
}

function formatarNumero(valor) {
  return new Intl.NumberFormat('pt-BR').format(Number(valor) || 0);
}

function formatarData(valor) {
  if (!valor) return '—';
  const data = new Date(`${valor}T12:00:00`);
  return Number.isNaN(data.getTime()) ? valor : data.toLocaleDateString('pt-BR');
}

restaurarSessao();
