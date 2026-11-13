// Esqueleto do mascote: 10 partes articuladas e a arma presa na mão da frente.
//
//                  capacete
//                     |
//   braço trás --- tronco --- braço frente
//        |          /   \          |
//   antebraço   coxa     coxa   antebraço --- arma
//    trás       trás    frente    frente
//                |        |
//             canela    canela
//
// Cada osso guarda a peça (sprites.js), o pai, o encaixe no pai e o ângulo.
// A pose é recalculada a cada quadro a partir da mira, do movimento e do recuo do tiro.
(function () {
  const app = (window.ExplAIner = window.ExplAIner || {});

  // Ordem de desenho: o que fica atrás do tronco vem primeiro.
  // A arma vem antes do antebraço da frente para a luva cobrir o cabo.
  const OSSOS = [
    { nome: 'bracoTras', peca: 'braco', pai: 'tronco', encaixe: 'ombroTras', atras: true },
    { nome: 'antebracoTras', peca: 'antebraco', pai: 'bracoTras', encaixe: 'cotovelo', atras: true },
    { nome: 'coxaTras', peca: 'coxa', pai: 'tronco', encaixe: 'quadrilTras', atras: true },
    { nome: 'canelaTras', peca: 'canela', pai: 'coxaTras', encaixe: 'joelho', atras: true },
    { nome: 'tronco', peca: 'tronco', pai: null },
    { nome: 'capacete', peca: 'capacete', pai: 'tronco', encaixe: 'pescoco' },
    { nome: 'coxaFrente', peca: 'coxa', pai: 'tronco', encaixe: 'quadrilFrente' },
    { nome: 'canelaFrente', peca: 'canela', pai: 'coxaFrente', encaixe: 'joelho' },
    { nome: 'bracoFrente', peca: 'braco', pai: 'tronco', encaixe: 'ombroFrente' },
    { nome: 'arma', peca: 'arma', pai: 'antebracoFrente', encaixe: 'mao', acessorio: true },
    { nome: 'antebracoFrente', peca: 'antebraco', pai: 'bracoFrente', encaixe: 'cotovelo' },
  ];
  // Os pais precisam ser calculados antes dos filhos (a ordem de desenho é outra).
  const ORDEM_CALCULO = ['tronco', 'capacete', 'bracoTras', 'antebracoTras', 'coxaTras', 'canelaTras',
    'coxaFrente', 'canelaFrente', 'bracoFrente', 'antebracoFrente', 'arma'];

  const RAD = 180 / Math.PI;
  const limitar = (valor, minimo, maximo) => Math.max(minimo, Math.min(maximo, valor));
  const misturar = (a, b, t) => a + (b - a) * t;

  function criarAstronauta() {
    const pecas = app.minijogoSprites.sprites();
    const porNome = Object.fromEntries(OSSOS.map((osso) => [osso.nome, osso]));
    const angulos = Object.fromEntries(OSSOS.map((osso) => [osso.nome, 0]));
    const matrizes = {};

    const boneco = {
      x: 200, y: 112, vx: 0, vy: 0,
      lado: 1,          // 1 olhando para a direita, -1 para a esquerda
      mira: 0,          // ângulo da mira em relação ao tronco
      inclinacao: 0,
      fase: 0,          // passo das pernas
      andando: 0,       // 0 parado, 1 andando (suavizado)
      recuo: 0,         // 1 logo depois do tiro, volta a 0
      tempo: 0,
      partes: OSSOS.filter((osso) => !osso.acessorio).map((osso) => osso.nome),

      // alvo: ponto do mundo para onde a arma aponta.
      atualizar(dt, alvo) {
        this.tempo += dt;
        const dx = alvo.x - this.x;
        const dy = alvo.y - (this.y - 8);
        if (Math.abs(dx) > 2) this.lado = dx >= 0 ? 1 : -1;
        const miraNoMundo = Math.atan2(dy, Math.abs(dx) < 0.001 ? 0.001 * this.lado : dx * this.lado);

        const rapidez = Math.hypot(this.vx, this.vy);
        this.andando = misturar(this.andando, limitar(rapidez / 70, 0, 1), Math.min(1, dt * 6));
        this.fase += dt * (4 + rapidez * 0.06) * (0.3 + this.andando);
        this.recuo = Math.max(0, this.recuo - dt * 7);

        // O corpo inclina na direção do movimento e acompanha um pouco a mira.
        const alvoInclinacao = limitar(this.vx * this.lado * 0.0025, -0.25, 0.25) + miraNoMundo * 0.12 - this.recuo * 0.06;
        this.inclinacao = misturar(this.inclinacao, alvoInclinacao, Math.min(1, dt * 8));
        this.mira = miraNoMundo - this.inclinacao;
        this.posar();
      },

      posar() {
        const a = angulos;
        const mira = this.mira;
        const flutuar = Math.sin(this.tempo * 2.2);
        const passo = Math.sin(this.fase);
        const passoOposto = Math.sin(this.fase + Math.PI);
        const andando = this.andando;

        a.tronco = this.inclinacao;
        a.capacete = limitar(mira * 0.45, -0.4, 0.35) + flutuar * 0.03;

        // Braço da frente: o antebraço aponta para a mira, o cotovelo fica um pouco dobrado.
        a.bracoFrente = mira - Math.PI / 2 + 0.38 - this.recuo * 0.35;
        a.antebracoFrente = -0.38 + this.recuo * 0.2;
        a.arma = Math.PI / 2 + this.recuo * 0.15;
        // Braço de trás ajuda a segurar e balança um pouco ao andar.
        a.bracoTras = mira - Math.PI / 2 + 0.95 + passoOposto * 0.25 * andando;
        a.antebracoTras = -0.75;

        // Pernas: flutuando no espaço ficam soltas; andando, fazem o ciclo do passo.
        const parado = { coxaFrente: -0.28 + flutuar * 0.06, canelaFrente: 0.35, coxaTras: 0.22 - flutuar * 0.06, canelaTras: 0.5 };
        const passada = {
          coxaFrente: -passo * 0.6,
          canelaFrente: 0.1 + Math.max(0, passo) * 0.9,
          coxaTras: -passoOposto * 0.6,
          canelaTras: 0.1 + Math.max(0, passoOposto) * 0.9,
        };
        Object.keys(parado).forEach((nome) => { a[nome] = misturar(parado[nome], passada[nome], andando); });
      },

      // Monta as matrizes de cada osso no espaço do mundo.
      calcularMatrizes() {
        const base = new DOMMatrix()
          .translate(Math.round(this.x), Math.round(this.y + Math.sin(this.tempo * 2.2) * 1.2))
          .scale(this.lado, 1);
        ORDEM_CALCULO.forEach((nome) => {
          const osso = porNome[nome];
          if (!osso.pai) {
            matrizes[nome] = base.rotate(angulos[nome] * RAD);
            return;
          }
          const pai = porNome[osso.pai];
          const pecaPai = pecas[pai.peca];
          const [ex, ey] = pecaPai.encaixes[osso.encaixe];
          matrizes[nome] = matrizes[osso.pai]
            .translate(ex - pecaPai.pivo[0], ey - pecaPai.pivo[1])
            .rotate(angulos[nome] * RAD);
        });
        return matrizes;
      },

      desenhar(ctx, escala, piscando = false) {
        this.calcularMatrizes();
        // Parte da transformação atual do canvas (assim o tremor da tela também vale para o boneco).
        const original = ctx.getTransform();
        const tela = original.scale(escala, escala);
        OSSOS.forEach((osso) => {
          const peca = pecas[osso.peca];
          ctx.setTransform(tela.multiply(matrizes[osso.nome]));
          // As peças de trás usam a versão mais escura, para dar profundidade.
          const imagem = piscando ? peca.imagemClara : (osso.atras ? peca.imagemEscura : peca.imagem);
          ctx.drawImage(imagem, -peca.pivo[0], -peca.pivo[1]);
        });
        ctx.setTransform(original);
      },

      // Ponta do cano no mundo e a direção para onde a arma aponta.
      cano() {
        this.calcularMatrizes();
        const arma = pecas.arma;
        const [cx, cy] = arma.encaixes.cano;
        const m = matrizes.arma;
        const ponta = m.transformPoint(new DOMPoint(cx - arma.pivo[0], cy - arma.pivo[1]));
        const adiante = m.transformPoint(new DOMPoint(cx - arma.pivo[0] + 1, cy - arma.pivo[1]));
        return { x: ponta.x, y: ponta.y, angulo: Math.atan2(adiante.y - ponta.y, adiante.x - ponta.x) };
      },

      // Centro do tronco, usado na colisão com os asteroides.
      centro() {
        this.calcularMatrizes();
        const p = matrizes.tronco.transformPoint(new DOMPoint(0, -6));
        return { x: p.x, y: p.y };
      },
    };
    boneco.posar();
    return boneco;
  }

  app.minijogoAstronauta = { criarAstronauta, OSSOS };
})();
