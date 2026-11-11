"""Arquivo das recompensas capturadas: prints em disco e um índice em JSON."""
from __future__ import annotations

import json
import shutil
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable

from .captura import Quadro, salvar_png

PIRATA = "acesso_pirata"


class ArquivoRecompensas:
    def __init__(self, pasta_capturas: Path, indice: Path,
                 relogio: Callable[[], datetime] = datetime.now):
        self.pasta = Path(pasta_capturas)
        self.pasta_pirata = self.pasta / "acesso_pirata"
        self.indice = Path(indice)
        self._relogio = relogio
        self._trava = threading.Lock()
        self._itens: list[dict] = self._ler()

    def _ler(self) -> list[dict]:
        try:
            dados = json.loads(self.indice.read_text(encoding="utf-8"))
            return dados if isinstance(dados, list) else []
        except (OSError, ValueError):
            return []

    def _gravar(self) -> None:
        self.indice.parent.mkdir(parents=True, exist_ok=True)
        self.indice.write_text(json.dumps(self._itens, indent=1, ensure_ascii=False), encoding="utf-8")

    def listar(self) -> list[dict]:
        with self._trava:
            return [dict(i) for i in self._itens]

    def registrar(self, quadro: Quadro, tipo: str, score: float, partida: int,
                  sessao: str, gatilho: str) -> dict:
        """Salva o print feito ANTES de qualquer clique e cria o registro."""
        agora = self._relogio()
        with self._trava:
            ident = f"{agora:%Y%m%d-%H%M%S}-{len(self._itens) + 1:04d}"
            nome = f"{ident}_p{partida}_{tipo}_antes.png"
            salvar_png(self.pasta / nome, quadro.imagem)
            item = {
                "id": ident,
                "tipo": tipo,
                "score": round(float(score), 3),
                "data": agora.strftime("%d/%m/%Y"),
                "hora": agora.strftime("%H:%M:%S"),
                "quando": agora.isoformat(timespec="seconds"),
                "partida": partida,
                "sessao": sessao,
                "gatilho": gatilho,
                "antes": nome,
                "depois": None,
                "confirmado": tipo != PIRATA,
            }
            if tipo == PIRATA:
                self._copiar_pirata(nome)
            self._itens.append(item)
            self._gravar()
            return dict(item)

    def anexar_depois(self, ident: str, quadro: Quadro) -> dict | None:
        """Salva o print feito depois do clique em Resgatar."""
        with self._trava:
            for item in self._itens:
                if item["id"] == ident:
                    nome = item["antes"].replace("_antes.png", "_depois.png")
                    salvar_png(self.pasta / nome, quadro.imagem)
                    item["depois"] = nome
                    if item["tipo"] == PIRATA:
                        self._copiar_pirata(nome)
                    self._gravar()
                    return dict(item)
        return None

    def _copiar_pirata(self, nome: str) -> None:
        try:
            self.pasta_pirata.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.pasta / nome, self.pasta_pirata / nome)
        except OSError:
            pass

    def alerta_pendente(self) -> dict | None:
        with self._trava:
            for item in reversed(self._itens):
                if item["tipo"] == PIRATA and not item.get("confirmado"):
                    return dict(item)
        return None

    def confirmar_alertas(self) -> None:
        with self._trava:
            for item in self._itens:
                item["confirmado"] = True
            self._gravar()
