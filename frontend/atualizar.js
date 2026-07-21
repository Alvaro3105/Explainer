const API_URL = 'http://127.0.0.1:5000';

const formAtualizar = document.getElementById('form-atualizar');

if (formAtualizar) {
  formAtualizar.addEventListener('submit', async (event) => {
    event.preventDefault();

    const idAluno = document.getElementById('atualizar-id').value;
    const form = event.target;
    const msgContainer = document.getElementById('mensagem-atualizar');
    const txtTitulo = document.getElementById('atualizar-titulo');
    const txtCorpo = document.getElementById('atualizar-corpo');

    const formData = new FormData(form);
    const dados = {};

    if (formData.get('nome')) dados.nome = formData.get('nome');
    if (formData.get('email')) dados.email = formData.get('email');
    if (formData.get('senha')) dados.senha = formData.get('senha');
    if (formData.get('data_nascimento')) dados.data_nascimento = formData.get('data_nascimento');

    if (Object.keys(dados).length === 0) {
      msgContainer.style.display = 'block';
      txtTitulo.innerText = '⚠️ Atenção';
      txtTitulo.style.color = '#d97706';
      txtCorpo.innerText = 'Preencha pelo menos um campo para atualizar.';
      return;
    }

    try {
      const response = await fetch(`${API_URL}/alunos/${idAluno}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dados)
      });

      const resultado = await response.json();
      msgContainer.style.display = 'block';

      if (response.ok) {
        txtTitulo.innerText = '🔄 Cadastro atualizado!';
        txtTitulo.style.color = '#16a34a';
        txtCorpo.innerText = `Os dados de ${resultado.nome} foram atualizados com sucesso.`;
        form.reset();
      } else {
        txtTitulo.innerText = '⚠️ Erro na atualização';
        txtTitulo.style.color = '#dc2626';
        txtCorpo.innerText = resultado.erro || 'Não foi possível atualizar o aluno.';
      }
    } catch (error) {
      msgContainer.style.display = 'block';
      txtTitulo.innerText = '❌ Erro de conexão';
      txtTitulo.style.color = '#dc2626';
      txtCorpo.innerText = 'Erro ao conectar com o backend.';
      console.error(error);
    }
  });
}
