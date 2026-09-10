const listaTemas = document.getElementById('lista-temas');

async function carregarTemas() {
  limparElemento(listaTemas);
  try {
    const temas = await explainerRequest('/temas');
    if (!temas.length) {
      const tr = document.createElement('tr'); const td = document.createElement('td'); td.colSpan = 3; td.textContent = 'Nenhum tema cadastrado.'; tr.appendChild(td); listaTemas.appendChild(tr); return;
    }
    temas.forEach((tema) => { const tr = document.createElement('tr'); [tema.id_tema, tema.materia, tema.nome].forEach((v) => adicionarCelula(tr, v)); listaTemas.appendChild(tr); });
  } catch (error) {
    const tr = document.createElement('tr'); const td = document.createElement('td'); td.colSpan = 3; td.textContent = error.message; tr.appendChild(td); listaTemas.appendChild(tr);
  }
}

document.getElementById('form-tema')?.addEventListener('submit', async (event) => {
  event.preventDefault(); const msg = document.getElementById('mensagem-tema'); const dados = Object.fromEntries(new FormData(event.currentTarget));
  try { await explainerRequest('/temas', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(dados) }); mostrarMensagem(msg, 'Tema cadastrado com sucesso.'); event.currentTarget.reset(); carregarTemas(); } catch (e) { mostrarMensagem(msg, e.message, 'erro'); }
});

document.getElementById('form-tema-atualizar')?.addEventListener('submit', async (event) => {
  event.preventDefault(); const msg = document.getElementById('mensagem-tema-atualizar'); const id = document.getElementById('tema-id-atualizar').value; const dados = {};
  const materia = document.getElementById('tema-materia-atualizar').value.trim(); const nome = document.getElementById('tema-nome-atualizar').value.trim(); if (materia) dados.materia = materia; if (nome) dados.nome = nome;
  if (!Object.keys(dados).length) return mostrarMensagem(msg, 'Preencha pelo menos um campo.', 'aviso');
  try { await explainerRequest(`/temas/${id}`, { method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify(dados) }); mostrarMensagem(msg, 'Tema atualizado com sucesso.'); event.currentTarget.reset(); carregarTemas(); } catch (e) { mostrarMensagem(msg, e.message, 'erro'); }
});

document.getElementById('form-tema-deletar')?.addEventListener('submit', async (event) => {
  event.preventDefault(); const msg = document.getElementById('mensagem-tema-deletar'); const id = document.getElementById('tema-id-deletar').value; if (!confirm(`Excluir o tema ${id}?`)) return;
  try { await explainerRequest(`/temas/${id}`, { method:'DELETE' }); mostrarMensagem(msg, 'Tema excluído com sucesso.'); event.currentTarget.reset(); carregarTemas(); } catch (e) { mostrarMensagem(msg, e.message, 'erro'); }
});

document.addEventListener('DOMContentLoaded', carregarTemas);
