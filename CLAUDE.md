# Where's the Duck

Aplicativo desktop para Windows que deixa o Fortnite rodando sozinho em partidas de Esquadrão + Preencher: lê a tela, reconhece recortes de botões (template matching) e simula teclado e mouse. Interface, logs e comentários em português do Brasil.

## Comandos

- Testes: `python -m pytest -q` (não precisa de Windows nem do jogo)
- Build da interface: `cd frontend && npm install && npm run build`
- Rodar: `iniciar.bat` no Windows, ou `python -m wheres_the_duck` (`--navegador` abre no navegador em vez da janela nativa)
- Frontend em desenvolvimento: `cd frontend && npm run dev` com o backend rodando na porta 8765

## Arquitetura

```
wheres_the_duck/
  config.py          modelos pydantic com os padrões; lê e grava config.json
  catalogo.py        lista dos templates conhecidos (12 principais, extras, tipos de recompensa)
  registro.py        log em memória, arquivo diário e ouvintes
  captura.py         interface Capturador: CapturadorTela (mss) e CapturadorPasta (simulação)
  deteccao.py        Detector: TM_CCOEFF_NORMED em cinza, escala, contagem sem sobreposição
  entrada.py         interface Entrada: EntradaDireta (pydirectinput) e EntradaSimulada (dry-run)
  foco.py            interface Foco: FocoWindows (título da janela) e FocoSimulado; DPI awareness
  comportamentos.py  esconder, reposicionar, rondar, coletar, olhar; sorteio por peso
  maquina.py         máquina de estados: tick() a cada ciclo, animar() entre ciclos
  recompensas.py     prints antes/depois, índice JSON, cópia extra do Acesso à Loja Pirata
  historico.py       sessões em JSON
  motor.py           thread que liga captura, máquina e publicação de estado; modos real, ensaio, simulação
  api.py             FastAPI em 127.0.0.1 + WebSocket; serve frontend/dist
  app.py             ponto de entrada: uvicorn em thread, atalho F8, janela pywebview
frontend/src/        React + TypeScript + Vite: Painel, Automação, Detecção, Templates, Histórico
tests/               pytest com imagens sintéticas (conftest.py monta templates e telas)
```

Dados do usuário ficam na raiz e fora do git: `config.json`, `templates/`, `capturas/`, `dados/`, `logs/`.

### Fluxo de um ciclo (`Maquina.tick`)

1. Fora de foco: pausa. 2. Recompensa: print, clique em Resgatar, print no ciclo seguinte. 3. Tela de fim (`fim_partida`): Jogar novamente, senão Retornar ao lobby. 4. Jogar (cooldown próprio). 5. Continuar/Fechar. 6. Aviso do ônibus: agenda o salto com atraso aleatório. 7. Tempo máximo: saída pelo ESC. 8. Sozinho por N ciclos: saída pelo ESC. 9. Movimento, executado em `animar()`.

`animar()` roda a cada 0,1 s e só move o personagem quando o último `tick` terminou com a tela livre (`_tela_livre`). O tempo é sempre passado como argumento (`agora`), o que permite relógio virtual na simulação e nos testes.

## Regras inegociáveis

- O app só usa o que um humano vê na tela e teclado/mouse normais.
- Nada de burlar, enganar ou se esconder do anti-cheat: sem driver, injeção de DLL, leitura ou escrita de memória do jogo, spoofing de hardware, ocultação de processo ou de janela, nem qualquer técnica cujo propósito seja evitar detecção. Se uma ideia servir só para isso, não implemente.
- Nada que dê vantagem em combate: sem mira, sem leitura de posição de inimigos. O bot nunca atira, nunca constrói, nunca segue jogadores.
- Nunca enviar input com o Fortnite fora de foco. Ao perder o foco, a única coisa permitida é soltar as teclas que estavam pressionadas.
- F8 sempre para tudo e solta todas as teclas.
- Nenhuma conexão externa, telemetria, login ou licença. A API escuta só em 127.0.0.1 e recusa Host/Origin que não sejam locais. Fontes e sons são locais.
- Nunca tocar em credenciais, tokens ou arquivos da conta Epic.
- O README abre com o aviso de que automação viola os termos da Epic e pode dar ban.
- Identidade visual própria; nada de marcas ou artes da Epic nem de outros apps.

## Convenções

- Template ausente nunca quebra o app: o estado correspondente é ignorado. Todo código novo de detecção precisa manter isso (há testes).
- Input e foco sempre atrás das interfaces `Entrada` e `Foco`; nada de chamar pydirectinput fora de `entrada.py`.
- Interrupções usam `Maquina._interromper()` (abandona o comportamento e solta as teclas, sem novos toques).
- Mudou a máquina de estados ou a detecção: acrescente teste com imagem sintética e rode o pytest e o build do frontend antes de concluir.
- Nomes de módulos, funções, logs e comentários em português.
