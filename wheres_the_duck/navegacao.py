"""Ir até o meio do mapa: abre o mapa, marca o centro e segue a marcação pela tela.

A marcação aparece na tela com a distância ("350 m"). O bot lê esse texto e vira a
câmera na direção dele, como um jogador faria olhando a tela. Serve para não planar
nem andar em linha reta até o mar.
"""
from __future__ import annotations

import random
import re
from typing import Callable

from .captura import Quadro
from .entrada import Entrada
from .texto import Linha
from .visao import achar_zona_segura

DISTANCIA = re.compile(r"^(\d{1,4})M$")


def distancias_na_tela(linhas: list[Linha], altura: int) -> list[tuple[int, Linha]]:
    """Textos do tipo "350 m" fora das bordas de cima e de baixo (HUD)."""
    achados = []
    for l in linhas:
        m = DISTANCIA.match(l.compacto)
        if m and altura * 0.08 <= l.y <= altura * 0.92:
            achados.append((int(m.group(1)), l))
    return achados


class Navegador:
    def __init__(self, entrada: Entrada, obter_cfg: Callable, log, rng: random.Random):
        self.entrada = entrada
        self.obter_cfg = obter_cfg
        self.log = log
        self.rng = rng
        self.ativo = False          # seguindo a marcação
        self._agenda: list[tuple[float, Callable[[], None]]] = []
        self._dist: int | None = None
        self._sem_alvo = 0
        self._tentativas = 0
        self._dims: tuple[int, int, int, int] | None = None
        self._proximo_pulo = 0.0
        self._procurando = False   # mapa aberto, esperando um print para achar a zona segura
        self._prazo = 0.0
        self.ultima_marcacao = -1e9

    @property
    def cfg(self):
        return self.obter_cfg().navegacao

    @property
    def marcando(self) -> bool:
        return bool(self._agenda) or self._procurando

    # ------------------------------------------------------------------ marcação
    def agendar_marcacao(self, quando: float, dims: tuple[int, int, int, int] | None,
                         nova: bool = True, zona: bool | None = None) -> None:
        """Abre o mapa, marca (centro da zona segura ou meio do mapa) e fecha, em passos com pausas."""
        if not self.cfg.ativa or dims is None:
            return
        if nova:
            self._tentativas = 0
        zona = self.cfg.seguir_zona if zona is None else zona
        self._tentativas += 1
        self._dims = dims
        self._dist = None
        self._sem_alvo = 0
        self.ultima_marcacao = quando
        tecla = self.cfg.tecla_mapa

        def olhar_mapa():
            if zona:
                self._procurando = True
                self._prazo = quando + 4.0
                self._agenda.append((self._prazo, lambda: self._sem_zona(self._prazo)))
            else:
                self._marcar_em(self._centro_do_mapa(), quando + 1.3, "meio do mapa")

        self._agenda = [(quando, lambda: self.entrada.tocar(tecla)), (quando + 1.3, olhar_mapa)]

    def _centro_do_mapa(self) -> tuple[int, int]:
        w, h, ox, oy = self._dims
        return ox + int(self.cfg.centro_mapa[0] * w), oy + int(self.cfg.centro_mapa[1] * h)

    def _marcar_em(self, ponto: tuple[int, int], agora: float, oque: str) -> None:
        tecla = self.cfg.tecla_mapa

        def concluir():
            self.ativo = True
            self.log.info(f"Marcado o {oque}: seguindo a marcação.")

        self.entrada.clicar(ponto[0], ponto[1], self.cfg.botao_marcar)
        self._agenda = [(agora + 0.6, lambda: self.entrada.tocar(tecla)), (agora + 1.1, concluir)]

    def _sem_zona(self, agora: float) -> None:
        if self._procurando:
            self._procurando = False
            self._marcar_em(self._centro_do_mapa(), agora, "meio do mapa (zona segura não achada)")

    def ver_mapa(self, quadro: Quadro, agora: float) -> None:
        """Com o mapa aberto: acha o círculo branco da zona segura e marca o centro dele."""
        if not self._procurando:
            return
        zona = achar_zona_segura(quadro.imagem)
        if zona is None:
            return
        self._procurando = False
        x, y, _ = zona
        self._marcar_em((x + quadro.offset_x, y + quadro.offset_y), agora, "centro da zona segura")

    def cancelar_marcacao(self) -> None:
        self._agenda = []
        self._procurando = False

    def passo_agenda(self, agora: float) -> bool:
        """Executa os passos vencidos da marcação. True enquanto a marcação está em andamento."""
        while self._agenda and agora >= self._agenda[0][0]:
            _, acao = self._agenda.pop(0)
            acao()
        return self.marcando

    # ------------------------------------------------------------------ seguir a marcação
    def atualizar(self, linhas: list[Linha], agora: float) -> None:
        """Chamado a cada ciclo com os textos lidos: vira a câmera para a marcação."""
        if not self.ativo or self._dims is None:
            return
        w, h, _, _ = self._dims
        candidatos = distancias_na_tela(linhas, h)
        if self._dist is not None and candidatos:
            # Segue a mesma marcação: a distância muda pouco de um ciclo para o outro.
            perto = [c for c in candidatos if abs(c[0] - self._dist) <= max(80, self._dist * 0.5)]
            candidatos = sorted(perto, key=lambda c: abs(c[0] - self._dist))[:1]
        elif candidatos:
            candidatos = [max(candidatos, key=lambda c: c[0])]  # o meio do mapa costuma estar longe
        if not candidatos:
            self._sem_alvo += 1
            if self._sem_alvo >= self.cfg.ciclos_sem_alvo:
                if self._tentativas < self.cfg.tentativas:
                    self.log.info("Perdi a marcação de vista: marcando o meio do mapa de novo.")
                    self.parar(soltar=False)
                    self.agendar_marcacao(agora, self._dims, nova=False)
                else:
                    self.log.aviso("Não consegui seguir a marcação; voltando aos movimentos normais.")
                    self.parar()
            return
        dist, linha = candidatos[0]
        self._sem_alvo = 0
        self._dist = dist
        if dist <= self.cfg.chegada_m:
            self.log.info(f"Cheguei perto do meio do mapa ({dist} m).")
            self.parar()
            return
        cx = linha.x + linha.largura / 2
        desvio = (cx - w / 2) / (w / 2)  # -1 (esquerda) a 1 (direita)
        if abs(desvio) > 0.9:
            graus = 75 if desvio > 0 else -75  # presa na borda: a marcação está atrás
        else:
            graus = desvio * 40
        if abs(graus) >= 3:
            self.entrada.mover_mouse_rel(graus * self.obter_cfg().movimento.pixels_por_grau, 0)

    def andar(self, agora: float) -> None:
        """No chão: corre para a frente; a direção vem de atualizar()."""
        mov = self.obter_cfg().movimento
        self.entrada.tecla_baixo(mov.tecla_correr)
        self.entrada.tecla_baixo("w")
        if agora >= self._proximo_pulo:
            if self.rng.random() < 0.3:
                self.entrada.tocar("space")
            self._proximo_pulo = agora + self.rng.uniform(2, 5)

    def desviar(self, agora: float) -> None:
        self.entrada.tocar("space")
        graus = self.rng.choice((-1, 1)) * self.rng.uniform(50, 80)
        self.entrada.mover_mouse_rel(graus * self.obter_cfg().movimento.pixels_por_grau, 0)

    def parar(self, soltar: bool = True) -> None:
        self.ativo = False
        self._agenda = []
        self._procurando = False
        if soltar:
            self.entrada.tecla_cima("w")
            self.entrada.tecla_cima(self.obter_cfg().movimento.tecla_correr)
