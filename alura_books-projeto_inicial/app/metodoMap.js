function aplicarDesconto(livros){
    const desconto = 0.3
    livrosComDesconto = livros.map(livros=>{
        return{...livros, preco: livros.preco * desconto}
    })
}