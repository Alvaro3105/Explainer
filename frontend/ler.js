const API_URL = window.location.protocol.startsWith('http') ? '' : 'http://127.0.0.1:5000';

function esc(valor) {
  if (valor === null || valor === undefined) return '';
  return String(valor).replace(/[&<>"']/g, (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
}

const formBuscar = document.getElementById('form-buscar');

if (formBuscar) {
  formBuscar.addEventListener('submit', async (event) => {
    event.preventDefault();

    const idAluno = document.getElementById('buscar-id').value;
    const buscaTitulo = document.getElementById('busca-titulo');
    const buscaCorpo = document.getElementById('busca-corpo');

    try {
      const response = await fetch(`${API_URL}/alunos/${idAluno}`);
      const resultado = await response.json();

      if (response.ok) {
        buscaTitulo.innerText = '🔍 Aluno encontrado';
        buscaTitulo.style.color = '#4f46e5';
        buscaCorpo.innerHTML = `
          <p><strong>Nome:</strong> ${esc(resultado.nome)}</p>
          <p><strong>E-mail:</strong> ${esc(resultado.email)}</p>
          <p><strong>Nascimento:</strong> ${esc(resultado.data_nascimento || 'Não informada')}</p>
          <p><strong>Pontos:</strong> ✨ ${esc(resultado.pontos)}</p>
          <p><strong>Foguinho:</strong> 🔥 ${esc(resultado.foguinho)} dias</p>
        `;
      } else {
        buscaTitulo.innerText = '⚠️ Informação';
        buscaTitulo.style.color = '#dc2626';
        buscaCorpo.innerText = resultado.erro || 'Aluno não encontrado.';
      }
    } catch (error) {
      buscaTitulo.innerText = '❌ Erro de conexão';
      buscaTitulo.style.color = '#dc2626';
      buscaCorpo.innerText = 'Não foi possível conectar ao servidor.';
      console.error(error);
    }
  });
}
