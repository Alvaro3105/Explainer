/*
 * Fluxo das atividades: peças de interface usadas por estudar.js.
 *
 * - Carregamento: camada que cobre e bloqueia a tela enquanto um desafio é gerado.
 * - Explicação do erro: painel sobre a questão, visível por exatamente 7,6 s, com barra de tempo.
 * - Avanço no caminho: anima o trecho da trilha entre a bolinha respondida e a próxima.
 *
 * Toda espera recebe um AbortSignal. Quando o fluxo é encerrado (o aluno sai do mapa, gera outro
 * desafio etc.), o sinal é abortado: temporizadores e animações param e nada mais acontece.
 */
(function () {
  'use strict';

  const TEMPO_EXPLICACAO_MS = 7600; // tempo definitivo de leitura da explicação do erro
  const $ = (id) => document.getElementById(id);
  const menosMovimento = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  class FluxoCancelado extends Error {
    constructor() { super('Fluxo cancelado'); this.name = 'FluxoCancelado'; }
  }
  const foiCancelado = (erro) => erro instanceof FluxoCancelado;

  function verificar(sinal) {
    if (sinal && sinal.aborted) throw new FluxoCancelado();
  }

  // Espera que respeita o cancelamento.
  function esperar(ms, sinal) {
    return new Promise((resolver, rejeitar) => {
      if (sinal && sinal.aborted) { rejeitar(new FluxoCancelado()); return; }
      const tempo = setTimeout(() => { sinal && sinal.removeEventListener('abort', aoAbortar); resolver(); }, ms);
      function aoAbortar() { clearTimeout(tempo); rejeitar(new FluxoCancelado()); }
      sinal && sinal.addEventListener('abort', aoAbortar, { once: true });
    });
  }

  // Espera o navegador pintar a tela (dois quadros), para começar a contar só com o painel visível.
  function depoisDePintar(sinal) {
    return new Promise((resolver, rejeitar) => {
      requestAnimationFrame(() => requestAnimationFrame(() => {
        if (sinal && sinal.aborted) rejeitar(new FluxoCancelado()); else resolver();
      }));
    });
  }

  /* ---------- Bloqueio do fundo ---------- */
  // Deixa inertes (sem clique, toque nem foco por teclado) todos os filhos do <body>,
  // menos os que devem continuar ativos. Devolve uma função que desfaz o bloqueio.
  function bloquearFundo(manterAtivos) {
    const alterados = [];
    [...document.body.children].forEach((filho) => {
      if (manterAtivos.includes(filho) || filho.tagName === 'SCRIPT' || filho.inert) return;
      filho.inert = true;
      alterados.push(filho);
    });
    return () => alterados.forEach((filho) => { filho.inert = false; });
  }

  // Escape fica bloqueado enquanto uma camada obrigatória está aberta (carregamento em curso
  // ou explicação do erro). O ouvinte fica na fase de captura, antes dos outros da página.
  // Na tela de falha da geração, Escape equivale a "Fechar".
  let explicacaoAberta = false;
  window.addEventListener('keydown', (evento) => {
    if (evento.key !== 'Escape') return;
    const geracaoEmCurso = carregamento._ativo && !carregamento._emErro;
    if (!geracaoEmCurso && !explicacaoAberta && !carregamento._emErro) return;
    evento.preventDefault();
    evento.stopImmediatePropagation();
    if (carregamento._emErro && !explicacaoAberta) carregamento._desistir();
  }, true);

  /* ---------- Carregamento ao gerar atividade ---------- */
  const carregamento = {
    _ativo: false,
    _emErro: false,
    _desbloquear: null,
    _focoAnterior: null,
    _aoTentar: null,
    _aoDesistir: null,

    ativo() { return this._ativo; },

    iniciar({ titulo = 'Gerando sua atividade…', texto = 'A inteligência artificial está preparando as questões. Isso pode levar alguns segundos.' } = {}) {
      const camada = $('camada-gerando');
      $('titulo-gerando').textContent = titulo;
      $('texto-gerando').textContent = texto;
      $('estado-carregando-gerando').hidden = false;
      $('estado-erro-gerando').hidden = true;
      camada.classList.remove('saindo');
      this._emErro = false;
      this._aoTentar = null;
      this._aoDesistir = null;
      if (this._ativo) { $('cartao-gerando').focus({ preventScroll: true }); return; }
      this._ativo = true;
      this._focoAnterior = document.activeElement;
      camada.hidden = false;
      document.body.classList.add('gerando-atividade');
      this._desbloquear = bloquearFundo([camada, $('aviso-rapido')]);
      $('cartao-gerando').focus({ preventScroll: true });
    },

    // Mostra a falha dentro da própria camada, com "Tentar novamente" e "Fechar".
    falhar(mensagem, aoTentarDeNovo, aoDesistir) {
      $('estado-carregando-gerando').hidden = true;
      $('estado-erro-gerando').hidden = false;
      $('mensagem-erro-gerando').textContent = mensagem || 'Não foi possível gerar a atividade.';
      this._emErro = true;
      this._aoTentar = aoTentarDeNovo;
      this._aoDesistir = aoDesistir;
      $('tentar-gerar-novamente').focus({ preventScroll: true });
    },

    _tentar() {
      const acao = this._aoTentar;
      this._aoTentar = null; this._aoDesistir = null;
      if (acao) acao();
    },

    _desistir() {
      const acao = this._aoDesistir;
      this._aoTentar = null; this._aoDesistir = null;
      this.encerrar();
      if (acao) acao();
    },

    encerrar() {
      if (!this._ativo) return;
      const camada = $('camada-gerando');
      this._emErro = false;
      this._ativo = false;
      if (this._desbloquear) this._desbloquear();
      this._desbloquear = null;
      document.body.classList.remove('gerando-atividade');
      const focoAnterior = this._focoAnterior;
      this._focoAnterior = null;
      if (menosMovimento()) {
        camada.hidden = true;
      } else {
        camada.classList.add('saindo');
        setTimeout(() => { if (!this._ativo) { camada.hidden = true; camada.classList.remove('saindo'); } }, 220);
      }
      if (focoAnterior && document.contains(focoAnterior) && !focoAnterior.closest('[inert]')) {
        focoAnterior.focus({ preventScroll: true });
      }
    },
  };

  // Executa uma geração com a camada de carregamento. A camada só sai quando a tarefa termina
  // de verdade. Em falha, mostra a mensagem com "Tentar novamente".
  // Devolve true se gerou, false se o aluno desistiu depois de uma falha.
  function gerarComCarregamento(tarefa, opcoes = {}) {
    return new Promise((resolver, rejeitar) => {
      const tentar = async () => {
        carregamento.iniciar(opcoes);
        try {
          await tarefa();
          carregamento.encerrar();
          resolver(true);
        } catch (erro) {
          if (erro && erro.status === 401) { carregamento.encerrar(); rejeitar(erro); return; }
          carregamento.falhar(erro && erro.message, tentar, () => resolver(false));
        }
      };
      tentar();
    });
  }

  // Os botões da tela de falha existem uma vez só no HTML; os ouvintes também.
  document.addEventListener('DOMContentLoaded', () => {
    $('tentar-gerar-novamente').addEventListener('click', () => carregamento._tentar());
    $('fechar-erro-gerando').addEventListener('click', () => carregamento._desistir());
  });

  /* ---------- Explicação do erro (7,6 s) ---------- */
  // Mostra o painel sobre a questão e resolve quando o tempo acaba.
  // Rejeita com FluxoCancelado se o sinal for abortado.
  async function mostrarExplicacaoErro(dados, sinal) {
    const janela = $('janela-explicacao');
    const cartao = $('cartao-explicacao');
    const barra = $('barra-tempo-explicacao');
    const progresso = $('progresso-tempo-explicacao');
    const segundos = $('segundos-explicacao');

    $('enunciado-explicacao').textContent = dados.enunciado || '';
    $('letra-marcada-explicacao').textContent = dados.letraMarcada;
    $('texto-marcado-explicacao').textContent = dados.textoMarcado || '';
    $('letra-correta-explicacao').textContent = dados.letraCorreta;
    $('texto-correto-explicacao').textContent = dados.textoCorreto || '';
    $('titulo-raciocinio-explicacao').textContent = `Por que a resposta certa é ${dados.letraCorreta}`;
    $('texto-explicacao').textContent = dados.explicacao
      || 'Esta questão não trouxe uma explicação. Compare a sua alternativa com a correta e releia o enunciado com atenção.';
    $('pontos-explicacao').textContent = dados.textoPontos || '';
    $('pontos-explicacao').hidden = !dados.textoPontos;

    barra.style.transform = 'scaleX(1)';
    segundos.textContent = String(Math.ceil(TEMPO_EXPLICACAO_MS / 1000));
    progresso.setAttribute('aria-valuenow', String(TEMPO_EXPLICACAO_MS / 1000));

    const quiz = $('janela-quiz');
    const quizEstavaInerte = quiz.inert;
    quiz.inert = true; // a questão fica visível ao fundo, mas sem interação
    explicacaoAberta = true;
    janela.hidden = false;

    let quadro = null;
    let tempoFim = null;
    const limpar = () => {
      if (quadro) cancelAnimationFrame(quadro);
      if (tempoFim) clearTimeout(tempoFim);
      quadro = null; tempoFim = null;
      explicacaoAberta = false;
      janela.hidden = true;
      quiz.inert = quizEstavaInerte;
    };

    try {
      // A contagem só começa com o painel pintado e com a animação de entrada terminada.
      await depoisDePintar(sinal);
      if (!menosMovimento()) await esperar(260, sinal);
      cartao.focus({ preventScroll: true });
      verificar(sinal);
    } catch (erro) {
      limpar();
      throw erro;
    }

    return new Promise((resolver, rejeitar) => {
      const inicio = performance.now();
      let ultimoSegundo = null;
      // A barra e o texto são calculados a partir do mesmo relógio do temporizador.
      const pintar = (agora) => {
        const restante = Math.max(0, TEMPO_EXPLICACAO_MS - (agora - inicio));
        barra.style.transform = `scaleX(${(restante / TEMPO_EXPLICACAO_MS).toFixed(4)})`;
        const s = Math.ceil(restante / 1000);
        if (s !== ultimoSegundo) {
          ultimoSegundo = s;
          segundos.textContent = String(s);
          progresso.setAttribute('aria-valuenow', (restante / 1000).toFixed(1));
        }
        if (restante > 0) quadro = requestAnimationFrame(pintar);
      };
      quadro = requestAnimationFrame(pintar);
      const aoAbortar = () => { limpar(); rejeitar(new FluxoCancelado()); };
      sinal && sinal.addEventListener('abort', aoAbortar, { once: true });
      tempoFim = setTimeout(() => {
        sinal && sinal.removeEventListener('abort', aoAbortar);
        barra.style.transform = 'scaleX(0)';
        limpar();
        resolver();
      }, TEMPO_EXPLICACAO_MS);
    });
  }

  /* ---------- Avanço no caminho ---------- */
  const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
  const bezier = (a, c, b, t) => ({
    x: (1 - t) * (1 - t) * a.x + 2 * (1 - t) * t * c.x + t * t * b.x,
    y: (1 - t) * (1 - t) * a.y + 2 * (1 - t) * t * c.y + t * t * b.y,
  });

  // Anima o trecho `segmento` (da bolinha `segmento` até a seguinte):
  // os pedaços da trilha mudam de cor em sequência, um marcador percorre a curva
  // e a área rola junto quando a próxima bolinha está fora da tela.
  function animarTrecho({ area, trilha, de, controle, ate, segmento, duracao = 950 }, sinal) {
    const pedacos = [...trilha.querySelectorAll(`.camada-trilha:not(.camada-trilha-sombra) .trecho-trilha[data-segmento="${segmento}"]`)];
    const rolagemInicial = { x: area.scrollLeft, y: area.scrollTop };
    const margem = 120;
    const alvo = {
      x: Math.min(Math.max(0, ate.x - area.clientWidth / 2), Math.max(0, area.scrollWidth - area.clientWidth)),
      y: Math.min(Math.max(0, ate.y - area.clientHeight / 2), Math.max(0, area.scrollHeight - area.clientHeight)),
    };
    const visivelX = ate.x - margem >= area.scrollLeft && ate.x + margem <= area.scrollLeft + area.clientWidth;
    const visivelY = ate.y - margem >= area.scrollTop && ate.y + margem <= area.scrollTop + area.clientHeight;
    const rolar = { x: !visivelX, y: !visivelY };

    if (menosMovimento()) {
      pedacos.forEach((p) => p.classList.add('feito'));
      if (rolar.x) area.scrollLeft = alvo.x;
      if (rolar.y) area.scrollTop = alvo.y;
      return esperar(250, sinal);
    }

    const marcador = document.createElement('span');
    marcador.className = 'marcador-avanco';
    marcador.setAttribute('aria-hidden', 'true');
    trilha.appendChild(marcador);

    return new Promise((resolver, rejeitar) => {
      let quadro = null;
      const inicio = performance.now();
      const limpar = () => { if (quadro) cancelAnimationFrame(quadro); marcador.remove(); };
      const aoAbortar = () => { limpar(); rejeitar(new FluxoCancelado()); };
      sinal && sinal.addEventListener('abort', aoAbortar, { once: true });
      const passo = (agora) => {
        const t = Math.min(1, (agora - inicio) / duracao);
        const k = ease(t);
        const ponto = bezier(de, controle, ate, k);
        marcador.style.left = `${ponto.x}px`;
        marcador.style.top = `${ponto.y}px`;
        const pintados = Math.round(k * pedacos.length);
        for (let i = 0; i < pintados; i += 1) pedacos[i].classList.add('feito');
        if (rolar.x) area.scrollLeft = rolagemInicial.x + (alvo.x - rolagemInicial.x) * k;
        if (rolar.y) area.scrollTop = rolagemInicial.y + (alvo.y - rolagemInicial.y) * k;
        if (t < 1) { quadro = requestAnimationFrame(passo); return; }
        sinal && sinal.removeEventListener('abort', aoAbortar);
        marcador.classList.add('chegou');
        setTimeout(() => marcador.remove(), 400);
        resolver();
      };
      quadro = requestAnimationFrame(passo);
    });
  }

  // Fecha uma janela com uma transição curta (ou na hora, com movimento reduzido).
  async function fecharComTransicao(janela, sinal) {
    if (janela.hidden) return;
    if (menosMovimento()) { janela.hidden = true; return; }
    janela.classList.add('fechando');
    try {
      await esperar(240, sinal);
    } finally {
      janela.classList.remove('fechando');
    }
    janela.hidden = true;
  }

  window.FluxoAtividade = {
    TEMPO_EXPLICACAO_MS,
    FluxoCancelado,
    foiCancelado,
    esperar,
    verificar,
    menosMovimento,
    carregamento,
    gerarComCarregamento,
    mostrarExplicacaoErro,
    animarTrecho,
    fecharComTransicao,
  };
})();
