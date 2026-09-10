const listaDesafios = document.getElementById('lista-desafios');

async function carregarDesafios() {
  limparElemento(listaDesafios);
  try {
    const itens = await explainerRequest('/desafio');
    if (!itens.length) { const tr=document.createElement('tr'); const td=document.createElement('td'); td.colSpan=5; td.textContent='Nenhum desafio cadastrado.'; tr.appendChild(td); listaDesafios.appendChild(tr); return; }
    itens.forEach((d) => { const tr=document.createElement('tr'); [d.id_desafio,d.nome,d.dificuldade,d.pontuacao,d.quantidade_questoes].forEach((v)=>adicionarCelula(tr,v)); listaDesafios.appendChild(tr); });
  } catch(e) { const tr=document.createElement('tr'); const td=document.createElement('td'); td.colSpan=5; td.textContent=e.message; tr.appendChild(td); listaDesafios.appendChild(tr); }
}

document.getElementById('form-desafio')?.addEventListener('submit', async (event) => {
  event.preventDefault(); const msg=document.getElementById('mensagem-desafio'); const dados=Object.fromEntries(new FormData(event.currentTarget)); dados.pontuacao=Number(dados.pontuacao); dados.quantidade_questoes=dados.quantidade_questoes?Number(dados.quantidade_questoes):null;
  try { await explainerRequest('/desafio',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(dados)}); mostrarMensagem(msg,'Desafio cadastrado com sucesso.'); event.currentTarget.reset(); carregarDesafios(); } catch(e){ mostrarMensagem(msg,e.message,'erro'); }
});

document.getElementById('form-desafio-atualizar')?.addEventListener('submit', async (event) => {
  event.preventDefault(); const msg=document.getElementById('mensagem-desafio-atualizar'); const id=document.getElementById('desafio-id-atualizar').value; const dados={}; const nome=document.getElementById('desafio-nome-atualizar').value.trim(); const dificuldade=document.getElementById('desafio-dificuldade-atualizar').value.trim(); const pontuacao=document.getElementById('desafio-pontuacao-atualizar').value; const quantidade=document.getElementById('desafio-quantidade-atualizar').value; if(nome)dados.nome=nome;if(dificuldade)dados.dificuldade=dificuldade;if(pontuacao)dados.pontuacao=Number(pontuacao);if(quantidade)dados.quantidade_questoes=Number(quantidade); if(!Object.keys(dados).length)return mostrarMensagem(msg,'Preencha pelo menos um campo.','aviso');
  try { await explainerRequest(`/desafio/${id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(dados)}); mostrarMensagem(msg,'Desafio atualizado com sucesso.'); event.currentTarget.reset(); carregarDesafios(); } catch(e){ mostrarMensagem(msg,e.message,'erro'); }
});

document.getElementById('form-desafio-deletar')?.addEventListener('submit', async (event) => {
  event.preventDefault(); const msg=document.getElementById('mensagem-desafio-deletar'); const id=document.getElementById('desafio-id-deletar').value; if(!confirm(`Excluir o desafio ${id}?`))return; try{await explainerRequest(`/desafio/${id}`,{method:'DELETE'});mostrarMensagem(msg,'Desafio excluído com sucesso.');event.currentTarget.reset();carregarDesafios();}catch(e){mostrarMensagem(msg,e.message,'erro');}
});

document.addEventListener('DOMContentLoaded', carregarDesafios);
