const API_URL = 'http://127.0.0.1:5000';

const formCadastro = document.getElementById('form-cadastro');

if (formCadastro) {
  formCadastro.addEventListener('submit', async (event) => {
    event.preventDefault();

    const form = event.target;
    const btnEnviar = document.getElementById('btn-enviar');
    const msgResposta = document.getElementById('mensagem-resposta');
    const respostaTitulo = document.getElementById('resposta-titulo');
    const respostaCorpo = document.getElementById('resposta-corpo');

    btnEnviar.disabled = true;
    btnEnviar.innerText = 'Cadastrando...';

    const formData = new FormData(form);
    const dados = {
      nome: formData.get('nome'),
      email: formData.get('email'),
      senha: formData.get('senha'),
      data_nascimento: formData.get('data_nascimento') || null
    };

    try {
      const response = await fetch(`${API_URL}/alunos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dados)
      });

      const resultado = await response.json();
      msgResposta.style.display = 'block';

      if (response.ok) {
        respostaTitulo.innerText = '✨ Cadastro realizado!';
        respostaTitulo.style.color = '#16a34a';
        respostaCorpo.innerText = `Aluno(a) ${resultado.nome} cadastrado(a) com sucesso. ID: ${resultado.id_aluno}.`;
        form.reset();
      } else {
        respostaTitulo.innerText = '⚠️ Ops, algo deu errado';
        respostaTitulo.style.color = '#dc2626';
        respostaCorpo.innerText = resultado.erro || 'Não foi possível realizar o cadastro.';
      }
    } catch (error) {
      msgResposta.style.display = 'block';
      respostaTitulo.innerText = '❌ Erro de conexão';
      respostaTitulo.style.color = '#dc2626';
      respostaCorpo.innerText = 'Não foi possível conectar ao backend. Verifique se a API Flask está rodando.';
      console.error(error);
    } finally {
      btnEnviar.disabled = false;
      btnEnviar.innerText = 'Cadastrar';
    }
  });
}
