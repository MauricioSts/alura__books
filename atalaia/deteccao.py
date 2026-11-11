"""Detecção por template matching (TM_CCOEFF_NORMED em escala de cinza)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .captura import Quadro


@dataclass
class Achado:
    nome: str
    score: float
    x: int  # centro, em coordenadas absolutas de tela
    y: int
    largura: int
    altura: int


@dataclass
class Preparado:
    """Quadro já reduzido e em cinza, pronto para vários matches no mesmo ciclo."""

    cinza: np.ndarray
    escala: float
    offset_x: int
    offset_y: int


class Detector:
    def __init__(self, pasta: Path, escala: float = 0.5, limiar: float = 0.82):
        self.pasta = Path(pasta)
        self.escala = escala
        self.limiar = limiar
        self._templates: dict[str, np.ndarray] = {}
        self.recarregar()

    def recarregar(self) -> None:
        """Lê os PNGs da pasta e reduz cada um pela mesma escala usada na tela."""
        novos: dict[str, np.ndarray] = {}
        if not self.pasta.is_dir():
            self._templates = novos
            return
        for arq in sorted(self.pasta.glob("*.png")):
            try:
                img = cv2.imdecode(np.fromfile(str(arq), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
            except OSError:
                img = None
            if img is None or img.size == 0:
                continue
            reduzido = self._reduzir(img)
            # Template sem variação (cor chapada) não serve para correlação normalizada.
            if reduzido.shape[0] < 4 or reduzido.shape[1] < 4 or float(reduzido.std()) < 1.0:
                continue
            novos[arq.stem] = reduzido
        self._templates = novos  # troca de uma vez: o motor pode estar lendo em outra thread

    def _reduzir(self, img: np.ndarray) -> np.ndarray:
        if self.escala >= 0.999:
            return img
        return cv2.resize(img, None, fx=self.escala, fy=self.escala, interpolation=cv2.INTER_AREA)

    def tem(self, nome: str) -> bool:
        return nome in self._templates

    def nomes(self) -> list[str]:
        return list(self._templates)

    def preparar(self, quadro: Quadro) -> Preparado:
        img = quadro.imagem
        cinza = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
        return Preparado(self._reduzir(cinza), self.escala, quadro.offset_x, quadro.offset_y)

    @staticmethod
    def _mapa(cinza: np.ndarray, tpl: np.ndarray) -> np.ndarray | None:
        if tpl.shape[0] > cinza.shape[0] or tpl.shape[1] > cinza.shape[1]:
            return None
        mapa = cv2.matchTemplate(cinza, tpl, cv2.TM_CCOEFF_NORMED)
        # Áreas chapadas da tela geram NaN/inf na correlação normalizada.
        return np.nan_to_num(mapa, nan=0.0, posinf=0.0, neginf=0.0)

    def pontuar(self, prep: Preparado, nome: str) -> Achado | None:
        """Melhor ocorrência do template, sem aplicar limiar. None se o template não existe."""
        tpl = self._templates.get(nome)
        if tpl is None:
            return None
        mapa = self._mapa(prep.cinza, tpl)
        if mapa is None:
            return None
        _, score, _, (mx, my) = cv2.minMaxLoc(mapa)
        th, tw = tpl.shape[:2]
        # Volta da imagem reduzida para a tela e soma o offset do monitor.
        cx = int(round((mx + tw / 2) / prep.escala)) + prep.offset_x
        cy = int(round((my + th / 2) / prep.escala)) + prep.offset_y
        return Achado(nome, float(score), cx, cy, int(tw / prep.escala), int(th / prep.escala))

    def localizar(self, prep: Preparado, nome: str, limiar: float | None = None) -> Achado | None:
        achado = self.pontuar(prep, nome)
        if achado and achado.score >= (self.limiar if limiar is None else limiar):
            return achado
        return None

    def contar(self, prep: Preparado, nome: str, regiao: list[float] | None = None,
               limiar: float | None = None, maximo: int = 12) -> int:
        """Conta ocorrências do template numa região (frações da tela), sem contar sobreposições."""
        tpl = self._templates.get(nome)
        if tpl is None:
            return 0
        cinza = prep.cinza
        if regiao:
            h, w = cinza.shape[:2]
            x0 = int(max(0.0, min(1.0, regiao[0])) * w)
            y0 = int(max(0.0, min(1.0, regiao[1])) * h)
            x1 = int(max(0.0, min(1.0, regiao[0] + regiao[2])) * w)
            y1 = int(max(0.0, min(1.0, regiao[1] + regiao[3])) * h)
            cinza = cinza[y0:y1, x0:x1]
        mapa = self._mapa(cinza, tpl)
        if mapa is None:
            return 0
        corte = self.limiar if limiar is None else limiar
        th, tw = tpl.shape[:2]
        total = 0
        while total < maximo:
            _, score, _, (mx, my) = cv2.minMaxLoc(mapa)
            if score < corte:
                break
            total += 1
            # Apaga a vizinhança do pico: qualquer match que se sobreponha a este é descartado.
            mapa[max(0, my - th + 1): my + th, max(0, mx - tw + 1): mx + tw] = -1.0
        return total

    def classificar(self, prep: Preparado, nomes: list[str], limiar: float) -> tuple[str | None, float]:
        """Entre vários templates, devolve o de maior score acima do limiar."""
        melhor, melhor_score = None, 0.0
        for nome in nomes:
            achado = self.pontuar(prep, nome)
            if achado and achado.score >= limiar and achado.score > melhor_score:
                melhor, melhor_score = nome, achado.score
        return melhor, melhor_score
