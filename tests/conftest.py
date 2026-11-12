"""Fábrica de imagens sintéticas: templates com padrões de blocos e telas montadas com eles."""
from __future__ import annotations

import random
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wheres_the_duck import catalogo  # noqa: E402
from wheres_the_duck.captura import Quadro  # noqa: E402
from wheres_the_duck.config import Config  # noqa: E402
from wheres_the_duck.deteccao import Detector  # noqa: E402
from wheres_the_duck.entrada import EntradaSimulada  # noqa: E402
from wheres_the_duck.foco import FocoSimulado  # noqa: E402
from wheres_the_duck.maquina import Maquina  # noqa: E402
from wheres_the_duck.recompensas import ArquivoRecompensas  # noqa: E402
from wheres_the_duck.registro import Registro  # noqa: E402

LARGURA, ALTURA = 1280, 720


def padrao(nome: str, largura: int = 96, altura: int = 48) -> np.ndarray:
    """Padrão de blocos único por nome, parecido com um botão com texto."""
    rng = np.random.default_rng(abs(hash(nome)) % (2**32) if False else sum(map(ord, nome)) * 7919)
    blocos = rng.integers(0, 2, size=(altura // 8, largura // 8, 3), dtype=np.uint8) * 200 + 30
    return cv2.resize(blocos, (largura, altura), interpolation=cv2.INTER_NEAREST)


class Cena:
    """Guarda os templates em disco e monta telas com eles."""

    def __init__(self, pasta: Path, nomes=None):
        self.pasta = pasta
        pasta.mkdir(parents=True, exist_ok=True)
        self.imagens: dict[str, np.ndarray] = {}
        for nome in (catalogo.NOMES if nomes is None else nomes):
            tam = (24, 24) if nome == "companheiro_morto" else (96, 48)
            self.imagens[nome] = padrao(nome, *tam)
            cv2.imwrite(str(pasta / f"{nome}.png"), self.imagens[nome])

    def tela(self, *itens, offset=(0, 0)) -> Quadro:
        """Cada item é um nome (posição automática) ou (nome, x, y)."""
        img = np.full((ALTURA, LARGURA, 3), 40, np.uint8)
        # Um leve gradiente evita áreas totalmente chapadas.
        img[:, :, 1] += (np.arange(LARGURA) % 16).astype(np.uint8)
        livre = 0
        for item in itens:
            if isinstance(item, str):
                nome, x, y = item, 500 + 110 * (livre % 4), 300 + 70 * (livre // 4)
                livre += 1
            else:
                nome, x, y = item
            p = padrao(nome, 24, 24) if nome == "companheiro_morto" else padrao(nome)
            img[y:y + p.shape[0], x:x + p.shape[1]] = p
        return Quadro(img, offset[0], offset[1], "sintetico")

    def mortos(self, n: int):
        # Lista da squad no canto inferior esquerdo (região padrão).
        return [("companheiro_morto", 40, 420 + 50 * i) for i in range(n)]


class Banco:
    """Máquina montada com dry-run de input e de foco."""

    def __init__(self, tmp_path: Path, nomes=None, semente: int = 7, **ajustes):
        self.cena = Cena(tmp_path / "templates", nomes)
        self.cfg = Config()
        for caminho, valor in ajustes.items():
            secao, campo = caminho.split("__")
            setattr(getattr(self.cfg, secao), campo, valor)
        self.detector = Detector(self.cena.pasta, self.cfg.deteccao.escala, self.cfg.deteccao.limiar)
        self.entrada = EntradaSimulada()
        self.foco = FocoSimulado(True)
        self.registro = Registro()
        self.recompensas = ArquivoRecompensas(tmp_path / "capturas", tmp_path / "dados" / "rec.json")
        self.eventos: list[dict] = []
        self.maquina = Maquina(self.cfg, self.detector, self.entrada, self.foco, self.registro,
                               self.recompensas, rng=random.Random(semente), sessao="teste",
                               ao_recompensa=self.eventos.append)
        self.agora = 100.0

    def tick(self, *itens, dt: float = 1.5):
        self.agora += dt
        self.maquina.tick(self.cena.tela(*itens), self.agora)

    def animar(self, segundos: float, passo: float = 0.1):
        fim = self.agora + segundos
        while self.agora < fim:
            self.agora += passo
            self.maquina.animar(self.agora)

    def cliques(self):
        return [a for a in self.entrada.acoes if a[0] == "clicar"]

    def centro(self, indice: int = 0):
        """Centro do item colocado na posição automática de índice dado."""
        return 500 + 110 * indice + 48, 300 + 24


@pytest.fixture
def banco(tmp_path):
    return Banco(tmp_path)


@pytest.fixture
def cena(tmp_path):
    return Cena(tmp_path / "templates")
