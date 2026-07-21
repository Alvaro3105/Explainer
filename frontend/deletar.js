const API_URL = 'http://127.0.0.1:5000';

const formDeletar = document.getElementById('form-deletar');

if (formDeletar) {
  formDeletar.addEventListener('submit', async (event) => {
    event.preventDefault();

    const idAluno = document.getElementById('deletar-id').value;
    const txtTitulo = document.getElementById('deletar-titulo');
    const txtCorpo = document.getElementById('deletar-corpo');

    const confirmacao = confirm(`Tem certeza absoluta que deseja excluir o aluno com ID ${idAluno}?`);
    if (!confirmacao) return;

    try {
      const response = await fetch(`${API_URL}/alunos/${idAluno}`, {
        method: 'DELETE'
      });

      if (response.status === 204) {
        txtTitulo.innerText = '🗑️ Aluno removido';
        txtTitulo.style.color = '#16a34a';
        txtCorpo.innerText = `O aluno com ID ${idAluno} foi excluído permanentemente do sistema.`;
        formDeletar.reset();
      } else {
        const resultado = await response.json();
        txtTitulo.innerText = '⚠️ Erro ao excluir';
        txtTitulo.style.color = '#dc2626';
        txtCorpo.innerText = resultado.erro || 'Não foi possível remover o aluno.';
      }
    } catch (error) {
      txtTitulo.innerText = '❌ Erro de conexão';
      txtTitulo.style.color = '#dc2626';
      txtCorpo.innerText = 'Erro ao estabelecer comunicação com o servidor.';
      console.error(error);
    }
  });
}
