"""Ponto de entrada: sobe a API em 127.0.0.1 e abre a janela nativa."""
from __future__ import annotations

import argparse
import socket
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn

from . import NOME_APP
from .api import criar_app
from .config import ArmazemConfig
from .foco import ativar_dpi
from .registro import Registro

BASE = Path(__file__).resolve().parent.parent
ENDERECO = "127.0.0.1"  # nunca 0.0.0.0: a API não deve ficar visível na rede


def _esperar_porta(porta: int, limite_s: float = 15.0) -> bool:
    fim = time.monotonic() + limite_s
    while time.monotonic() < fim:
        try:
            with socket.create_connection((ENDERECO, porta), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.15)
    return False


def _registrar_f8(motor, registro: Registro) -> None:
    try:
        import keyboard

        keyboard.add_hotkey("f8", motor.alternar)
        registro.info("Atalho F8 ativo: inicia ou para tudo.")
    except Exception as erro:
        registro.aviso(f"Atalho F8 indisponível ({erro}). Use o botão da interface.")


def main() -> None:
    parser = argparse.ArgumentParser(description=f"{NOME_APP} — vigia de partidas")
    parser.add_argument("--navegador", action="store_true",
                        help="abre no navegador padrão em vez da janela nativa")
    parser.add_argument("--porta", type=int, default=None)
    args = parser.parse_args()

    ativar_dpi()
    armazem = ArmazemConfig(BASE / "config.json")
    registro = Registro(BASE / "logs")
    app = criar_app(BASE, armazem, registro)
    motor = app.state.motor
    porta = args.porta or armazem.atual.porta
    url = f"http://{ENDERECO}:{porta}"

    servidor = uvicorn.Server(uvicorn.Config(app, host=ENDERECO, port=porta, log_level="warning"))
    thread = threading.Thread(target=servidor.run, daemon=True, name="atalaia-api")
    thread.start()
    if not _esperar_porta(porta):
        raise SystemExit(f"A API não subiu na porta {porta}. Ela está em uso? Mude 'porta' no config.json.")
    _registrar_f8(motor, registro)

    try:
        janela_nativa = not args.navegador
        if janela_nativa:
            try:
                import webview
            except ImportError:
                registro.aviso("pywebview não instalado; abrindo no navegador.")
                janela_nativa = False
        if janela_nativa:
            webview.create_window(NOME_APP, url, width=1280, height=820, min_size=(1024, 680),
                                  background_color="#0c1116")
            webview.start()
        else:
            webbrowser.open(url)
            print(f"{NOME_APP} rodando em {url} — Ctrl+C para encerrar.")
            while thread.is_alive():
                time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        motor.parar("aplicativo fechado")
        servidor.should_exit = True
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
