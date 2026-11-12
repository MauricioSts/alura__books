"""Máquina de estados: decide, a cada ciclo, o que fazer com o que está na tela.

Ordem de prioridade do ciclo:
1. jogo fora de foco: pausa, sem input;
2. recompensa na tela: print, clique em Resgatar, print de novo;
3. tela de fim: Jogar novamente ou Retornar ao lobby;
4. botão Jogar do lobby;
5. pop-up com Continuar ou Fechar;
6. aviso do ônibus: agenda o salto;
7. tempo máximo de partida: sai pelo menu ESC;
8. só o bot vivo: sai pelo menu ESC;
9. movimento anti-inatividade (feito em animar(), entre um ciclo e outro).
"""
from __future__ import annotations

import random
from enum import Enum
from typing import Callable

import cv2

from .captura import Quadro
from .catalogo import NAO_IDENTIFICADA, TIPOS_RECOMPENSA
from .comportamentos import GerenciadorMovimento
from .config import Config
from .deteccao import Achado, Detector, Preparado
from .entrada import Entrada
from .foco import Foco
from .recompensas import PIRATA, ArquivoRecompensas
from .registro import Registro
from .visao import contar_companheiros_vivos, diferenca, linhas_de_barras, miniatura_cenario


class Fase(str, Enum):
    LOBBY = "lobby"
    FILA = "fila"
    ONIBUS = "onibus"
    PLANANDO = "planando"
    EM_PARTIDA = "em_partida"
    ESPECTANDO = "espectando"
    SAINDO = "saindo"


EM_JOGO = (Fase.ONIBUS, Fase.PLANANDO, Fase.EM_PARTIDA, Fase.ESPECTANDO)
BOTOES_RESGATE = ("resgatar_tudo", "resgatar")
TELAS_RECOMPENSA = ("acesso_pirata", "tesouro_encontrado", "aviso_encontrou")
TENTATIVAS_SAIDA = 4
BLOQUEIO_SAIDA_S = 60.0


class Maquina:
    def __init__(self, cfg: Config, detector: Detector, entrada: Entrada, foco: Foco,
                 registro: Registro, recompensas: ArquivoRecompensas | None = None,
                 rng: random.Random | None = None, sessao: str = "",
                 ao_recompensa: Callable[[dict], None] | None = None):
        self.cfg = cfg
        self.detector = detector
        self.entrada = entrada
        self.foco = foco
        self.log = registro
        self.recompensas = recompensas
        self.rng = rng or random.Random()
        self.sessao = sessao
        self.ao_recompensa = ao_recompensa
        self.movimento = GerenciadorMovimento(entrada, cfg.movimento, self.rng)

        self.fase = Fase.LOBBY
        self.pausado = False
        self.partidas = 0
        self.tesouros = 0
        self.por_tipo: dict[str, int] = {}
        self.inicio_partida: float | None = None
        self.pedido_parada: str | None = None

        self._ultimo_clique = -1e9
        self._t_jogar = -1e9
        self._t_fila = 0.0
        self._fila_pendente = False
        self._salto_agendado = False
        self._t_salto = 0.0
        self._t_planador: float | None = None
        self._fim_planar = 0.0
        self._t_espectador = 0.0
        self._ciclos_sozinho = 0
        self._viu_companheiros = False
        self._y_proprio: int | None = None
        self._ciclos_sem_espectar = 0
        self._ciclos_parado = 0
        self._miniatura = None
        self._inicio_planar = 0.0
        self._ciclos_fim = 0
        self._saida_passo = 0
        self._saida_tentativas = 0
        self._saida_bloqueada_ate = -1e9
        # Só há movimento depois de um ciclo que viu a tela livre de botões e telas de recompensa.
        self._tela_livre = False
        self._aviso_ativo = False
        self._cinza_recompensa = None
        self._depois_pendente: str | None = None
        self._parar_apos_depois = False
        self._avisos_dados: set[str] = set()

    # ------------------------------------------------------------------ utilidades
    def tempo_partida(self, agora: float) -> float:
        return max(0.0, agora - self.inicio_partida) if self.inicio_partida is not None else 0.0

    def _avisar_uma_vez(self, chave: str, msg: str) -> None:
        if chave not in self._avisos_dados:
            self._avisos_dados.add(chave)
            self.log.aviso(msg)

    def _interromper(self) -> None:
        """Para qualquer movimento em curso e solta todas as teclas."""
        self.movimento.abandonar()
        self.entrada.soltar_tudo()

    def _checar_foco(self) -> bool:
        if self.foco.em_foco():
            if self.pausado:
                self.pausado = False
                self.log.info("Jogo em foco de novo, retomando.")
            return True
        if not self.pausado:
            self.pausado = True
            # Único efeito ao perder o foco: soltar o que estava pressionado.
            self._interromper()
            self.log.aviso("Jogo fora de foco: pausado, nenhum input será enviado.")
        return False

    def _clicar(self, achado: Achado, agora: float, descricao: str) -> bool:
        if agora - self._ultimo_clique < self.cfg.automacao.cooldown_clique_s:
            return False
        self._interromper()
        self._tela_livre = False
        self.entrada.clicar(achado.x, achado.y)
        self._ultimo_clique = agora
        self.log.info(f"Clique em {descricao} ({achado.x}, {achado.y}), score {achado.score:.2f}.")
        return True

    def _primeiro(self, prep: Preparado, nomes, limiar: float | None = None) -> Achado | None:
        for nome in nomes:
            achado = self.detector.localizar(prep, nome, limiar)
            if achado:
                return achado
        return None

    def _encerrar_partida(self) -> None:
        self._interromper()
        self.movimento.nova_partida()
        self._viu_companheiros = False
        self._y_proprio = None
        self._fila_pendente = False
        self._salto_agendado = False
        self._t_planador = None
        self._ciclos_sozinho = 0
        self.inicio_partida = None

    def _nova_partida(self, agora: float, fase: Fase) -> None:
        if not self._fila_pendente:
            self.partidas += 1
            self.log.info(f"Partida nº {self.partidas}.")
        self._fila_pendente = True
        self._salto_agendado = False
        self._ciclos_sozinho = 0
        self.movimento.nova_partida()
        self.inicio_partida = agora
        self._t_fila = agora
        self.fase = fase

    # ------------------------------------------------------------------ ciclo principal
    def tick(self, quadro: Quadro, agora: float) -> None:
        """Um ciclo completo: olha a tela e age conforme a prioridade."""
        self._tela_livre = False
        if not self._checar_foco():
            return
        prep = self.detector.preparar(quadro)

        if self._depois_pendente:
            self._salvar_depois(quadro)
            if self.pedido_parada:
                return
        if self._tratar_recompensa(quadro, prep, agora):
            return
        if self._tratar_fim(prep, agora):
            return
        if self._tratar_lobby(prep, agora):
            return
        if self._tratar_popup(prep, agora):
            return
        if self.fase == Fase.SAINDO:
            self._passo_saida(prep, agora)
            return
        self._tratar_onibus(prep, agora)

        if self.fase == Fase.FILA and agora - self._t_fila >= self.cfg.automacao.tempo_fila_max_s:
            self.log.info("Aviso do ônibus não foi visto; assumindo partida em andamento.")
            self.fase = Fase.EM_PARTIDA

        if self.fase in (Fase.EM_PARTIDA, Fase.ESPECTANDO, Fase.PLANANDO):
            espectando = self.detector.localizar(prep, "espectando") is not None
            if espectando and self.fase != Fase.ESPECTANDO:
                self._interromper()
                self.movimento.nova_partida()  # a postura (agachado) zera ao morrer
                self.fase = Fase.ESPECTANDO
                self._t_espectador = agora
                self._ciclos_sem_espectar = 0
                self.log.info("Bot eliminado: espectando um companheiro.")
            elif self.fase == Fase.ESPECTANDO:
                self._ciclos_sem_espectar = 0 if espectando else self._ciclos_sem_espectar + 1
                if self._ciclos_sem_espectar >= 2:
                    self._renascer(agora)

        self._checar_preso(quadro, agora)

        if self.fase in EM_JOGO and agora >= self._saida_bloqueada_ate:
            limite = self.cfg.automacao.tempo_max_partida_min * 60
            if limite > 0 and self.tempo_partida(agora) >= limite:
                self._iniciar_saida(agora, "tempo máximo de partida atingido")
                return
            self._checar_sozinho(prep, agora)
        self._tela_livre = self.fase != Fase.SAINDO

    def animar(self, agora: float) -> None:
        """Chamado várias vezes por segundo, entre os ciclos: executa salto e movimento."""
        if not self._checar_foco():
            return
        if self.fase == Fase.ONIBUS:
            if agora >= self._t_salto:
                self._saltar(agora)
        elif self.fase == Fase.PLANANDO:
            if not self._tela_livre:
                self.entrada.tecla_cima("w")  # algo na frente: espera a tela liberar
                return
            self.entrada.tecla_baixo("w")
            if self._t_planador is not None and agora >= self._t_planador:
                self._t_planador = None
                self.entrada.tocar("space")
                self.log.info("Planador aberto cedo.")
            if agora >= self._fim_planar:
                self.entrada.tecla_cima("w")
                self.fase = Fase.EM_PARTIDA
                self.log.info("Fim do planeio: iniciando movimentação em partida.")
        elif not self._tela_livre:
            return  # há um botão ou tela na frente: nada de movimento por cima da interface
        elif self.fase == Fase.EM_PARTIDA:
            novo = self.movimento.passo(agora)
            if novo:
                self.log.info(f"Comportamento: {novo}.")
        elif self.fase == Fase.ESPECTANDO:
            # Espectando: só o mínimo de input para não ser expulso.
            if agora - self._t_espectador >= self.cfg.movimento.intervalo_espectando_s:
                self._t_espectador = agora
                self.entrada.mover_mouse_rel(self.rng.choice((-1, 1)) * self.rng.randint(8, 25), 0)

    def parar(self) -> None:
        self._interromper()

    # ------------------------------------------------------------------ recompensas
    def _tratar_recompensa(self, quadro: Quadro, prep: Preparado, agora: float) -> bool:
        botao = self._primeiro(prep, BOTOES_RESGATE)
        # "Loja Pirata" escrito na tela não basta por texto (o lobby pode mostrar a loja do evento):
        # por texto, o gatilho é o aviso "Você encontrou".
        telas = [n for n in TELAS_RECOMPENSA
                 if not (n == "acesso_pirata" and self.detector.por_texto(n))]
        tela = self._primeiro(prep, telas, self.cfg.deteccao.limiar_recompensa)
        if not botao and not tela:
            self._aviso_ativo = False
            self._cinza_recompensa = None
            return False
        if botao:
            if agora - self._ultimo_clique < self.cfg.automacao.cooldown_clique_s:
                return True
            if self._mesma_tela(prep):
                # O clique anterior não fechou a tela: clica de novo sem contar outro tesouro.
                self._clicar(botao, agora, "Resgatar (de novo)")
                return True
            self._cinza_recompensa = prep.cinza
            # O print é salvo ANTES do clique; o seguinte vem no próximo ciclo.
            item = self._registrar_recompensa(quadro, prep, botao.nome)
            self._clicar(botao, agora, "Resgatar tudo" if botao.nome == "resgatar_tudo" else "Resgatar")
            self._depois_pendente = item.get("id")
            self._aviso_ativo = True
            if item["tipo"] == PIRATA and self.cfg.automacao.apos_acesso_pirata == "parar":
                self._parar_apos_depois = True
                if not self._depois_pendente:
                    self.pedido_parada = "Acesso à Loja Pirata resgatado"
            return True
        if not self._aviso_ativo:
            # Tela ou aviso sem botão: registra uma vez só enquanto estiver visível.
            self._aviso_ativo = True
            item = self._registrar_recompensa(quadro, prep, tela.nome)
            if item["tipo"] == PIRATA and self.cfg.automacao.apos_acesso_pirata == "parar":
                self.pedido_parada = "Acesso à Loja Pirata encontrado"
                return True
        return False

    def _mesma_tela(self, prep: Preparado) -> bool:
        """True se a tela é praticamente idêntica à da última recompensa registrada."""
        anterior = self._cinza_recompensa
        if anterior is None or anterior.shape != prep.cinza.shape:
            return False
        mudou = cv2.absdiff(anterior, prep.cinza) > 30
        return float(mudou.mean()) < 0.001  # menos de 0,1% dos pixels mudou

    def _registrar_recompensa(self, quadro: Quadro, prep: Preparado, gatilho: str) -> dict:
        tipo, score = self.detector.classificar(
            prep, TIPOS_RECOMPENSA, self.cfg.deteccao.limiar_recompensa)
        tipo = tipo or NAO_IDENTIFICADA
        self.tesouros += 1
        self.por_tipo[tipo] = self.por_tipo.get(tipo, 0) + 1
        if self.recompensas:
            alertar = tipo == NAO_IDENTIFICADA and self.cfg.automacao.alertar_nao_identificada
            item = self.recompensas.registrar(quadro, tipo, score, self.partidas, self.sessao,
                                              gatilho, alertar)
        else:
            item = {"id": None, "tipo": tipo, "partida": self.partidas}
        if tipo == PIRATA:
            self.log.destaque("ACESSO À LOJA PIRATA ENCONTRADO! Print salvo.")
        else:
            self.log.destaque(f"Recompensa capturada: {tipo} (gatilho: {gatilho}).")
        if self.ao_recompensa:
            self.ao_recompensa(item)
        return item

    def _salvar_depois(self, quadro: Quadro) -> None:
        ident, self._depois_pendente = self._depois_pendente, None
        if self.recompensas and ident:
            item = self.recompensas.anexar_depois(ident, quadro)
            if item and self.ao_recompensa:
                self.ao_recompensa(item)
        if self._parar_apos_depois:
            self._parar_apos_depois = False
            self.pedido_parada = "Acesso à Loja Pirata resgatado"

    # ------------------------------------------------------------------ telas e botões
    def _fim_inferido(self, prep: Preparado) -> bool:
        """Sem template de fim: Jogar novamente / Retornar ao lobby sem estar espectando, 2 ciclos."""
        if self.detector.tem("fim_partida") or self.fase in (Fase.LOBBY, Fase.FILA):
            self._ciclos_fim = 0
            return False
        botao = self._primeiro(prep, ("jogar_novamente", "retornar_lobby"))
        if botao and not self.detector.localizar(prep, "espectando"):
            self._ciclos_fim += 1
        else:
            self._ciclos_fim = 0
        return self._ciclos_fim >= 2

    def _tratar_fim(self, prep: Preparado, agora: float) -> bool:
        if not self.detector.localizar(prep, "fim_partida") and not self._fim_inferido(prep):
            return False
        de_novo = self.detector.localizar(prep, "jogar_novamente")
        if de_novo:
            if self._clicar(de_novo, agora, "Jogar novamente"):
                self._encerrar_partida()
                self._nova_partida(agora, Fase.FILA)
            return True
        lobby = self.detector.localizar(prep, "retornar_lobby")
        if lobby:
            if self._clicar(lobby, agora, "Retornar ao lobby"):
                self._encerrar_partida()
                self.fase = Fase.LOBBY
            return True
        self._interromper()
        self._avisar_uma_vez("fim_sem_botao", "Tela de fim detectada, mas sem template de "
                             "Jogar novamente nem Retornar ao lobby visível.")
        return True

    def _tratar_lobby(self, prep: Preparado, agora: float) -> bool:
        jogar = self.detector.localizar(prep, "jogar")
        if not jogar:
            return False
        if self.fase not in (Fase.LOBBY, Fase.FILA):
            self.log.info("De volta ao lobby.")
            self._encerrar_partida()
            self.fase = Fase.LOBBY
        if agora - self._t_jogar < self.cfg.automacao.cooldown_jogar_s:
            return True
        if self._clicar(jogar, agora, "Jogar"):
            self._t_jogar = agora
            self._nova_partida(agora, Fase.FILA)
        return True

    def _tratar_popup(self, prep: Preparado, agora: float) -> bool:
        botao = self._primeiro(prep, ("continuar", "fechar"))
        if not botao:
            return False
        self._clicar(botao, agora, "Continuar" if botao.nome == "continuar" else "Fechar")
        return True

    # ------------------------------------------------------------------ ônibus e salto
    def _tratar_onibus(self, prep: Preparado, agora: float) -> None:
        if self._salto_agendado or self.fase not in (Fase.LOBBY, Fase.FILA, Fase.EM_PARTIDA):
            return
        if self.fase == Fase.LOBBY and self.detector.por_texto("pular_onibus"):
            return  # "PULAR" escrito no lobby (vídeos, avisos) não é o ônibus
        if not self.detector.localizar(prep, "pular_onibus"):
            return
        if self.fase == Fase.LOBBY:
            # O app foi iniciado com a partida já carregando.
            self._nova_partida(agora, Fase.ONIBUS)
        self._interromper()
        menor, maior = sorted((self.cfg.salto.atraso_min_s, self.cfg.salto.atraso_max_s))
        atraso = self.rng.uniform(menor, maior)
        self._salto_agendado = True
        self._t_salto = agora + atraso
        self.fase = Fase.ONIBUS
        self.log.info(f"Ônibus liberado: salto em {atraso:.0f}s, no trecho final da rota.")

    def _saltar(self, agora: float) -> None:
        salto = self.cfg.salto
        lado = self.rng.choice((-1, 1))
        self.entrada.tocar("space")
        self.entrada.mover_mouse_rel(lado * salto.angulo_graus * self.cfg.movimento.pixels_por_grau, 0)
        self.entrada.tecla_baixo("w")
        self._t_planador = agora + 1.2 if salto.abrir_planador_cedo else None
        self._fim_planar = agora + salto.tempo_planando_s
        self._inicio_planar = agora
        self.fase = Fase.PLANANDO
        self.log.info(f"Salto: câmera {salto.angulo_graus:.0f}° para a "
                      f"{'direita' if lado > 0 else 'esquerda'}, planando para longe da rota.")

    def _renascer(self, agora: float) -> None:
        """O espectador sumiu por 2 ciclos: o bot foi revivido e cai do céu de novo."""
        self._interromper()
        self.movimento.nova_partida()
        self._ciclos_sem_espectar = 0
        self.entrada.tecla_baixo("w")
        self._t_planador = agora + 1.0  # abre o planador logo
        self._fim_planar = agora + self.cfg.salto.tempo_planando_renascer_s
        self._inicio_planar = agora
        self.fase = Fase.PLANANDO
        self.log.destaque("Bot revivido: segurando W e abrindo o planador.")

    # ------------------------------------------------------------------ preso em obstáculo
    def _checar_preso(self, quadro: Quadro, agora: float) -> None:
        """Se o cenário não muda enquanto o bot anda, ele está preso: desvia (ou termina o pouso)."""
        mini = miniatura_cenario(quadro.imagem)
        mudanca = diferenca(self._miniatura, mini)
        self._miniatura = mini
        limiar = self.cfg.movimento.limiar_preso
        andando = (self.fase == Fase.EM_PARTIDA and self.movimento.andando) or (
            self.fase == Fase.PLANANDO and agora - self._inicio_planar >= 12)
        if not andando or mudanca >= limiar:
            self._ciclos_parado = 0
            return
        self._ciclos_parado += 1
        if self._ciclos_parado < 2:
            return
        self._ciclos_parado = 0
        if self.fase == Fase.PLANANDO:
            self.entrada.tecla_cima("w")
            self._t_planador = None
            self.fase = Fase.EM_PARTIDA
            self.log.info("Já no chão e parado: encerrando o planeio e começando a se mover.")
        else:
            self.movimento.desviar(agora)
            self.log.info("Preso em obstáculo (tela parada): pulando e mudando de direção.")

    # ------------------------------------------------------------------ saída pelo menu ESC
    def _checar_sozinho(self, prep: Preparado, agora: float) -> None:
        auto = self.cfg.automacao
        if self.fase != Fase.EM_PARTIDA or not auto.sair_quando_sozinho:
            self._ciclos_sozinho = 0
            return
        if self.detector.tem("companheiro_morto"):
            mortos = self.detector.contar(prep, "companheiro_morto", self.cfg.deteccao.regiao_squad)
            sozinho = mortos >= auto.num_companheiros
        elif self.cfg.deteccao.barras_vida and prep.original is not None:
            regiao = self.cfg.deteccao.regiao_squad
            if self.cfg.deteccao.ignorar_barra_propria:
                if self._y_proprio is None:
                    linhas = linhas_de_barras(prep.original, regiao)
                    if len(linhas) < 2:
                        return  # ainda não dá para separar a barra do bot das dos colegas
                    # A do bot é a mais baixa da lista (fica embaixo dos colegas).
                    self._y_proprio = linhas[-1]
                    self.log.info(f"Barra do próprio bot identificada; {len(linhas) - 1} colega(s) na squad.")
                vivos = contar_companheiros_vivos(prep.original, regiao, self._y_proprio)
            else:
                vivos = contar_companheiros_vivos(prep.original, regiao)
            if vivos:
                self._viu_companheiros = True
            # Só conclui "sozinho" se já tinha visto barras de colegas nesta partida.
            sozinho = self._viu_companheiros and vivos == 0
        else:
            return
        self._ciclos_sozinho = self._ciclos_sozinho + 1 if sozinho else 0
        if self._ciclos_sozinho >= auto.ciclos_sozinho:
            self._iniciar_saida(agora, "todos os companheiros eliminados, sobrou só o bot")

    def _iniciar_saida(self, agora: float, motivo: str) -> None:
        if not (self.detector.disponivel("sair_partida") and self.detector.disponivel("confirmar_sair")):
            self._avisar_uma_vez("saida_sem_template", "Não dá para sair pelo menu: faltam os "
                                 "templates sair_partida e/ou confirmar_sair (e a leitura de texto está desligada).")
            self._saida_bloqueada_ate = agora + BLOQUEIO_SAIDA_S
            return
        self.log.info(f"Saindo da partida: {motivo}.")
        self._interromper()
        self.fase = Fase.SAINDO
        self._saida_passo = 1
        self._saida_tentativas = 0
        self.entrada.tocar("esc")

    def _passo_saida(self, prep: Preparado, agora: float) -> None:
        nome, rotulo = (("sair_partida", "Sair"), ("confirmar_sair", "Confirmar"))[self._saida_passo - 1]
        achado = self.detector.localizar(prep, nome)
        if not achado:
            self._saida_tentativas += 1
            if self._saida_tentativas >= TENTATIVAS_SAIDA:
                self.log.aviso(f"Botão {rotulo} não apareceu; desistindo da saída por enquanto.")
                self.entrada.tocar("esc")
                self.fase = Fase.EM_PARTIDA
                self._ciclos_sozinho = 0
                self._saida_bloqueada_ate = agora + BLOQUEIO_SAIDA_S
            return
        if not self._clicar(achado, agora, rotulo):
            return  # ainda no cooldown de clique; tenta no próximo ciclo
        self._saida_tentativas = 0
        if self._saida_passo == 1:
            self._saida_passo = 2
        else:
            self._encerrar_partida()
            self.fase = Fase.LOBBY
            self.log.info("Saída confirmada; aguardando o lobby.")
