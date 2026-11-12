"""Teclado e mouse atrás de uma interface: implementação real (SendInput) e dry-run."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Callable


class Entrada(ABC):
    """Controla quais teclas estão pressionadas para poder soltar tudo a qualquer momento."""

    def __init__(self) -> None:
        self._teclas: set[str] = set()
        self._mouse_preso = False

    # --- operações de baixo nível, implementadas por cada backend ---
    @abstractmethod
    def _baixo(self, tecla: str) -> None: ...
    @abstractmethod
    def _cima(self, tecla: str) -> None: ...
    @abstractmethod
    def _tocar(self, tecla: str) -> None: ...
    @abstractmethod
    def _clicar(self, x: int, y: int, botao: str = "esquerdo") -> None: ...
    @abstractmethod
    def _mouse(self, baixo: bool) -> None: ...
    @abstractmethod
    def _mover_rel(self, dx: int, dy: int) -> None: ...

    # --- API usada pelo resto do app ---
    @property
    def teclas_pressionadas(self) -> set[str]:
        return set(self._teclas)

    @property
    def mouse_pressionado(self) -> bool:
        return self._mouse_preso

    def tecla_baixo(self, tecla: str) -> None:
        if tecla not in self._teclas:
            self._teclas.add(tecla)
            self._baixo(tecla)

    def tecla_cima(self, tecla: str) -> None:
        if tecla in self._teclas:
            self._teclas.discard(tecla)
            self._cima(tecla)

    def tocar(self, tecla: str) -> None:
        self._tocar(tecla)

    def clicar(self, x: int, y: int, botao: str = "esquerdo") -> None:
        self._clicar(int(x), int(y), botao)

    def mouse_baixo(self) -> None:
        if not self._mouse_preso:
            self._mouse_preso = True
            self._mouse(True)

    def mouse_cima(self) -> None:
        if self._mouse_preso:
            self._mouse_preso = False
            self._mouse(False)

    def mover_mouse_rel(self, dx: float, dy: float) -> None:
        dx, dy = int(round(dx)), int(round(dy))
        if dx or dy:
            self._mover_rel(dx, dy)

    def soltar_tudo(self) -> None:
        for tecla in list(self._teclas):
            self.tecla_cima(tecla)
        self.mouse_cima()


class EntradaSimulada(Entrada):
    """Dry-run: não envia nada ao sistema, só registra o que faria."""

    def __init__(self, ao_registrar: Callable[[str], None] | None = None):
        super().__init__()
        self.acoes: list[tuple] = []
        self._ao_registrar = ao_registrar

    def _anotar(self, *acao) -> None:
        self.acoes.append(acao)
        if self._ao_registrar:
            self._ao_registrar("[ensaio] " + " ".join(str(a) for a in acao))

    def _baixo(self, tecla): self._anotar("segurar", tecla)
    def _cima(self, tecla): self._anotar("soltar", tecla)
    def _tocar(self, tecla): self._anotar("tocar", tecla)
    def _clicar(self, x, y, botao="esquerdo"):
        self._anotar("clicar" if botao == "esquerdo" else "clicar_direito", x, y)
    def _mouse(self, baixo): self._anotar("mouse_baixo" if baixo else "mouse_cima")
    def _mover_rel(self, dx, dy): self.acoes.append(("mover", dx, dy))  # fora do log: é muito frequente

    def nomes(self) -> list[str]:
        return [a[0] for a in self.acoes]


class EntradaDireta(Entrada):
    """Teclado e mouse de verdade via pydirectinput (SendInput), que funciona em jogos DirectX."""

    def __init__(self) -> None:
        super().__init__()
        import pydirectinput  # só existe no Windows

        pydirectinput.PAUSE = 0.02
        # O "fail-safe" de canto de tela dispararia com o mouse relativo do jogo; a parada é o F8.
        pydirectinput.FAILSAFE = False
        self._pdi = pydirectinput

    def _baixo(self, tecla): self._pdi.keyDown(tecla)
    def _cima(self, tecla): self._pdi.keyUp(tecla)
    def _tocar(self, tecla): self._pdi.press(tecla)

    def _clicar(self, x, y, botao="esquerdo"):
        self._pdi.moveTo(x, y)
        time.sleep(0.08)
        self._pdi.click(button="right" if botao == "direito" else "left")

    def _mouse(self, baixo):
        (self._pdi.mouseDown if baixo else self._pdi.mouseUp)()

    def _mover_rel(self, dx, dy):
        # Giros grandes num único evento costumam ser cortados pelo jogo: envia em passos curtos.
        passos = max(1, int(max(abs(dx), abs(dy)) // 40) + 1)
        feito_x = feito_y = 0
        for i in range(1, passos + 1):
            alvo_x, alvo_y = round(dx * i / passos), round(dy * i / passos)
            self._pdi.moveRel(alvo_x - feito_x, alvo_y - feito_y, relative=True, _pause=False)
            feito_x, feito_y = alvo_x, alvo_y
            time.sleep(0.004)
