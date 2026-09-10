const formDeletar = document.getElementById('form-deletar');
const mensagemDeletar = document.getElementById('mensagem-deletar');

formDeletar?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const id = document.getElementById('deletar-id').value;
  if (!window.confirm(`Excluir o aluno de ID ${id}?`)) return;

  try {
    await explainerRequest(`/alunos/${id}`, { method: 'DELETE' });
    mostrarMensagem(mensagemDeletar, `Aluno de ID ${id} excluído com sucesso.`);
    formDeletar.reset();
  } catch (error) {
    mostrarMensagem(mensagemDeletar, error.message || 'Não foi possível excluir o aluno.', 'erro');
  }
});
