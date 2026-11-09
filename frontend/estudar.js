const API_URL = '';
const LETRAS = ['A', 'B', 'C', 'D'];
const state = {
  aluno: null,
  progresso: null,
  catalogo: [],
  desafio: null,
  temaAtual: null,
  questoes: [],
  indiceQuestao: 0,
  alternativaSelecionada: null,
  respostaEnviada: false,
  modoMapa: false,
  modoRevisao: false,
  questoesRespondidas: new Set(),
  resultadoQuestoes: new Map(),   // índice da questão -> true (acertou) / false (errou)
  acertosSeguidos: 0,
  inicioQuestao: 0,
  heartbeat: null,
  toastTimeout: null,
  configuracaoBase: null,
  revisao: null,          // { lista: [desafios concluídos], pos: índice atual } durante o "refazer"
  faseAtiva: 1,           // fase (1, 2, 3…) do desafio em andamento: define a cor do espaço
  jornadaReprovada: false,
};

const elemento = (id) => document.getElementById(id);

async function api(caminho, opcoes = {}) {
  const configuracao = {
    method: opcoes.method || 'GET',
    credentials: 'same-origin',
    headers: { ...(opcoes.body ? { 'Content-Type': 'application/json' } : {}), ...(opcoes.headers || {}) },
    ...(opcoes.body ? { body: JSON.stringify(opcoes.body) } : {}),
  };
  const resposta = await fetch(`${API_URL}${caminho}`, configuracao);
  let dados = {};
  try { dados = await resposta.json(); } catch (_) { dados = {}; }
  if (!resposta.ok) {
    const erro = new Error(dados.erro || `Não foi possível concluir a solicitação (${resposta.status}).`);
    erro.status = resposta.status;
    erro.payload = dados;
    throw erro;
  }
  return dados;
}

function mostrarAviso(mensagem, tipo = 'success', destino = 'auth-message') {
  const alvo = elemento(destino);
  if (!alvo) return;
  alvo.textContent = mensagem;
  alvo.className = `notice ${tipo}`;
  alvo.hidden = false;
}

function mostrarToast(mensagem) {
  const toast = elemento('toast');
  toast.textContent = mensagem;
  toast.hidden = false;
  clearTimeout(state.toastTimeout);
  state.toastTimeout = setTimeout(() => { toast.hidden = true; }, 4400);
}

/* ==========================================================================
   Janela de confirmação, elogios, emojis, confetes e sons
   ========================================================================== */
let resolverModal = null;

// Com campoSenha, mostra um campo de senha mascarado e resolve com o texto digitado
// (ou null se a pessoa cancelar); sem ele, resolve com true/false.
function perguntar({ titulo, texto, sim = 'Sim', nao = 'Não', informativo = false, icone = null, campoSenha = false }) {
  if (resolverModal) resolverModal(false);
  const overlay = elemento('confirm-overlay');
  const campo = elemento('confirm-field');
  const entrada = elemento('confirm-input');
  elemento('confirm-title').textContent = titulo;
  elemento('confirm-text').textContent = texto;
  elemento('confirm-yes').textContent = sim;
  elemento('confirm-no').textContent = nao;
  elemento('confirm-no').hidden = informativo;
  campo.hidden = !campoSenha;
  entrada.value = '';
  overlay.querySelector('.modal-card').classList.toggle('is-info', informativo);
  elemento('confirm-icon').innerHTML = `<i class="fa-solid ${icone || (informativo ? 'fa-lock' : 'fa-triangle-exclamation')}"></i>`;
  overlay.hidden = false;
  (campoSenha ? entrada : informativo ? elemento('confirm-yes') : elemento('confirm-no')).focus();
  return new Promise((resolver) => {
    resolverModal = (resposta) => {
      overlay.hidden = true;
      resolverModal = null;
      const valor = entrada.value;
      entrada.value = '';
      campo.hidden = true;
      resolver(campoSenha ? (resposta ? valor : null) : resposta);
    };
  });
}
elemento('confirm-input').addEventListener('keydown', (evento) => {
  if (evento.key === 'Enter' && resolverModal) { evento.preventDefault(); resolverModal(true); }
});
const avisar = (titulo, texto, botao = 'Entendi') => perguntar({ titulo, texto, sim: botao, informativo: true });

elemento('confirm-yes').addEventListener('click', () => resolverModal && resolverModal(true));
elemento('confirm-no').addEventListener('click', () => resolverModal && resolverModal(false));
elemento('confirm-overlay').addEventListener('click', (evento) => {
  if (evento.target === elemento('confirm-overlay') && resolverModal) resolverModal(false);
});

let tempoElogio = null;
function fecharElogio(imediato = false) {
  clearTimeout(tempoElogio);
  const overlay = elemento('praise-overlay');
  const cartao = elemento('praise-card');
  if (overlay.hidden) return;
  if (imediato) { overlay.hidden = true; return; }
  cartao.classList.add('is-out');
  setTimeout(() => { overlay.hidden = true; cartao.classList.remove('is-out'); }, 280);
}

function mostrarElogio({ icone, titulo, texto, xp = 0, duracao = 6, tipo = 'normal' }) {
  clearTimeout(tempoElogio);
  const overlay = elemento('praise-overlay');
  const cartao = elemento('praise-card');
  cartao.className = `praise-card${tipo === 'streak' ? ' is-streak' : tipo === 'party' ? ' is-party' : ''}`;
  elemento('praise-icon').textContent = icone;
  elemento('praise-title').textContent = titulo;
  elemento('praise-text').textContent = texto;
  const rotuloXp = elemento('praise-xp');
  rotuloXp.hidden = !(xp > 0);
  rotuloXp.textContent = `+${formatarNumero(xp)} XP de bônus`;
  const barra = elemento('praise-timer-bar');
  barra.style.setProperty('--dur', `${duracao}s`);
  barra.style.animation = 'none';
  void barra.offsetWidth; // reinicia a animação da barrinha de tempo
  barra.style.animation = '';
  overlay.hidden = false;
  tempoElogio = setTimeout(() => fecharElogio(), duracao * 1000);
}
elemento('praise-close').addEventListener('click', () => fecharElogio());

document.addEventListener('keydown', (evento) => {
  if (evento.key !== 'Escape') return;
  if (resolverModal) resolverModal(false);
  else if (!elemento('praise-overlay').hidden) fecharElogio();
});

function emojisSubindo(emoji = '👍', quantidade = 26) {
  const camada = elemento('celebrate-layer');
  for (let i = 0; i < quantidade; i += 1) {
    const item = document.createElement('span');
    item.className = 'rising-emoji';
    item.textContent = emoji;
    item.style.left = `${4 + Math.random() * 92}%`;
    item.style.setProperty('--tam', `${28 + Math.random() * 34}px`);
    item.style.setProperty('--dur', `${2.6 + Math.random() * 1.8}s`);
    item.style.setProperty('--delay', `${Math.random() * 1.1}s`);
    item.style.setProperty('--alt', `${60 + Math.random() * 35}vh`);
    item.style.setProperty('--balanco', `${(Math.random() - 0.5) * 140}px`);
    item.style.setProperty('--giro', `${(Math.random() - 0.5) * 50}deg`);
    item.addEventListener('animationend', () => item.remove());
    camada.appendChild(item);
  }
}

function confete(quantidade = 170) {
  const camada = elemento('celebrate-layer');
  const cores = ['#D1DC5A', '#33B4BD', '#7C79FF', '#FF8918', '#FEC701', '#EA2B2B', '#F6F9FC'];
  for (let i = 0; i < quantidade; i += 1) {
    const peca = document.createElement('i');
    peca.className = `confetti-piece${Math.random() < 0.3 ? ' is-round' : ''}`;
    peca.style.left = `${Math.random() * 100}%`;
    peca.style.setProperty('--cor', cores[i % cores.length]);
    peca.style.setProperty('--w', `${7 + Math.random() * 8}px`);
    peca.style.setProperty('--h', `${10 + Math.random() * 12}px`);
    peca.style.setProperty('--dur', `${3 + Math.random() * 2.6}s`);
    peca.style.setProperty('--delay', `${Math.random() * 1.2}s`);
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
  } catch (_) { /* sem voz disponível: o som sintetizado já toca */ }
}

// tipos: 'ok' (fase concluída), 'uhul' (5 seguidos), 'festa' (jornada concluída)
function tocarSom(tipo) {
  const contexto = obterAudio();
  if (contexto) {
    if (tipo === 'ok') {
      [523, 659, 784].forEach((nota, i) => tocarNota(contexto, nota, i * 0.1, 0.3));
    } else if (tipo === 'uhul') {
      // "uuu-hul": glissando de comemoração + vibrato curto
      tocarNota(contexto, 330, 0, 0.55, { tipo: 'sawtooth', volume: 0.07, ate: 820 });
      tocarNota(contexto, 660, 0.45, 0.3, { tipo: 'square', volume: 0.05, ate: 520 });
    } else {
      [523, 659, 784, 1047, 784, 1047, 1319].forEach((nota, i) => tocarNota(contexto, nota, i * 0.12, 0.35));
      tocarNota(contexto, 330, 0, 0.9, { tipo: 'sawtooth', volume: 0.05, ate: 880 });
    }
  }
  if (tipo !== 'ok') falarUhul();
}

/* ---------- jornada salva por desafio (para o "Continuar" voltar na fase certa) ---------- */
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
  } catch (_) { /* armazenamento indisponível */ }
}

/* ---------- desafios concluídos em sequência (elogio dos 5 seguidos) ---------- */
function chaveSeguidos() { return `explainer-seguidos-v1-${state.aluno?.id_aluno || 0}`; }
function lerSeguidos() {
  try { return Number(localStorage.getItem(chaveSeguidos())) || 0; } catch (_) { return 0; }
}
function gravarSeguidos(valor) {
  try { localStorage.setItem(chaveSeguidos(), String(valor)); } catch (_) {}
}

function trocarModoAutenticacao(modo) {
  const login = modo === 'login';
  document.querySelectorAll('[data-auth-mode]').forEach((botao) => {
    const ativo = botao.dataset.authMode === modo;
    botao.classList.toggle('active', ativo);
    botao.setAttribute('aria-selected', String(ativo));
  });
  elemento('login-form').hidden = !login;
  elemento('register-form').hidden = login;
  elemento('auth-title').textContent = login ? 'Bom ter você de volta.' : 'Sua jornada começa aqui.';
  elemento('auth-subtitle').textContent = login ? 'Entre para continuar sua jornada.' : 'Crie sua conta e comece a avançar por fases.';
  elemento('auth-message').hidden = true;
}

document.querySelectorAll('[data-auth-mode]').forEach((botao) => {
  botao.addEventListener('click', () => trocarModoAutenticacao(botao.dataset.authMode));
});

// Os modos de login e cadastro são exclusivos; somente o formulário ativo fica no layout.
trocarModoAutenticacao('login');

elemento('login-form').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  const botao = evento.currentTarget.querySelector('button[type="submit"]');
  const textoOriginal = botao.innerHTML;
  botao.disabled = true;
  botao.textContent = 'Entrando…';
  const dadosFormulario = Object.fromEntries(new FormData(evento.currentTarget));
  try {
    const dados = await api('/api/auth/login', { method: 'POST', body: dadosFormulario });
    await iniciarPlataforma(dados);
  } catch (erro) {
    mostrarAviso(erro.message, 'error');
  } finally {
    botao.disabled = false;
    botao.innerHTML = textoOriginal;
  }
});

elemento('register-form').addEventListener('submit', async (evento) => {
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
    await iniciarPlataforma({ aluno: dados.aluno });
  } catch (erro) {
    const emailEnviado = String(dadosFormulario.email || '').trim();
    if (erro.status === 409 && /e-mail/i.test(erro.message)) {
      trocarModoAutenticacao('login');
      elemento('login-form').elements.email.value = emailEnviado;
      mostrarAviso('Este e-mail já possui uma conta. Entre com sua senha para continuar e manter seu progresso.', 'error');
    } else {
      mostrarAviso(erro.message, 'error');
    }
  } finally {
    botao.disabled = false;
    botao.innerHTML = textoOriginal;
  }
});

async function iniciarPlataforma(dados) {
  state.aluno = dados.aluno;
  state.progresso = dados.progresso || null;
  elemento('auth-screen').hidden = true;
  elemento('app-layout').hidden = false;
  historicoVisoes.length = 0;
  visaoAtual = 'study';
  atualizarBotaoVoltar();
  atualizarIdentidade();
  try {
    const [catalogo, perfil] = await Promise.all([
      api('/api/learning/catalog'),
      api('/api/learning/me'),
    ]);
    state.catalogo = catalogo.materias || [];
    state.aluno = perfil.aluno;
    state.progresso = perfil.progresso;
    if (state.aluno.precisa_aceitar_termos && !(await pedirAceiteDosTermos())) {
      await encerrarSessao(false);
      mostrarAviso('Sem o aceite dos termos não é possível usar o ExplAIner. Você pode aceitá-los no próximo login.', 'error');
      return;
    }
    montarSelectMaterias();
    atualizarPainelPerfil();
    await atualizarPainel();
    await atualizarBotoesDesafio();
    iniciarContagemDeTempo();
  } catch (erro) {
    if (erro.status === 401) mostrarTelaAutenticacao();
    else mostrarToast(erro.message);
  }
}

// Contas criadas antes dos termos (ou de uma versão nova) precisam aceitar para continuar.
// A decisão fica registrada no servidor (data, hora e versão) por POST /api/auth/accept-terms.
function pedirAceiteDosTermos() {
  const overlay = elemento('terms-overlay');
  overlay.hidden = false;
  elemento('terms-accept').focus();
  return new Promise((resolver) => {
    const finalizar = (aceitou) => {
      overlay.hidden = true;
      elemento('terms-accept').onclick = null;
      elemento('terms-refuse').onclick = null;
      resolver(aceitou);
    };
    elemento('terms-refuse').onclick = () => finalizar(false);
    elemento('terms-accept').onclick = async () => {
      elemento('terms-accept').disabled = true;
      try {
        const dados = await api('/api/auth/accept-terms', { method: 'POST', body: {} });
        state.aluno = dados.aluno;
        finalizar(true);
      } catch (erro) {
        mostrarToast(erro.message);
      } finally {
        elemento('terms-accept').disabled = false;
      }
    };
  });
}

function atualizarStatusDosTermos() {
  const status = elemento('terms-status');
  if (!status || !state.aluno) return;
  const quando = state.aluno.termos_aceitos_em ? new Date(state.aluno.termos_aceitos_em) : null;
  status.textContent = quando && !Number.isNaN(quando.getTime())
    ? `Você aceitou os termos (versão ${state.aluno.versao_termos}) em ${quando.toLocaleDateString('pt-BR')} às ${quando.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}. Para revogar o consentimento, exclua sua conta no menu da conta.`
    : 'Você ainda não aceitou os termos.';
}

function mostrarTelaAutenticacao() {
  pararContagemDeTempo();
  // Ao sair ou trocar de conta, nada do desafio da conta anterior pode continuar na página.
  Object.assign(state, {
    desafio: null, temaAtual: null, questoes: [], configuracaoBase: null, revisao: null,
    modoRevisao: false, jornadaReprovada: false, faseConcluida: false,
    proximaFasePendente: null, questoesRespondidas: new Set(), resultadoQuestoes: new Map(),
  });
  window.__historicoDesafios = [];
  elemento('jump-to-challenge').hidden = true;
  elemento('replay-latest-button').hidden = true;
  elemento('auth-screen').hidden = false;
  elemento('app-layout').hidden = true;
  elemento('quiz-overlay').hidden = true;
  elemento('challenge-map-screen').hidden = true;
  document.body.classList.remove('map-open');
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
  if (!state.aluno) return;
  const nick = state.aluno.nick || state.aluno.nome || 'Estudante';
  const inicial = nick.trim().charAt(0).toUpperCase() || 'E';
  elemento('sidebar-nick').textContent = nick;
  elemento('sidebar-email').textContent = state.aluno.email || 'Minha conta';
  elemento('sidebar-avatar').textContent = inicial;
  elemento('top-avatar').textContent = inicial;
  elemento('top-points').textContent = formatarNumero(state.aluno.pontos || 0);
  elemento('stat-points').textContent = formatarNumero(state.aluno.pontos || 0);
  elemento('top-streak').textContent = state.aluno.sequencia_atual || state.aluno.foguinho || 0;
  elemento('stat-streak').textContent = state.aluno.sequencia_atual || state.aluno.foguinho || 0;
  elemento('sidebar-streak').textContent = `${state.aluno.sequencia_atual || state.aluno.foguinho || 0} ${(state.aluno.sequencia_atual || state.aluno.foguinho || 0) === 1 ? 'dia' : 'dias'}`;
  elemento('stat-minutes').textContent = formatarNumero(state.aluno.minutos_ativos || 0);
  atualizarSequenciaSemanal();
  elemento('profile-nick').value = nick;
  atualizarStatusDosTermos();
}

function atualizarSequenciaSemanal() {
  const sequencia = Number(state.aluno?.sequencia_atual || state.aluno?.foguinho || 0);
  const bolinhas = elemento('week-dots');
  if (bolinhas) {
    Array.from(bolinhas.children).forEach((bolinha, indice) => {
      bolinha.classList.toggle('active', indice >= 7 - Math.min(sequencia, 7));
    });
  }
  const mensagem = elemento('sequence-message');
  if (mensagem) {
    mensagem.textContent = sequencia > 0
      ? `${sequencia} ${sequencia === 1 ? 'dia seguido' : 'dias seguidos'} estudando. Continue para manter seu foguinho aceso.`
      : 'Acesse diariamente para manter seu foguinho aceso.';
  }
}

function atualizarPainelPerfil() {
  if (!state.progresso) return;
  elemento('progress-completed').textContent = formatarNumero(state.progresso.desafios_concluidos || 0);
  if (elemento('stat-lessons')) elemento('stat-lessons').textContent = formatarNumero(state.progresso.desafios_concluidos || 0);
  elemento('progress-accuracy').textContent = formatarNumero(state.progresso.precisao || 0);
  elemento('progress-answered').textContent = formatarNumero(state.progresso.questoes_respondidas || 0);
  elemento('stat-minutes').textContent = formatarNumero(state.progresso.minutos_ativos || state.aluno.minutos_ativos || 0);
  atualizarSequenciaSemanal();
}

function montarSelectMaterias() {
  const select = elemento('subject-select');
  const materiaAnterior = select.value;
  select.replaceChildren();
  state.catalogo.forEach((materia) => {
    const option = document.createElement('option');
    option.value = materia.nome;
    option.textContent = materia.nome;
    select.appendChild(option);
  });
  if (!state.catalogo.length) {
    select.add(new Option('Nenhuma matéria cadastrada', ''));
    select.disabled = true;
    return;
  }
  select.disabled = false;
  if (state.catalogo.some((materia) => materia.nome === materiaAnterior)) select.value = materiaAnterior;
  atualizarSelectTemas();
}

function atualizarSelectTemas() {
  const materia = state.catalogo.find((item) => item.nome === elemento('subject-select').value) || state.catalogo[0];
  const select = elemento('theme-select');
  select.replaceChildren();
  if (!materia || !materia.temas.length) {
    select.add(new Option('Nenhum tema cadastrado', ''));
    return;
  }
  materia.temas.forEach((tema) => select.add(new Option(tema.nome, String(tema.id_tema))));
  atualizarMapaSelecionado();
}

elemento('subject-select').addEventListener('change', atualizarSelectTemas);
elemento('theme-select').addEventListener('change', atualizarMapaSelecionado);
document.querySelectorAll('input[name="quantidade"], input[name="dificuldade"]').forEach((input) => input.addEventListener('change', atualizarPreviewPontos));
atualizarPreviewPontos();

function temaSelecionado() {
  const id = Number(elemento('theme-select').value);
  for (const materia of state.catalogo) {
    const tema = materia.temas.find((item) => item.id_tema === id);
    if (tema) return { ...tema, materia: materia.nome };
  }
  return null;
}

function fasesPorQuantidade(quantidade) {
  const mapa = { 5: 5, 10: 4, 15: 3, 20: 2 };
  return mapa[Number(quantidade)] || 5;
}

function atualizarMapaSelecionado() {
  const tema = temaSelecionado();
  const materia = elemento('subject-select').value;
  elemento('path-theme-title').textContent = tema ? tema.nome : 'Escolha um tema';
  elemento('path-subject-label').textContent = tema ? materia : 'Seu caminho será montado aqui';
  const selecionadoId = tema ? tema.id_tema : null;
  const historico = (window.__historicoDesafios || []).filter((item) => !item.modo_revisao && !String(item.nome || "").startsWith("[REFAZER] "));
  const concluidos = historico.filter((item) => item.concluido && item.tema === (tema && tema.nome) && item.materia === materia).length;
  const nivel = concluidos + 1;
  elemento('path-level').textContent = `NÍVEL ${String(nivel).padStart(2, '0')}`;
  const mapa = elemento('learning-map');
  const materiaVisual = String(materia || '').toLocaleLowerCase('pt-BR');
  const familiaVisual = materiaVisual.includes('matem') ? 0 : materiaVisual.includes('ciên') || materiaVisual.includes('biolog') ? 1 : materiaVisual.includes('hist') || materiaVisual.includes('geo') ? 2 : 3;
  const variacao = ((familiaVisual + (selecionadoId || 1) + nivel - 1) % 3);
  mapa.classList.remove('map-variant-0', 'map-variant-1', 'map-variant-2');
  mapa.classList.add(`map-variant-${variacao}`);
  const paletas = [
    ['#8b7cf6', '#c7bfff', '#f0edff'], ['#20b99a', '#91e2d1', '#e4fbf5'],
    ['#e5a33d', '#f4d18c', '#fff5df'], ['#4c9ee8', '#a9d4ff', '#e9f4ff'],
    ['#e879a9', '#f5b8d2', '#fff0f6'], ['#8aaf4f', '#cde4a5', '#f2f9e5']
  ];
  const paleta = paletas[(Math.abs(Number(selecionadoId || 0) * 3 + nivel + familiaVisual) % paletas.length)];
  mapa.style.setProperty('--map-accent', paleta[0]);
  mapa.style.setProperty('--map-accent-soft', paleta[1]);
  mapa.style.setProperty('--map-surface', paleta[2]);
  elemento('path-panel').style.setProperty('--map-accent', paleta[0]);
  elemento('path-panel').style.setProperty('--map-accent-soft', paleta[1]);
  const layouts = [
    [{ x: '10%', y: '66%' }, { x: '34%', y: '38%' }, { x: '62%', y: '64%' }, { x: '89%', y: '30%' }],
    [{ x: '10%', y: '34%' }, { x: '34%', y: '68%' }, { x: '62%', y: '36%' }, { x: '89%', y: '62%' }],
    [{ x: '10%', y: '64%' }, { x: '34%', y: '36%' }, { x: '62%', y: '66%' }, { x: '89%', y: '32%' }],
  ];
  const caminhos = [
    'M25 145 C75 145 75 70 145 90 S220 165 285 105 S365 45 425 95 S500 145 575 55',
    'M25 70 C90 45 90 160 180 145 S245 45 330 75 S440 155 575 130',
    'M25 140 C90 170 100 50 180 75 S260 160 345 130 S455 35 575 65',
  ];
  const pontosMapa = layouts[variacao];
  const nos = document.querySelectorAll('.map-node');
  nos.forEach((no, indice) => {
    no.style.setProperty('--x', pontosMapa[indice].x);
    no.style.setProperty('--y', pontosMapa[indice].y);
    no.classList.remove('map-node-done', 'map-node-current', 'map-node-locked');
    if (indice < Math.min(concluidos, 3)) no.classList.add('map-node-done');
    else if (indice === Math.min(concluidos, 3)) no.classList.add('map-node-current');
    else no.classList.add('map-node-locked');
    const span = no.querySelector('span');
    if (span) span.textContent = no.classList.contains('map-node-done') ? '✓' : String(indice + 1);
  });
  const linhaMapa = mapa.querySelector('.map-path-line path');
  if (linhaMapa) linhaMapa.setAttribute('d', caminhos[variacao]);
  const meta = mapa.querySelector('.map-goal');
  if (meta) { meta.style.left = layouts[variacao][3].x; meta.style.top = layouts[variacao][3].y; }
  if (selecionadoId && tema) {
    const mapLabel = document.querySelector('.map-node-current small');
    if (mapLabel) mapLabel.textContent = `Fase ${nivel}`;
  }
  atualizarPreviewPontos();
  const quantidade = Number(document.querySelector('input[name="quantidade"]:checked')?.value || 5);
  const numeroFases = fasesPorQuantidade(quantidade);
  if (elemento('path-journey-count')) {
    elemento('path-journey-count').textContent = tema
      ? `Sua jornada de ${numeroFases} desafios começa com ${tema.nome}. Cada fase concluída muda o mapa.`
      : 'Escolha uma matéria e um tema para preparar sua jornada.';
  }
}

function atualizarPreviewPontos() {
  const quantidade = Number(document.querySelector('input[name="quantidade"]:checked')?.value || 5);
  const dificuldade = document.querySelector('input[name="dificuldade"]:checked')?.value || 'normal';
  const pontosPorQuestao = dificuldade === 'facil' ? 10 : dificuldade === 'dificil' ? 20 : 15;
  const fases = fasesPorQuantidade(quantidade);
  if (elemento('possible-points')) elemento('possible-points').textContent = `Até ${formatarNumero(quantidade * pontosPorQuestao)} pontos por fase`;
  if (elemento('journey-count')) elemento('journey-count').textContent = `${fases} ${fases === 1 ? 'desafio' : 'desafios'}`;
  if (elemento('journey-description')) elemento('journey-description').textContent = `${quantidade} questões por fase · ${quantidade * fases} questões na jornada`;
  if (elemento('journey-steps')) {
    const passos = elemento('journey-steps');
    passos.replaceChildren();
    for (let indice = 0; indice < fases; indice += 1) {
      const passo = document.createElement('i');
      if (indice === 0) passo.classList.add('is-current');
      passos.appendChild(passo);
    }
    passos.setAttribute('aria-label', `${fases} desafios planejados`);
  }
  if (elemento('path-journey-count')) {
    const tema = temaSelecionado();
    elemento('path-journey-count').textContent = tema
      ? `Jornada planejada: ${fases} desafios de ${quantidade} questões cada.`
      : `Você terá ${fases} desafios, com ${quantidade} questões em cada fase.`;
  }
}

// Ordem da progressão. O valor interno de "Médio" continua sendo 'normal'/"Normal"
// (banco e API), e só o rótulo exibido muda.
const ESCADA_DIFICULDADE = ['facil', 'normal', 'dificil'];
const ROTULOS_DIFICULDADE = { facil: 'Fácil', normal: 'Médio', dificil: 'Difícil' };

// Aceita a chave interna ('normal'), o valor salvo ("Normal") e o rótulo novo ("Médio"),
// com ou sem acento, para não quebrar dados já existentes.
function chaveDificuldade(valor) {
  const texto = String(valor || '').trim().toLocaleLowerCase('pt-BR');
  if (texto === 'facil' || texto === 'fácil' || texto === 'easy') return 'facil';
  if (texto === 'dificil' || texto === 'difícil' || texto === 'hard') return 'dificil';
  return 'normal';
}

function rotuloDificuldade(valor) {
  return ROTULOS_DIFICULDADE[chaveDificuldade(valor)];
}

// A dificuldade sobe um nível a cada fase concluída, com teto em "Difícil":
// base Fácil → fase 1 Fácil, fase 2 Médio, fase 3+ Difícil; base Médio → fase 2+ Difícil.
function dificuldadeDaFase(dificuldadeBase, fase) {
  const base = ESCADA_DIFICULDADE.indexOf(chaveDificuldade(dificuldadeBase));
  const avanco = Math.max(1, Number(fase) || 1) - 1;
  return ESCADA_DIFICULDADE[Math.min(base + avanco, ESCADA_DIFICULDADE.length - 1)];
}

// Reconstrói a dificuldade inicial a partir da dificuldade e da fase atuais, para quando
// a configuração da jornada não está mais no armazenamento local.
function dificuldadeBaseDaFase(dificuldadeAtual, fase) {
  const atual = ESCADA_DIFICULDADE.indexOf(chaveDificuldade(dificuldadeAtual));
  const avanco = Math.max(1, Number(fase) || 1) - 1;
  return ESCADA_DIFICULDADE[Math.max(atual - avanco, 0)];
}

// Zera TODO o estado do desafio em um só lugar, para que nada de um desafio anterior (respondidas,
// modo revisão, jornada…) vaze para o próximo.
function iniciarEstadoDesafio(dados, { modoMapa = true, modoRevisao = false, configuracao = null, revisao = null, respondidas = null, acertos = null, concluido = false } = {}) {
  state.faseConcluida = Boolean(concluido);
  state.desafio = dados.desafio;
  state.temaAtual = dados.tema || state.catalogo.flatMap((m) => (m.temas || []).map((t) => ({ ...t, materia: m.nome }))).find((t) => Number(t.id_tema) === Number(dados.desafio.id_tema)) || { nome: dados.desafio.nome, materia: '' };
  state.questoes = dados.questoes || [];
  state.indiceQuestao = 0;
  state.alternativaSelecionada = null;
  state.respostaEnviada = false;
  state.modoMapa = modoMapa;
  state.modoRevisao = modoRevisao;
  state.revisao = revisao;
  state.jornadaReprovada = false;
  state.questoesRespondidas = new Set();
  state.acertosSeguidos = 0;
  state.configuracaoBase = configuracao;
  state.resultadoQuestoes = new Map();
  if (respondidas) {
    state.questoes.forEach((q, i) => { if (respondidas[String(q.id_questao)]) state.questoesRespondidas.add(i); });
  }
  if (acertos) {
    // Ao retomar, o servidor informa quais respostas estavam certas: o mapa volta com ✓ e ✗.
    state.questoes.forEach((q, i) => { if (String(q.id_questao) in acertos) state.resultadoQuestoes.set(i, Boolean(acertos[String(q.id_questao)])); });
  }
  if (!modoRevisao) {
    state.faseAtiva = state.desafio.nivel_mapa || 1;
    salvarJornada(state.desafio.id_desafio, configuracao);
  }
}

async function criarProximoDesafio({ idTema, quantidade, dificuldadeBase, mostrarMapa = true, fasesPlanejadas = fasesPorQuantidade(quantidade), faseNaJornada = 1 }) {
  const fase = Number(faseNaJornada);
  const dificuldade = dificuldadeDaFase(dificuldadeBase, fase);
  const dados = await api('/api/learning/challenges', { method: 'POST', body: {
    id_tema: Number(idTema), quantidade_questoes: Number(quantidade), dificuldade, fase_jornada: fase,
    dificuldade_base: chaveDificuldade(dificuldadeBase),
  }});
  iniciarEstadoDesafio(dados, {
    modoMapa: mostrarMapa,
    configuracao: { idTema: Number(idTema), quantidade: Number(quantidade), dificuldadeBase, fasesPlanejadas: Number(fasesPlanejadas), faseNaJornada: Number(faseNaJornada) },
  });
  // A dificuldade real é a que o servidor gravou (ele pode reiniciar a jornada na fase 1).
  const dificuldadeFinal = chaveDificuldade(dados.desafio.dificuldade || dificuldade);
  if (dificuldadeFinal !== chaveDificuldade(dificuldadeBase)) {
    mostrarToast(`Nova fase desbloqueada! A dificuldade subiu para ${rotuloDificuldade(dificuldadeFinal)}.`);
  } else {
    mostrarToast(`Fase ${dados.desafio.nivel_mapa || fase} pronta. Bora continuar?`);
  }
  if (mostrarMapa) abrirMapaDesafio(); else abrirQuiz();
}

// Desafios normais (não-revisão) concluídos de um tema, na ordem da jornada: desafio 1, 2, 3…
function desafiosConcluidosDoTema(idTema) {
  const concluidos = (window.__historicoDesafios || [])
    .filter((item) => item.concluido && !item.modo_revisao && !String(item.nome || '').startsWith('[REFAZER] ') && Number(item.id_tema) === Number(idTema))
    .sort((a, b) => a.id_desafio - b.id_desafio);
  // Só a jornada mais recente: começa no último desafio de fase 1 concluído.
  let inicio = 0;
  concluidos.forEach((item, indice) => { if ((item.nivel_mapa || 1) === 1) inicio = indice; });
  return concluidos.slice(inicio);
}

async function atualizarBotoesDesafio() {
  const continuarTopo = elemento('jump-to-challenge');
  const refazer = elemento('replay-latest-button');
  try {
    const [ativo, historico] = await Promise.all([
      api('/api/learning/active-challenge'),
      api('/api/learning/history')
    ]);
    window.__historicoDesafios = historico.historico || [];
    state.faseAtiva = ativo.ativo ? (ativo.desafio.nivel_mapa || 1) : 0;
    // "Refazer" sempre começa pelo desafio 1 do último tema concluído.
    const ultimo = window.__historicoDesafios
      .filter((item) => item.concluido && item.id_tema && !item.modo_revisao && !String(item.nome || '').startsWith('[REFAZER] '))
      .sort((a, b) => b.id_desafio - a.id_desafio)[0];
    const primeiro = ultimo ? desafiosConcluidosDoTema(ultimo.id_tema)[0] : null;
    refazer.hidden = !primeiro;
    if (primeiro) {
      refazer.dataset.historyId = String(primeiro.id_desafio);
      refazer.innerHTML = '<span aria-hidden="true">↻</span> Refazer desafio 1 <small>Sem ganhar pontos</small>';
    }
    // Sem desafio em andamento, mas com a última fase concluída e outra planejada:
    // o mesmo botão vira "Continuar jornada" e cria a próxima fase.
    state.proximaFasePendente = ativo.ativo ? null : proximaFasePendente(window.__historicoDesafios);
    const pendente = state.proximaFasePendente;
    continuarTopo.hidden = !ativo.ativo && !pendente;
    continuarTopo.dataset.challengeId = ativo.ativo ? String(ativo.desafio.id_desafio) : '';
    if (ativo.ativo) {
      const rotulo = ativo.todas_respondidas ? `Concluir fase ${ativo.desafio.nivel_mapa || 1}` : 'Continuar desafio';
      continuarTopo.innerHTML = `<span aria-hidden="true">▶</span> <span>${rotulo}</span> <span aria-hidden="true">→</span>`;
    } else if (pendente) {
      continuarTopo.innerHTML = `<span aria-hidden="true">▶</span> <span>Continuar jornada · Fase ${pendente.faseNaJornada + 1}/${pendente.fasesPlanejadas}</span> <span aria-hidden="true">→</span>`;
    } else {
      continuarTopo.innerHTML = '';
    }
    elemento('create-challenge-button').innerHTML = ativo.ativo
      ? '<span aria-hidden="true">✦</span> Criar um novo desafio <span aria-hidden="true">→</span>'
      : '<span aria-hidden="true">✦</span> Gerar desafio <span aria-hidden="true">→</span>';
    atualizarFundoMiniMapa();
  } catch (erro) { console.warn('Não foi possível atualizar as ações de desafio:', erro.message); }
}

async function continuarDesafioSalvo(idInformado = null) {
  try {
    const id = idInformado || elemento('jump-to-challenge').dataset.challengeId;
    const dados = await api(`/api/learning/challenges/${id}`);
    const quantidadeSalva = Number(dados.desafio.quantidade_questoes || (dados.questoes || []).length || 5);
    const salva = lerJornadas()[dados.desafio.id_desafio];
    // A fase vem do servidor (nivel_mapa), então "continuar" sempre volta na fase certa.
    const configuracao = {
      idTema: Number(dados.desafio.id_tema),
      quantidade: quantidadeSalva,
      dificuldadeBase: salva?.dificuldadeBase || dificuldadeBaseDaFase(dados.desafio.dificuldade, dados.desafio.nivel_mapa || 1),
      fasesPlanejadas: fasesPorQuantidade(quantidadeSalva),
      faseNaJornada: Number(dados.desafio.nivel_mapa || 1),
    };
    iniciarEstadoDesafio(dados, { modoMapa: true, configuracao, respondidas: dados.respondidas || {}, acertos: dados.acertos || {}, concluido: dados.concluido });
    abrirMapaDesafio();
    mostrarToast(state.questoesRespondidas.size >= state.questoes.length && !state.faseConcluida
      ? 'Desafio restaurado. Todas as questões já foram respondidas: conclua a fase para salvar o resultado.'
      : 'Desafio restaurado. Continue de onde você parou.');
  } catch (erro) { mostrarToast(`Não foi possível continuar: ${erro.message}`); }
}

// Próxima fase da jornada mais recente, quando a pessoa concluiu uma fase e saiu antes de
// começar a seguinte. Usa só o histórico do servidor (funciona após recarregar a página ou
// em outro dispositivo); a dificuldade inicial vem do armazenamento local se existir, senão
// é reconstruída — o que dá exatamente a mesma próxima dificuldade, já que a escada sobe
// um nível por fase até o teto.
function proximaFasePendente(historico) {
  const ultimo = (historico || [])
    .filter((item) => item.concluido && item.id_tema && !item.modo_revisao && !String(item.nome || '').startsWith('[REFAZER] '))
    .sort((a, b) => b.id_desafio - a.id_desafio)[0];
  if (!ultimo) return null;
  const quantidade = [5, 10, 15, 20].includes(Number(ultimo.quantidade_questoes)) ? Number(ultimo.quantidade_questoes) : 5;
  const fasesPlanejadas = fasesPorQuantidade(quantidade);
  const fase = Number(ultimo.nivel_mapa || 1);
  if (fase >= fasesPlanejadas) return null; // jornada já terminou
  const salva = lerJornadas()[ultimo.id_desafio];
  return {
    idTema: Number(ultimo.id_tema),
    quantidade,
    dificuldadeBase: salva?.dificuldadeBase || dificuldadeBaseDaFase(ultimo.dificuldade, fase),
    fasesPlanejadas,
    faseNaJornada: fase,
  };
}

elemento('jump-to-challenge').addEventListener('click', async (evento) => {
  const botao = evento.currentTarget;
  if (botao.dataset.challengeId) {
    continuarDesafioSalvo(botao.dataset.challengeId);
    return;
  }
  if (!state.proximaFasePendente) return;
  botao.disabled = true;
  try {
    state.configuracaoBase = state.proximaFasePendente;
    await seguirParaProximaFase();
  } finally {
    botao.disabled = false;
  }
});
elemento('replay-latest-button').addEventListener('click', async () => {
  const item = (window.__historicoDesafios || []).find((registro) => String(registro.id_desafio) === elemento('replay-latest-button').dataset.historyId && !registro.modo_revisao && !String(registro.nome || "").startsWith("[REFAZER] "));
  if (item) await refazerDesafio(item);
});

elemento('challenge-form').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  const tema = temaSelecionado();
  if (!tema) {
    mostrarToast('Selecione uma matéria e um tema antes de gerar o desafio.');
    return;
  }
  const botao = elemento('create-challenge-button');
  if (botao.disabled) return;
  botao.disabled = true;
  try {
    // Confere no servidor se existe um desafio em andamento; se existir, pede confirmação antes de descartá-lo.
    let ativo = { ativo: false };
    try { ativo = await api('/api/learning/active-challenge'); } catch (erro) { if (erro.status === 401) throw erro; }
    if (ativo.ativo) {
      const confirmou = await perguntar({
        titulo: 'Gerar um novo desafio?',
        texto: 'Você tem um desafio em andamento. Gerar um novo vai excluir o desafio antigo e o progresso dele. Deseja continuar?',
        sim: 'Sim, gerar novo',
        nao: 'Não, manter o atual',
      });
      if (!confirmou) return;
      gravarSeguidos(0); // abandonar um desafio interrompe a sequência de desafios seguidos
    }
    await gerarNovoDesafio(tema);
  } catch (erro) {
    mostrarToast(erro.message);
  } finally {
    botao.disabled = false;
  }
});

async function gerarNovoDesafio(tema, reinicio = null) {
  const botao = elemento('create-challenge-button');
  const textoOriginal = botao.innerHTML;
  if (!reinicio) botao.innerHTML = '<span class="button-spark">✦</span> Preparando questões…';
  try {
    // Um desafio novo sempre começa na fase 1 da jornada (ou usa a configuração da jornada reprovada).
    const quantidade = reinicio ? reinicio.quantidade : Number(document.querySelector('input[name="quantidade"]:checked').value);
    const dificuldadeBase = reinicio ? reinicio.dificuldadeBase : document.querySelector('input[name="dificuldade"]:checked').value;
    const dificuldade = dificuldadeDaFase(dificuldadeBase, 1);
    const dados = await api('/api/learning/challenges', {
      method: 'POST',
      body: {
        id_tema: tema.id_tema, quantidade_questoes: quantidade, dificuldade, fase_jornada: 1,
        dificuldade_base: chaveDificuldade(dificuldadeBase),
      },
    });
    iniciarEstadoDesafio(dados, {
      modoMapa: true,
      configuracao: { idTema: Number(tema.id_tema), quantidade, dificuldadeBase, fasesPlanejadas: fasesPorQuantidade(quantidade), faseNaJornada: 1 },
    });
    if (dados.origem_questoes !== 'ia') {
      mostrarToast('Mapa criado com questões demonstrativas locais. Para gerar questões novas com IA, configure OPENAI_API_KEY no servidor.');
    } else {
      mostrarToast('Seu mapa de desafio foi criado pela IA. Clique na primeira bolinha para começar.');
    }
    abrirMapaDesafio();
  } finally {
    botao.innerHTML = textoOriginal;
  }
  await atualizarBotoesDesafio();
}

function abrirMapaDesafio() {
  if (!state.questoes.length) {
    mostrarToast('O desafio foi criado sem questões disponíveis. Tente novamente.');
    return;
  }
  elemento('quiz-overlay').hidden = true;
  elemento('challenge-map-screen').hidden = false;
  document.body.classList.add('map-open');
  renderizarMapaDesafio();
  elemento('space-map-scroll').scrollTop = 0;
  window.scrollTo({ top: 0, behavior: 'auto' });
}

// Tons do espaço: o fundo original é azul-noturno; cada desafio gira esse tom para uma cor diferente.
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
// Cada "pedaço" mostra uma faixa diferente da imagem espacial (estrelas, planetas, satélite).
// O astronauta é uma imagem à parte (.space-astronaut), então estas faixas evitam o astronauta embutido.
const FAIXAS_ESPACO = [820, 1500, 2420, 3040, 640, 1900, 2700, 1100];

// A cor do espaço depende da FASE (1, 2, 3…), não do id: a fase 1 é sempre a cor original,
// também ao refazer ou ao criar um desafio novo.
function aplicarCorEspaco(elementoAlvo, fase) {
  const cor = PALETAS_ESPACO[(Math.max(1, Number(fase) || 1) - 1) % PALETAS_ESPACO.length];
  elementoAlvo.style.setProperty('--space-hue', `${cor.matiz}deg`);
  elementoAlvo.style.setProperty('--space-sat', cor.saturacao);
  elementoAlvo.style.setProperty('--space-bright', cor.brilho);
  elementoAlvo.dataset.cor = cor.nome;
}

// O mapa pequeno da tela inicial usa o mesmo fundo (e a mesma cor) da fase atual.
function atualizarFundoMiniMapa() {
  const fundo = elemento('learning-map-bg');
  if (!fundo) return;
  let fase = state.faseAtiva;
  if (!fase) {
    const ultimo = (window.__historicoDesafios || [])
      .filter((item) => item.concluido && !item.modo_revisao && !String(item.nome || '').startsWith('[REFAZER] '))
      .sort((a, b) => b.id_desafio - a.id_desafio)[0];
    fase = ultimo ? ultimo.nivel_mapa || 1 : 1;
  }
  aplicarCorEspaco(fundo, fase);
}

function montarFundoEspacial(largura, altura) {
  const camada = elemento('space-map-bg');
  if (!camada) return;
  camada.replaceChildren();
  const larguraPedaco = 1920;
  const total = Math.ceil(largura / larguraPedaco);
  for (let i = 0; i < total; i += 1) {
    const pedaco = document.createElement('div');
    pedaco.className = 'space-map-tile';
    pedaco.style.left = `${i * larguraPedaco}px`;
    // Mantém a faixa dentro da imagem (5400px de altura) mesmo em telas altas.
    const faixa = Math.min(FAIXAS_ESPACO[i % FAIXAS_ESPACO.length], Math.max(0, 5400 - (altura || 560)));
    pedaco.style.backgroundPosition = `0 -${faixa}px`;
    camada.appendChild(pedaco);
  }
}

function renderizarMapaDesafio() {
  if (!state.desafio || !state.temaAtual || !state.questoes.length) return;
  const quantidade = state.questoes.length;
  const nivel = state.desafio.nivel_mapa || 1;
  elemento('challenge-map-title').textContent = state.temaAtual.nome;
  const jornada = state.configuracaoBase;
  const faseJornada = nivel;
  const totalFases = jornada?.fasesPlanejadas || fasesPorQuantidade(quantidade);
  const proximaQuestao = indiceDaProximaQuestao();
  elemento('challenge-map-subtitle').textContent = state.modoRevisao
    ? `${state.temaAtual.materia} · Revisão do desafio ${(state.revisao?.pos || 0) + 1} · sem pontos`
    : `${state.temaAtual.materia} · Fase ${nivel} · Jornada ${faseJornada}/${totalFases} — ${proximaQuestao >= 0 ? `próxima: Questão ${proximaQuestao + 1}` : 'todas respondidas'}`;
  elemento('map-progress-count').textContent = `${state.questoesRespondidas.size}/${quantidade}`;
  elemento('map-xp-total').textContent = `${formatarNumero(state.aluno?.pontos || 0)} XP`;

  const moldura = elemento('space-map');
  const textoTema = `${state.temaAtual.materia || ''} ${state.temaAtual.nome || ''}`.toLocaleLowerCase('pt-BR');
  const familiaClasse = /matem|álgebra|geometr|cálculo/.test(textoTema) ? 'math' : /ciên|biolog|quím|físic|natureza/.test(textoTema) ? 'science' : /hist|antig|medieval|civiliza/.test(textoTema) ? 'history' : /geograf|clima|relevo|mapa/.test(textoTema) ? 'geography' : /portugu|literat|inglês|língua|gramát/.test(textoTema) ? 'language' : 'default';
  moldura.className = `space-map map-subject-${familiaClasse}`;
  // Cada desafio criado recebe uma cor própria para o espaço (mesmo astronauta e estrelas, outro tom).
  aplicarCorEspaco(moldura, nivel);
  // O mapa sempre cobre a tela inteira: usa a largura/altura visíveis como mínimo e só cresce (rolagem) se precisar.
  const area = elemento('space-map-scroll');
  const largura = Math.max(area.clientWidth || window.innerWidth, quantidade * 190 + 220);
  const altura = Math.max(area.clientHeight || 560, 420);
  moldura.style.setProperty('--map-width', `${largura}px`);
  moldura.style.setProperty('--map-height', `${altura}px`);
  montarFundoEspacial(largura, altura);
  const containerNos = elemento('challenge-node-list');
  containerNos.replaceChildren();

  // Bolinhas e trilha usam as mesmas coordenadas em pixels, então ficam sempre alinhadas.
  // A margem lateral garante que a primeira e a última bolinha não encostem na borda.
  const margemX = Math.min(90, largura * 0.06);
  const pontos = state.questoes.map((_, indice) => {
    const progresso = quantidade === 1 ? 0.5 : indice / (quantidade - 1);
    return { x: margemX + progresso * (largura - margemX * 2), y: altura * (0.50 + Math.sin(indice * 1.42) * 0.27 + Math.cos(indice * 0.61) * 0.08) };
  });
  desenharTrilha(elemento('space-map-route'), pontos);

  state.questoes.forEach((questao, indice) => {
    const respondida = state.questoesRespondidas.has(indice);
    // Requisitos 13 e 14: ✗ no que errou e ✓ no que acertou.
    const errou = respondida && state.resultadoQuestoes.get(indice) === false;
    const bloqueada = !respondida && indice !== proximaQuestao;
    const botao = document.createElement('button');
    botao.type = 'button';
    botao.className = `challenge-map-node ${indice % 2 === 0 ? 'node-lime' : 'node-turquoise'}${respondida ? ' node-complete' : ''}${errou ? ' node-wrong' : ''}${bloqueada ? ' node-locked' : ''}${indice === proximaQuestao ? ' node-current' : ''}`;
    botao.style.left = `${pontos[indice].x}px`;
    botao.style.top = `${pontos[indice].y}px`;
    const estado = respondida ? (errou ? ', respondida: errou' : ', respondida: acertou') : bloqueada ? ', bloqueada: responda as anteriores primeiro' : ', disponível';
    botao.setAttribute('aria-label', `Questão ${indice + 1}${estado}`);
    if (bloqueada) botao.setAttribute('aria-disabled', 'true');
    botao.title = `Questão ${indice + 1}${respondida ? (errou ? ' — errou' : ' — acertou') : bloqueada ? ' — bloqueada' : ''}`;
    botao.innerHTML = `<span class="node-shadow" aria-hidden="true"></span><span class="node-face" aria-hidden="true"><i class="node-play-mark fa-solid ${respondida ? (errou ? 'fa-xmark' : 'fa-check') : bloqueada ? 'fa-lock' : 'fa-play'}"></i></span><span class="node-caption">Questão ${indice + 1}</span>`;
    botao.addEventListener('click', () => {
      if (respondida) {
        mostrarToast('Esta questão já foi concluída. Siga para a próxima bolinha.');
        return;
      }
      if (indice !== indiceDaProximaQuestao()) {
        mostrarToast(`Siga a sequência: responda primeiro a Questão ${indiceDaProximaQuestao() + 1}.`);
        botao.classList.remove('node-shake');
        void botao.offsetWidth;
        botao.classList.add('node-shake');
        return;
      }
      state.indiceQuestao = indice;
      abrirQuestaoDoMapa();
    });
    containerNos.appendChild(botao);
  });
  atualizarAcaoDoMapa();
}

// Ação principal no rodapé do mapa. Cobre os casos em que a pessoa sai no meio do caminho:
// - respondeu tudo mas fechou o quiz antes de concluir → "Concluir fase";
// - concluiu a fase e voltou ao mapa (ou retomou depois) → "Próxima fase N/T".
function atualizarAcaoDoMapa() {
  const botao = elemento('map-next-action');
  if (!botao) return;
  const todasRespondidas = state.questoes.length > 0 && state.questoesRespondidas.size >= state.questoes.length;
  botao.hidden = true;
  if (!state.desafio || state.jornadaReprovada || !todasRespondidas) return;
  if (!state.faseConcluida) {
    botao.textContent = state.modoRevisao ? 'Concluir revisão ✓' : 'Concluir fase ✓';
    botao.hidden = false;
    return;
  }
  const config = state.configuracaoBase;
  if (state.modoRevisao || !config) return;
  const faseAtual = Number(config.faseNaJornada || 1);
  const total = Number(config.fasesPlanejadas || fasesPorQuantidade(config.quantidade));
  if (faseAtual >= total) return;
  botao.textContent = `Próxima fase ${faseAtual + 1}/${total} →`;
  botao.hidden = false;
}

elemento('map-next-action').addEventListener('click', async () => {
  const botao = elemento('map-next-action');
  botao.disabled = true;
  try {
    if (!state.faseConcluida) {
      // Mesmo fluxo de conclusão do quiz; o resultado aparece na tela de resultado de sempre.
      elemento('quiz-result').hidden = true;
      elemento('quiz-content').hidden = true;
      await concluirQuiz();
      if (!elemento('quiz-result').hidden) {
        elemento('quiz-theme-label').textContent = `${state.temaAtual.materia} · ${state.temaAtual.nome}`;
        elemento('quiz-xp-total').textContent = formatarNumero(state.aluno?.pontos || 0);
        elemento('quiz-overlay').hidden = false;
      } else {
        elemento('quiz-content').hidden = false;
      }
    } else {
      await seguirParaProximaFase();
    }
  } finally {
    botao.disabled = false;
  }
});

// Desenha a trilha só com elementos HTML: cada ligação entre duas bolinhas é uma curva
// (Bézier quadrática, a mesma forma da trilha antiga) dividida em pílulas curtas. Como as
// pílulas têm pontas totalmente arredondadas e se sobrepõem, o traço sai contínuo e liso.
// A trilha até uma questão já respondida fica na cor de "concluída".
function desenharTrilha(container, pontos) {
  container.replaceChildren();
  if (pontos.length < 2) return;
  const espessura = parseFloat(getComputedStyle(container).getPropertyValue('--route-thickness')) || 20;
  const camadaSombra = document.createElement('div');
  camadaSombra.className = 'route-layer route-layer-shadow';
  const camadaCor = document.createElement('div');
  camadaCor.className = 'route-layer';

  const criarPilula = (de, ate, classe) => {
    const pilula = document.createElement('span');
    pilula.className = classe;
    // Centro do trecho + comprimento estendido pela espessura, para as pontas redondas se encontrarem.
    pilula.style.left = `${((de.x + ate.x) / 2).toFixed(1)}px`;
    pilula.style.top = `${((de.y + ate.y) / 2).toFixed(1)}px`;
    pilula.style.width = `${(Math.hypot(ate.x - de.x, ate.y - de.y) + espessura).toFixed(1)}px`;
    pilula.style.setProperty('--angulo', `${Math.atan2(ate.y - de.y, ate.x - de.x).toFixed(4)}rad`);
    return pilula;
  };

  pontos.slice(0, -1).forEach((inicio, indice) => {
    const fim = pontos[indice + 1];
    const controle = { x: (inicio.x + fim.x) / 2, y: (inicio.y + fim.y) / 2 + (indice % 2 === 0 ? -58 : 58) };
    const cor = state.questoesRespondidas.has(indice + 1) ? 'is-done' : indice % 2 === 0 ? 'is-lime' : 'is-turquoise';
    // Mais pílulas em trechos longos: o passo fica próximo da espessura, então a curva não "quebra".
    const passos = Math.max(8, Math.ceil(Math.hypot(fim.x - inicio.x, fim.y - inicio.y) / espessura));
    let anterior = inicio;
    for (let passo = 1; passo <= passos; passo += 1) {
      const t = passo / passos;
      const atual = {
        x: (1 - t) * (1 - t) * inicio.x + 2 * (1 - t) * t * controle.x + t * t * fim.x,
        y: (1 - t) * (1 - t) * inicio.y + 2 * (1 - t) * t * controle.y + t * t * fim.y,
      };
      camadaSombra.appendChild(criarPilula(anterior, atual, 'route-segment'));
      camadaCor.appendChild(criarPilula(anterior, atual, `route-segment ${cor}`));
      anterior = atual;
    }
  });
  container.append(camadaSombra, camadaCor);
}

// A próxima questão a responder é sempre a primeira ainda não respondida (ordem 1, 2, 3…).
function indiceDaProximaQuestao() {
  for (let i = 0; i < state.questoes.length; i += 1) {
    if (!state.questoesRespondidas.has(i)) return i;
  }
  return -1;
}

function abrirQuestaoDoMapa() {
  if (!state.questoes[state.indiceQuestao] || state.indiceQuestao !== indiceDaProximaQuestao()) return;
  elemento('quiz-overlay').hidden = false;
  elemento('quiz-content').hidden = false;
  elemento('quiz-result').hidden = true;
  elemento('quiz-theme-label').textContent = `${state.temaAtual.materia} · ${state.temaAtual.nome}`;
  elemento('quiz-xp-total').textContent = formatarNumero(state.aluno.pontos || 0);
  mostrarQuestaoAtual();
}

function fecharMapaDesafio() {
  elemento('quiz-overlay').hidden = true;
  elemento('challenge-map-screen').hidden = true;
  document.body.classList.remove('map-open');
  trocarVisao('study');
  atualizarPainel().catch((erro) => console.warn('Não foi possível atualizar o painel:', erro.message));
  atualizarBotoesDesafio();
}

// Redesenha o mapa se a janela mudar de tamanho, para ele continuar cobrindo a tela.
let tempoRedimensionar = null;
window.addEventListener('resize', () => {
  clearTimeout(tempoRedimensionar);
  tempoRedimensionar = setTimeout(() => {
    if (!elemento('challenge-map-screen').hidden) renderizarMapaDesafio();
  }, 150);
});

elemento('exit-challenge-map').addEventListener('click', fecharMapaDesafio);
elemento('map-close-bottom').addEventListener('click', fecharMapaDesafio);

function aplicarTema(claro) {
  document.body.classList.toggle('theme-light', claro);
  const chave = elemento('theme-switch');
  if (chave) chave.checked = claro;
}

elemento('theme-switch').addEventListener('change', (evento) => {
  const claro = evento.target.checked;
  aplicarTema(claro);
  try { localStorage.setItem('explainer-theme-v4', claro ? 'light' : 'dark'); } catch (_) {}
});
try { aplicarTema(localStorage.getItem('explainer-theme-v4') === 'light'); } catch (_) {}

function abrirConfiguracoes(abrir) {
  elemento('config-panel').hidden = !abrir;
  document.body.classList.toggle('config-open', abrir);
}
elemento('open-config').addEventListener('click', () => { abrirConfiguracoes(true); elemento('sidebar').classList.remove('open'); });
elemento('config-close').addEventListener('click', () => abrirConfiguracoes(false));
document.addEventListener('keydown', (evento) => { if (evento.key === 'Escape') abrirConfiguracoes(false); });
elemento('top-avatar').addEventListener('click', () => { abrirConfiguracoes(false); trocarVisao('progress'); });

function abrirQuiz() {
  if (!state.questoes.length) {
    mostrarToast('O desafio foi criado sem questões disponíveis. Tente novamente.');
    return;
  }
  elemento('quiz-overlay').hidden = false;
  elemento('quiz-content').hidden = false;
  elemento('quiz-result').hidden = true;
  elemento('quiz-theme-label').textContent = `${state.temaAtual.materia} · ${state.temaAtual.nome}`;
  elemento('quiz-xp-total').textContent = formatarNumero(state.aluno.pontos || 0);
  mostrarQuestaoAtual();
}

function mostrarQuestaoAtual() {
  const questao = state.questoes[state.indiceQuestao];
  state.alternativaSelecionada = null;
  state.respostaEnviada = false;
  state.inicioQuestao = Date.now();
  elemento('quiz-counter').textContent = `Questão ${state.indiceQuestao + 1} de ${state.questoes.length}`;
  elemento('quiz-question-number').textContent = `Questão ${state.indiceQuestao + 1}`;
  elemento('quiz-progress-fill').style.width = `${(state.indiceQuestao / state.questoes.length) * 100}%`;
  elemento('quiz-question-title').textContent = questao.enunciado;
  elemento('quiz-action-hint').textContent = 'Escolha uma alternativa';
  elemento('next-question').disabled = true;
  elemento('next-question').innerHTML = state.modoMapa ? 'Continuar' : 'Confirmar resposta <span>→</span>';
  elemento('answer-feedback').hidden = true;
  elemento('answer-feedback').classList.remove('wrong');
  const lista = elemento('answer-list');
  lista.replaceChildren();
  LETRAS.forEach((letra) => {
    const botao = document.createElement('button');
    botao.type = 'button';
    botao.className = 'answer-option';
    botao.dataset.answer = letra;
    const marcador = document.createElement('span');
    marcador.className = 'answer-letter';
    marcador.textContent = letra;
    const texto = document.createElement('span');
    texto.className = 'answer-text';
    texto.textContent = questao.alternativas[letra] || 'Alternativa indisponível';
    botao.append(marcador, texto);
    botao.addEventListener('click', () => selecionarAlternativa(letra));
    lista.appendChild(botao);
  });
}

function selecionarAlternativa(letra) {
  if (state.respostaEnviada) return;
  state.alternativaSelecionada = letra;
  document.querySelectorAll('.answer-option').forEach((botao) => {
    botao.classList.toggle('selected', botao.dataset.answer === letra);
  });
  elemento('next-question').disabled = false;
  elemento('quiz-action-hint').textContent = `Alternativa ${letra} selecionada`;
}

elemento('next-question').addEventListener('click', async () => {
  if (state.respostaEnviada) {
    if (state.modoMapa) {
      if (state.questoesRespondidas.size >= state.questoes.length) {
        await concluirQuiz();
      } else {
        elemento('quiz-overlay').hidden = true;
        renderizarMapaDesafio();
        mostrarToast('Questão concluída. Escolha a próxima bolinha no mapa.');
      }
      return;
    }
    if (state.indiceQuestao < state.questoes.length - 1) {
      state.indiceQuestao += 1;
      mostrarQuestaoAtual();
    } else {
      await concluirQuiz();
    }
    return;
  }
  if (!state.alternativaSelecionada) return;
  const botaoProximo = elemento('next-question');
  botaoProximo.disabled = true;
  botaoProximo.textContent = 'Verificando…';
  const questao = state.questoes[state.indiceQuestao];
  const segundosGastos = Math.max(0, Math.round((Date.now() - state.inicioQuestao) / 1000));
  try {
    const resultado = await api(`/api/learning/challenges/${state.desafio.id_desafio}/answer`, {
      method: 'POST',
      body: { id_questao: questao.id_questao, alternativa: state.alternativaSelecionada, segundos_gastos: segundosGastos },
    });
    state.respostaEnviada = true;
    if (state.modoMapa) state.questoesRespondidas.add(state.indiceQuestao);
    state.resultadoQuestoes.set(state.indiceQuestao, Boolean(resultado.correta));
    state.aluno.pontos = resultado.pontos_totais;
    state.aluno.minutos_ativos = Math.max(state.aluno.minutos_ativos || 0, resultado.minutos_ativos || 0);
    elemento('quiz-xp-total').textContent = formatarNumero(state.aluno.pontos || 0);
    atualizarIdentidade();
    document.querySelectorAll('.answer-option').forEach((botao) => {
      botao.disabled = true;
      if (botao.dataset.answer === resultado.alternativa_correta) botao.classList.add('correct');
      else if (botao.dataset.answer === state.alternativaSelecionada && !resultado.correta) botao.classList.add('incorrect');
    });
    const feedback = elemento('answer-feedback');
    feedback.hidden = false;
    feedback.classList.toggle('wrong', !resultado.correta);
    elemento('feedback-title').textContent = resultado.correta ? 'Resposta correta!' : `A resposta correta é ${resultado.alternativa_correta}.`;
    elemento('feedback-text').textContent = resultado.explicacao;
    elemento('feedback-points').textContent = resultado.correta
      ? (resultado.pontos_ganhos > 0 ? `+${resultado.pontos_ganhos} pontos adicionados ao seu total.` : 'Revisão: esta tentativa não altera seus pontos.')
      : (resultado.pontos_ganhos < 0 ? `${Math.abs(resultado.pontos_ganhos)} pontos perdidos por errar. Continue tentando.` : 'Nenhum ponto nesta questão. Continue tentando.');
    if (resultado.correta) {
      state.acertosSeguidos += 1;
      const elogios = [
        'Mandou bem! Você acabou de conquistar mais um acerto.',
        'Boa leitura da questão! Seu esforço está aparecendo.',
        'Acertou! Mais um passo na sua jornada.',
        'Resposta certa! Pode comemorar essa evolução.',
        'Aí sim! Você está construindo conhecimento de verdade.'
      ];
      mostrarToast(elogios[(state.acertosSeguidos - 1) % elogios.length]);
    } else {
      state.acertosSeguidos = 0;
    }
    elemento('quiz-progress-fill').style.width = `${(state.questoesRespondidas.size / state.questoes.length) * 100}%`;
    elemento('quiz-action-hint').textContent = state.modoMapa
      ? (state.questoesRespondidas.size >= state.questoes.length ? 'Todas as questões foram respondidas.' : 'Volte ao mapa para escolher outra bolinha.')
      : (resultado.correta ? 'Boa! Vamos continuar.' : 'Revise a explicação e siga para a próxima.');
    botaoProximo.disabled = false;
    botaoProximo.innerHTML = state.modoMapa
      ? (state.questoesRespondidas.size >= state.questoes.length ? 'Concluir fase →' : 'Voltar ao mapa')
      : (state.indiceQuestao < state.questoes.length - 1 ? 'Próxima questão <span>→</span>' : 'Ver resultado <span>→</span>');
    if (state.modoMapa) renderizarMapaDesafio();
  } catch (erro) {
    mostrarToast(erro.message);
    botaoProximo.disabled = false;
    botaoProximo.innerHTML = 'Tentar novamente <span>→</span>';
    // 409 = a questão já foi respondida (ex.: em outra aba) ou está fora de ordem. Repetir o
    // envio daria o mesmo erro para sempre; recarrega o desafio salvo para sincronizar o mapa.
    if (erro.status === 409 && state.desafio && state.modoMapa && !state.modoRevisao) {
      elemento('quiz-overlay').hidden = true;
      await continuarDesafioSalvo(state.desafio.id_desafio);
    }
  }
});

const ELOGIOS_FASE = [
  { icone: '👍', titulo: 'Parabéns!', texto: 'Você concluiu um desafio. Você é bacana demais, continue assim!' },
  { icone: '🌟', titulo: 'Mandou muito bem!', texto: 'Mais um desafio concluído. Seu esforço está aparecendo!' },
  { icone: '🚀', titulo: 'Decolou!', texto: 'Desafio concluído! Você está evoluindo rápido.' },
  { icone: '💪', titulo: 'Que orgulho!', texto: 'Mais um desafio no bolso. Seu foco é inspirador!' },
  { icone: '🎯', titulo: 'Na mosca!', texto: 'Você concluiu o desafio. Continue nesse ritmo!' },
];

// Escolhe e mostra a comemoração certa. Prioridade: jornada completa > 5 seguidos > desafio comum.
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
      tipo: 'party',
    });
  } else if (fezCincoSeguidos) {
    tocarSom('uhul');
    mostrarElogio({
      icone: '🔥',
      titulo: `${seguidos} desafios seguidos!`,
      texto: 'Você concluiu 5 desafios em sequência. Está imparável!',
      xp: xpExtra,
      duracao: 7,
      tipo: 'streak',
    });
  } else {
    emojisSubindo('👍');
    tocarSom('ok');
    const elogio = ELOGIOS_FASE[Math.floor(Math.random() * ELOGIOS_FASE.length)];
    mostrarElogio({ ...elogio, xp: xpExtra, duracao: 6 });
  }
}

// Jornada reprovada: erros >= 70% somando todas as fases. O servidor já apagou tudo e tirou os pontos.
async function tratarJornadaReprovada(resultado) {
  state.jornadaReprovada = true;
  gravarSeguidos(0);
  fecharElogio(true);
  elemento('quiz-content').hidden = true;
  elemento('quiz-result').hidden = false;
  elemento('quiz-progress-fill').style.width = '100%';
  elemento('result-title').textContent = 'Jornada não concluída';
  elemento('result-description').textContent = `Você errou ${resultado.taxa_erro}% das questões da jornada (o limite é 70%). Todo o progresso e os pontos desta jornada foram perdidos, como se ela não tivesse acontecido. Recomece com perguntas novas!`;
  elemento('result-correct').textContent = `${resultado.questoes_corretas}/${resultado.questoes_total}`;
  elemento('result-points').textContent = resultado.pontos_perdidos > 0 ? `−${formatarNumero(resultado.pontos_perdidos)}` : '0';
  elemento('result-points').previousElementSibling.textContent = 'Pontos perdidos';
  elemento('quiz-result').querySelector('.mini-kicker').textContent = 'JORNADA REPROVADA';
  elemento('result-accuracy').textContent = `${resultado.aproveitamento}%`;
  elemento('result-bonus').hidden = true;
  elemento('result-review').hidden = true;
  elemento('next-challenge').hidden = false;
  elemento('next-challenge').disabled = false;
  elemento('next-challenge').innerHTML = 'Recomeçar jornada <span>↻</span>';
  elemento('finish-quiz').textContent = 'Voltar ao painel';
  atualizarIdentidade();
  atualizarPainelPerfil();
  elemento('quiz-xp-total').textContent = formatarNumero(state.aluno.pontos || 0);
  state.faseAtiva = 0;
  await atualizarPainel();
  await atualizarBotoesDesafio();
}

// Resumo da fase na tela de resultado (requisitos 13 e 14): "1 ✓", "2 ✗"...
function mostrarResumoDaFase() {
  const lista = elemento('result-review-list');
  lista.replaceChildren();
  state.questoes.forEach((_, indice) => {
    if (!state.resultadoQuestoes.has(indice)) return;
    const acertou = state.resultadoQuestoes.get(indice);
    const item = document.createElement('li');
    item.className = acertou ? 'is-right' : 'is-wrong';
    item.textContent = `${indice + 1} ${acertou ? '✓' : '✗'}`;
    item.setAttribute('aria-label', `Questão ${indice + 1}: ${acertou ? 'acertou' : 'errou'}`);
    lista.appendChild(item);
  });
  elemento('result-review').hidden = !lista.children.length;
}

async function concluirQuiz() {
  const botao = elemento('next-question');
  botao.disabled = true;
  botao.textContent = 'Salvando resultado…';
  const ehRevisao = Boolean(state.modoRevisao);
  const jornadaAtual = Number(state.configuracaoBase?.faseNaJornada || 1);
  const totalJornada = Number(state.configuracaoBase?.fasesPlanejadas || fasesPorQuantidade(state.questoes.length));
  const ultimaDaJornada = !ehRevisao && jornadaAtual >= totalJornada;
  try {
    const resultado = await api(`/api/learning/challenges/${state.desafio.id_desafio}/complete`, { method: 'POST', body: { jornada_concluida: ultimaDaJornada } });
    state.progresso = resultado.progresso;
    state.aluno.pontos = resultado.pontos_totais;
    if (resultado.reprovado) { await tratarJornadaReprovada(resultado); return; }
    state.faseConcluida = true;
    atualizarAcaoDoMapa();
    elemento('quiz-content').hidden = true;
    elemento('quiz-result').hidden = false;
    elemento('result-points').previousElementSibling.textContent = 'Pontos ganhos';
    elemento('quiz-result').querySelector('.mini-kicker').textContent = 'FASE CONCLUÍDA';
    elemento('result-correct').textContent = `${resultado.questoes_corretas}/${resultado.quantidade_questoes}`;
    elemento('result-points').textContent = `${resultado.pontos_ganhos < 0 ? '−' : '+'}${formatarNumero(Math.abs(resultado.pontos_ganhos))}`;
    elemento('result-accuracy').textContent = `${Math.round((resultado.questoes_corretas / Math.max(resultado.quantidade_questoes, 1)) * 100)}%`;
    elemento('result-title').textContent = resultado.questoes_corretas === resultado.quantidade_questoes ? 'Desafio perfeito!' : 'Mais uma fase concluída!';
    elemento('result-description').textContent = resultado.questoes_corretas === resultado.quantidade_questoes ? 'Você acertou todas as questões. Continue mantendo esse ritmo.' : 'Cada tentativa conta. Revise os conceitos e avance para a próxima fase.';
    elemento('result-bonus').hidden = !(resultado.bonus_perfeito > 0);
    mostrarResumoDaFase();
    elemento('quiz-progress-fill').style.width = '100%';

    // Botões do resultado
    elemento('next-challenge').disabled = false;
    if (ehRevisao) {
      const revisao = state.revisao || { lista: [], pos: 0 };
      const proximo = revisao.lista[revisao.pos + 1] || null;
      elemento('next-challenge').hidden = !proximo;
      if (proximo) elemento('next-challenge').innerHTML = `Refazer desafio ${revisao.pos + 2} <span>→</span>`;
      elemento('finish-quiz').textContent = 'Voltar ao painel';
    } else {
      elemento('next-challenge').hidden = false;
      elemento('next-challenge').innerHTML = jornadaAtual >= totalJornada
        ? 'Concluir jornada <span>✓</span>'
        : `Próxima fase ${jornadaAtual + 1}/${totalJornada} <span>→</span>`;
      elemento('finish-quiz').textContent = 'Voltar ao mapa';
    }
    atualizarIdentidade();
    atualizarPainelPerfil();
    elemento('quiz-xp-total').textContent = formatarNumero(state.aluno.pontos || 0);

    if (ehRevisao) {
      mostrarToast('Revisão concluída. Esta tentativa não concede pontos.');
      const revisao = state.revisao || { lista: [], pos: 0 };
      const numeroProximo = revisao.pos + 2;
      const totalFases = fasesPorQuantidade(state.questoes.length);
      if (!revisao.lista[revisao.pos + 1] && numeroProximo <= totalFases) {
        avisar(`Desafio ${numeroProximo} ainda bloqueado`, `Conclua o desafio ${numeroProximo} no seu progresso normal para conseguir refazê-lo.`);
      }
    } else if (!resultado.ja_concluido) {
      comemorarConclusao({ ultimaDaJornada, resultado });
    }
    await atualizarPainel();
    await atualizarBotoesDesafio();
  } catch (erro) {
    mostrarToast(erro.message);
    botao.disabled = false;
    botao.innerHTML = 'Tentar salvar resultado <span>→</span>';
  }
}

elemento('finish-quiz').addEventListener('click', async () => {
  elemento('quiz-overlay').hidden = true;
  if (state.modoRevisao || state.jornadaReprovada) {
    fecharMapaDesafio();
    return;
  }
  if (state.modoMapa && !elemento('challenge-map-screen').hidden) {
    renderizarMapaDesafio();
  } else {
    trocarVisao('study');
  }
  await atualizarPainel();
  if (state.modoMapa && !elemento('challenge-map-screen').hidden) renderizarMapaDesafio();
});

elemento('close-quiz').addEventListener('click', () => {
  if ((state.modoRevisao || state.jornadaReprovada) && !elemento('quiz-result').hidden) { elemento('quiz-overlay').hidden = true; fecharMapaDesafio(); return; }
  if (state.modoRevisao) { elemento('quiz-overlay').hidden = true; renderizarMapaDesafio(); return; }
  if (state.desafio && !elemento('quiz-result').hidden) {
    elemento('quiz-overlay').hidden = true;
    renderizarMapaDesafio();
    return;
  }
  // A resposta já foi salva no servidor: fecha direto (o mapa mostra "Concluir fase" se for a última).
  const confirmou = state.respostaEnviada || window.confirm('Voltar ao mapa? A resposta desta questão só será salva quando você confirmar.');
  if (confirmou) {
    elemento('quiz-overlay').hidden = true;
    renderizarMapaDesafio();
  }
});

async function atualizarPainel() {
  const tarefas = await Promise.allSettled([
    api('/api/learning/me'),
    api(`/api/learning/ranking?limite=${elemento('ranking-view').hidden ? 5 : 100}`),
    api('/api/learning/history'),
  ]);
  if (tarefas[0].status === 'fulfilled') {
    state.aluno = tarefas[0].value.aluno;
    state.progresso = tarefas[0].value.progresso;
    atualizarIdentidade();
    atualizarPainelPerfil();
  }
  if (tarefas[1].status === 'fulfilled') renderizarRankingPreview(tarefas[1].value);
  if (tarefas[2].status === 'fulfilled') {
    window.__historicoDesafios = tarefas[2].value.historico || [];
    renderizarHistorico(tarefas[2].value.historico || []);
    atualizarMapaSelecionado();
  }
}

function renderizarRankingPreview(dados) {
  const contenedor = elemento('ranking-preview-list');
  contenedor.replaceChildren();
  const itens = dados.itens || [];
  if (!itens.length) {
    contenedor.innerHTML = '<div class="empty-state">Ainda não há estudantes no ranking.</div>';
    return;
  }
  itens.slice(0, 4).forEach((item) => {
    const linha = document.createElement('div');
    linha.className = 'ranking-row';
    const posicao = document.createElement('span');
    posicao.className = `ranking-place ${item.posicao === 1 ? 'first' : ''}`;
    posicao.textContent = String(item.posicao).padStart(2, '0');
    const avatar = document.createElement('span');
    avatar.className = 'ranking-avatar';
    avatar.textContent = (item.nick || 'E').charAt(0).toUpperCase();
    const nome = document.createElement('span');
    nome.className = 'ranking-name';
    nome.textContent = item.nick || 'Estudante';
    const detalhe = document.createElement('small');
    detalhe.textContent = `${item.sequencia_atual || 0} dias de sequência`;
    nome.appendChild(detalhe);
    const pontos = document.createElement('span');
    pontos.className = 'ranking-score';
    pontos.textContent = `${formatarNumero(item.pontos)} pts`;
    linha.append(posicao, avatar, nome, pontos);
    contenedor.appendChild(linha);
  });
  renderizarTabelaRanking(dados);
}

function renderizarTabelaRanking(dados) {
  const itensRanking = dados.itens || [];
  const posicaoUsuario = itensRanking.find((item) => state.aluno && item.id_aluno === state.aluno.id_aluno)?.posicao || dados.posicao_usuario;
  if (elemento('stat-rank')) elemento('stat-rank').textContent = posicaoUsuario ? `#${posicaoUsuario}` : '#—';
  if (elemento('top-rank')) elemento('top-rank').textContent = posicaoUsuario ? `#${posicaoUsuario}` : '#—';
  const corpo = elemento('ranking-table-body');
  corpo.replaceChildren();
  const itens = dados.itens || [];
  if (!itens.length) {
    const linha = corpo.insertRow();
    linha.insertCell().colSpan = 5;
    linha.cells[0].textContent = 'Ainda não há pontuações registradas.';
    return;
  }
  itens.forEach((item) => {
    const linha = corpo.insertRow();
    if (state.aluno && item.id_aluno === state.aluno.id_aluno) linha.className = 'current-user-row';
    const rank = linha.insertCell();
    const medalha = document.createElement('span');
    const classe = item.posicao === 1 ? 'gold' : item.posicao === 2 ? 'silver' : item.posicao === 3 ? 'bronze' : '';
    medalha.className = `rank-medal ${classe}`;
    medalha.textContent = item.posicao;
    rank.appendChild(medalha);
    const estudante = linha.insertCell();
    estudante.className = 'student-cell';
    const avatar = document.createElement('span');
    avatar.className = 'ranking-avatar';
    avatar.textContent = (item.nick || 'E').charAt(0).toUpperCase();
    const nome = document.createElement('span');
    nome.textContent = item.nick || 'Estudante';
    estudante.append(avatar, nome);
    linha.insertCell().textContent = `${item.sequencia_atual || 0} dias`;
    linha.insertCell().textContent = `${formatarNumero(item.minutos_ativos || 0)} min`;
    const pontos = linha.insertCell();
    pontos.className = 'points-cell';
    pontos.textContent = `${formatarNumero(item.pontos)} pts`;
  });
}

function renderizarHistorico(historico) {
  const preview = elemento('recent-preview-list');
  preview.replaceChildren();
  const corpo = elemento('history-table-body');
  corpo.replaceChildren();
  if (!historico.length) {
    preview.innerHTML = '<div class="empty-state">Você ainda não concluiu um desafio. Seu primeiro está a um clique.</div>';
    const linha = corpo.insertRow();
    linha.insertCell().colSpan = 6;
    linha.cells[0].textContent = 'Seu histórico aparecerá aqui depois do primeiro desafio.';
    return;
  }
  historico.slice(0, 3).forEach((item) => {
    const linha = document.createElement('div');
    linha.className = 'recent-row';
    const icone = document.createElement('span');
    icone.className = 'recent-icon';
    icone.textContent = item.concluido ? '✓' : '◷';
    const copia = document.createElement('span');
    copia.className = 'recent-copy';
    const titulo = document.createElement('strong');
    titulo.textContent = item.nome;
    const subtitulo = document.createElement('span');
    subtitulo.textContent = `${item.materia} · ${rotuloDificuldade(item.dificuldade)}`;
    copia.append(titulo, subtitulo);
    const pontos = document.createElement('span');
    pontos.className = 'recent-points';
    pontos.textContent = `+${formatarNumero(item.pontuacao_obtida || 0)}`;
    linha.append(icone, copia, pontos);
    preview.appendChild(linha);
  });
  historico.forEach((item) => {
    const linha = corpo.insertRow();
    const nome = linha.insertCell();
    nome.textContent = item.nome;
    const tema = linha.insertCell();
    tema.textContent = `${item.materia} · ${item.tema}`;
    const dificuldade = linha.insertCell();
    const tag = document.createElement('span');
    const chave = chaveDificuldade(item.dificuldade);
    tag.className = `difficulty-tag ${chave === 'dificil' ? 'hard' : chave === 'normal' ? 'normal' : ''}`;
    tag.textContent = rotuloDificuldade(item.dificuldade);
    dificuldade.appendChild(tag);
    linha.insertCell().textContent = `${formatarNumero(item.pontuacao_obtida || 0)} pts`;
    linha.insertCell().textContent = formatarData(item.data_realizacao);
    const acao = linha.insertCell();
    const refazer = document.createElement('button');
    refazer.type = 'button';
    refazer.className = 'history-replay-button';
    refazer.textContent = 'Refazer ↻';
    refazer.disabled = !item.id_tema || Boolean(item.modo_revisao);
    refazer.title = 'Criar uma nova tentativa com a mesma matéria, tema e dificuldade';
    refazer.addEventListener('click', () => refazerDesafio(item));
    acao.appendChild(refazer);
  });
}

async function refazerDesafio(item, lista = null, pos = null) {
  try {
    mostrarToast('Preparando uma nova tentativa…');
    const quantidade = [5, 10, 15, 20].includes(Number(item.quantidade_questoes)) ? Number(item.quantidade_questoes) : 5;
    // Refazer repete a dificuldade do desafio original: nunca avança na escada.
    const dificuldadeBase = chaveDificuldade(item.dificuldade);
    const dados = await api('/api/learning/challenges', { method: 'POST', body: {
      id_tema: Number(item.id_tema), quantidade_questoes: quantidade, dificuldade: dificuldadeBase, refazer: true, refazer_de: item.id_desafio,
    }});
    // Sequência de revisão: desafio 1, 2, 3… (só os que já foram concluídos no progresso normal).
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
    mostrarToast(`Revisão do desafio ${posicao + 1}: você pode sair a qualquer momento. Esta tentativa não altera sua jornada nem concede pontos.`);
  } catch (erro) {
    mostrarToast(`Não foi possível refazer: ${erro.message}`);
  }
}

elemento('next-challenge').addEventListener('click', async () => {
  if (state.jornadaReprovada) {
    const config = state.configuracaoBase;
    elemento('quiz-overlay').hidden = true;
    try {
      await gerarNovoDesafio({ id_tema: config.idTema }, { quantidade: config.quantidade, dificuldadeBase: config.dificuldadeBase });
    } catch (erro) { mostrarToast(`Não foi possível recomeçar: ${erro.message}`); fecharMapaDesafio(); }
    return;
  }
  if (state.modoRevisao) {
    const revisao = state.revisao;
    const proximo = revisao && revisao.lista[revisao.pos + 1];
    if (!proximo) {
      avisar(`Desafio ${(revisao?.pos || 0) + 2} ainda bloqueado`, `Conclua o desafio ${(revisao?.pos || 0) + 2} no seu progresso normal para conseguir refazê-lo.`);
      return;
    }
    elemento('quiz-overlay').hidden = true;
    await refazerDesafio(proximo, revisao.lista, revisao.pos + 1);
    return;
  }
  const botao = elemento('next-challenge');
  botao.disabled = true;
  try {
    await seguirParaProximaFase({ aoPreparar: () => { botao.textContent = 'Preparando próxima fase…'; } });
  } finally {
    botao.disabled = false;
    const configAtual = state.configuracaoBase;
    if (configAtual) {
      const faseAtual = Number(configAtual.faseNaJornada || 1);
      const total = Number(configAtual.fasesPlanejadas || fasesPorQuantidade(configAtual.quantidade));
      botao.innerHTML = faseAtual >= total ? 'Concluir jornada <span>✓</span>' : `Próxima fase ${faseAtual + 1}/${total} <span>→</span>`;
    }
  }
});

// Avança para a próxima fase planejada da jornada atual. Usado pela tela de resultado,
// pelo botão do mapa e pelo "Continuar jornada" do painel.
async function seguirParaProximaFase({ aoPreparar = null } = {}) {
  const config = state.configuracaoBase;
  if (!config) {
    elemento('quiz-overlay').hidden = true;
    trocarVisao('study');
    return;
  }
  const jornadaConcluida = Number(config.faseNaJornada || 1) >= Number(config.fasesPlanejadas || fasesPorQuantidade(config.quantidade));
  if (jornadaConcluida) {
    elemento('quiz-overlay').hidden = true;
    elemento('challenge-map-screen').hidden = true;
    document.body.classList.remove('map-open');
    trocarVisao('study');
    await atualizarPainel();
    mostrarToast('Jornada concluída! Você terminou todas as fases planejadas. Escolha um novo tema para continuar.');
    return;
  }
  if (aoPreparar) aoPreparar();
  try {
    await criarProximoDesafio({ ...config, faseNaJornada: Number(config.faseNaJornada || 1) + 1, mostrarMapa: true });
  } catch (erro) {
    mostrarToast(`Não foi possível criar a próxima fase: ${erro.message}`);
  }
  await atualizarBotoesDesafio();
}

// Visões visitadas nesta página, para o botão "Voltar" desfazer a última troca de visão
// antes de recorrer ao histórico do navegador (voltar.js).
const historicoVisoes = [];
let visaoAtual = 'study';

function atualizarBotaoVoltar() {
  const botao = elemento('back-button');
  if (!botao) return;
  const semDestino = !historicoVisoes.length && visaoAtual === 'study' && !window.ExplAIner?.temPaginaAnteriorDoApp?.();
  botao.setAttribute('aria-disabled', semDestino ? 'true' : 'false');
  botao.title = semDestino ? 'Você já está na página inicial' : 'Voltar';
}

if (window.ExplAIner) {
  window.ExplAIner.aoVoltar = () => {
    if (historicoVisoes.length) {
      trocarVisao(historicoVisoes.pop(), { registrar: false });
      return true;
    }
    if (visaoAtual !== 'study') {
      trocarVisao('study', { registrar: false });
      return true;
    }
    return false; // segue para o histórico do navegador ou para o fallback
  };
}

function trocarVisao(visao, { registrar = true } = {}) {
  if (registrar && visao !== visaoAtual) {
    historicoVisoes.push(visaoAtual);
    if (historicoVisoes.length > 20) historicoVisoes.shift();
  }
  visaoAtual = visao;
  atualizarBotaoVoltar();
  const titulos = { study: 'Aprender', ranking: 'Ranking', progress: 'Meu progresso' };
  ['study', 'ranking', 'progress'].forEach((nome) => {
    elemento(`${nome}-view`).hidden = nome !== visao;
  });
  document.querySelectorAll('.nav-item[data-view]').forEach((botao) => botao.classList.toggle('active', botao.dataset.view === visao));
  elemento('page-heading').textContent = titulos[visao] || 'Aprender';
  elemento('sidebar').classList.remove('open');
  abrirConfiguracoes(false);
  if (visao !== 'study') atualizarPainel().catch(() => {});
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

document.querySelectorAll('.nav-item[data-view]').forEach((botao) => botao.addEventListener('click', () => trocarVisao(botao.dataset.view)));
document.querySelectorAll('[data-go-view]').forEach((botao) => botao.addEventListener('click', () => trocarVisao(botao.dataset.goView)));
elemento('mobile-menu').addEventListener('click', () => elemento('sidebar').classList.toggle('open'));
document.addEventListener('click', (evento) => {
  const sidebar = elemento('sidebar');
  if (window.innerWidth <= 720 && sidebar.classList.contains('open') && !sidebar.contains(evento.target) && !elemento('mobile-menu').contains(evento.target)) sidebar.classList.remove('open');
});

function fecharMenuConta() {
  elemento('account-popover').hidden = true;
  elemento('logout-button').setAttribute('aria-expanded', 'false');
}

async function encerrarSessao(voltarAoLogin = true) {
  try { await api('/api/auth/logout', { method: 'POST', body: {} }); } catch (erro) { console.warn(erro); }
  state.aluno = null;
  state.progresso = null;
  pararContagemDeTempo();
  fecharMenuConta();
  mostrarTelaAutenticacao();
  trocarModoAutenticacao('login');
  elemento('login-form').reset();
  if (voltarAoLogin) elemento('login-form').querySelector('input[name="email"]').focus();
}

elemento('logout-button').addEventListener('click', (evento) => {
  evento.stopPropagation();
  const menu = elemento('account-popover');
  menu.hidden = !menu.hidden;
  elemento('logout-button').setAttribute('aria-expanded', String(!menu.hidden));
});
elemento('account-popover').addEventListener('click', async (evento) => {
  const botao = evento.target.closest('[data-account-action]');
  if (!botao) return;
  const acao = botao.dataset.accountAction;
  if (acao === 'logout') {
    fecharMenuConta();
    await encerrarSessao(false);
  } else if (acao === 'switch') {
    fecharMenuConta();
    await encerrarSessao(true);
    mostrarAviso('Entre com outra conta ou use o mesmo e-mail para voltar ao seu perfil.', 'success');
  } else if (acao === 'delete') {
    fecharMenuConta();
    const confirmou = await perguntar({
      titulo: 'Excluir sua conta?',
      texto: 'Seu perfil, pontos e histórico serão apagados permanentemente. Esta ação não pode ser desfeita.',
      sim: 'Continuar', nao: 'Cancelar', icone: 'fa-trash',
    });
    if (!confirmou) return;
    // A senha é pedida num campo mascarado do próprio modal, para não aparecer na tela.
    const senha = await perguntar({
      titulo: 'Confirme com sua senha',
      texto: 'Por segurança, digite sua senha para excluir a conta.',
      sim: 'Excluir conta', nao: 'Cancelar', icone: 'fa-lock', campoSenha: true,
    });
    if (!senha) return;
    try {
      await api('/api/auth/delete-account', { method: 'DELETE', body: { senha } });
      state.aluno = null;
      state.progresso = null;
      pararContagemDeTempo();
      mostrarTelaAutenticacao();
      trocarModoAutenticacao('register');
      mostrarAviso('Conta excluída com sucesso.');
    } catch (erro) { mostrarToast(erro.message); }
  }
});
document.addEventListener('click', (evento) => {
  if (!elemento('account-popover').hidden && !elemento('account-popover').contains(evento.target) && !elemento('logout-button').contains(evento.target)) fecharMenuConta();
});

elemento('profile-form').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  const nick = elemento('profile-nick').value.trim();
  const botao = evento.currentTarget.querySelector('button');
  botao.disabled = true;
  try {
    const dados = await api('/api/learning/profile', { method: 'PATCH', body: { nick } });
    state.aluno = { ...state.aluno, ...dados.aluno };
    atualizarIdentidade();
    mostrarAviso('Nick atualizado. Ele já aparece no seu perfil.', 'success', 'profile-message');
    await atualizarPainel();
  } catch (erro) {
    mostrarAviso(erro.message, 'error', 'profile-message');
  } finally {
    botao.disabled = false;
  }
});

function iniciarContagemDeTempo() {
  pararContagemDeTempo();
  state.heartbeat = setInterval(async () => {
    if (document.visibilityState !== 'visible' || !state.aluno) return;
    try {
      const dados = await api('/api/learning/activity', { method: 'POST', body: { segundos: 60 } });
      state.aluno.minutos_ativos = dados.minutos_ativos;
      state.aluno.sequencia_atual = dados.sequencia_atual;
      elemento('stat-minutes').textContent = formatarNumero(dados.minutos_ativos);
      elemento('sidebar-streak').textContent = `${dados.sequencia_atual} ${dados.sequencia_atual === 1 ? 'dia' : 'dias'}`;
      elemento('top-streak').textContent = dados.sequencia_atual;
      elemento('stat-streak').textContent = dados.sequencia_atual;
    } catch (erro) {
      console.warn('Não foi possível registrar o tempo ativo:', erro.message);
    }
  }, 60000);
}

function pararContagemDeTempo() {
  if (state.heartbeat) clearInterval(state.heartbeat);
  state.heartbeat = null;
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
