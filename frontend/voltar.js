(function () {
  const app = (window.ExplAIner = window.ExplAIner || {});

  function temPaginaAnteriorDoApp() {
    if (window.history.length <= 1) return false;
    try {
      const anterior = new URL(document.referrer);
      return anterior.origin === window.location.origin && anterior.href !== window.location.href;
    } catch (_) {
      return false;
    }
  }

  function voltar(fallback) {
    if (typeof app.aoVoltar === 'function' && app.aoVoltar()) return;
    if (temPaginaAnteriorDoApp()) window.history.back();
    else window.location.assign(fallback || '/');
  }

  app.voltar = voltar;
  app.temPaginaAnteriorDoApp = temPaginaAnteriorDoApp;

  document.addEventListener('click', (evento) => {
    const botao = evento.target.closest('[data-voltar]');
    if (!botao || botao.getAttribute('aria-disabled') === 'true') return;
    evento.preventDefault();
    voltar(botao.dataset.voltarFallback);
  });
})();
