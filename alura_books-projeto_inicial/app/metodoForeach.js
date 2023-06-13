const elementoParaInserirLivros= document.getElementById('livros')

function exibirOsLivrosNaTela(ListaDeLivros){
    ListaDeLivros.forEach(livros => {
        elementoParaInserirLivros.innerHTML+=`
        <div class="livro">
        <img class="livro__imagens" src="${livros.imagem}"
          alt="${livros.alt}" />
        <h2 class="livro__titulo">
          ${livros.titulo}
        </h2>
        <p class="livro__descricao">${livros.autor}</p>
        <p class="livro__preco" id="preco">R$${livros.preco}</p>
        <div class="tags">
          <span class="tag">${livros.categoria}</span>
        </div>
      </div>
        `
    })
}