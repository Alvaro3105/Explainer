const formBuscar = document.getElementById('form-buscar');
const resultadoBusca = document.getElementById('resultado-busca');

formBuscar?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const id = document.getElementById('buscar-id').value;

  try {
    const aluno = await explainerRequest(`/alunos/${id}`);
    limparElemento(resultadoBusca);
    resultadoBusca.dataset.tipo = 'sucesso';

    const dados = [
      ['Nome', aluno.nome], ['E-mail', aluno.email], ['Nascimento', aluno.data_nascimento || 'Não informado'],
      ['Pontos', aluno.pontos], ['Foguinho', `${aluno.foguinho} dia(s)`]
    ];

    dados.forEach(([rotulo, valor]) => {
      const p = document.createElement('p');
      const strong = document.createElement('strong');
      strong.textContent = `${rotulo}: `;
      p.append(strong, document.createTextNode(String(valor ?? '-')));
      resultadoBusca.appendChild(p);
    });
  } catch (error) {
    mostrarMensagem(resultadoBusca, error.message || 'Aluno não encontrado.', 'erro');
  }
});
