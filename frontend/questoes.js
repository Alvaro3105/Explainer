const API_URL = window.location.protocol.startsWith('http') ? '' : 'http://127.0.0.1:5000';

function esc(valor) {
  if (valor === null || valor === undefined) return '';
  return String(valor).replace(/[&<>"']/g, (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
}

async function carregarQuestoes() {
  const tbody = document.getElementById('lista-questoes');
  try {
    const response = await fetch(`${API_URL}/questoes`);
    const questoes = await response.json();
    tbody.innerHTML = '';
    if (!questoes.length) {
      tbody.innerHTML = '<tr><td colspan="4" style="padding:1rem;color:#6b7280;">Nenhuma questão cadastrada.</td></tr>';
      return;
    }
    questoes.forEach((questao) => {
      const linha = document.createElement('tr');
      linha.innerHTML = `<td style="padding:0.7rem">${esc(questao.id_questao)}</td><td style="padding:0.7rem">${esc(questao.enunciado)}</td><td style="padding:0.7rem">${esc(questao.alternativa_correta || '-')}</td><td style="padding:0.7rem">${esc(questao.id_tema)}</td>`;
      tbody.appendChild(linha);
    });
  } catch (error) {
    tbody.innerHTML = '<tr><td colspan="4" style="padding:1rem;color:#dc2626;">Erro ao carregar questões.</td></tr>';
  }
}

const formQuestao = document.getElementById('form-questao');
if (formQuestao) {
  formQuestao.addEventListener('submit', async (event) => {
    event.preventDefault();
    const mensagem = document.getElementById('mensagem-questao');
    const dados = Object.fromEntries(new FormData(event.target));
    dados.id_tema = Number(dados.id_tema);
    try {
      const response = await fetch(`${API_URL}/questoes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dados)
      });
      const resultado = await response.json();
      mensagem.style.display = 'block';
      if (response.ok) {
        mensagem.innerHTML = '<strong>Sucesso:</strong> questão cadastrada.';
        formQuestao.reset();
        carregarQuestoes();
      } else {
        mensagem.innerHTML = `<strong>Erro:</strong> ${esc(resultado.erro) || 'Não foi possível salvar.'}`;
      }
    } catch (error) {
      mensagem.style.display = 'block';
      mensagem.innerHTML = '<strong>Erro:</strong> falha na conexão com o backend.';
    }
  });
}

const formQuestaoAtualizar = document.getElementById('form-questao-atualizar');
if (formQuestaoAtualizar) {
  formQuestaoAtualizar.addEventListener('submit', async (event) => {
    event.preventDefault();
    const mensagem = document.getElementById('mensagem-questao-atualizar');
    const id = document.getElementById('questao-id-atualizar').value;
    const enunciado = document.getElementById('questao-enunciado-atualizar').value;
    const alternativa = document.getElementById('questao-alternativa-atualizar').value;
    const idTema = document.getElementById('questao-tema-atualizar').value;
    const dados = {};
    if (enunciado) dados.enunciado = enunciado;
    if (alternativa) dados.alternativa_correta = alternativa;
    if (idTema) dados.id_tema = Number(idTema);

    if (!Object.keys(dados).length) {
      mensagem.style.display = 'block';
      mensagem.innerHTML = '<strong>Aviso:</strong> Preencha pelo menos um campo para atualizar.';
      return;
    }

    try {
      const response = await fetch(`${API_URL}/questoes/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dados)
      });
      const resultado = await response.json();
      mensagem.style.display = 'block';
      if (response.ok) {
        mensagem.innerHTML = '<strong>Sucesso:</strong> questão atualizada.';
        formQuestaoAtualizar.reset();
        carregarQuestoes();
      } else {
        mensagem.innerHTML = `<strong>Erro:</strong> ${esc(resultado.erro) || 'Não foi possível atualizar.'}`;
      }
    } catch (error) {
      mensagem.style.display = 'block';
      mensagem.innerHTML = '<strong>Erro:</strong> falha na conexão com o backend.';
    }
  });
}

const formQuestaoDeletar = document.getElementById('form-questao-deletar');
if (formQuestaoDeletar) {
  formQuestaoDeletar.addEventListener('submit', async (event) => {
    event.preventDefault();
    const mensagem = document.getElementById('mensagem-questao-deletar');
    const id = document.getElementById('questao-id-deletar').value;

    try {
      const response = await fetch(`${API_URL}/questoes/${id}`, {
        method: 'DELETE'
      });
      mensagem.style.display = 'block';
      if (response.status === 204) {
        mensagem.innerHTML = '<strong>Sucesso:</strong> questão excluída.';
        formQuestaoDeletar.reset();
        carregarQuestoes();
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

window.addEventListener('DOMContentLoaded', carregarQuestoes);
