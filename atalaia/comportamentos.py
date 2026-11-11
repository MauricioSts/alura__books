"""Comportamentos de movimento em partida, sorteados com pesos e durações variáveis.

Nenhum deles atira, constrói ou segue jogadores: são só deslocamentos e giros de câmera
feitos às cegas para o jogo não expulsar por inatividade.
"""
from __future__ import annotations

import random

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

    def iniciar(self, agora: float) -> None: ...
    def passo(self, agora: float) -> None: ...
    def encerrar(self) -> None: ...


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

    def iniciar(self, agora):
        self.postura.levantar()
        self.girar(self.rng.choice((-1, 1)) * self.rng.uniform(30, 170))
        self.entrada.tecla_baixo(self.cfg.tecla_correr)
        self.entrada.tecla_baixo("w")
        self._proximo_pulo = agora + self.rng.uniform(1.5, 4)

    def passo(self, agora):
        # Um pulo de vez em quando ajuda a não ficar preso em obstáculos baixos.
        if agora >= self._proximo_pulo:
            if self.rng.random() < 0.4:
                self.entrada.tocar("space")
            self._proximo_pulo = agora + self.rng.uniform(1.5, 4)

    def encerrar(self):
        self.entrada.tecla_cima("w")
        self.entrada.tecla_cima(self.cfg.tecla_correr)
        self.girar(self.rng.uniform(-40, 40))


class Rondar(Comportamento):
    """Anda agachado em trajetos curtos, mudando de direção."""

    nome = "rondar"

    def iniciar(self, agora):
        self.postura.agachar()
        self._tecla = "w"
        self.entrada.tecla_baixo(self._tecla)
        self._proximo = agora + self.rng.uniform(1.2, 2.8)

    def passo(self, agora):
        if agora >= self._proximo:
            self.girar(self.rng.choice((-1, 1)) * self.rng.uniform(20, 90))
            self.entrada.tecla_cima(self._tecla)
            self._tecla = self.rng.choice(("w", "w", "a", "d"))
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


CLASSES = {c.nome: c for c in (Esconder, Reposicionar, Rondar, Coletar, Olhar)}


class GerenciadorMovimento:
    """Sorteia um comportamento por vez e o executa até a duração sorteada acabar."""

    def __init__(self, entrada: Entrada, cfg: Movimento, rng: random.Random | None = None):
        self.entrada = entrada
        self.cfg = cfg
        self.rng = rng or random.Random()
        self.postura = Postura(entrada, cfg)
        self.atual: Comportamento | None = None
        self._fim = 0.0

    @property
    def nome_atual(self) -> str:
        return self.atual.nome if self.atual else ""

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

    def nova_partida(self) -> None:
        self.atual = None
        self.postura.zerar()
