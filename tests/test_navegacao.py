"""Marcar o meio do mapa e seguir a marcação pela distância mostrada na tela."""
import random

import numpy as np

from wheres_the_duck.captura import Quadro
from wheres_the_duck.config import Config
from wheres_the_duck.deteccao import Detector
from wheres_the_duck.entrada import EntradaSimulada
from wheres_the_duck.foco import FocoSimulado
from wheres_the_duck.maquina import Fase, Maquina
from wheres_the_duck.registro import Registro
from wheres_the_duck.texto import LeitorFixo, Linha

TELA = np.full((1080, 1920, 3), 50, np.uint8)


def distancia(metros, x):
    return Linha(f"{metros} m", x, 500, 60, 22, 0.9)


class Partida:
    def __init__(self, tmp_path, **nav):
        self.leitor = LeitorFixo()
        self.cfg = Config()
        for k, v in nav.items():
            setattr(self.cfg.navegacao, k, v)
        self.det = Detector(tmp_path / "vazia", leitor=self.leitor, padroes=self.cfg.textos.padroes)
        self.entrada = EntradaSimulada()
        self.m = Maquina(self.cfg, self.det, self.entrada, FocoSimulado(True), Registro(),
                         rng=random.Random(2))
        self.agora = 100.0

    def tick(self, *linhas, dt=1.5, img=None):
        self.leitor.linhas = list(linhas)
        self.agora += dt
        self.m.tick(Quadro(TELA if img is None else img), self.agora)

    def animar(self, segundos):
        fim = self.agora + segundos
        while self.agora < fim:
            self.agora += 0.1
            self.m.animar(self.agora)

    def saltar(self):
        self.tick(Linha("JOGAR", 1600, 980, 140, 50, 0.9))
        self.tick(Linha("PULAR", 900, 900, 90, 30, 0.9))
        self.entrada.acoes.clear()
        self.animar(self.cfg.salto.atraso_max_s + 0.5)

    def giros(self):
        return [a[1] for a in self.entrada.acoes if a[0] == "mover"]


def test_depois_do_salto_abre_o_mapa_marca_o_centro_e_fecha(tmp_path):
    p = Partida(tmp_path)
    p.saltar()
    p.animar(5)
    acoes = p.entrada.acoes
    i = acoes.index(("tocar", "m"))
    assert acoes[i + 1] == ("clicar", 960, 540) and acoes[i + 2] == ("tocar", "m")
    assert p.m.nav.ativo and p.m.fase == Fase.PLANANDO


def test_nada_de_clique_de_interface_enquanto_o_mapa_esta_aberto(tmp_path):
    p = Partida(tmp_path)
    p.saltar()
    p.animar(1.5)  # marcação agendada para 2,5 s depois do salto
    p.animar(1.5)
    assert p.m.nav.marcando
    p.tick(Linha("CONTINUAR", 900, 600, 160, 40, 0.9), dt=0.1)
    assert not any(a[0] == "clicar" and a[1:] != (960, 540) for a in p.entrada.acoes)


def test_vira_para_o_lado_da_marcacao_e_para_ao_chegar(tmp_path):
    p = Partida(tmp_path)
    p.saltar()
    p.animar(5)
    p.entrada.acoes.clear()
    p.tick(distancia(900, 1500))  # à direita
    assert p.giros() and p.giros()[-1] > 0
    p.entrada.acoes.clear()
    p.tick(distancia(880, 300))  # à esquerda
    assert p.giros()[-1] < 0
    p.entrada.acoes.clear()
    p.tick(distancia(860, 950))  # quase no meio: não vira
    assert p.giros() == []
    p.tick(distancia(1910, 1880))  # na borda, mas é outra marcação (distância muito diferente)
    p.tick(distancia(40, 960))
    assert not p.m.nav.ativo or p.m.nav._dist == 860


def test_chegada_volta_aos_comportamentos(tmp_path):
    p = Partida(tmp_path)
    p.saltar()
    p.animar(5)
    p.tick(distancia(120, 960))
    p.tick(distancia(90, 960))
    p.tick(distancia(55, 960))
    assert not p.m.nav.ativo
    assert any("Cheguei perto" in l["msg"] for l in p.m.log.linhas())


def test_marcacao_atras_vira_bastante(tmp_path):
    p = Partida(tmp_path)
    p.saltar()
    p.animar(5)
    p.entrada.acoes.clear()
    p.tick(distancia(700, 1895))
    assert p.giros()[-1] == 75 * p.cfg.movimento.pixels_por_grau


def test_no_chao_corre_ate_a_marcacao(tmp_path):
    p = Partida(tmp_path)
    p.saltar()
    p.animar(p.cfg.salto.tempo_planando_s + 1)
    p.tick(distancia(500, 960))
    assert p.m.fase == Fase.EM_PARTIDA and p.m.nav.ativo
    p.animar(1)
    assert {"w", "shift"} <= p.entrada.teclas_pressionadas


def test_perde_a_marcacao_marca_de_novo_e_depois_desiste(tmp_path):
    p = Partida(tmp_path, ciclos_sem_alvo=3, tentativas=2)
    p.saltar()
    p.animar(5)
    for _ in range(3):
        p.tick()
    assert p.m.nav.marcando  # segunda tentativa
    p.animar(3)
    assert p.entrada.acoes.count(("tocar", "m")) == 4
    for _ in range(3):
        p.tick()
    assert not p.m.nav.ativo and not p.m.nav.marcando


def test_revivido_tambem_marca_o_centro(tmp_path):
    p = Partida(tmp_path)
    p.tick(Linha("JOGAR", 1600, 980, 140, 50, 0.9))
    p.tick(dt=200)
    p.tick(Linha("MODO ESPECTADOR", 800, 20, 300, 30, 0.9))
    assert p.m.fase == Fase.ESPECTANDO
    p.tick()
    p.tick()
    assert p.m.fase == Fase.PLANANDO
    p.entrada.acoes.clear()
    p.animar(5)
    assert ("tocar", "m") in p.entrada.acoes and ("clicar", 960, 540) in p.entrada.acoes


def test_botao_direito_e_centro_configuraveis(tmp_path):
    p = Partida(tmp_path, botao_marcar="direito", centro_mapa=[0.45, 0.5])
    p.saltar()
    p.animar(5)
    assert ("clicar_direito", 864, 540) in p.entrada.acoes


def test_navegacao_desligada(tmp_path):
    p = Partida(tmp_path, ativa=False)
    p.saltar()
    p.animar(5)
    assert ("tocar", "m") not in p.entrada.acoes and not p.m.nav.ativo
