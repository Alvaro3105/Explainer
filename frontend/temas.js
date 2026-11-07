const API_URL = window.location.protocol.startsWith('http') ? '' : 'http://127.0.0.1:5000';

function esc(valor) {
  if (valor === null || valor === undefined) return '';
  return String(valor).replace(/[&<>"']/g, (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
}

async function carregarTemas() {
  const tbody = document.getElementById('lista-temas');
  try {
    const response = await fetch(`${API_URL}/temas`);
    const temas = await response.json();
    tbody.innerHTML = '';
    if (!temas.length) {
      tbody.innerHTML = '<tr><td colspan="3" style="padding:1rem;color:#6b7280;">Nenhum tema cadastrado.</td></tr>';
      return;
    }
    temas.forEach((tema) => {
      const linha = document.createElement('tr');
      linha.innerHTML = `<td style="padding:0.7rem">${esc(tema.id_tema)}</td><td style="padding:0.7rem">${esc(tema.materia)}</td><td style="padding:0.7rem">${esc(tema.nome)}</td>`;
      tbody.appendChild(linha);
    });
  } catch (error) {
    tbody.innerHTML = '<tr><td colspan="3" style="padding:1rem;color:#dc2626;">Erro ao carregar temas.</td></tr>';
  }
}

const formTema = document.getElementById('form-tema');
if (formTema) {
  formTema.addEventListener('submit', async (event) => {
    event.preventDefault();
    const mensagem = document.getElementById('mensagem-tema');
    const dados = Object.fromEntries(new FormData(event.target));
    try {
      const response = await fetch(`${API_URL}/temas`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dados)
      });
      const resultado = await response.json();
      mensagem.style.display = 'block';
      if (response.ok) {
        mensagem.innerHTML = `<strong>Sucesso:</strong> tema cadastrado.`;
        formTema.reset();
        carregarTemas();
      } else {
        mensagem.innerHTML = `<strong>Erro:</strong> ${esc(resultado.erro) || 'Não foi possível salvar.'}`;
      }
    } catch (error) {
      mensagem.style.display = 'block';
      mensagem.innerHTML = '<strong>Erro:</strong> falha na conexão com o backend.';
    }
  });
}

const formTemaAtualizar = document.getElementById('form-tema-atualizar');
if (formTemaAtualizar) {
  formTemaAtualizar.addEventListener('submit', async (event) => {
    event.preventDefault();
    const mensagem = document.getElementById('mensagem-tema-atualizar');
    const id = document.getElementById('tema-id-atualizar').value;
    const materia = document.getElementById('tema-materia-atualizar').value;
    const nome = document.getElementById('tema-nome-atualizar').value;
    const dados = {};
    if (materia) dados.materia = materia;
    if (nome) dados.nome = nome;

    if (!Object.keys(dados).length) {
      mensagem.style.display = 'block';
      mensagem.innerHTML = '<strong>Aviso:</strong> Preencha pelo menos um campo para atualizar.';
      return;
    }

    try {
      const response = await fetch(`${API_URL}/temas/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dados)
      });
      const resultado = await response.json();
      mensagem.style.display = 'block';
      if (response.ok) {
        mensagem.innerHTML = `<strong>Sucesso:</strong> tema atualizado.`;
        formTemaAtualizar.reset();
        carregarTemas();
      } else {
        mensagem.innerHTML = `<strong>Erro:</strong> ${esc(resultado.erro) || 'Não foi possível atualizar.'}`;
      }
    } catch (error) {
      mensagem.style.display = 'block';
      mensagem.innerHTML = '<strong>Erro:</strong> falha na conexão com o backend.';
    }
  });
}

const formTemaDeletar = document.getElementById('form-tema-deletar');
if (formTemaDeletar) {
  formTemaDeletar.addEventListener('submit', async (event) => {
    event.preventDefault();
    const mensagem = document.getElementById('mensagem-tema-deletar');
    const id = document.getElementById('tema-id-deletar').value;

    try {
      const response = await fetch(`${API_URL}/temas/${id}`, {
        method: 'DELETE'
      });
      mensagem.style.display = 'block';
      if (response.status === 204) {
        mensagem.innerHTML = `<strong>Sucesso:</strong> tema excluído.`;
        formTemaDeletar.reset();
        carregarTemas();
      } else {
        const resultado = await response.json();
        mensagem.innerHTML = `<strong>Erro:</strong> ${esc(resultado.erro) || 'Não foi possível excluir.'}`;
      }
    } catch (error) {
      mensagem.style.display = 'block';
      mensagem.innerHTML = '<strong>Erro:</strong> falha na conexão com o backend.';
    }
  });
}

window.addEventListener('DOMContentLoaded', carregarTemas);
