"""Leituras simples de imagem que não dependem de recorte: barras de vida da squad e movimento da tela.

Usam só o que aparece na tela, como um humano veria.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Barra:
    x: int
    y: int
    largura: int
    altura: int
    cor: str


def recortar_regiao(imagem: np.ndarray, regiao: list[float]) -> tuple[np.ndarray, int, int]:
    """Recorte de uma região em frações da tela. Devolve o recorte e o canto (x, y)."""
    h, w = imagem.shape[:2]
    x0 = int(max(0.0, min(1.0, regiao[0])) * w)
    y0 = int(max(0.0, min(1.0, regiao[1])) * h)
    x1 = int(max(0.0, min(1.0, regiao[0] + regiao[2])) * w)
    y1 = int(max(0.0, min(1.0, regiao[1] + regiao[3])) * h)
    return imagem[y0:y1, x0:x1], x0, y0


# Faixas HSV (OpenCV: H 0-179) das barras de vida, escudo e de companheiro derrubado.
CORES_BARRA = {
    "vida": ((38, 110, 110), (85, 255, 255)),
    "escudo": ((92, 110, 120), (112, 255, 255)),
    "derrubado": ((0, 140, 140), (8, 255, 255)),
}


def barras_de_vida(imagem: np.ndarray, regiao: list[float]) -> list[Barra]:
    """Barras horizontais finas e saturadas na região da squad: cada uma indica um companheiro vivo."""
    recorte, ox, oy = recortar_regiao(imagem, regiao)
    if recorte.size == 0:
        return []
    altura_tela = imagem.shape[0]
    alt_min = max(2, int(altura_tela * 0.0025))   # ~3 px em 1080p
    alt_max = max(alt_min + 2, int(altura_tela * 0.025))  # ~27 px em 1080p
    larg_min = max(12, int(altura_tela * 0.022))  # ~24 px em 1080p
    hsv = cv2.cvtColor(recorte, cv2.COLOR_BGR2HSV)
    barras: list[Barra] = []
    for cor, (baixo, alto) in CORES_BARRA.items():
        mascara = cv2.inRange(hsv, np.array(baixo), np.array(alto))
        if cor == "derrubado":
            mascara |= cv2.inRange(hsv, np.array((172, 140, 140)), np.array((179, 255, 255)))
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, np.ones((1, 5), np.uint8))
        contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contornos:
            x, y, w, h = cv2.boundingRect(c)
            preenchido = cv2.contourArea(c) / float(max(1, w * h))
            if alt_min <= h <= alt_max and w >= larg_min and w >= 4 * h and preenchido >= 0.6:
                barras.append(Barra(x + ox, y + oy, w, h, cor))
    return barras


def contar_companheiros_vivos(imagem: np.ndarray, regiao: list[float]) -> int:
    """Conta linhas da lista da squad que têm alguma barra (vida e escudo na mesma linha contam uma vez)."""
    barras = sorted(barras_de_vida(imagem, regiao), key=lambda b: b.y)
    linhas: list[int] = []
    tolerancia = max(6, int(imagem.shape[0] * 0.012))
    for b in barras:
        centro = b.y + b.altura // 2
        if not linhas or centro - linhas[-1] > tolerancia:
            linhas.append(centro)
    return len(linhas)


def miniatura_cenario(imagem: np.ndarray) -> np.ndarray:
    """Faixa central-superior da tela, sem o HUD das bordas e sem o personagem (que fica embaixo)."""
    cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY) if imagem.ndim == 3 else imagem
    faixa, _, _ = recortar_regiao(cinza, [0.2, 0.08, 0.6, 0.37])
    pequena = cv2.resize(faixa, (96, 40), interpolation=cv2.INTER_AREA)
    return cv2.GaussianBlur(pequena, (3, 3), 0)


def diferenca(a: np.ndarray | None, b: np.ndarray) -> float:
    """Quanto o cenário mudou entre dois ciclos (0 = idêntico)."""
    if a is None or a.shape != b.shape:
        return 255.0
    return float(cv2.absdiff(a, b).mean())
