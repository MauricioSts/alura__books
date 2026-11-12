# Where's the Duck

> **Aviso importante, leia antes de usar.** Automatizar o jogo **viola os termos de serviço da Epic Games** e pode resultar em **banimento permanente da conta**, sem aviso e sem recurso. Este app não tenta esconder nada do anti-cheat e não oferece nenhuma proteção contra isso. Se decidir usar, **use uma conta secundária** que você aceite perder. Além disso, um bot parado numa partida de Esquadrão ocupa a vaga de um jogador de verdade no time de outras pessoas. O uso é por sua conta e risco.

Where's the Duck é um aplicativo desktop para Windows que deixa o Fortnite rodando sozinho em Battle Royale ou Zero Build, em **Esquadrão + Preencher**, durante o evento de caça ao tesouro. Ele entra na partida, evita a expulsão por inatividade, fica assistindo enquanto houver companheiro vivo, clica em **Resgatar** quando a tela de tesouro aparece, salva os prints e puxa outra partida quando não faz mais sentido ficar.

Ele faz isso do jeito mais simples possível: tira prints da tela, **lê os textos que aparecem nela** (OCR que roda no próprio PC, sem internet) e simula teclado e mouse. Você não precisa recortar nada: o app reconhece "JOGAR", "RESGATAR", "VOCÊ ENCONTROU", "ACESSO À LOJA PIRATA" etc. sozinho. Recortes de botão (templates) continuam existindo como opção, para o caso de algum texto não ser lido. Não lê memória do jogo, não injeta nada, não usa driver.

## O que ele faz a cada ciclo (~1,5 s)

Nesta ordem de prioridade:

1. **Fortnite fora de foco**: pausa e não envia nenhum input.
2. **Recompensa na tela**: salva um print, clica em Resgatar ou Resgatar tudo, conta o tesouro e salva outro print no ciclo seguinte.
3. **Tela de fim** (esquadrão eliminado): clica em Jogar novamente; se não houver, em Retornar ao lobby.
4. **Botão Jogar** do lobby: clica (cooldown de 15 s) e conta uma partida.
5. **Pop-up** com Continuar ou Fechar: clica.
6. **Aviso de pular do ônibus**: agenda o salto para o trecho final da rota.
7. **Tempo máximo de partida** (0 = desligado): sai pelo menu ESC.
8. **Sobrou só o bot vivo**: o app conta as barras de vida e escudo dos colegas na lista da squad (canto inferior esquerdo, ignorando a linha da vida do próprio bot). Se já tinha visto colegas nesta partida e nenhuma barra aparece por 3 ciclos seguidos, sem estar espectando, sai pelo menu ESC (veja "Como ele sai da partida"). Colega derrubado (barra vermelha) ainda conta como vivo. Se você recortar o ícone `companheiro_morto`, a contagem de ícones é usada no lugar das barras.
9. **Movimento anti-inatividade**, descrito abaixo.

### Como ele sai da partida

Aperta ESC e, a cada ciclo, clica no que estiver na tela, do passo mais adiantado para o mais cedo:

1. **Confirmar / Sim**, só depois de já ter clicado em Voltar ao lobby;
2. **Voltar ao lobby / Retornar ao lobby / Sair da partida** (lido pelo texto);
3. **Menu sanduíche (≡)**: reconhecido pelo formato (três tracinhos claros iguais e empilhados), sem recorte.

Ou seja: ESC → ≡ → Voltar ao lobby → Confirmar, e também funciona se o botão aparecer direto no menu ou se não houver confirmação. Se nada disso aparecer em 4 ciclos, ele fecha o menu com ESC e tenta de novo em 60 s. Se o ≡ do seu jogo não for reconhecido, recorte o template opcional `menu_sanduiche`.

### Salto e pouso

Quando o aviso do ônibus aparece, o bot espera um tempo aleatório entre o atraso mínimo e o máximo (padrão 28 a 40 s), salta, gira a câmera cerca de 90° para um lado sorteado e segura W, afastando-se da rota. Com "abrir planador cedo" ligado, aperta espaço de novo logo depois do salto. Continua segurando W pelo "tempo segurando W" (padrão 80 s), porque o app não enxerga o chão.

### Movimentação em partida

Comportamentos sorteados por peso, com duração variável, todos configuráveis na tela Automação:

| Comportamento | O que faz |
|---|---|
| Esconder | Agacha e fica parado, com pequenos ajustes de câmera. Nunca passa de 80% do limite de inatividade. |
| Reposicionar | Vira, corre (Shift+W) alguns segundos e para. |
| Rondar | Anda agachado em trajetos curtos, mudando de direção. |
| Coletar | Seleciona a picareta e bate no que estiver à frente. |
| Atirar a esmo | Pega uma arma (teclas 1 a 5) e dá rajadas curtas para direções sorteadas, andando. Não mira em nada. |
| Olhar em volta | Giro lento de câmera, sem andar. |

O bot **não mira, não procura inimigos, nunca constrói e nunca segue jogadores**; os tiros são a esmo. Atirar entrega a posição, então com "Atirar a esmo" ligado ele tende a morrer mais cedo (peso 0 desliga). Espectando, ele reduz o input a um pequeno movimento de mouse de tempos em tempos.

**Preso em obstáculo:** a cada ciclo o app compara o cenário (faixa central de cima da tela, sem o personagem) com o do ciclo anterior. Se o bot está andando e a imagem praticamente não muda por 2 ciclos, ele está batendo em algo: pula, vira de 90° a 180° e muda de direção. No pouso, se já está parado no chão, ele encerra o planeio e começa a se mover. O "Reposicionar" também faz desvios curtos para os lados (A/D) e o "Rondar" usa W, A, S e D.

**Ir até a zona segura:** logo depois do salto do ônibus e logo depois de ser revivido, ainda no ar, o bot abre o mapa (M), clica no centro da zona segura (ou do mapa) para marcar e fecha. A marcação aparece na tela com a distância ("350 m"); a cada ciclo ele lê esse texto e vira a câmera na direção dele. Assim plana e depois corre (Shift+W) até o meio, em vez de ir reto para o mar. A menos de 60 m ele volta aos comportamentos normais. Se perder a marcação de vista por 8 ciclos, marca de novo (no máximo 2 vezes). Ajustes em **Automação → Ir até o meio do mapa**:

- o botão de marcar é o do meio (padrão do jogo); se a marcação não aparecer, o bot tenta o esquerdo e o direito sozinho;
- se a marca cair fora do centro da ilha, ajuste "Centro da ilha no mapa" (x e y, em frações da tela com o mapa aberto).

**Esperando reinício:** morto, com "Realocando… / Esperando para ser reiniciado" na tela por mais de 3 minutos (configurável em Automação), o bot volta ao lobby pelo menu.

**Revivido:** se o bot estava espectando e o indicador de espectador some por 2 ciclos seguidos, ele foi revivido (reinício): segura W e abre o planador por 35 s (configurável), depois volta aos comportamentos normais.

**Tempestade:** o bot abre o mapa, acha o círculo branco da próxima zona segura e marca o centro dele (sem círculo, marca o meio do mapa), e segue a marcação. Refaz isso a cada 75 s e na hora em que a tela fica arroxeada (dentro da tempestade). Ainda assim ele pode morrer para a tempestade ou para outro jogador e seguir espectando, o que é esperado.

### Recompensas

| Recompensa | Chance por baú |
|---|---|
| Traje Dourado Semanal | 1 em 1.562.500 |
| **Acesso à Loja Pirata** | **1 em 137.500** |
| Veículo e Decalque Semanal | 1 em 7.813 |
| Picareta ou Acessório para as Costas Semanal | 1 em 568 |
| Faixa de Improviso Semanal | 1 em 391 |
| Tela de Carregamento Semanal | 1 em 272 |
| Gizmo (cinco tipos, o único que repete) | 1 em 127 |

- Sempre que um botão Resgatar, a tela de tesouro, o aviso "Você encontrou" ou a tela dourada de acesso aparecer, o print é salvo **antes** de qualquer clique e outro é salvo depois.
- O tipo é identificado pelos templates de recompensa. Sem template correspondente, o registro fica como "não identificada" e o print é salvo do mesmo jeito.
- Cada captura aparece na hora no feed do Painel e fica na galeria do Histórico, com tipo, data, hora e número da partida. Os arquivos ficam em `capturas/`.
- **Como o token aparece de verdade**: não é uma tela com botão. É uma faixa dourada no meio da tela, durante a partida, com "VOCÊ ENCONTROU" em cima e "ACESSO À LOJA PIRATA" embaixo, que some sozinha em poucos segundos. O app trata isso com dois recortes: `aviso_encontrou` (só o texto "VOCÊ ENCONTROU", igual para qualquer recompensa) e `acesso_pirata` (só o texto "ACESSO À LOJA PIRATA").
- **O problema do primeiro token**: você só consegue recortar `acesso_pirata` na sua resolução depois de vê-lo uma vez. Por isso, enquanto esse template não existir, o caminho é: recorte `aviso_encontrou` na primeira recompensa comum que aparecer e deixe ligado "Alertar quando aparecer uma recompensa sem template" (Automação, ligado por padrão). Toda recompensa que nenhum template reconhecer toca o alarme e mostra o print para você conferir; o bot continua rodando. Conforme você recorta os tipos comuns (gizmo, tela de carregamento, faixa, picareta), o alarme passa a tocar só para o que é raro.
- **Acesso à Loja Pirata**: alerta em tela cheia que só some quando você fecha, som em loop até você confirmar, destaque permanente no topo do Painel e do Histórico e cópia extra dos prints em `capturas/acesso_pirata/`. Lembre-se: **o token precisa ser ativado na loja até 15/12/2026**. Depois dele, o app para tudo (padrão) ou continua farmando, conforme a tela Automação.

## Aviso no Discord (opcional)

Em **Automação → Avisos no Discord**, cole a URL de um webhook do seu canal (Discord: Configurações do canal → Integrações → Webhooks → Novo webhook → Copiar URL), ligue a chave e salve. Use **Enviar mensagem de teste** para conferir.

- Cada recompensa capturada gera **um** aviso, com tipo, data, hora, número da partida e o print.
- Filtro: todas, tudo menos gizmo, ou só o Acesso à Loja Pirata.
- No Acesso à Loja Pirata, o aviso pode mencionar alguém (por exemplo `@everyone`).
- Essa é a única conexão do app para fora do PC. Fica desligada até você configurar, e a URL fica só no `config.json` do seu computador. Não compartilhe essa URL: quem tiver ela consegue postar no seu canal.

## Instalação

Requisitos: Windows 10 ou 11, [Python 3.11+](https://www.python.org/downloads/) (marque "Add python.exe to PATH") e [Node.js 18+](https://nodejs.org/) (só para compilar a interface na primeira vez).

```
git clone <endereço deste repositório>
cd <pasta>
iniciar.bat
```

O `iniciar.bat` cria o ambiente virtual, instala as dependências, compila a interface se ainda não existir e abre o app. Nas próximas vezes, é só rodar o mesmo arquivo.

Manual, se preferir:

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
.venv\Scripts\python -m wheres_the_duck
```

`python -m wheres_the_duck --navegador` abre a interface no navegador padrão em vez da janela nativa.

### Executável (.exe), sem instalar Python nem Node

Há duas formas de obter o `WheresTheDuck.exe`:

- **Baixar do GitHub**: na aba **Actions** do repositório, abra a execução mais recente de "Executável para Windows" e baixe o artefato `WheresTheDuck-windows` (um .zip com o .exe dentro). É preciso estar logado no GitHub.
- **Gerar no seu PC**: rode `compilar.bat`. O arquivo sai em `dist\WheresTheDuck.exe`.

Coloque o .exe numa pasta só dele: `config.json`, `templates\`, `capturas\`, `dados\` e `logs\` são criados ao lado do executável. A janela usa o WebView2, que já vem no Windows 10/11 atualizado.

O executável não é assinado. O Windows SmartScreen vai avisar na primeira vez ("Mais informações" → "Executar assim mesmo") e alguns antivírus desconfiam de executáveis feitos com PyInstaller. O app não faz nada para contornar isso; se preferir, use o `iniciar.bat`, que roda direto do código.

## Comandos do jogo que o bot usa

Baseado nos controles padrão do Fortnite no PC (confira em Configurações → Controles; se os seus forem outros, ajuste em Automação):

| Ação | Tecla padrão | Como o bot usa |
|---|---|---|
| Andar | W A S D | Movimento, contorno de obstáculos |
| Correr | Correr por padrão (ligado) | O bot não segura Shift: com "Correr por padrão", Shift faz andar devagar |
| Pular / escalar | Espaço | Pular, abrir o planador e escalar bordas baixas ao pular contra elas |
| Agachar / deslizar | Ctrl esquerdo | Esconder e rondar |
| Mapa | M | Abrir o mapa para marcar a zona segura |
| Marcar no mapa | Botão do meio do mouse | Marcar o centro da zona; se não aparecer marcação, tenta o esquerdo e o direito e guarda o que funcionou |
| Picareta | F | Coletar |
| Armas | 1 a 5 | Atirar a esmo |

**Contornar estruturas:** quando o cenário para de mudar enquanto ele anda (preso), o bot recua (S), pula duas vezes (para escalar se for baixo) e anda na diagonal para um lado. Se ficar preso de novo em seguida, tenta o outro lado virando 90°; na terceira vez, dá meia-volta.

**Salto do ônibus:** ele salta 3 a 10 s depois do aviso (antes saltava no fim da rota e acabava longe da zona, morrendo no gás) e plana já na direção da zona segura marcada.

## Configurando o jogo

- Modo de janela: **Tela cheia em janela** (sem borda). Em tela cheia exclusiva a captura pode vir preta.
- Jogue no **monitor principal**.
- Deixe o modo Esquadrão com **Preencher** ligado, e não mude resolução nem idioma depois de recortar os templates.
- Teclas no padrão: W/A/S/D, Espaço, Shift para correr, Ctrl para agachar, F para a picareta. Se as suas forem outras, ajuste em Automação.

## Reconhecimento automático (sem prints)

Por padrão, cada estado é reconhecido pelo texto na tela:

| Estado | Textos procurados (padrão) |
|---|---|
| Lobby | JOGAR (o maior texto "JOGAR" da tela, para não confundir com a aba) |
| Recompensa | VOCÊ ENCONTROU, ACESSO DESBLOQUEADO, TESOURO ENCONTRADO, RESGATAR, RESGATAR TUDO |
| Tipo da recompensa | LOJA PIRATA, TRAJE DOURADO, VEÍCULO, PICARETA, FAIXA DE IMPROVISO, TELA DE CARREGAMENTO, GIZMO |
| Fim de partida | ESQUADRÃO ELIMINADO, VOCÊ FICOU EM… ou, sem isso, JOGAR NOVAMENTE / RETORNAR AO LOBBY por 2 ciclos **sem** ESPECTANDO na tela |
| Ônibus | PULAR, SALTAR (ignorado no lobby) |
| Espectando | MODO ESPECTADOR, ESPECTANDO, ASSISTINDO |
| Menu ESC | SAIR DA PARTIDA, SAIR, CONFIRMAR, SIM |
| Pop-ups | CONTINUAR, FECHAR |

Maiúsculas, acentos e espaços não importam, e pequenos erros de leitura são tolerados.

**Os textos acima são palpites** para o jogo em português do Brasil; eu não consegui conferir cada tela do jogo. Se algum estado não for reconhecido:

1. Deixe o jogo naquela tela e use **Detecção → Testar detecção agora**. Além do score de cada estado, aparece a lista **"Textos lidos na tela"**, ou seja, exatamente o que o app enxergou.
2. Copie o texto certo para o estado em **Detecção → Leitura de texto → Palavras que identificam cada estado** e salve.
3. Só se mesmo assim não der certo, recorte um template daquele estado (abaixo). O recorte tem prioridade sobre o texto.

O único estado que **não** tem versão por texto é o ícone de companheiro eliminado (`companheiro_morto`), porque é um desenho, não texto. Sem ele, o bot não sai antecipadamente quando sobra sozinho; fica até morrer e a partida acabar, o que só custa alguns minutos por partida.

Custo: a leitura leva cerca de 0,3 a 0,6 s por ciclo e usa 2 núcleos da CPU. Se o jogo pesar, diminua a "Largura de leitura" (Detecção) ou aumente o intervalo de checagem.

### Por que não usar imagens prontas da internet

O template matching compara pixel a pixel. Um recorte feito por outra pessoa, em outra resolução, outra escala de HUD ou outro idioma, não casa com a sua tela. Por isso o app lê o texto em vez de depender de imagens, e nenhuma arte do jogo vem junto com ele.

## Como recortar um template (opcional)

Os templates são PNGs recortados **por você**, na **sua** resolução e no **seu** idioma. Eles ficam em `templates/` e não vão para o git.

Na tela **Templates**, clique em **Recortar da tela**, depois em **Capturar tela em 5 s**, troque para o jogo e espere. De volta ao app, arraste um retângulo sobre o elemento e salve. Também dá para enviar um PNG pronto.

Regras para um bom recorte:

- Recorte **justo**: o texto do botão e um pouco do fundo dele. Nada de fundo animado, contadores, nomes de jogador ou qualquer coisa que mude.
- Evite recortes minúsculos (menos de ~20 px) e áreas de cor chapada.
- Capture com o botão no estado normal, sem o mouse em cima.
- Depois de recortar, use **Detecção → Testar detecção agora** com aquela tela aberta: o score deve ficar bem acima do limiar (0,82) e os outros templates, bem abaixo.

| Template | O que recortar | Onde aparece |
|---|---|---|
| `jogar` | O texto do botão JOGAR | Lobby |
| `resgatar` | O botão RESGATAR | Tela de tesouro |
| `resgatar_tudo` | O botão RESGATAR TUDO | Tela de tesouro com vários itens |
| `fim_partida` | Um trecho fixo que só existe na tela final, quando o esquadrão todo caiu (por exemplo, o rótulo da colocação) | Fim de partida |
| `jogar_novamente` | O botão JOGAR NOVAMENTE | Fim de partida |
| `retornar_lobby` | O botão RETORNAR AO LOBBY | Fim de partida |
| `continuar` | O botão CONTINUAR | Pop-ups |
| `pular_onibus` | O aviso da tecla de saltar | Ônibus, depois que as portas abrem |
| `sair_partida` | A opção de sair da partida | Menu ESC |
| `confirmar_sair` | O botão que confirma a saída | Menu ESC |
| `companheiro_morto` | Só o ícone de eliminado ao lado do nome de um companheiro, bem justo | Lista da squad |
| `espectando` | Um trecho fixo do HUD de espectador | Depois de morrer, assistindo |

Opcionais: `fechar` (pop-ups), `tesouro_encontrado` e `aviso_encontrou` (para salvar print mesmo sem botão) e os sete tipos de recompensa (`acesso_pirata`, `traje_dourado`, `veiculo`, `picareta_costas`, `faixa`, `tela_carregamento`, `gizmo`). Para os tipos de recompensa você só consegue recortar depois de ver cada tela ao menos uma vez; os prints salvos como "não identificada" servem de fonte.

**Template ausente nunca quebra o app**: o estado é reconhecido pelo texto ou, se a leitura de texto estiver desligada, simplesmente ignorado.

Atenção ao `fim_partida`: o botão Retornar ao lobby também aparece enquanto você assiste a um companheiro. Por isso o app só trata como fim de partida quando o template `fim_partida` está na tela. Escolha um trecho que **não** apareça durante o modo espectador.

## Como rodar

1. Abra o Fortnite e fique no lobby, com o modo já escolhido.
2. Abra o Where's the Duck e confira a tela Templates.
3. Clique em **Iniciar** ou aperte **F8** e volte para o jogo. O app só age com a janela do jogo em foco.
4. **F8 para tudo e solta todas as teclas**, a qualquer momento.

Modos do botão Iniciar:

- **Real**: captura a tela e envia teclado e mouse. É o que o F8 usa.
- **Ensaio**: captura a tela de verdade, mas só escreve no log o que faria. Bom para validar os templates com o jogo aberto, sem risco de input errado.
- **Simulação**: roda a máquina de estados sobre uma pasta de screenshots (em ordem alfabética), com relógio acelerado e sem input. "Ciclos por imagem" define por quantos ciclos cada screenshot fica na tela.

### Telas

- **Painel**: estado atual, Iniciar/Parar, indicador de foco, contadores, recompensas por tipo, feed de recompensas e log ao vivo.
- **Automação**: tempos, saída quando sozinho, salto, comportamentos e o que fazer depois do Acesso à Loja Pirata.
- **Detecção**: limiar, escala, região da squad e o teste de detecção.
- **Templates**: status, preview, upload e recorte de cada template.
- **Histórico**: sessões anteriores e galeria de prints.

Tudo é gravado em `config.json`, na raiz, e pode ser editado pela interface ou à mão (com o app fechado). Alterações feitas com o bot rodando valem a partir do próximo Iniciar.

## Solução de problemas

| Sintoma | O que verificar |
|---|---|
| "Fortnite fora de foco" mesmo com o jogo aberto | O título da janela precisa conter o texto de Detecção → Título da janela do jogo (padrão `Fortnite`). Clique na janela do jogo. |
| O app vê os botões, mas os cliques e teclas não chegam ao jogo | Se o jogo ou o launcher roda como administrador, o Windows bloqueia input vindo de um programa sem a mesma permissão. Rode o `iniciar.bat` como administrador. |
| Clique cai deslocado | Jogue no monitor principal, em tela cheia em janela. Confira a escala do Windows; o app já ativa DPI awareness, mas recorte os templates de novo se mudou a escala. |
| Um estado não é reconhecido pelo texto | Detecção → Testar detecção agora, com o jogo naquela tela. Veja em "Textos lidos na tela" como o texto aparece e copie para as palavras daquele estado. |
| "Leitura de texto indisponível" no log | Falta o pacote `rapidocr_onnxruntime`. Rode `iniciar.bat` de novo ou use o .exe, que já vem com ele. |
| Jogo travando com o bot ligado | Diminua a largura de leitura (por exemplo 960) ou aumente o intervalo de checagem para 2 s. |
| Nada é detectado | Rode Detecção → Testar detecção agora com a tela certa aberta. Score baixo: refaça o recorte, mais justo. Se mudou resolução, idioma ou escala de HUD, todos os templates precisam ser refeitos. |
| Detecta coisa que não está na tela | Suba o limiar (0,85 a 0,90) ou refaça o recorte com mais detalhe. |
| Captura preta | Troque tela cheia exclusiva por tela cheia em janela. |
| O bot sai da partida com companheiros vivos | O template `companheiro_morto` está casando com outra coisa. Recorte mais justo, confira a região da squad e o número de companheiros. |
| O bot nunca sai quando fica sozinho | Faltam `companheiro_morto`, `sair_partida` ou `confirmar_sair`, ou o Preencher completou menos de 3 companheiros (ajuste o número em Automação). |
| O bot só segura W e não vira a câmera | O giro é enviado como movimento relativo do mouse. Aumente "Pixels de mouse por grau" em Automação (por exemplo 20 a 40) até 90° virar 90°. |
| Abre o mapa mas não marca | Troque o botão de marcar em Automação → Ir até o meio do mapa. |
| Vai para o lado errado depois de marcar | Rode Detecção → Testar detecção agora com a marcação na tela e veja se a distância ("350 m") aparece em "Textos lidos na tela". |
| O bot fica empurrando a parede | Aumente a "Sensibilidade de 'preso'" em Automação (por exemplo 3) para ele desviar mais cedo. |
| Ele desvia toda hora mesmo andando | Diminua a "Sensibilidade de 'preso'" (por exemplo 0,8). |
| Sai da partida com colegas vivos, ou nunca sai | Em Detecção, com uma partida aberta, rode o teste e olhe a prévia da região da squad: as barras dos colegas precisam estar dentro do recorte e aparecer contornadas. Ajuste a região. |
| A câmera vira muito ou pouco no salto | Ajuste "Pixels de mouse por grau" em Automação até 90° virar 90° na sua sensibilidade. |
| O bot é ejetado do ônibus antes de saltar | A rota era curta. Diminua os atrasos do salto. |
| Expulso por inatividade | Diminua a duração do Esconder e o intervalo de input ao espectar; confira o log para ver se o app estava pausado por falta de foco. |
| O aviso "Você encontrou" passou e não foi capturado | O aviso dura poucos segundos. Diminua o intervalo de checagem (por exemplo 0,8 s) e confira o recorte de `aviso_encontrou`: só o texto, sem o cenário em volta. |
| O alarme toca a cada recompensa comum | É o alerta de recompensa sem template. Recorte o template daquele tipo, ou desligue o alerta em Automação (aí o token só é reconhecido se `acesso_pirata` já estiver recortado). |
| O contador de tesouros parece alto | Se a tela de resgate tem fundo animado e o clique demora a fechar, a mesma tela pode ser contada mais de uma vez. Os prints mostram o que realmente aconteceu. |
| F8 não funciona | Veja o log ao abrir o app. Outro programa pode estar usando o F8; use o botão da interface. |
| Porta em uso | Mude `porta` no `config.json`. |

Logs ficam em `logs/`, um arquivo por dia.

## Limites do app (de propósito)

- Só usa o que um humano vê na tela e teclado/mouse comuns (SendInput, via pydirectinput).
- Não burla, não engana e não se esconde do anti-cheat: sem driver, sem injeção de DLL, sem leitura ou escrita de memória, sem spoofing de hardware, sem ocultar processo ou janela, sem nenhuma técnica para evitar detecção. As variações aleatórias de tempo e movimento existem para o bot não ficar preso nem cair sempre no mesmo lugar, não para se disfarçar.
- Nenhuma vantagem em combate: sem mira, sem leitura de inimigos.
- Nunca envia input com o jogo fora de foco.
- Nenhuma conexão externa, telemetria, login ou licença, exceto o aviso opcional no Discord, que só existe se você configurar o seu webhook. A API escuta só em `127.0.0.1` e recusa requisições de outras origens. Fontes e sons são locais.
- Não toca em credenciais, tokens nem arquivos da conta Epic.

## Decisões tomadas durante o desenvolvimento

- **Nome e identidade**: "Where's the Duck", nome escolhido por você, com um pato como ícone. O nome é só o nome: não esconde nada do anti-cheat. Paleta de casco escuro, latão e verde-mar; tipografia do próprio Windows (Bahnschrift, Segoe UI, Cascadia Mono), sem baixar fontes.
- **Prioridade do ônibus**: a regra "apertar espaço ao ver o aviso" foi substituída pelo salto atrasado da seção Salto e pouso.
- **Fim de partida** só é reconhecido pelo template `fim_partida`, porque Retornar ao lobby também aparece no modo espectador.
- **Movimento só com evidência de partida**: o bot só se move depois de ele mesmo ter clicado em Jogar ou de ver o aviso do ônibus. Se você iniciar o app no meio de uma partida, ele espera o próximo lobby. Isso evita teclas e cliques soltos em menus.
- **Sem movimento por cima de interface**: depois de qualquer clique, ou enquanto houver botão ou tela reconhecida na frente, o movimento fica bloqueado até um ciclo ver a tela livre.
- **Sem aviso do ônibus em 120 s** depois de clicar em Jogar, o app assume que a partida começou (cobre a falta do template `pular_onibus`).
- **Contagem de partidas**: conta no clique em Jogar ou Jogar novamente; cliques repetidos na mesma fila não contam de novo.
- **Perda de foco**: o app solta as teclas que estavam pressionadas (para não ficarem presas no Windows) e não envia mais nada.
- **Saída pelo ESC**: se Sair ou Confirmar não aparecer em 4 ciclos, o app fecha o menu e tenta de novo depois de 60 s. Sem os dois templates, ele nem abre o menu.
- **Tela de resgate travada**: se a tela continua praticamente idêntica depois do clique, o app clica de novo sem contar outro tesouro.
- **Aviso do token sem botão**: é registrado uma vez; com "parar tudo" ligado, o app para ali mesmo, no meio da partida, e solta as teclas.
- **Recompensa sem template** dispara alarme por padrão (sem parar o bot), porque o template do token não pode ser recortado antes de ele aparecer.
- **Lista da squad no canto inferior esquerdo** (região padrão: 0% a 30% da largura, de 55% da altura até embaixo). A vida do próprio bot fica na mesma região: no começo da partida, com pelo menos 2 linhas de barra visíveis, a mais baixa é tomada como a do bot e ignorada dali em diante. Antes disso o app não conclui que está sozinho. Quem tinha a região antiga padrão no `config.json` é migrado automaticamente; uma região editada à mão é mantida.
- **"Sozinho" sem recorte** é decidido pelas barras de vida e escudo coloridas dos colegas. Só vale depois de o app ter visto pelo menos uma barra de colega na partida, para não sair por causa de uma região errada ou de um HUD diferente.
- **Revivido** = indicador de espectador sumido por 2 ciclos. O primeiro ciclo sem ele não basta, para não confundir com uma leitura falha.
- **Pesos padrão rebalanceados** para mais movimento (Esconder 1, Reposicionar 4, Rondar 3, Atirar 2, Coletar 1, Olhar 1). Quem estava com os pesos padrão antigos recebe os novos; pesos editados à mão são mantidos.
- **Agachar** é tratado como alternado por padrão (um toque agacha), configurável.
- **Leitura de texto (OCR)** com RapidOCR, que roda local e traz os modelos dentro do pacote (sem download na primeira execução). Foi escolhido no lugar do OCR do Windows porque dá para testar fora do Windows e vai embutido no .exe.
- **Fim de partida sem template**: inferido por Jogar novamente / Retornar ao lobby visível por 2 ciclos sem "Espectando", para não sair enquanto assiste a um colega.
- **"Loja Pirata" escrito na tela só conta junto do aviso "Você encontrou"**, porque o lobby pode mostrar a loja do evento.
- **Templates extras** além dos 12: `fechar`, `tesouro_encontrado`, `aviso_encontrou` e os sete tipos de recompensa, todos opcionais.
- **Modo Ensaio** foi acrescentado além da Simulação pedida.
- **`config.json` fica fora do git**: é criado com os padrões na primeira execução. Arquivo corrompido é renomeado para `config.invalido.json` e os padrões voltam.
- **F8** alterna: parado inicia em modo real, rodando para tudo.

## Desenvolvimento

```
pip install -r requirements-dev.txt
python -m pytest -q
cd frontend && npm run build
```

Os testes usam imagens sintéticas e as implementações dry-run de input e foco, então rodam em qualquer sistema. A arquitetura e as regras do projeto estão em [CLAUDE.md](CLAUDE.md).

### O que os testes cobrem e o que só dá para validar com o jogo

Coberto por testes automáticos: detecção (escala, offset do monitor, contagem sem sobreposição, templates ausentes ou inválidos), toda a ordem de prioridade da máquina de estados, salto atrasado, comportamentos de movimento, saída pelo ESC, captura e classificação de recompensas, fluxo do Acesso à Loja Pirata, modo simulação, API e WebSocket.

Só dá para validar no seu PC, com o jogo aberto: se os seus recortes casam com as telas reais, se o pydirectinput entrega teclado e mouse ao jogo, a detecção de foco pelo título da janela, a captura em tela cheia em janela, os tempos reais do ônibus e do planeio, se o input mínimo ao espectar evita a expulsão, o atalho F8 global, a janela do pywebview e o som do alerta. Comece pelo modo Ensaio.
