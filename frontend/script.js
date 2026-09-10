const formCadastro = document.getElementById('form-cadastro');
const mensagem = document.getElementById('mensagem-resposta');
const botao = document.getElementById('btn-enviar');

formCadastro?.addEventListener('submit', async (event) => {
  event.preventDefault();
  botao.disabled = true;
  botao.textContent = 'Cadastrando...';

  const dados = Object.fromEntries(new FormData(formCadastro));

  try {
    const aluno = await explainerRequest('/alunos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(dados)
    });
    mostrarMensagem(mensagem, `Aluno ${aluno.nome} cadastrado com sucesso. ID: ${aluno.id_aluno}.`);
    formCadastro.reset();
  } catch (error) {
    mostrarMensagem(mensagem, error.message || 'Não foi possível cadastrar o aluno.', 'erro');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Cadastrar';
  }
});
