"""Comportamentos de movimento em partida, sorteados com pesos e durações variáveis.

São deslocamentos, giros de câmera e tiros a esmo, todos feitos às cegas: nenhum mira,
procura inimigos, constrói ou segue jogadores.
"""
from __future__ import annotations

import random
from typing import Callable

from .config import Movimento
from .entrada import Entrada

TECLAS_ANDAR = ("w", "a", "s", "d")


class Postura:
    """Controla o agachar, que no jogo pode ser alternado (um toque) ou segurado."""

    def __init__(self, entrada: Entrada, cfg: Movimento):
        self.entrada = entrada
        self.cfg = cfg
        self.agachado = False

    def agachar(self) -> None:
        if not self.agachado:
            self.agachado = True
            if self.cfg.agachar_alternado:
                self.entrada.tocar(self.cfg.tecla_agachar)
            else:
                self.entrada.tecla_baixo(self.cfg.tecla_agachar)

    def levantar(self) -> None:
        if self.agachado:
            self.agachado = False
            if self.cfg.agachar_alternado:
                self.entrada.tocar(self.cfg.tecla_agachar)
            else:
                self.entrada.tecla_cima(self.cfg.tecla_agachar)

    def zerar(self) -> None:
        """Partida nova: o personagem começa em pé."""
        self.agachado = False


class Comportamento:
    nome = ""

    def __init__(self, entrada: Entrada, postura: Postura, cfg: Movimento, rng: random.Random):
        self.entrada = entrada
        self.postura = postura
        self.cfg = cfg
        self.rng = rng

    def girar(self, graus: float, vertical: float = 0.0) -> None:
        self.entrada.mover_mouse_rel(graus * self.cfg.pixels_por_grau, vertical * self.cfg.pixels_por_grau)

    anda = False  # segura tecla de movimento (pode ficar preso em obstáculo)

    def iniciar(self, agora: float) -> None: ...
    def passo(self, agora: float) -> None: ...
    def encerrar(self) -> None: ...

    def desviar(self, agora: float) -> None:
        """Chamado quando a tela parou de mudar enquanto o bot andava: está preso."""


class Esconder(Comportamento):
    """Agachado e parado, com pequenos ajustes de câmera."""

    nome = "esconder"

    def iniciar(self, agora):
        self.postura.agachar()
        self._proximo = agora + self.rng.uniform(4, 9)

    def passo(self, agora):
        if agora >= self._proximo:
            self.girar(self.rng.uniform(-6, 6), self.rng.uniform(-1.5, 1.5))
            self._proximo = agora + self.rng.uniform(4, 9)


class Reposicionar(Comportamento):
    """Vira para uma direção, corre alguns segundos e para."""

    nome = "reposicionar"
    anda = True

    def iniciar(self, agora):
        self.postura.levantar()
        self.girar(self.rng.choice((-1, 1)) * self.rng.uniform(30, 170))
        self.entrada.tecla_baixo(self.cfg.tecla_correr)
        self.entrada.tecla_baixo("w")
        self._proximo_pulo = agora + self.rng.uniform(1.5, 4)
        self._lateral: str | None = None
        self._fim_lateral = 0.0
        self._proxima_lateral = agora + self.rng.uniform(1.5, 3.5)

    def passo(self, agora):
        # Um pulo de vez em quando ajuda a não ficar preso em obstáculos baixos.
        if agora >= self._proximo_pulo:
            if self.rng.random() < 0.4:
                self.entrada.tocar("space")
            self._proximo_pulo = agora + self.rng.uniform(1.5, 4)
        # Desvios laterais curtos (A ou D) e pequenas correções de rumo.
        if self._lateral and agora >= self._fim_lateral:
            self.entrada.tecla_cima(self._lateral)
            self._lateral = None
        if not self._lateral and agora >= self._proxima_lateral:
            self._lateral = self.rng.choice(("a", "d"))
            self.entrada.tecla_baixo(self._lateral)
            self.girar(self.rng.uniform(-25, 25))
            self._fim_lateral = agora + self.rng.uniform(0.4, 1.2)
            self._proxima_lateral = agora + self.rng.uniform(2, 4.5)

    def desviar(self, agora):
        self.entrada.tocar("space")
        self.girar(self.rng.choice((-1, 1)) * self.rng.uniform(100, 170))
        self._proximo_pulo = agora + 0.8

    def encerrar(self):
        if self._lateral:
            self.entrada.tecla_cima(self._lateral)
        self.entrada.tecla_cima("w")
        self.entrada.tecla_cima(self.cfg.tecla_correr)
        self.girar(self.rng.uniform(-40, 40))


class Rondar(Comportamento):
    """Anda agachado em trajetos curtos, mudando de direção."""

    nome = "rondar"
    anda = True

    def iniciar(self, agora):
        self.postura.agachar()
        self._tecla = "w"
        self.entrada.tecla_baixo(self._tecla)
        self._proximo = agora + self.rng.uniform(1.2, 2.8)

    def passo(self, agora):
        if agora >= self._proximo:
            self.girar(self.rng.choice((-1, 1)) * self.rng.uniform(20, 90))
            self.entrada.tecla_cima(self._tecla)
            self._tecla = self.rng.choice(("w", "w", "a", "d", "s"))
            self.entrada.tecla_baixo(self._tecla)
            self._proximo = agora + self.rng.uniform(1.2, 2.8)

    def desviar(self, agora):
        self.entrada.tecla_cima(self._tecla)
        self.entrada.tocar("space")
        self.girar(self.rng.choice((-1, 1)) * self.rng.uniform(90, 180))
        self._tecla = self.rng.choice(("w", "a", "d"))
        self.entrada.tecla_baixo(self._tecla)
        self._proximo = agora + self.rng.uniform(1.2, 2.8)

    def encerrar(self):
        self.entrada.tecla_cima(self._tecla)


class Coletar(Comportamento):
    """Seleciona a picareta e bate no que estiver à frente."""

    nome = "coletar"

    def iniciar(self, agora):
        self.entrada.tocar(self.cfg.tecla_picareta)
        self.entrada.mouse_baixo()

    def encerrar(self):
        self.entrada.mouse_cima()


class Atirar(Comportamento):
    """Pega uma arma e dá rajadas curtas para direções aleatórias, andando. Não mira em nada."""

    nome = "atirar"
    anda = True

    def iniciar(self, agora):
        self.postura.levantar()
        self.entrada.tocar(self.rng.choice(self.cfg.teclas_armas))
        self._tecla = self.rng.choice(("w", "w", "a", "d"))
        self.entrada.tecla_baixo(self._tecla)
        self._fim_rajada = 0.0
        self._proxima = agora + self.rng.uniform(0.4, 1.2)
        self._proxima_troca = agora + self.rng.uniform(1.5, 3)

    def passo(self, agora):
        if self.entrada.mouse_pressionado and agora >= self._fim_rajada:
            self.entrada.mouse_cima()
            self._proxima = agora + self.rng.uniform(0.6, 2.0)
        if not self.entrada.mouse_pressionado and agora >= self._proxima:
            # Direção sorteada, sem olhar para alvo nenhum.
            self.girar(self.rng.uniform(-60, 60), self.rng.uniform(-3, 3))
            self.entrada.mouse_baixo()
            self._fim_rajada = agora + self.rng.uniform(0.2, 0.7)
        if agora >= self._proxima_troca:
            self.entrada.tecla_cima(self._tecla)
            self._tecla = self.rng.choice(("w", "w", "a", "d", "s"))
            self.entrada.tecla_baixo(self._tecla)
            self._proxima_troca = agora + self.rng.uniform(1.5, 3)

    def desviar(self, agora):
        self.entrada.tocar("space")
        self.girar(self.rng.choice((-1, 1)) * self.rng.uniform(90, 160))

    def encerrar(self):
        self.entrada.mouse_cima()
        self.entrada.tecla_cima(self._tecla)


class Olhar(Comportamento):
    """Giro lento de câmera, sem andar."""

    nome = "olhar"

    def iniciar(self, agora):
        self._velocidade = self.rng.choice((-1, 1)) * self.rng.uniform(15, 40)  # graus por segundo
        self._ultimo = agora

    def passo(self, agora):
        dt = min(0.5, max(0.0, agora - self._ultimo))
        self._ultimo = agora
        self.girar(self._velocidade * dt)


CLASSES = {c.nome: c for c in (Esconder, Reposicionar, Rondar, Coletar, Olhar, Atirar)}


class Contorno:
    """Manobra para contornar uma estrutura quando o bot fica preso.

    Recua (S), pula duas vezes (o jogo escala bordas baixas ao pular contra elas) e anda
    na diagonal para um lado. Se ficar preso de novo logo em seguida, tenta o outro lado
    virando 90°; na terceira, dá meia-volta.
    """

    def __init__(self, entrada: Entrada, pixels_por_grau: Callable[[], float], rng: random.Random):
        self.entrada = entrada
        self.ppg = pixels_por_grau
        self.rng = rng
        self._passos: list[tuple[float, Callable[[], None]]] = []
        self._seguidos = 0
        self._ultimo_fim = -1e9
        self._lado = "a"

    @property
    def ativo(self) -> bool:
        return bool(self._passos)

    def iniciar(self, agora: float) -> None:
        self._seguidos = self._seguidos + 1 if agora - self._ultimo_fim <= 6 else 1
        if self._seguidos == 1:
            self._lado = self.rng.choice(("a", "d"))
        else:
            self._lado = "d" if self._lado == "a" else "a"
        giro = 0.0
        if self._seguidos == 2:
            giro = 90 if self._lado == "d" else -90
        elif self._seguidos >= 3:
            giro = 180
            self._seguidos = 0
        lado = self._lado

        def recuar():
            for tecla in ("w", "a", "s", "d"):
                self.entrada.tecla_cima(tecla)
            self.entrada.tecla_baixo("s")

        def contornar():
            self.entrada.tecla_cima("s")
            if giro:
                self.entrada.mover_mouse_rel(giro * self.ppg(), 0)
            self.entrada.tocar("space")
            self.entrada.tecla_baixo("w")
            self.entrada.tecla_baixo(lado)

        self._passos = [
            (agora, recuar),
            (agora + 0.45, contornar),
            (agora + 0.65, lambda: self.entrada.tocar("space")),
            (agora + 1.6, lambda: self.entrada.tecla_cima(lado)),
        ]

    def passo(self, agora: float) -> bool:
        """Executa a manobra. True enquanto ela está em andamento."""
        while self._passos and agora >= self._passos[0][0]:
            _, acao = self._passos.pop(0)
            acao()
            if not self._passos:
                self._ultimo_fim = agora
        return self.ativo

    def cancelar(self) -> None:
        self._passos = []


class GerenciadorMovimento:
    """Sorteia um comportamento por vez e o executa até a duração sorteada acabar."""

    def __init__(self, entrada: Entrada, cfg: Movimento, rng: random.Random | None = None):
        self.entrada = entrada
        self.cfg = cfg
        self.rng = rng or random.Random()
        self.postura = Postura(entrada, cfg)
        self.atual: Comportamento | None = None
        self._fim = 0.0
        self.contorno = Contorno(entrada, lambda: self.cfg.pixels_por_grau, self.rng)

    @property
    def nome_atual(self) -> str:
        return self.atual.nome if self.atual else ""

    @property
    def andando(self) -> bool:
        return bool(self.atual and self.atual.anda)

    def desviar(self, agora: float) -> None:
        if self.atual and self.atual.anda:
            self.entrada.mouse_cima()
            self.contorno.iniciar(agora)

    def _sortear(self) -> tuple[Comportamento, float]:
        nomes = list(CLASSES)
        pesos = [getattr(self.cfg, n).peso for n in nomes]
        nome = self.rng.choices(nomes, weights=pesos)[0] if sum(pesos) > 0 else "olhar"
        faixa = getattr(self.cfg, nome)
        menor, maior = sorted((faixa.duracao_min_s, faixa.duracao_max_s))
        duracao = self.rng.uniform(menor, maior)
        if nome == "esconder":
            # Ficar parado sempre abaixo do limite de inatividade, com folga.
            duracao = min(duracao, self.cfg.limite_inatividade_s * 0.8)
        return CLASSES[nome](self.entrada, self.postura, self.cfg, self.rng), duracao

    def passo(self, agora: float) -> str | None:
        """Avança o comportamento atual. Devolve o nome quando um novo começa."""
        if self.contorno.passo(agora):
            return None  # contornando um obstáculo: o comportamento espera
        novo = None
        if self.atual is None or agora >= self._fim:
            if self.atual:
                self.atual.encerrar()
            self.atual, duracao = self._sortear()
            self._fim = agora + duracao
            self.atual.iniciar(agora)
            novo = f"{self.atual.nome} ({duracao:.0f}s)"
        self.atual.passo(agora)
        return novo

    def abandonar(self) -> None:
        """Interrompe sem enviar nenhum toque; quem chama solta as teclas."""
        self.atual = None
        self.contorno.cancelar()

    def nova_partida(self) -> None:
        self.atual = None
        self.postura.zerar()
