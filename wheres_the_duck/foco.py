"""Verificação de foco da janela do jogo, atrás de uma interface."""
from __future__ import annotations

import sys
from abc import ABC, abstractmethod


class Foco(ABC):
    @abstractmethod
    def em_foco(self) -> bool:
        """True quando a janela em primeiro plano é a do jogo."""


class FocoSimulado(Foco):
    """Dry-run: o foco é o que o teste ou a simulação mandar."""

    def __init__(self, valor: bool = True):
        self.valor = valor

    def em_foco(self) -> bool:
        return self.valor


class FocoWindows(Foco):
    """Lê apenas o título da janela em primeiro plano (API pública do Windows)."""

    def __init__(self, titulo: str = "Fortnite"):
        self.titulo = titulo.strip().lower()
        import ctypes

        self._user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        self._ctypes = ctypes

    def titulo_atual(self) -> str:
        hwnd = self._user32.GetForegroundWindow()
        if not hwnd:
            return ""
        tamanho = self._user32.GetWindowTextLengthW(hwnd)
        buffer = self._ctypes.create_unicode_buffer(tamanho + 1)
        self._user32.GetWindowTextW(hwnd, buffer, tamanho + 1)
        return buffer.value

    def em_foco(self) -> bool:
        try:
            return bool(self.titulo) and self.titulo in self.titulo_atual().lower()
        except Exception:
            return False


def ativar_dpi() -> None:
    """Sem isso, em telas com escala (125%, 150%) o clique cai no lugar errado."""
    if sys.platform != "win32":
        return
    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # por monitor
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
