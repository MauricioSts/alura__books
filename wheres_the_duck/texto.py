"""Leitura dos textos da tela (OCR local), para funcionar sem templates recortados.

O motor de OCR (RapidOCR) roda no próprio PC: os modelos vêm dentro do pacote
e nenhuma conexão externa é feita.
"""
from __future__ import annotations

import difflib
import re
import threading
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Linha:
    """Um trecho de texto lido, em coordenadas da imagem original (sem offset de monitor)."""

    texto: str
    x: int  # canto superior esquerdo
    y: int
    largura: int
    altura: int
    confianca: float

    @property
    def compacto(self) -> str:
        return compactar(self.texto)


def compactar(texto: str) -> str:
    """Maiúsculas, sem acentos, sem espaços nem pontuação: o OCR às vezes junta palavras."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]", "", sem_acento.upper())


def parecido(a: str, b: str, minimo: float = 0.84) -> bool:
    return a == b or difflib.SequenceMatcher(None, a, b).ratio() >= minimo


def linha_igual(linha: str, padrao: str) -> bool:
    """A linha inteira é o padrão (com tolerância a erro de leitura). Usado para botões."""
    if not padrao:
        return False
    if parecido(linha, padrao):
        return True
    # O botão às vezes vem com a tecla de atalho junto ("E RESGATAR"): aceita pouca sobra.
    return padrao in linha and len(linha) - len(padrao) <= 3


def contem(texto: str, padrao: str) -> bool:
    """O padrão aparece dentro do texto, com tolerância para padrões longos."""
    if not padrao:
        return False
    if padrao in texto:
        return True
    if len(padrao) < 8 or len(texto) < len(padrao):
        return False
    janela = len(padrao)
    return any(parecido(texto[i:i + janela], padrao, 0.88) for i in range(len(texto) - janela + 1))


class LeitorTexto(ABC):
    @abstractmethod
    def ler(self, imagem: np.ndarray) -> list[Linha]:
        """Devolve as linhas de texto encontradas na imagem BGR."""


class LeitorFixo(LeitorTexto):
    """Para testes e simulação: devolve linhas definidas por quem chamou."""

    def __init__(self, linhas: list[Linha] | None = None):
        self.linhas = linhas or []
        self.chamadas = 0

    def ler(self, imagem):
        self.chamadas += 1
        return list(self.linhas)


class LeitorRapidOCR(LeitorTexto):
    """OCR local com RapidOCR (ONNX). Reduz a tela para `largura` antes de ler."""

    _motor = None
    _trava = threading.Lock()

    def __init__(self, largura: int = 1280):
        self.largura = largura

    @classmethod
    def _carregar(cls):
        with cls._trava:
            if cls._motor is None:
                from rapidocr_onnxruntime import RapidOCR

                # Poucas threads: o jogo precisa da CPU mais do que nós.
                cls._motor = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1)
            return cls._motor

    @staticmethod
    def disponivel() -> bool:
        try:
            import rapidocr_onnxruntime  # noqa: F401
            return True
        except Exception:
            return False

    def ler(self, imagem: np.ndarray) -> list[Linha]:
        motor = self._carregar()
        altura, largura = imagem.shape[:2]
        fator = min(1.0, self.largura / float(largura))
        reduzida = imagem if fator >= 0.999 else cv2.resize(
            imagem, None, fx=fator, fy=fator, interpolation=cv2.INTER_AREA)
        resultado, _ = motor(reduzida)
        linhas = []
        for caixa, texto, confianca in resultado or []:
            pontos = np.asarray(caixa, dtype=np.float32) / fator
            x0, y0 = pontos.min(axis=0)
            x1, y1 = pontos.max(axis=0)
            linhas.append(Linha(str(texto), int(x0), int(y0), int(x1 - x0), int(y1 - y0),
                                float(confianca)))
        return linhas
