const API_URL = window.location.protocol.startsWith('http') ? '' : 'http://127.0.0.1:5000';

function esc(valor) {
  if (valor === null || valor === undefined) return '';
  return String(valor).replace(/[&<>"']/g, (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
}

async function carregarRanking() {
  const tbody = document.getElementById('lista-ranking');
  try {
    const response = await fetch(`${API_URL}/ranking`);
    const ranking = await response.json();
    tbody.innerHTML = '';
    if (!ranking.length) {
      tbody.innerHTML = '<tr><td colspan="4" style="padding:1rem;color:#6b7280;">Nenhum registro de ranking.</td></tr>';
      return;
    }
    ranking.forEach((item) => {
      const linha = document.createElement('tr');
      linha.innerHTML = `<td style="padding:0.7rem">${esc(item.id_ranking)}</td><td style="padding:0.7rem">${esc(item.classificacao)}</td><td style="padding:0.7rem">${esc(item.pontos)}</td><td style="padding:0.7rem">${esc(item.id_aluno)}</td>`;
      tbody.appendChild(linha);
    });
  } catch (error) {
    tbody.innerHTML = '<tr><td colspan="4" style="padding:1rem;color:#dc2626;">Erro ao carregar ranking.</td></tr>';
  }
}

const formRanking = document.getElementById('form-ranking');
if (formRanking) {
  formRanking.addEventListener('submit', async (event) => {
    event.preventDefault();
    const mensagem = document.getElementById('mensagem-ranking');
    const dados = Object.fromEntries(new FormData(event.target));
    dados.classificacao = Number(dados.classificacao);
    dados.pontos = Number(dados.pontos);
    dados.id_aluno = Number(dados.id_aluno);
    try {
      const response = await fetch(`${API_URL}/ranking`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dados)
      });
      const resultado = await response.json();
      mensagem.style.display = 'block';
      if (response.ok) {
        mensagem.innerHTML = '<strong>Sucesso:</strong> registro salvo.';
        formRanking.reset();
        carregarRanking();
      } else {
        mensagem.innerHTML = `<strong>Erro:</strong> ${esc(resultado.erro) || 'Não foi possível salvar.'}`;
      }
    } catch (error) {
      mensagem.style.display = 'block';
      mensagem.innerHTML = '<strong>Erro:</strong> falha na conexão com o backend.';
    }
  });
}

const formRankingAtualizar = document.getElementById('form-ranking-atualizar');
if (formRankingAtualizar) {
  formRankingAtualizar.addEventListener('submit', async (event) => {
    event.preventDefault();
    const mensagem = document.getElementById('mensagem-ranking-atualizar');
    const id = document.getElementById('ranking-id-atualizar').value;
    const classificacao = document.getElementById('ranking-classificacao-atualizar').value;
    const pontos = document.getElementById('ranking-pontos-atualizar').value;
    const idAluno = document.getElementById('ranking-aluno-atualizar').value;
    const dados = {};
    if (classificacao) dados.classificacao = Number(classificacao);
    if (pontos) dados.pontos = Number(pontos);
    if (idAluno) dados.id_aluno = Number(idAluno);

    if (!Object.keys(dados).length) {
      mensagem.style.display = 'block';
      mensagem.innerHTML = '<strong>Aviso:</strong> Preencha pelo menos um campo para atualizar.';
      return;
    }

    try {
      const response = await fetch(`${API_URL}/ranking/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dados)
      });
      const resultado = await response.json();
      mensagem.style.display = 'block';
      if (response.ok) {
        mensagem.innerHTML = '<strong>Sucesso:</strong> ranking atualizado.';
        formRankingAtualizar.reset();
        carregarRanking();
      } else {
        mensagem.innerHTML = `<strong>Erro:</strong> ${esc(resultado.erro) || 'Não foi possível atualizar.'}`;
      }
    } catch (error) {
      mensagem.style.display = 'block';
      mensagem.innerHTML = '<strong>Erro:</strong> falha na conexão com o backend.';
    }
  });
}

const formRankingDeletar = document.getElementById('form-ranking-deletar');
if (formRankingDeletar) {
  formRankingDeletar.addEventListener('submit', async (event) => {
    event.preventDefault();
    const mensagem = document.getElementById('mensagem-ranking-deletar');
    const id = document.getElementById('ranking-id-deletar').value;

    try {
      const response = await fetch(`${API_URL}/ranking/${id}`, {
        method: 'DELETE'
      });
      mensagem.style.display = 'block';
      if (response.status === 204) {
        mensagem.innerHTML = '<strong>Sucesso:</strong> ranking excluído.';
        formRankingDeletar.reset();
        carregarRanking();
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

window.addEventListener('DOMContentLoaded', carregarRanking);
