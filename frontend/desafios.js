const API_URL = window.location.protocol.startsWith('http') ? '' : 'http://127.0.0.1:5000';

function esc(valor) {
  if (valor === null || valor === undefined) return '';
  return String(valor).replace(/[&<>"']/g, (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
}

async function carregarDesafios() {
  const tbody = document.getElementById('lista-desafios');
  try {
    const response = await fetch(`${API_URL}/desafio`);
    const desafios = await response.json();
    tbody.innerHTML = '';
    if (!desafios.length) {
      tbody.innerHTML = '<tr><td colspan="5" style="padding:1rem;color:#6b7280;">Nenhum desafio cadastrado.</td></tr>';
      return;
    }
    desafios.forEach((desafio) => {
      const linha = document.createElement('tr');
      linha.innerHTML = `<td style="padding:0.7rem">${esc(desafio.id_desafio)}</td><td style="padding:0.7rem">${esc(desafio.nome)}</td><td style="padding:0.7rem">${esc(desafio.dificuldade)}</td><td style="padding:0.7rem">${esc(desafio.pontuacao)}</td><td style="padding:0.7rem">${esc(desafio.quantidade_questoes || '-')}</td>`;
      tbody.appendChild(linha);
    });
  } catch (error) {
    tbody.innerHTML = '<tr><td colspan="5" style="padding:1rem;color:#dc2626;">Erro ao carregar desafios.</td></tr>';
  }
}

const formDesafio = document.getElementById('form-desafio');
if (formDesafio) {
  formDesafio.addEventListener('submit', async (event) => {
    event.preventDefault();
    const mensagem = document.getElementById('mensagem-desafio');
    const dados = Object.fromEntries(new FormData(event.target));
    dados.pontuacao = Number(dados.pontuacao);
    dados.quantidade_questoes = dados.quantidade_questoes ? Number(dados.quantidade_questoes) : null;
    try {
      const response = await fetch(`${API_URL}/desafio`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dados)
      });
      const resultado = await response.json();
      mensagem.style.display = 'block';
      if (response.ok) {
        mensagem.innerHTML = '<strong>Sucesso:</strong> desafio cadastrado.';
        formDesafio.reset();
        carregarDesafios();
      } else {
        mensagem.innerHTML = `<strong>Erro:</strong> ${esc(resultado.erro) || 'Não foi possível salvar.'}`;
      }
    } catch (error) {
      mensagem.style.display = 'block';
      mensagem.innerHTML = '<strong>Erro:</strong> falha na conexão com o backend.';
    }
  });
}

const formDesafioAtualizar = document.getElementById('form-desafio-atualizar');
if (formDesafioAtualizar) {
  formDesafioAtualizar.addEventListener('submit', async (event) => {
    event.preventDefault();
    const mensagem = document.getElementById('mensagem-desafio-atualizar');
    const id = document.getElementById('desafio-id-atualizar').value;
    const nome = document.getElementById('desafio-nome-atualizar').value;
    const dificuldade = document.getElementById('desafio-dificuldade-atualizar').value;
    const pontuacao = document.getElementById('desafio-pontuacao-atualizar').value;
    const quantidade = document.getElementById('desafio-quantidade-atualizar').value;
    const dados = {};
    if (nome) dados.nome = nome;
    if (dificuldade) dados.dificuldade = dificuldade;
    if (pontuacao) dados.pontuacao = Number(pontuacao);
    if (quantidade) dados.quantidade_questoes = Number(quantidade);

    if (!Object.keys(dados).length) {
      mensagem.style.display = 'block';
      mensagem.innerHTML = '<strong>Aviso:</strong> Preencha pelo menos um campo para atualizar.';
      return;
    }

    try {
      const response = await fetch(`${API_URL}/desafio/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dados)
      });
      const resultado = await response.json();
      mensagem.style.display = 'block';
      if (response.ok) {
        mensagem.innerHTML = '<strong>Sucesso:</strong> desafio atualizado.';
        formDesafioAtualizar.reset();
        carregarDesafios();
      } else {
        mensagem.innerHTML = `<strong>Erro:</strong> ${esc(resultado.erro) || 'Não foi possível atualizar.'}`;
      }
    } catch (error) {
      mensagem.style.display = 'block';
      mensagem.innerHTML = '<strong>Erro:</strong> falha na conexão com o backend.';
    }
  });
}

const formDesafioDeletar = document.getElementById('form-desafio-deletar');
if (formDesafioDeletar) {
  formDesafioDeletar.addEventListener('submit', async (event) => {
    event.preventDefault();
    const mensagem = document.getElementById('mensagem-desafio-deletar');
    const id = document.getElementById('desafio-id-deletar').value;

    try {
      const response = await fetch(`${API_URL}/desafio/${id}`, {
        method: 'DELETE'
      });
      mensagem.style.display = 'block';
      if (response.status === 204) {
        mensagem.innerHTML = '<strong>Sucesso:</strong> desafio excluído.';
        formDesafioDeletar.reset();
        carregarDesafios();
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

window.addEventListener('DOMContentLoaded', carregarDesafios);
