"""Log do app: memória (para a interface), arquivo diário e ouvintes em tempo real."""
from __future__ import annotations

import threading
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Callable


class Registro:
    def __init__(self, pasta: Path | None = None, capacidade: int = 500):
        self.pasta = Path(pasta) if pasta else None
        self._linhas: deque[dict] = deque(maxlen=capacidade)
        self._ouvintes: list[Callable[[dict], None]] = []
        self._trava = threading.Lock()

    def ouvir(self, ouvinte: Callable[[dict], None]) -> None:
        self._ouvintes.append(ouvinte)

    def linhas(self) -> list[dict]:
        with self._trava:
            return list(self._linhas)

    def _emitir(self, nivel: str, msg: str) -> None:
        agora = datetime.now()
        linha = {"hora": agora.strftime("%H:%M:%S"), "nivel": nivel, "msg": msg}
        with self._trava:
            self._linhas.append(linha)
            if self.pasta:
                try:
                    self.pasta.mkdir(parents=True, exist_ok=True)
                    arq = self.pasta / f"wheres_the_duck-{agora:%Y%m%d}.log"
                    with arq.open("a", encoding="utf-8") as f:
                        f.write(f"{agora:%Y-%m-%d %H:%M:%S} [{nivel}] {msg}\n")
                except OSError:
                    pass
        for ouvinte in list(self._ouvintes):
            try:
                ouvinte(linha)
            except Exception:
                pass

    def info(self, msg: str) -> None:
        self._emitir("info", msg)

    def aviso(self, msg: str) -> None:
        self._emitir("aviso", msg)

    def erro(self, msg: str) -> None:
        self._emitir("erro", msg)

    def destaque(self, msg: str) -> None:
        self._emitir("destaque", msg)
