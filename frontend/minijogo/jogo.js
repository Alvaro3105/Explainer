// Minijogo "Chuva de asteroides": o mascote flutua no espaço e destrói asteroides.
//
// Controles: setas ou WASD movem, o mouse mira, clique ou Espaço atira,
// P pausa e Esc fecha. No celular, tocar e arrastar move e atira na direção do dedo.
//
// O mundo tem 320x180 pixels de arte e é desenhado num canvas de 960x540
// (cada pixel da arte vira 3x3), com suavização desligada para manter o pixel art.
(function () {
  const app = (window.ExplAIner = window.ExplAIner || {});

  const LARGURA = 320;
  const ALTURA = 180;
  const ESCALA = 3;
  const CHAVE_RECORDE = 'explainer-minijogo-recorde';

  const CONFIG = {
    aceleracao: 260,
    velocidadeMaxima: 120,
    freio: 1.8,              // quanto a velocidade cai por segundo sem apertar nada
    intervaloTiro: 0.17,
    velocidadeTiro: 280,
    vidaTiro: 0.8,
    tirosNaTela: 10,
    vidas: 3,
    invencivel: 2.2,         // segundos piscando depois de levar dano
    raioJogador: 8,
    asteroides: {
      3: { raio: 14, pontos: 20, velocidade: [12, 26] },
      2: { raio: 8, pontos: 50, velocidade: [20, 38] },
      1: { raio: 5, pontos: 100, velocidade: [28, 52] },
    },
  };

  const sorteio = (min, max) => min + Math.random() * (max - min);
  const distancia = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
  const movimentoReduzido = () => window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Distância "dando a volta" na tela, já que tudo atravessa as bordas.
  function distanciaNaTela(a, b) {
    let dx = Math.abs(a.x - b.x);
    let dy = Math.abs(a.y - b.y);
    dx = Math.min(dx, LARGURA - dx);
    dy = Math.min(dy, ALTURA - dy);
    return Math.hypot(dx, dy);
  }

  function darVolta(objeto, margem = 0) {
    if (objeto.x < -margem) objeto.x += LARGURA + margem * 2;
    else if (objeto.x > LARGURA + margem) objeto.x -= LARGURA + margem * 2;
    if (objeto.y < -margem) objeto.y += ALTURA + margem * 2;
    else if (objeto.y > ALTURA + margem) objeto.y -= ALTURA + margem * 2;
  }

  function lerRecorde() {
    try { return Number(window.localStorage.getItem(CHAVE_RECORDE)) || 0; } catch (_) { return 0; }
  }
  function salvarRecorde(valor) {
    try { window.localStorage.setItem(CHAVE_RECORDE, String(valor)); } catch (_) { /* sem armazenamento: o recorde vale só nesta visita */ }
  }

  // ---------- Asteroides em pixel art ----------
  // Cada asteroide é um polígono irregular pintado pixel a pixel, com luz vinda do alto à esquerda e crateras.
  function desenharAsteroide(raio) {
    const lado = Math.ceil(raio * 2) + 4;
    const centro = lado / 2;
    const vertices = [];
    const quantidade = 9 + Math.floor(Math.random() * 4);
    for (let i = 0; i < quantidade; i += 1) {
      const angulo = (i / quantidade) * Math.PI * 2;
      const r = raio * sorteio(0.72, 1.02);
      vertices.push([centro + Math.cos(angulo) * r, centro + Math.sin(angulo) * r]);
    }
    const dentro = (x, y) => {
      let resultado = false;
      for (let i = 0, j = vertices.length - 1; i < vertices.length; j = i, i += 1) {
        const [xi, yi] = vertices[i];
        const [xj, yj] = vertices[j];
        if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) resultado = !resultado;
      }
      return resultado;
    };
    const crateras = Array.from({ length: Math.max(1, Math.round(raio / 4)) }, () => {
      const angulo = Math.random() * Math.PI * 2;
      const d = Math.random() * raio * 0.55;
      return { x: centro + Math.cos(angulo) * d, y: centro + Math.sin(angulo) * d, r: sorteio(1.2, Math.max(1.6, raio / 4.5)) };
    });

    const tela = document.createElement('canvas');
    tela.width = lado;
    tela.height = lado;
    const ctx = tela.getContext('2d');
    const mapa = [];
    for (let y = 0; y < lado; y += 1) {
      mapa.push([]);
      for (let x = 0; x < lado; x += 1) mapa[y].push(dentro(x + 0.5, y + 0.5));
    }
    const ocupado = (x, y) => y >= 0 && y < lado && x >= 0 && x < lado && mapa[y][x];
    for (let y = 0; y < lado; y += 1) {
      for (let x = 0; x < lado; x += 1) {
        if (!mapa[y][x]) continue;
        const borda = !ocupado(x - 1, y) || !ocupado(x + 1, y) || !ocupado(x, y - 1) || !ocupado(x, y + 1);
        let cor;
        if (borda) cor = '#0d0d10';
        else {
          const luz = ((centro - x) + (centro - y)) / (raio * 1.4);
          cor = luz > 0.35 ? '#a49aa8' : luz < -0.35 ? '#564e5c' : '#7b7181';
          crateras.forEach((cratera) => {
            const d = Math.hypot(x + 0.5 - cratera.x, y + 0.5 - cratera.y);
            if (d < cratera.r) cor = '#4a4350';
            else if (d < cratera.r + 1 && x + 0.5 > cratera.x && y + 0.5 > cratera.y) cor = '#b3aab7';
          });
        }
        ctx.fillStyle = cor;
        ctx.fillRect(x, y, 1, 1);
      }
    }
    return tela;
  }

  function criarAsteroide(tamanho, x, y, nivel) {
    const tipo = CONFIG.asteroides[tamanho];
    const angulo = Math.random() * Math.PI * 2;
    const rapidez = sorteio(...tipo.velocidade) * (1 + (nivel - 1) * 0.08);
    return {
      tamanho, x, y,
      raio: tipo.raio,
      vx: Math.cos(angulo) * rapidez,
      vy: Math.sin(angulo) * rapidez,
      angulo: Math.random() * Math.PI * 2,
      giro: sorteio(-1.2, 1.2),
      imagem: desenharAsteroide(tipo.raio),
    };
  }

  // ---------- Janela do jogo ----------
  function criarJanela() {
    const janela = document.createElement('div');
    janela.className = 'janela-minijogo';
    janela.id = 'janela-minijogo';
    janela.hidden = true;
    janela.innerHTML = `
      <section class="cartao-minijogo" role="dialog" aria-modal="true" aria-labelledby="titulo-minijogo" aria-describedby="ajuda-minijogo">
        <header class="topo-minijogo">
          <div class="nome-minijogo"><span class="chamada-minijogo">MINIJOGO</span><h2 id="titulo-minijogo">Chuva de asteroides</h2></div>
          <dl class="placar-minijogo" aria-live="polite">
            <div><dt>Pontos</dt><dd data-placar="pontos">0</dd></div>
            <div><dt>Nível</dt><dd data-placar="nivel">1</dd></div>
            <div><dt>Vidas</dt><dd data-placar="vidas" class="vidas-minijogo"></dd></div>
            <div><dt>Recorde</dt><dd data-placar="recorde">0</dd></div>
          </dl>
          <button class="botao-icone fechar-minijogo" type="button" data-acao="fechar" aria-label="Fechar minijogo" title="Fechar (Esc)"><i class="fa-solid fa-xmark" aria-hidden="true"></i></button>
        </header>
        <div class="palco-minijogo">
          <canvas width="${LARGURA * ESCALA}" height="${ALTURA * ESCALA}" tabindex="0" role="img" aria-label="Área do jogo: o astronauta flutua entre asteroides"></canvas>
          <div class="aviso-minijogo" data-aviso>
            <h3 data-aviso-titulo>Chuva de asteroides</h3>
            <p data-aviso-texto>Destrua os asteroides antes que eles acertem o astronauta.</p>
            <button class="botao botao-principal" type="button" data-acao="jogar">Jogar</button>
          </div>
        </div>
        <p class="ajuda-minijogo" id="ajuda-minijogo">
          <span><kbd>←</kbd><kbd>↑</kbd><kbd>↓</kbd><kbd>→</kbd> ou <kbd>W</kbd><kbd>A</kbd><kbd>S</kbd><kbd>D</kbd> mover</span>
          <span><i class="fa-solid fa-computer-mouse" aria-hidden="true"></i> mirar</span>
          <span>clique ou <kbd>Espaço</kbd> atirar</span>
          <span><kbd>P</kbd> pausar</span>
          <span><kbd>Esc</kbd> sair</span>
        </p>
      </section>`;
    document.body.appendChild(janela);
    return janela;
  }

  // ---------- Jogo ----------
  function criarJogo() {
    const janela = criarJanela();
    const tela = janela.querySelector('canvas');
    const ctx = tela.getContext('2d');
    const aviso = janela.querySelector('[data-aviso]');
    const placar = Object.fromEntries([...janela.querySelectorAll('[data-placar]')].map((el) => [el.dataset.placar, el]));
    const botaoJogar = janela.querySelector('[data-acao="jogar"]');

    const teclas = new Set();
    const ponteiro = { x: LARGURA / 2 + 50, y: ALTURA / 2, apertado: false, toque: false, mexeu: false };
    const estrelas = Array.from({ length: 65 }, () => ({
      x: Math.random() * LARGURA, y: Math.random() * ALTURA,
      brilho: Math.random(), camada: Math.random() < 0.7 ? 0.15 : 0.4,
    }));

    let jogo = null;
    let situacao = 'pronto'; // pronto, jogando, pausado, fim
    let quadro = 0;
    let ultimoTempo = 0;
    let quemAbriu = null;
    let recorde = lerRecorde();

    function novaPartida() {
      const astronauta = app.minijogoAstronauta.criarAstronauta();
      astronauta.x = LARGURA / 2;
      astronauta.y = ALTURA / 2 + 10;
      jogo = {
        astronauta,
        tiros: [],
        asteroides: [],
        particulas: [],
        pontos: 0,
        nivel: 0,
        vidas: CONFIG.vidas,
        invencivel: CONFIG.invencivel,
        recarga: 0,
        tremor: 0,
        proximaOnda: 0,
      };
      proximaOnda();
      atualizarPlacar();
    }

    function proximaOnda() {
      jogo.nivel += 1;
      const quantidade = Math.min(2 + jogo.nivel, 9);
      const centro = jogo.astronauta;
      for (let i = 0; i < quantidade; i += 1) {
        let x;
        let y;
        // Nasce longe do astronauta, para ninguém perder vida sem tempo de reagir.
        do {
          x = Math.random() * LARGURA;
          y = Math.random() * ALTURA;
        } while (distanciaNaTela({ x, y }, centro) < 90);
        jogo.asteroides.push(criarAsteroide(3, x, y, jogo.nivel));
      }
      atualizarPlacar();
    }

    function atualizarPlacar() {
      if (!jogo) return;
      placar.pontos.textContent = jogo.pontos.toLocaleString('pt-BR');
      placar.nivel.textContent = jogo.nivel;
      placar.recorde.textContent = recorde.toLocaleString('pt-BR');
      placar.vidas.innerHTML = '';
      placar.vidas.setAttribute('aria-label', `${jogo.vidas} ${jogo.vidas === 1 ? 'vida' : 'vidas'}`);
      for (let i = 0; i < CONFIG.vidas; i += 1) {
        const coracao = document.createElement('i');
        coracao.className = `fa-solid fa-heart${i < jogo.vidas ? '' : ' vida-perdida'}`;
        coracao.setAttribute('aria-hidden', 'true');
        placar.vidas.appendChild(coracao);
      }
    }

    function mostrarAviso(titulo, texto, rotulo) {
      aviso.querySelector('[data-aviso-titulo]').textContent = titulo;
      aviso.querySelector('[data-aviso-texto]').textContent = texto;
      botaoJogar.textContent = rotulo;
      aviso.hidden = false;
      botaoJogar.focus({ preventScroll: true });
    }

    function comecar() {
      if (situacao !== 'pausado') novaPartida();
      situacao = 'jogando';
      aviso.hidden = true;
      teclas.clear();
      ponteiro.apertado = false;
      tela.focus({ preventScroll: true });
    }

    function pausar() {
      if (situacao !== 'jogando') return;
      situacao = 'pausado';
      teclas.clear();
      ponteiro.apertado = false;
      mostrarAviso('Pausado', 'Respire fundo. Os asteroides esperam por você.', 'Continuar');
    }

    function terminar() {
      situacao = 'fim';
      const novoRecorde = jogo.pontos > recorde;
      if (novoRecorde) {
        recorde = jogo.pontos;
        salvarRecorde(recorde);
      }
      atualizarPlacar();
      const pontos = jogo.pontos.toLocaleString('pt-BR');
      mostrarAviso(
        novoRecorde ? 'Novo recorde!' : 'Fim de jogo',
        `Você fez ${pontos} ${jogo.pontos === 1 ? 'ponto' : 'pontos'} e chegou ao nível ${jogo.nivel}.`,
        'Jogar de novo',
      );
    }

    // ---------- Física e regras ----------
    function explodir(x, y, quantidade, cores) {
      for (let i = 0; i < quantidade; i += 1) {
        const angulo = Math.random() * Math.PI * 2;
        const rapidez = sorteio(20, 90);
        jogo.particulas.push({
          x, y,
          vx: Math.cos(angulo) * rapidez,
          vy: Math.sin(angulo) * rapidez,
          vida: sorteio(0.3, 0.8),
          cor: cores[Math.floor(Math.random() * cores.length)],
        });
      }
    }

    function atirar() {
      if (jogo.recarga > 0 || jogo.tiros.length >= CONFIG.tirosNaTela) return;
      const cano = jogo.astronauta.cano();
      jogo.tiros.push({
        x: cano.x, y: cano.y,
        vx: Math.cos(cano.angulo) * CONFIG.velocidadeTiro + jogo.astronauta.vx * 0.3,
        vy: Math.sin(cano.angulo) * CONFIG.velocidadeTiro + jogo.astronauta.vy * 0.3,
        vida: CONFIG.vidaTiro,
      });
      jogo.astronauta.recuo = 1;
      jogo.recarga = CONFIG.intervaloTiro;
      explodir(cano.x, cano.y, 3, ['#7ff3ff', '#ffffff']);
    }

    function quebrar(indice) {
      const pedra = jogo.asteroides[indice];
      jogo.asteroides.splice(indice, 1);
      jogo.pontos += CONFIG.asteroides[pedra.tamanho].pontos;
      explodir(pedra.x, pedra.y, 6 + pedra.tamanho * 4, ['#a49aa8', '#7b7181', '#564e5c', '#ffd34d']);
      if (pedra.tamanho > 1) {
        for (let i = 0; i < 2; i += 1) jogo.asteroides.push(criarAsteroide(pedra.tamanho - 1, pedra.x, pedra.y, jogo.nivel));
      }
      atualizarPlacar();
    }

    function levarDano() {
      const centro = jogo.astronauta.centro();
      explodir(centro.x, centro.y, 24, ['#ffffff', '#e8e7ea', '#fff200', '#e8202a']);
      jogo.vidas -= 1;
      jogo.tremor = movimentoReduzido() ? 0 : 0.35;
      atualizarPlacar();
      if (jogo.vidas <= 0) {
        terminar();
        return;
      }
      Object.assign(jogo.astronauta, { x: LARGURA / 2, y: ALTURA / 2 + 10, vx: 0, vy: 0 });
      jogo.invencivel = CONFIG.invencivel;
    }

    function direcaoDoTeclado() {
      let dx = 0;
      let dy = 0;
      if (teclas.has('ArrowLeft') || teclas.has('KeyA')) dx -= 1;
      if (teclas.has('ArrowRight') || teclas.has('KeyD')) dx += 1;
      if (teclas.has('ArrowUp') || teclas.has('KeyW')) dy -= 1;
      if (teclas.has('ArrowDown') || teclas.has('KeyS')) dy += 1;
      // No toque, o astronauta vai na direção do dedo.
      if (ponteiro.toque && ponteiro.apertado) {
        const a = jogo.astronauta;
        const ddx = ponteiro.x - a.x;
        const ddy = ponteiro.y - (a.y - 8);
        if (Math.hypot(ddx, ddy) > 28) {
          dx = ddx;
          dy = ddy;
        }
      }
      const tamanho = Math.hypot(dx, dy);
      return tamanho ? { x: dx / tamanho, y: dy / tamanho } : { x: 0, y: 0 };
    }

    function atualizar(dt) {
      const a = jogo.astronauta;
      const direcao = direcaoDoTeclado();
      a.vx += direcao.x * CONFIG.aceleracao * dt;
      a.vy += direcao.y * CONFIG.aceleracao * dt;
      const freio = Math.exp(-CONFIG.freio * dt);
      a.vx *= freio;
      a.vy *= freio;
      const rapidez = Math.hypot(a.vx, a.vy);
      if (rapidez > CONFIG.velocidadeMaxima) {
        a.vx *= CONFIG.velocidadeMaxima / rapidez;
        a.vy *= CONFIG.velocidadeMaxima / rapidez;
      }
      a.x += a.vx * dt;
      a.y += a.vy * dt;
      darVolta(a, 12);

      // Sem mouse (só teclado), a mira segue a direção do movimento.
      if (!ponteiro.mexeu && rapidez > 10) {
        ponteiro.x = a.x + (a.vx / rapidez) * 80;
        ponteiro.y = a.y - 8 + (a.vy / rapidez) * 80;
      }
      a.atualizar(dt, ponteiro);

      jogo.recarga = Math.max(0, jogo.recarga - dt);
      jogo.invencivel = Math.max(0, jogo.invencivel - dt);
      jogo.tremor = Math.max(0, jogo.tremor - dt);
      if (ponteiro.apertado || teclas.has('Space')) atirar();

      jogo.tiros.forEach((tiro) => {
        tiro.x += tiro.vx * dt;
        tiro.y += tiro.vy * dt;
        tiro.vida -= dt;
        darVolta(tiro);
      });
      jogo.tiros = jogo.tiros.filter((tiro) => tiro.vida > 0);

      jogo.asteroides.forEach((pedra) => {
        pedra.x += pedra.vx * dt;
        pedra.y += pedra.vy * dt;
        pedra.angulo += pedra.giro * dt;
        darVolta(pedra, pedra.raio);
      });

      // Tiro x asteroide.
      for (let t = jogo.tiros.length - 1; t >= 0; t -= 1) {
        const tiro = jogo.tiros[t];
        const acerto = jogo.asteroides.findIndex((pedra) => distancia(tiro, pedra) < pedra.raio);
        if (acerto >= 0) {
          jogo.tiros.splice(t, 1);
          quebrar(acerto);
        }
      }

      // Asteroide x astronauta.
      if (!jogo.invencivel) {
        const centro = a.centro();
        if (jogo.asteroides.some((pedra) => distancia(centro, pedra) < pedra.raio * 0.85 + CONFIG.raioJogador)) {
          levarDano();
          if (situacao !== 'jogando') return;
        }
      }

      jogo.particulas.forEach((p) => {
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        p.vx *= 0.96;
        p.vy *= 0.96;
        p.vida -= dt;
      });
      jogo.particulas = jogo.particulas.filter((p) => p.vida > 0);

      // Onda limpa: a próxima chega depois de um respiro.
      if (!jogo.asteroides.length) {
        jogo.proximaOnda += dt;
        if (jogo.proximaOnda > 1.2) {
          jogo.proximaOnda = 0;
          proximaOnda();
        }
      }
    }

    // ---------- Desenho ----------
    function desenharFundo(tempo) {
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.fillStyle = '#0b1418';
      ctx.fillRect(0, 0, tela.width, tela.height);
      const deslocX = jogo ? jogo.astronauta.x : 0;
      const deslocY = jogo ? jogo.astronauta.y : 0;
      estrelas.forEach((estrela) => {
        const x = ((estrela.x - deslocX * estrela.camada) % LARGURA + LARGURA) % LARGURA;
        const y = ((estrela.y - deslocY * estrela.camada) % ALTURA + ALTURA) % ALTURA;
        const brilho = 0.35 + 0.65 * Math.abs(Math.sin(tempo * 0.8 + estrela.brilho * 9));
        ctx.globalAlpha = brilho * (estrela.camada > 0.3 ? 1 : 0.6);
        ctx.fillStyle = estrela.camada > 0.3 ? '#f6f9fc' : '#6ac5cb';
        ctx.fillRect(Math.floor(x) * ESCALA, Math.floor(y) * ESCALA, ESCALA, ESCALA);
      });
      ctx.globalAlpha = 1;
    }

    function desenhar(tempo) {
      desenharFundo(tempo);
      if (!jogo) return;
      const tremor = jogo.tremor > 0 ? jogo.tremor * 10 : 0;
      ctx.save();
      if (tremor) ctx.translate(sorteio(-tremor, tremor), sorteio(-tremor, tremor));

      jogo.asteroides.forEach((pedra) => {
        ctx.save();
        ctx.scale(ESCALA, ESCALA);
        ctx.translate(Math.round(pedra.x), Math.round(pedra.y));
        ctx.rotate(pedra.angulo);
        ctx.drawImage(pedra.imagem, -pedra.imagem.width / 2, -pedra.imagem.height / 2);
        ctx.restore();
      });

      jogo.tiros.forEach((tiro) => {
        const x = Math.round(tiro.x) * ESCALA;
        const y = Math.round(tiro.y) * ESCALA;
        const rastroX = Math.round(tiro.x - tiro.vx * 0.012) * ESCALA;
        const rastroY = Math.round(tiro.y - tiro.vy * 0.012) * ESCALA;
        ctx.fillStyle = '#33b4bd';
        ctx.fillRect(rastroX, rastroY, ESCALA, ESCALA);
        ctx.fillStyle = '#7ff3ff';
        ctx.fillRect(x - ESCALA / 2, y - ESCALA / 2, ESCALA * 2, ESCALA * 2);
      });

      const a = jogo.astronauta;
      const visivel = situacao === 'fim' ? false : !jogo.invencivel || Math.floor(tempo * 12) % 2 === 0;
      if (visivel) {
        // O astronauta é desenhado de novo do outro lado quando está atravessando a borda.
        const copias = [[0, 0]];
        if (a.x < 16) copias.push([LARGURA, 0]);
        if (a.x > LARGURA - 16) copias.push([-LARGURA, 0]);
        if (a.y < 24) copias.push([0, ALTURA]);
        if (a.y > ALTURA - 16) copias.push([0, -ALTURA]);
        copias.forEach(([cx, cy]) => {
          const x = a.x;
          const y = a.y;
          a.x += cx;
          a.y += cy;
          a.desenhar(ctx, ESCALA, jogo.invencivel > CONFIG.invencivel - 0.15);
          a.x = x;
          a.y = y;
        });
      }

      jogo.particulas.forEach((p) => {
        ctx.globalAlpha = Math.min(1, p.vida * 2);
        ctx.fillStyle = p.cor;
        ctx.fillRect(Math.round(p.x) * ESCALA, Math.round(p.y) * ESCALA, ESCALA, ESCALA);
      });
      ctx.globalAlpha = 1;

      // Mira do mouse.
      if (situacao === 'jogando' && ponteiro.mexeu && !ponteiro.toque) {
        const x = Math.round(ponteiro.x) * ESCALA;
        const y = Math.round(ponteiro.y) * ESCALA;
        ctx.fillStyle = '#d1dc5a';
        [[-6, 0], [4, 0], [0, -6], [0, 4]].forEach(([dx, dy]) => {
          ctx.fillRect(x + dx, y + dy, dx ? 4 : 2, dy ? 4 : 2);
        });
      }
      ctx.restore();
    }

    function passo(agora) {
      if (janela.hidden) return;
      const tempo = agora / 1000;
      const dt = Math.min(0.05, ultimoTempo ? tempo - ultimoTempo : 0);
      ultimoTempo = tempo;
      if (situacao === 'jogando') atualizar(dt);
      else if (jogo && situacao === 'fim') {
        // As peças da explosão continuam se espalhando na tela de fim de jogo.
        jogo.particulas.forEach((p) => { p.x += p.vx * dt; p.y += p.vy * dt; p.vida -= dt; });
        jogo.particulas = jogo.particulas.filter((p) => p.vida > 0);
      }
      desenhar(tempo);
      quadro = window.requestAnimationFrame(passo);
    }

    // ---------- Entrada ----------
    function pontoNoMundo(evento) {
      const caixa = tela.getBoundingClientRect();
      return {
        x: ((evento.clientX - caixa.left) / caixa.width) * LARGURA,
        y: ((evento.clientY - caixa.top) / caixa.height) * ALTURA,
      };
    }

    tela.addEventListener('pointermove', (evento) => {
      Object.assign(ponteiro, pontoNoMundo(evento), { mexeu: true, toque: evento.pointerType === 'touch' });
    });
    tela.addEventListener('pointerdown', (evento) => {
      if (evento.button !== 0 || situacao !== 'jogando') return;
      evento.preventDefault();
      tela.setPointerCapture?.(evento.pointerId);
      Object.assign(ponteiro, pontoNoMundo(evento), { mexeu: true, apertado: true, toque: evento.pointerType === 'touch' });
    });
    const soltar = () => { ponteiro.apertado = false; };
    tela.addEventListener('pointerup', soltar);
    tela.addEventListener('pointercancel', soltar);
    tela.addEventListener('contextmenu', (evento) => evento.preventDefault());

    const TECLAS_DO_JOGO = new Set(['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'KeyW', 'KeyA', 'KeyS', 'KeyD', 'Space']);
    function teclaApertada(evento) {
      if (janela.hidden) return;
      if (evento.key === 'Escape') {
        evento.preventDefault();
        fechar();
        return;
      }
      if (evento.key === 'Tab') {
        prenderFoco(evento);
        return;
      }
      if (evento.code === 'KeyP') {
        if (situacao === 'jogando') pausar();
        else if (situacao === 'pausado') comecar();
        return;
      }
      if (situacao === 'jogando' && TECLAS_DO_JOGO.has(evento.code)) {
        evento.preventDefault();
        teclas.add(evento.code);
      }
    }
    function teclaSolta(evento) {
      teclas.delete(evento.code);
    }

    // O foco fica dentro da janela enquanto ela estiver aberta.
    function prenderFoco(evento) {
      const focaveis = [...janela.querySelectorAll('button, canvas[tabindex]')].filter((el) => !el.closest('[hidden]'));
      if (!focaveis.length) return;
      const primeiro = focaveis[0];
      const ultimo = focaveis[focaveis.length - 1];
      if (evento.shiftKey && document.activeElement === primeiro) {
        evento.preventDefault();
        ultimo.focus();
      } else if (!evento.shiftKey && document.activeElement === ultimo) {
        evento.preventDefault();
        primeiro.focus();
      }
    }

    function aoSairDaAba() {
      if (document.hidden) pausar();
    }

    botaoJogar.addEventListener('click', comecar);
    // Só o X e o Esc fecham: num jogo de mira, clicar um pouco fora da área não pode encerrar a partida.
    janela.querySelector('[data-acao="fechar"]').addEventListener('click', fechar);

    // ---------- Abrir e fechar ----------
    function abrir() {
      if (!janela.hidden) return;
      quemAbriu = document.activeElement;
      janela.hidden = false;
      document.body.classList.add('minijogo-aberto');
      ctx.imageSmoothingEnabled = false;
      situacao = 'pronto';
      jogo = null;
      recorde = lerRecorde();
      placar.pontos.textContent = '0';
      placar.nivel.textContent = '1';
      placar.recorde.textContent = recorde.toLocaleString('pt-BR');
      placar.vidas.innerHTML = '<i class="fa-solid fa-heart" aria-hidden="true"></i>'.repeat(CONFIG.vidas);
      placar.vidas.setAttribute('aria-label', `${CONFIG.vidas} vidas`);
      mostrarAviso('Chuva de asteroides', 'Destrua os asteroides antes que eles acertem o astronauta.', 'Jogar');
      // Mostra o astronauta parado no centro enquanto espera o "Jogar".
      novaPartida();
      jogo.asteroides = [];
      jogo.invencivel = 0;
      atualizarPlacar();
      window.addEventListener('keydown', teclaApertada);
      window.addEventListener('keyup', teclaSolta);
      window.addEventListener('blur', pausar);
      document.addEventListener('visibilitychange', aoSairDaAba);
      ultimoTempo = 0;
      quadro = window.requestAnimationFrame(passo);
    }

    function fechar() {
      if (janela.hidden) return;
      janela.hidden = true;
      document.body.classList.remove('minijogo-aberto');
      window.cancelAnimationFrame(quadro);
      window.removeEventListener('keydown', teclaApertada);
      window.removeEventListener('keyup', teclaSolta);
      window.removeEventListener('blur', pausar);
      document.removeEventListener('visibilitychange', aoSairDaAba);
      teclas.clear();
      ponteiro.apertado = false;
      ponteiro.mexeu = false;
      situacao = 'pronto';
      jogo = null;
      if (quemAbriu && typeof quemAbriu.focus === 'function') quemAbriu.focus({ preventScroll: true });
    }

    // Leitura do estado, usada nos testes automáticos (não altera nada).
    function estado() {
      return {
        aberto: !janela.hidden,
        situacao,
        pontos: jogo ? jogo.pontos : 0,
        nivel: jogo ? jogo.nivel : 0,
        vidas: jogo ? jogo.vidas : 0,
        tiros: jogo ? jogo.tiros.length : 0,
        astronauta: jogo ? { x: jogo.astronauta.x, y: jogo.astronauta.y, lado: jogo.astronauta.lado, partes: jogo.astronauta.partes.length } : null,
        asteroides: jogo ? jogo.asteroides.map((p) => ({ x: p.x, y: p.y, raio: p.raio, tamanho: p.tamanho })) : [],
      };
    }

    return { abrir, fechar, estado };
  }

  let instancia = null;
  app.minijogo = {
    abrir() {
      if (!instancia) instancia = criarJogo();
      instancia.abrir();
    },
    fechar() { instancia?.fechar(); },
    estado() { return instancia ? instancia.estado() : { aberto: false }; },
  };
})();
