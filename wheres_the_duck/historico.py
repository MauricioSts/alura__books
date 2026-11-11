"""Histórico de sessões em um JSON local."""
from __future__ import annotations

import json
import threading
from pathlib import Path


class Historico:
    LIMITE = 300

    def __init__(self, caminho: Path):
        self.caminho = Path(caminho)
        self._trava = threading.Lock()
        try:
            dados = json.loads(self.caminho.read_text(encoding="utf-8"))
            self._sessoes: list[dict] = dados if isinstance(dados, list) else []
        except (OSError, ValueError):
            self._sessoes = []

    def listar(self) -> list[dict]:
        with self._trava:
            return [dict(s) for s in reversed(self._sessoes)]

    def gravar(self, sessao: dict) -> None:
        """Insere ou atualiza a sessão pelo id."""
        with self._trava:
            for i, s in enumerate(self._sessoes):
                if s.get("id") == sessao.get("id"):
                    self._sessoes[i] = dict(sessao)
                    break
            else:
                self._sessoes.append(dict(sessao))
            self._sessoes = self._sessoes[-self.LIMITE:]
            self.caminho.parent.mkdir(parents=True, exist_ok=True)
            self.caminho.write_text(
                json.dumps(self._sessoes, indent=1, ensure_ascii=False), encoding="utf-8")
