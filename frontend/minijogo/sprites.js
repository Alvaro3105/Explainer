// Pixel art do minijogo: o mascote do ExplAIner dividido em 10 partes
// (capacete, tronco, 2 braços, 2 antebraços, 2 coxas e 2 canelas) e a arma.
//
// Cada parte é desenhada virada para a direita, "pendurada" a partir do ponto
// de articulação (pivô). Assim o esqueleto em astronauta.js só precisa girar
// cada peça em volta do próprio pivô.
//
// Letras da grade: "." é transparente; as outras estão em PALETA.
(function () {
  const app = (window.ExplAIner = window.ExplAIner || {});

  const PALETA = {
    k: '#0d0d10', // contorno
    w: '#e8e7ea', // traje
    s: '#cfcad2', // sombra do traje
    g: '#c2bdc6', // luvas, botas e painéis
    d: '#a29ca7', // cinza escuro
    y: '#fff200', // viseira
    H: '#ffffff', // brilho da viseira
    b: '#2ab8f0', // bandeira (azul)
    r: '#e8202a', // bandeira (vermelho)
    m: '#2f3542', // arma: corpo
    n: '#6b7590', // arma: brilho
    c: '#7ff3ff', // arma: cano aceso
  };

  // pivo: onde a peça gira. encaixes: pontos (na grade da peça) onde outras peças se prendem.
  const PARTES = {
    capacete: {
      pivo: [7, 12],
      grade: [
        '....kkkkkkk...',
        '...kwwwwwwwk..',
        '..kwkkkkkkkwk.',
        '.kwkyyyyyHHkwk',
        '.kwkyyyyyyHkgk',
        'kwwkyyyyyyHkwk',
        'kwwkyyyyyHHkwk',
        'kwwkyyyyHHkkwk',
        '.kwwkkkkkkkwwk',
        '.kwwwkkkkkwwk.',
        '..kwwwwwwwwk..',
        '...kssssssk...',
        '...kkkkkkkk...',
      ],
    },
    tronco: {
      pivo: [9, 12],
      encaixes: { pescoco: [9, 1], ombroFrente: [12, 3], ombroTras: [6, 3], quadrilFrente: [11, 12], quadrilTras: [7, 12] },
      grade: [
        '.....kkkkkkk....',
        'kkkkkwwwwwwwkk..',
        'kddkwwwwwwwwwwk.',
        'kddkwwwwwwwwbrk.',
        'kddkwwwwwwwwrwk.',
        'kddkwwkkkkkkwwk.',
        'kddkwwkggggkwwk.',
        'kddkwwwkkkkwwwk.',
        'kddkswwwwwwwwsk.',
        'kddksskwwwwkssk.',
        'kkkkswkwwwwkwsk.',
        '....kwwwwwwwwk..',
        '....kggggggggk..',
        '....kkkkkkkkkk..',
      ],
    },
    braco: {
      pivo: [2, 1],
      encaixes: { cotovelo: [2, 6] },
      grade: [
        'kkkkk',
        'kwwsk',
        'kwwsk',
        'kwwsk',
        'kwwsk',
        'kwwsk',
        'kkkkk',
      ],
    },
    antebraco: {
      pivo: [2, 1],
      encaixes: { mao: [3, 6] },
      grade: [
        'kkkkk.',
        'kwwsk.',
        'kwwsk.',
        'kwwsk.',
        'kkkkkk',
        'kgggdk',
        'kgggdk',
        'kgggdk',
        'kkkkkk',
      ],
    },
    coxa: {
      pivo: [3, 1],
      encaixes: { joelho: [3, 6] },
      grade: [
        'kkkkkk',
        'kwwwsk',
        'kwwwsk',
        'kwwwsk',
        'kwwwsk',
        'kwwwsk',
        'kkkkkk',
      ],
    },
    canela: {
      pivo: [3, 1],
      grade: [
        'kkkkkk.',
        'kwwwsk.',
        'kwwwsk.',
        'kwwwsk.',
        'kwwwsk.',
        'kkkkkkk',
        'kgggggk',
        'kgggggk',
        'kdddddk',
        'kkkkkkk',
      ],
    },
    arma: {
      pivo: [2, 5],
      encaixes: { cano: [11, 2] },
      grade: [
        '..kkkkkkk..',
        '.kmnnnnnnkk',
        'kmmmmmmmmck',
        'kmmkkkkkkk.',
        '.kmmk......',
        '.kmmk......',
        '.kkkk......',
      ],
    },
  };

  // Desenha a grade num canvas pequeno: 1 pixel da arte = 1 pixel do canvas.
  function criarImagem(grade, paleta = PALETA) {
    const largura = Math.max(...grade.map((linha) => linha.length));
    const tela = document.createElement('canvas');
    tela.width = largura;
    tela.height = grade.length;
    const ctx = tela.getContext('2d');
    grade.forEach((linha, y) => {
      [...linha].forEach((letra, x) => {
        if (letra === '.' || !paleta[letra]) return;
        ctx.fillStyle = paleta[letra];
        ctx.fillRect(x, y, 1, 1);
      });
    });
    return tela;
  }

  // Versão "atingido" de cada peça: mesma forma, toda clara, para piscar ao levar dano.
  function paletaClara() {
    const clara = {};
    Object.keys(PALETA).forEach((letra) => { clara[letra] = letra === 'k' ? '#ff6b6b' : '#ffffff'; });
    return clara;
  }

  // Versão mais escura, para as peças que ficam atrás do tronco.
  function paletaEscura(fator = 0.8) {
    const escura = {};
    Object.entries(PALETA).forEach(([letra, cor]) => {
      const canais = [1, 3, 5].map((i) => Math.round(parseInt(cor.slice(i, i + 2), 16) * fator));
      escura[letra] = `rgb(${canais.join(',')})`;
    });
    return escura;
  }

  let cache = null;
  function sprites() {
    if (cache) return cache;
    const clara = paletaClara();
    const escura = paletaEscura();
    cache = {};
    Object.entries(PARTES).forEach(([nome, parte]) => {
      cache[nome] = {
        ...parte,
        imagem: criarImagem(parte.grade),
        imagemEscura: criarImagem(parte.grade, escura),
        imagemClara: criarImagem(parte.grade, clara),
      };
    });
    return cache;
  }

  app.minijogoSprites = { PALETA, PARTES, sprites, criarImagem };
})();
