const API_URL = 'http://127.0.0.1:5000';

async function carregarAlunos() {
  const tabelaCorpo = document.getElementById('tabela-alunos-corpo');
  const msgStatus = document.getElementById('mensagem-status');

  try {
    const response = await fetch(`${API_URL}/alunos`);
    const alunos = await response.json();

    if (response.ok) {
      if (alunos.length === 0) {
        msgStatus.innerText = 'Nenhum aluno cadastrado ainda.';
        return;
      }

      tabelaCorpo.innerHTML = '';

      alunos.forEach((aluno) => {
        const linha = document.createElement('tr');
        linha.style.borderBottom = '1px solid var(--borda)';
        linha.innerHTML = `
          <td style="padding: 0.8rem 0.5rem; font-weight: 600; color: var(--primaria);">${aluno.id_aluno}</td>
          <td style="padding: 0.8rem 0.5rem; color: var(--texto);">${aluno.nome}</td>
          <td style="padding: 0.8rem 0.5rem; color: var(--texto-suave);">${aluno.email}</td>
          <td style="padding: 0.8rem 0.5rem; color: var(--texto-suave);">${aluno.data_nascimento || '-'}</td>
          <td style="padding: 0.8rem 0.5rem; color: var(--texto);">✨ ${aluno.pontos}</td>
          <td style="padding: 0.8rem 0.5rem; color: var(--texto);">🔥 ${aluno.foguinho}</td>
        `;
        tabelaCorpo.appendChild(linha);
      });
    } else {
      msgStatus.innerText = 'Erro ao carregar a lista de alunos do servidor.';
      msgStatus.style.color = '#dc2626';
    }
  } catch (error) {
    msgStatus.innerText = 'Não foi possível conectar ao backend. Verifique se a API está rodando.';
    msgStatus.style.color = '#dc2626';
    console.error(error);
  }
}

window.addEventListener('DOMContentLoaded', carregarAlunos);
