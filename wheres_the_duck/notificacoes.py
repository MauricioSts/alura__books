"""Aviso opcional no Discord quando uma recompensa é capturada.

É a única conexão externa do app: desligada por padrão, só envia para um webhook
do Discord que o próprio usuário configurou, e só manda o aviso (texto e print).
"""
from __future__ import annotations

import json
import re
import threading
import uuid
import urllib.request
from pathlib import Path
from typing import Callable

from .catalogo import NAO_IDENTIFICADA
from .recompensas import PIRATA

URL_WEBHOOK = re.compile(
    r"^https://(?:(?:ptb|canary)\.)?discord(?:app)?\.com/api/webhooks/\d+/[\w-]+/?$")

ROTULOS = {
    "acesso_pirata": "Acesso à Loja Pirata",
    "traje_dourado": "Traje Dourado Semanal",
    "veiculo": "Veículo e Decalque Semanal",
    "picareta_costas": "Picareta ou Acessório para as Costas",
    "faixa": "Faixa de Improviso Semanal",
    "tela_carregamento": "Tela de Carregamento Semanal",
    "gizmo": "Gizmo",
    NAO_IDENTIFICADA: "Recompensa não identificada",
}

# Enviar(url, campos multipart) -> código HTTP. Trocável nos testes.
Envio = Callable[[str, bytes, str], int]


def url_valida(url: str) -> bool:
    return bool(URL_WEBHOOK.match((url or "").strip()))


def _multipart(payload: dict, arquivo: Path | None) -> tuple[bytes, str]:
    fronteira = uuid.uuid4().hex
    partes = [
        f"--{fronteira}\r\nContent-Disposition: form-data; name=\"payload_json\"\r\n"
        f"Content-Type: application/json\r\n\r\n".encode() + json.dumps(payload).encode() + b"\r\n"
    ]
    if arquivo is not None and arquivo.is_file():
        partes.append(
            f"--{fronteira}\r\nContent-Disposition: form-data; name=\"files[0]\"; "
            f"filename=\"{arquivo.name}\"\r\nContent-Type: image/png\r\n\r\n".encode()
            + arquivo.read_bytes() + b"\r\n")
    partes.append(f"--{fronteira}--\r\n".encode())
    return b"".join(partes), f"multipart/form-data; boundary={fronteira}"


def enviar_http(url: str, corpo: bytes, tipo: str) -> int:
    pedido = urllib.request.Request(url, data=corpo, method="POST", headers={
        "Content-Type": tipo, "User-Agent": "WheresTheDuck (notificacao local)"})
    with urllib.request.urlopen(pedido, timeout=15) as resposta:
        return resposta.status


def deve_notificar(tipo: str, filtro: str) -> bool:
    if filtro == "so_pirata":
        return tipo == PIRATA
    if filtro == "sem_gizmo":
        return tipo not in ("gizmo",)
    return True


def montar_mensagem(item: dict, mencao: str = "") -> dict:
    tipo = item.get("tipo", NAO_IDENTIFICADA)
    rotulo = ROTULOS.get(tipo, tipo)
    pirata = tipo == PIRATA
    linhas = []
    if pirata:
        linhas.append(f"{mencao} **ACESSO À LOJA PIRATA ENCONTRADO!**".strip())
        linhas.append("Ative o token na loja até **15/12/2026**. Confira no jogo.")
    elif tipo == NAO_IDENTIFICADA:
        linhas.append("Recompensa **não identificada**: confira o print, pode ser o Acesso à Loja Pirata.")
    else:
        linhas.append(f"Recompensa: **{rotulo}**")
    linhas.append(f"{item.get('data', '')} às {item.get('hora', '')} · partida nº {item.get('partida', '?')}")
    return {
        "username": "Where's the Duck",
        "content": "\n".join(linhas),
        # Menção só para quem o usuário colocou na configuração.
        "allowed_mentions": {"parse": ["everyone", "users", "roles"] if pirata and mencao else []},
    }


class NotificadorDiscord:
    def __init__(self, obter_config: Callable[[], object], pasta_capturas: Path,
                 registro=None, enviar: Envio = enviar_http, em_segundo_plano: bool = True):
        self.obter_config = obter_config
        self.pasta = Path(pasta_capturas)
        self.log = registro
        self.enviar = enviar
        self.em_segundo_plano = em_segundo_plano
        self._enviados: set[str] = set()

    def _cfg(self):
        return self.obter_config().discord

    def _executar(self, funcao) -> None:
        if self.em_segundo_plano:
            threading.Thread(target=funcao, daemon=True, name="aviso-discord").start()
        else:
            funcao()

    def _postar(self, url: str, payload: dict, arquivo: Path | None) -> bool:
        corpo, tipo = _multipart(payload, arquivo)
        try:
            codigo = self.enviar(url, corpo, tipo)
            ok = 200 <= codigo < 300
        except Exception as erro:  # nunca derruba o motor
            ok = False
            if self.log:
                self.log.aviso(f"Não consegui avisar no Discord: {type(erro).__name__}.")
            return False
        if not ok and self.log:
            self.log.aviso(f"Discord recusou o aviso (HTTP {codigo}). Confira a URL do webhook.")
        return ok

    def recompensa(self, item: dict) -> None:
        """Chamado a cada evento de recompensa; avisa uma vez por recompensa."""
        cfg = self._cfg()
        ident = item.get("id")
        if not cfg.ativo or not ident or ident in self._enviados:
            return
        if not url_valida(cfg.webhook_url) or not deve_notificar(item.get("tipo", ""), cfg.filtro):
            return
        self._enviados.add(ident)
        arquivo = self.pasta / item["antes"] if cfg.enviar_print and item.get("antes") else None
        payload = montar_mensagem(item, cfg.mencao)
        url = cfg.webhook_url.strip()

        def tarefa():
            if self._postar(url, payload, arquivo) and self.log:
                self.log.info("Aviso enviado ao Discord.")
        self._executar(tarefa)

    def testar(self, url: str | None = None) -> tuple[bool, str]:
        url = (url or self._cfg().webhook_url).strip()
        if not url_valida(url):
            return False, "URL inválida. Ela deve começar com https://discord.com/api/webhooks/"
        payload = {"username": "Where's the Duck", "allowed_mentions": {"parse": []},
                   "content": "Teste do Where's the Duck: os avisos de recompensa vão chegar aqui."}
        ok = self._postar(url, payload, None)
        return ok, "Mensagem de teste enviada." if ok else "Não foi possível enviar. Veja o log."
