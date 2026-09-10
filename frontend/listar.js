const tabelaAlunos = document.getElementById('tabela-alunos-corpo');
const mensagemLista = document.getElementById('mensagem-lista');

async function carregarAlunos() {
  try {
    const alunos = await explainerRequest('/alunos');
    limparElemento(tabelaAlunos);

    if (!alunos.length) {
      const linha = document.createElement('tr');
      const celula = document.createElement('td');
      celula.colSpan = 6;
      celula.textContent = 'Nenhum aluno cadastrado.';
      linha.appendChild(celula);
      tabelaAlunos.appendChild(linha);
      return;
    }

    alunos.forEach((aluno) => {
      const linha = document.createElement('tr');
      [aluno.id_aluno, aluno.nome, aluno.email, aluno.data_nascimento || '-', aluno.pontos, aluno.foguinho].forEach((valor) => adicionarCelula(linha, valor));
      tabelaAlunos.appendChild(linha);
    });
  } catch (error) {
    limparElemento(tabelaAlunos);
    mostrarMensagem(mensagemLista, error.message || 'Não foi possível carregar os alunos.', 'erro');
  }
}

document.addEventListener('DOMContentLoaded', carregarAlunos);
