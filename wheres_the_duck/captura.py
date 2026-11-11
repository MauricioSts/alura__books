"""Captura de tela atrás de uma interface, com implementação real (mss) e de simulação (pasta)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class Quadro:
    """Imagem BGR e a posição do monitor na área de trabalho virtual."""

    imagem: np.ndarray
    offset_x: int = 0
    offset_y: int = 0
    origem: str = ""


class Capturador(ABC):
    @abstractmethod
    def capturar(self) -> Quadro | None:
        """Devolve o próximo quadro, ou None quando não há mais o que capturar."""


class CapturadorTela(Capturador):
    """Captura um monitor com mss (o mesmo que um print de tela)."""

    def __init__(self, monitor: int = 1):
        self.monitor = monitor

    def capturar(self) -> Quadro | None:
        import mss  # importado aqui para os testes não dependerem de um display

        with mss.mss() as sct:
            indice = self.monitor if self.monitor < len(sct.monitors) else 1
            mon = sct.monitors[indice]
            bruto = np.asarray(sct.grab(mon))
        imagem = cv2.cvtColor(bruto, cv2.COLOR_BGRA2BGR)
        return Quadro(imagem, int(mon["left"]), int(mon["top"]), f"monitor {indice}")


class CapturadorPasta(Capturador):
    """Entrega, em ordem alfabética, as imagens de uma pasta (modo simulação)."""

    EXTENSOES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}

    def __init__(self, pasta: Path, repetir: int = 1):
        self.pasta = Path(pasta)
        if not self.pasta.is_dir():
            raise FileNotFoundError(f"Pasta de simulação não encontrada: {self.pasta}")
        self.arquivos = sorted(
            p for p in self.pasta.iterdir() if p.suffix.lower() in self.EXTENSOES
        )
        self.repetir = max(1, int(repetir))
        self._passo = 0

    @property
    def total(self) -> int:
        return len(self.arquivos) * self.repetir

    def capturar(self) -> Quadro | None:
        while self._passo < self.total:
            arq = self.arquivos[self._passo // self.repetir]
            self._passo += 1
            # imdecode em vez de imread para aceitar caminhos com acento no Windows
            imagem = cv2.imdecode(np.fromfile(str(arq), dtype=np.uint8), cv2.IMREAD_COLOR)
            if imagem is not None:
                return Quadro(imagem, 0, 0, arq.name)
        return None


def salvar_png(caminho: Path, imagem: np.ndarray) -> bool:
    """Grava um PNG aceitando caminhos com acento."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    ok, dados = cv2.imencode(".png", imagem)
    if ok:
        dados.tofile(str(caminho))
    return bool(ok)


def codificar_png(imagem: np.ndarray) -> bytes:
    ok, dados = cv2.imencode(".png", imagem)
    return dados.tobytes() if ok else b""
