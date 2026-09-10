const EXPLAINER_API_URL = window.location.protocol.startsWith('http') ? '' : 'http://127.0.0.1:5000';

async function explainerRequest(path, options = {}) {
  const response = await fetch(`${EXPLAINER_API_URL}${path}`, options);
  const payload = response.status === 204 ? null : await response.json().catch(() => null);

  if (!response.ok) {
    const error = new Error(payload?.erro || `Erro HTTP ${response.status}`);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }

  return payload;
}

function mostrarMensagem(elemento, texto, tipo = 'sucesso') {
  elemento.hidden = false;
  elemento.dataset.tipo = tipo;
  elemento.textContent = texto;
}

function limparElemento(elemento) {
  while (elemento.firstChild) elemento.removeChild(elemento.firstChild);
}

function adicionarCelula(linha, valor) {
  const celula = document.createElement('td');
  celula.textContent = valor ?? '-';
  linha.appendChild(celula);
}
