/* Botão "Voltar" compartilhado por todas as páginas do ExplAIner.
   Qualquer elemento com [data-voltar] passa a voltar para a página anterior:
   - usa o histórico do navegador quando a página anterior é do próprio ExplAIner;
   - se a página foi aberta direto (aba nova, link externo, favorito), vai para
     o destino de fallback em data-voltar-fallback (padrão: "/").
   Uma página pode tratar o "voltar" internamente (ex.: trocar de visão numa SPA)
   registrando ExplAIner.aoVoltar = () => true quando já resolveu sozinha. */
(function () {
  const app = (window.ExplAIner = window.ExplAIner || {});

  function temPaginaAnteriorDoApp() {
    if (window.history.length <= 1) return false;
    try {
      const anterior = new URL(document.referrer);
      return anterior.origin === window.location.origin && anterior.href !== window.location.href;
    } catch (_) {
      return false; // sem referrer: página aberta diretamente
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
