const formAtualizar = document.getElementById('form-atualizar');
const mensagemAtualizar = document.getElementById('mensagem-atualizar');

formAtualizar?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const id = document.getElementById('atualizar-id').value;
  const formData = new FormData(formAtualizar);
  const dados = {};
  for (const [chave, valor] of formData.entries()) {
    if (String(valor).trim()) dados[chave] = valor;
  }

  if (!Object.keys(dados).length) {
    mostrarMensagem(mensagemAtualizar, 'Preencha pelo menos um campo para atualizar.', 'aviso');
    return;
  }

  try {
    const aluno = await explainerRequest(`/alunos/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(dados) });
    mostrarMensagem(mensagemAtualizar, `Dados de ${aluno.nome} atualizados com sucesso.`);
    formAtualizar.reset();
  } catch (error) {
    mostrarMensagem(mensagemAtualizar, error.message || 'Não foi possível atualizar o aluno.', 'erro');
  }
});
