"""Motor: a thread que captura a tela, roda a máquina de estados e publica o estado."""
from __future__ import annotations

import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

from . import catalogo
from .captura import Capturador, CapturadorPasta, CapturadorTela, Quadro
from .config import ArmazemConfig
from .deteccao import Detector
from .entrada import Entrada, EntradaSimulada
from .foco import Foco, FocoSimulado
from .historico import Historico
from .maquina import Maquina
from .recompensas import ArquivoRecompensas
from .registro import Registro

PASSO_S = 0.1  # intervalo entre chamadas de animar()
MODOS = ("real", "ensaio", "simulacao")


class Motor:
    def __init__(self, base: Path, armazem: ArmazemConfig, registro: Registro,
                 publicar: Callable[[dict], None] | None = None):
        self.base = Path(base)
        self.armazem = armazem
        self.log = registro
        self.publicar = publicar or (lambda msg: None)
        self.pasta_templates = self.base / "templates"
        self.pasta_capturas = self.base / "capturas"
        self.pasta_templates.mkdir(parents=True, exist_ok=True)
        self.recompensas = ArquivoRecompensas(self.pasta_capturas, self.base / "dados" / "recompensas.json")
        self.historico = Historico(self.base / "dados" / "historico.json")
        self.ultima_captura: Quadro | None = None

        self._trava = threading.Lock()
        self._thread: threading.Thread | None = None
        self._parar = threading.Event()
        self._maquina: Maquina | None = None
        self._entrada: Entrada | None = None
        self._modo = ""
        self._sessao: dict | None = None
        self._relogio: Callable[[], float] = time.monotonic
        self._inicio = 0.0
        self._progresso: dict | None = None
        self._foco_ocioso: Foco | None = None
        self._motivo_parada = ""

    # ------------------------------------------------------------------ fábricas
    def _criar_foco(self) -> Foco:
        from .foco import FocoWindows

        return FocoWindows(self.armazem.atual.deteccao.titulo_janela)

    def novo_detector(self) -> Detector:
        det = self.armazem.atual.deteccao
        return Detector(self.pasta_templates, det.escala, det.limiar)

    @property
    def rodando(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------------ controle
    def iniciar(self, modo: str = "real", pasta: str | None = None, repetir: int = 1) -> None:
        if modo not in MODOS:
            raise ValueError(f"Modo desconhecido: {modo}")
        with self._trava:
            if self.rodando:
                return
            cfg = self.armazem.atual
            capturador: Capturador
            if modo == "simulacao":
                if not pasta:
                    raise ValueError("Informe a pasta de screenshots da simulação.")
                capturador = CapturadorPasta(Path(pasta), repetir)
                if not capturador.arquivos:
                    raise ValueError("A pasta da simulação não tem imagens.")
                entrada: Entrada = EntradaSimulada(self.log.info)
                foco: Foco = FocoSimulado(True)
                self._progresso = {"quadro": 0, "total": capturador.total}
                virtual = {"t": 0.0}
                self._relogio = lambda: virtual["t"]
                self._avancar = lambda: virtual.__setitem__("t", virtual["t"] + PASSO_S)
                self._dormir = 0.002
            else:
                if sys.platform != "win32" and modo == "real":
                    raise RuntimeError("O modo real só funciona no Windows.")
                capturador = CapturadorTela(cfg.deteccao.monitor)
                if modo == "real":
                    from .entrada import EntradaDireta

                    entrada = EntradaDireta()
                else:
                    entrada = EntradaSimulada(self.log.info)
                foco = self._criar_foco() if sys.platform == "win32" else FocoSimulado(True)
                self._progresso = None
                self._relogio = time.monotonic
                self._avancar = lambda: None
                self._dormir = PASSO_S

            detector = self.novo_detector()
            agora = datetime.now()
            self._sessao = {
                "id": f"{agora:%Y%m%d-%H%M%S}", "inicio": agora.isoformat(timespec="seconds"),
                "fim": None, "modo": modo, "partidas": 0, "tesouros": 0, "por_tipo": {},
                "duracao_s": 0, "motivo": "",
            }
            self._maquina = Maquina(cfg, detector, entrada, foco, self.log, self.recompensas,
                                    sessao=self._sessao["id"], ao_recompensa=self._ao_recompensa)
            self._entrada = entrada
            self._modo = modo
            self._motivo_parada = ""
            self._parar.clear()
            self._inicio = self._relogio()
            self.historico.gravar(self._sessao)
            faltando = [t.nome for t in catalogo.PRINCIPAIS if not detector.tem(t.nome)]
            self.log.info(f"Iniciado em modo {modo}. Templates carregados: {len(detector.nomes())}.")
            if faltando:
                self.log.aviso("Templates principais ausentes (estados ignorados): " + ", ".join(faltando))
            self._thread = threading.Thread(target=self._laco, args=(capturador,), daemon=True,
                                            name="atalaia-motor")
            self._thread.start()
        self.publicar_estado()

    def parar(self, motivo: str = "parado pelo usuário") -> None:
        """Para tudo e solta todas as teclas. Seguro de chamar de qualquer thread."""
        thread = self._thread
        if not self.rodando:
            return
        self._motivo_parada = self._motivo_parada or motivo
        self._parar.set()
        if self._entrada:
            try:
                self._entrada.soltar_tudo()
            except Exception:
                pass
        if thread and thread is not threading.current_thread():
            thread.join(timeout=5)
        self.publicar_estado()

    def alternar(self) -> None:
        """Atalho F8: se está rodando, para; senão, inicia em modo real."""
        if self.rodando:
            self.parar("parado pelo F8")
        else:
            try:
                self.iniciar("real")
            except Exception as erro:
                self.log.erro(f"Não foi possível iniciar: {erro}")

    # ------------------------------------------------------------------ laço
    def _laco(self, capturador: Capturador) -> None:
        maquina = self._maquina
        assert maquina is not None
        proximo_tick = self._relogio()
        proxima_pub = 0.0
        falhas = 0
        try:
            while not self._parar.is_set():
                agora = self._relogio()
                if agora >= proximo_tick:
                    proximo_tick = agora + self.armazem.atual.automacao.intervalo_checagem_s
                    try:
                        quadro = capturador.capturar()
                        falhas = 0
                    except Exception as erro:
                        falhas += 1
                        self.log.erro(f"Falha ao capturar a tela: {erro}")
                        if falhas >= 5:
                            self._motivo_parada = "falhas seguidas de captura"
                            break
                        quadro = False
                    if quadro is None:
                        self._motivo_parada = "fim da simulação"
                        break
                    if quadro:
                        if self._progresso:
                            self._progresso["quadro"] += 1
                            self._progresso["arquivo"] = quadro.origem
                        maquina.tick(quadro, agora)
                        if maquina.pedido_parada:
                            self._motivo_parada = maquina.pedido_parada
                            break
                else:
                    maquina.animar(agora)
                if time.monotonic() >= proxima_pub:
                    proxima_pub = time.monotonic() + 1.0
                    self.publicar_estado()
                self._avancar()
                time.sleep(self._dormir)
        except Exception as erro:  # nunca deixar tecla presa por causa de um erro
            self._motivo_parada = f"erro: {erro}"
            self.log.erro(f"Erro no motor: {erro!r}")
        finally:
            try:
                maquina.parar()
            except Exception:
                pass
            self._finalizar()

    def _finalizar(self) -> None:
        maquina, sessao = self._maquina, self._sessao
        if maquina and sessao:
            sessao.update(
                fim=datetime.now().isoformat(timespec="seconds"),
                partidas=maquina.partidas, tesouros=maquina.tesouros,
                por_tipo=dict(maquina.por_tipo),
                duracao_s=round(self._relogio() - self._inicio),
                motivo=self._motivo_parada or "parado",
            )
            self.historico.gravar(sessao)
        self.log.info(f"Parado ({self._motivo_parada or 'parado'}). Todas as teclas soltas.")
        self._thread = None
        self.publicar_estado()

    def _ao_recompensa(self, item: dict) -> None:
        self.publicar({"tipo": "recompensa", "item": item})

    # ------------------------------------------------------------------ estado
    def _em_foco_ocioso(self) -> bool:
        if sys.platform != "win32":
            return False
        try:
            if self._foco_ocioso is None:
                self._foco_ocioso = self._criar_foco()
            return self._foco_ocioso.em_foco()
        except Exception:
            return False

    def estado(self) -> dict:
        maquina = self._maquina
        rodando = self.rodando
        base = {
            "rodando": rodando, "modo": self._modo if rodando else "", "fase": "parado",
            "pausado": False, "em_foco": False, "partidas": 0, "partidas_hora": 0.0,
            "tesouros": 0, "por_tipo": {}, "tempo_partida_s": 0, "tempo_sessao_s": 0,
            "comportamento": "", "simulacao": self._progresso if rodando else None,
            "ultimo_motivo": self._motivo_parada,
            "alerta_pirata": self.recompensas.alerta_pendente(),
        }
        if maquina:
            # Parado, os contadores da última sessão continuam visíveis.
            base.update(partidas=maquina.partidas, tesouros=maquina.tesouros,
                        por_tipo=dict(maquina.por_tipo))
        if rodando and maquina:
            agora = self._relogio()
            sessao_s = max(0.0, agora - self._inicio)
            base.update(
                fase=maquina.fase.value, pausado=maquina.pausado, em_foco=not maquina.pausado,
                partidas_hora=round(maquina.partidas / (sessao_s / 3600), 1) if sessao_s >= 60 else 0.0,
                tempo_partida_s=round(maquina.tempo_partida(agora)), tempo_sessao_s=round(sessao_s),
                comportamento=maquina.movimento.nome_atual if maquina.fase.value == "em_partida" else "",
            )
        else:
            base["em_foco"] = self._em_foco_ocioso()
        return base

    def publicar_estado(self) -> None:
        try:
            self.publicar({"tipo": "estado", "estado": self.estado()})
        except Exception:
            pass

    # ------------------------------------------------------------------ ferramentas da interface
    def recarregar_templates(self) -> None:
        if self.rodando and self._maquina:
            self._maquina.detector.recarregar()

    def capturar_tela(self) -> Quadro:
        quadro = CapturadorTela(self.armazem.atual.deteccao.monitor).capturar()
        assert quadro is not None
        self.ultima_captura = quadro
        return quadro

    def testar_deteccao(self, quadro: Quadro | None = None) -> dict:
        """Score de cada template na tela atual. Não clica em nada."""
        quadro = quadro or self.capturar_tela()
        cfg = self.armazem.atual.deteccao
        detector = self.novo_detector()
        prep = detector.preparar(quadro)
        resultados = []
        for info in catalogo.TODOS:
            achado = detector.pontuar(prep, info.nome)
            limiar = cfg.limiar_recompensa if info.grupo == "recompensa" else cfg.limiar
            resultados.append({
                "nome": info.nome, "rotulo": info.rotulo, "grupo": info.grupo,
                "configurado": detector.tem(info.nome),
                "score": round(achado.score, 3) if achado else None,
                "detectado": bool(achado and achado.score >= limiar),
                "x": achado.x if achado else None, "y": achado.y if achado else None,
            })
        return {
            "resultados": resultados,
            "companheiros_mortos": detector.contar(prep, "companheiro_morto", cfg.regiao_squad),
            "largura": int(quadro.imagem.shape[1]), "altura": int(quadro.imagem.shape[0]),
        }
