"""API local (somente 127.0.0.1): REST para comandos e WebSocket para estado, log e recompensas."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError

from . import NOME_APP, __version__, catalogo
from .captura import codificar_png, salvar_png
from .config import ArmazemConfig
from .motor import Motor
from .registro import Registro

HOSTS_LOCAIS = {"127.0.0.1", "localhost", "testserver"}


class Difusor:
    """Entrega mensagens vindas de qualquer thread a todos os WebSockets conectados."""

    def __init__(self) -> None:
        # Cada cliente guarda o laço de eventos em que a sua fila foi criada.
        self.clientes: dict[asyncio.Queue, asyncio.AbstractEventLoop] = {}

    def entrar(self) -> asyncio.Queue:
        fila: asyncio.Queue = asyncio.Queue()
        self.clientes[fila] = asyncio.get_running_loop()
        return fila

    def sair(self, fila: asyncio.Queue) -> None:
        self.clientes.pop(fila, None)

    def publicar(self, msg: dict) -> None:
        for fila, laco in list(self.clientes.items()):
            try:
                laco.call_soon_threadsafe(self._por, fila, msg)
            except RuntimeError:  # laço já encerrado
                self.clientes.pop(fila, None)

    @staticmethod
    def _por(fila: asyncio.Queue, msg: dict) -> None:
        if fila.qsize() < 500:
            fila.put_nowait(msg)


class PedidoIniciar(BaseModel):
    modo: str = "real"
    pasta: str | None = None
    repetir: int = Field(1, ge=1, le=200)


class PedidoRecorte(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    largura: int = Field(ge=4)
    altura: int = Field(ge=4)


def _host_local(valor: str | None) -> bool:
    if not valor:
        return False
    nome = urlparse(valor if "//" in valor else f"//{valor}").hostname
    return nome in HOSTS_LOCAIS


def criar_app(base: Path, armazem: ArmazemConfig | None = None,
              registro: Registro | None = None) -> FastAPI:
    base = Path(base)
    armazem = armazem or ArmazemConfig(base / "config.json")
    registro = registro or Registro(base / "logs")
    difusor = Difusor()
    motor = Motor(base, armazem, registro, difusor.publicar)
    registro.ouvir(lambda linha: difusor.publicar({"tipo": "log", "linha": linha}))

    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI):
        yield
        motor.parar("aplicativo fechado")

    app = FastAPI(title=NOME_APP, version=__version__, lifespan=ciclo_de_vida,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.motor = motor
    app.state.armazem = armazem
    app.state.registro = registro

    @app.middleware("http")
    async def somente_local(request: Request, call_next):
        # Barra páginas de outros sites tentando falar com a API local (CSRF, DNS rebinding).
        origem = request.headers.get("origin")
        if not _host_local(request.headers.get("host")) or (origem and not _host_local(origem)):
            return JSONResponse({"detail": "Acesso permitido apenas localmente."}, status_code=403)
        return await call_next(request)

    def _nome_valido(nome: str) -> str:
        if nome not in catalogo.NOMES:
            raise HTTPException(404, "Template desconhecido.")
        return nome

    # ------------------------------------------------------------------ estado e controle
    @app.get("/api/estado")
    def estado():
        return {"app": NOME_APP, "versao": __version__, "estado": motor.estado(),
                "log": registro.linhas(), "chances": catalogo.CHANCES}

    @app.post("/api/iniciar")
    def iniciar(pedido: PedidoIniciar):
        try:
            motor.iniciar(pedido.modo, pedido.pasta, pedido.repetir)
        except Exception as erro:
            registro.erro(f"Não foi possível iniciar: {erro}")
            raise HTTPException(400, str(erro))
        return motor.estado()

    @app.post("/api/parar")
    def parar():
        motor.parar()
        return motor.estado()

    @app.post("/api/alerta/confirmar")
    def confirmar_alerta():
        motor.recompensas.confirmar_alertas()
        motor.publicar_estado()
        return {"ok": True}

    # ------------------------------------------------------------------ configuração
    @app.get("/api/config")
    def ler_config():
        return armazem.atual.model_dump()

    @app.put("/api/config")
    async def salvar_config(request: Request):
        try:
            cfg = armazem.salvar(await request.json())
        except ValidationError as erro:
            campos = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in erro.errors())
            raise HTTPException(422, f"Configuração inválida: {campos}")
        registro.info("Configuração salva." + (" Vale a partir do próximo Iniciar." if motor.rodando else ""))
        return cfg.model_dump()

    # ------------------------------------------------------------------ templates
    def _info_templates() -> list[dict]:
        itens = []
        for info in catalogo.como_dicts():
            arq = motor.pasta_templates / f"{info['nome']}.png"
            existe = arq.is_file()
            info.update(configurado=existe, versao=int(arq.stat().st_mtime) if existe else 0,
                        chance=catalogo.CHANCES.get(info["nome"]))
            itens.append(info)
        return itens

    def _gravar_template(nome: str, imagem: np.ndarray) -> None:
        if imagem is None or imagem.size == 0 or min(imagem.shape[:2]) < 4:
            raise HTTPException(400, "Imagem inválida ou pequena demais.")
        salvar_png(motor.pasta_templates / f"{nome}.png", imagem)
        motor.recarregar_templates()
        registro.info(f"Template '{nome}' atualizado ({imagem.shape[1]}x{imagem.shape[0]}).")

    @app.get("/api/templates")
    def listar_templates():
        return _info_templates()

    @app.get("/api/templates/{nome}/imagem")
    def imagem_template(nome: str):
        arq = motor.pasta_templates / f"{_nome_valido(nome)}.png"
        if not arq.is_file():
            raise HTTPException(404, "Template não configurado.")
        return FileResponse(arq, media_type="image/png", headers={"Cache-Control": "no-store"})

    @app.put("/api/templates/{nome}")
    async def enviar_template(nome: str, request: Request):
        _nome_valido(nome)
        dados = await request.body()
        if len(dados) > 20_000_000:
            raise HTTPException(413, "Arquivo grande demais.")
        imagem = cv2.imdecode(np.frombuffer(dados, dtype=np.uint8), cv2.IMREAD_COLOR)
        _gravar_template(nome, imagem)
        return _info_templates()

    @app.delete("/api/templates/{nome}")
    def apagar_template(nome: str):
        arq = motor.pasta_templates / f"{_nome_valido(nome)}.png"
        arq.unlink(missing_ok=True)
        motor.recarregar_templates()
        return _info_templates()

    @app.post("/api/captura")
    async def capturar(atraso: float = 3.0):
        await asyncio.sleep(max(0.0, min(atraso, 15.0)))
        try:
            quadro = await asyncio.to_thread(motor.capturar_tela)
        except Exception as erro:
            raise HTTPException(500, f"Não foi possível capturar a tela: {erro}")
        return {"largura": int(quadro.imagem.shape[1]), "altura": int(quadro.imagem.shape[0])}

    @app.get("/api/captura/imagem")
    def imagem_captura():
        if motor.ultima_captura is None:
            raise HTTPException(404, "Nenhuma captura feita ainda.")
        return Response(codificar_png(motor.ultima_captura.imagem), media_type="image/png",
                        headers={"Cache-Control": "no-store"})

    @app.post("/api/templates/{nome}/recorte")
    def recortar_template(nome: str, r: PedidoRecorte):
        _nome_valido(nome)
        if motor.ultima_captura is None:
            raise HTTPException(400, "Capture a tela antes de recortar.")
        recorte = motor.ultima_captura.imagem[r.y: r.y + r.altura, r.x: r.x + r.largura]
        _gravar_template(nome, recorte)
        return _info_templates()

    # ------------------------------------------------------------------ detecção
    @app.post("/api/deteccao/testar")
    async def testar_deteccao():
        try:
            return await asyncio.to_thread(motor.testar_deteccao)
        except Exception as erro:
            raise HTTPException(500, f"Não foi possível testar: {erro}")

    # ------------------------------------------------------------------ histórico
    @app.get("/api/historico")
    def historico():
        return {"sessoes": motor.historico.listar(),
                "recompensas": list(reversed(motor.recompensas.listar()))}

    @app.get("/api/capturas/{arquivo}")
    def captura_salva(arquivo: str):
        arq = motor.pasta_capturas / Path(arquivo).name
        if arq.suffix.lower() != ".png" or not arq.is_file():
            raise HTTPException(404, "Print não encontrado.")
        return FileResponse(arq, media_type="image/png")

    # ------------------------------------------------------------------ tempo real
    @app.websocket("/ws")
    async def tempo_real(ws: WebSocket):
        origem = ws.headers.get("origin")
        if not _host_local(ws.headers.get("host")) or (origem and not _host_local(origem)):
            await ws.close(code=1008)
            return
        await ws.accept()
        fila = difusor.entrar()

        async def enviar():
            await ws.send_json({"tipo": "estado", "estado": motor.estado()})
            while True:
                await ws.send_json(await fila.get())

        async def escutar():
            # O cliente não manda nada; isto só serve para perceber a desconexão.
            while True:
                await ws.receive_text()

        tarefas = [asyncio.create_task(enviar()), asyncio.create_task(escutar())]
        try:
            await asyncio.wait(tarefas, return_when=asyncio.FIRST_COMPLETED)
        finally:
            difusor.sair(fila)
            for tarefa in tarefas:
                tarefa.cancel()
            await asyncio.gather(*tarefas, return_exceptions=True)

    # ------------------------------------------------------------------ frontend
    dist = base / "frontend" / "dist"
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    else:
        @app.get("/")
        def sem_frontend():
            return Response("Frontend não compilado. Rode 'npm install' e 'npm run build' na "
                            "pasta frontend (o iniciar.bat faz isso).", media_type="text/plain; charset=utf-8")

    return app
