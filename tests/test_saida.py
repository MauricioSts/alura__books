"""Saída pelo menu ESC: menu sanduíche (≡) reconhecido pelo formato e caminho adaptável."""
import random

import cv2
import numpy as np

from wheres_the_duck.captura import Quadro
from wheres_the_duck.config import Config
from wheres_the_duck.deteccao import Detector
from wheres_the_duck.entrada import EntradaSimulada
from wheres_the_duck.foco import FocoSimulado
from wheres_the_duck.maquina import Fase, Maquina
from wheres_the_duck.registro import Registro
from wheres_the_duck.texto import LeitorFixo, Linha
from wheres_the_duck.visao import achar_menu_sanduiche


def tela(icone=None, largura=1920, altura=1080, texto_falso=False):
    img = np.full((altura, largura, 3), 35, np.uint8)
    img[:, :, 2] += (np.arange(largura) % 20).astype(np.uint8)
    if icone:
        x, y, tam = icone
        traco = max(2, tam // 7)
        for i in range(3):
            yy = y + i * (tam // 3)
            cv2.rectangle(img, (x, yy), (x + tam, yy + traco), (245, 245, 245), -1)
    if texto_falso:
        # Linhas de uma lista (4 ou mais) não são o ícone.
        for i in range(6):
            cv2.rectangle(img, (300, 300 + 14 * i), (330, 303 + 14 * i), (250, 250, 250), -1)
        cv2.putText(img, "VOLTAR AO LOBBY", (900, 700), cv2.FONT_HERSHEY_DUPLEX, 1.4, (255, 255, 255), 3)
    return img


def test_acha_o_icone_em_varios_tamanhos_e_resolucoes():
    for largura, altura, tam in ((1920, 1080, 32), (1280, 720, 22), (2560, 1440, 44)):
        x, y = int(largura * 0.95), int(altura * 0.04)
        achado = achar_menu_sanduiche(tela((x, y, tam), largura, altura))
        assert achado, (largura, tam)
        assert abs(achado[0] - (x + tam // 2)) <= 3 and abs(achado[1] - (y + tam // 3)) <= tam


def test_lista_e_texto_nao_sao_confundidos_com_o_icone():
    assert achar_menu_sanduiche(tela(texto_falso=True)) is None
    assert achar_menu_sanduiche(tela()) is None


class Roteiro:
    def __init__(self, tmp_path):
        self.leitor = LeitorFixo()
        self.cfg = Config()
        self.cfg.navegacao.ativa = False  # navegação tem testes próprios
        self.cfg.automacao.tempo_max_partida_min = 1
        self.det = Detector(tmp_path / "vazia", leitor=self.leitor, padroes=self.cfg.textos.padroes)
        self.entrada = EntradaSimulada()
        self.m = Maquina(self.cfg, self.det, self.entrada, FocoSimulado(True), Registro(),
                         rng=random.Random(5))
        self.agora = 100.0

    def tick(self, img=None, *linhas, dt=3.0):
        self.leitor.linhas = list(linhas)
        self.agora += dt
        self.m.tick(Quadro(img if img is not None else tela()), self.agora)

    def cliques(self):
        return [a[1:] for a in self.entrada.acoes if a[0] == "clicar"]

    def em_partida_saindo(self):
        self.tick(None, Linha("JOGAR", 1600, 980, 140, 50, 0.9))
        self.tick(dt=200)  # fila sem ônibus: partida em andamento
        self.tick(dt=61)   # tempo máximo de 1 min atingido
        assert self.m.fase == Fase.SAINDO and ("tocar", "esc") in self.entrada.acoes


def test_esc_menu_sanduiche_voltar_ao_lobby_confirmar(tmp_path):
    r = Roteiro(tmp_path)
    r.em_partida_saindo()
    r.tick(tela((1820, 40, 32)))  # menu ESC aberto: só o ícone ≡ visível
    assert r.cliques()[-1][0] in range(1830, 1842)
    r.tick(None, Linha("VOLTAR AO LOBBY", 820, 620, 280, 40, 0.9))
    assert r.cliques()[-1] == (960, 640)
    r.tick(None, Linha("CONFIRMAR", 900, 500, 160, 40, 0.9))
    assert r.cliques()[-1] == (980, 520)
    assert r.m.fase == Fase.LOBBY and len(r.cliques()) == 4  # Jogar, ≡, Voltar, Confirmar


def test_voltar_direto_no_menu_esc_sem_sanduiche_e_sem_confirmacao(tmp_path):
    r = Roteiro(tmp_path)
    r.em_partida_saindo()
    r.tick(None, Linha("RETORNAR AO LOBBY", 820, 620, 280, 40, 0.9))
    r.tick()
    r.tick()
    assert r.m.fase == Fase.LOBBY and len(r.cliques()) == 2


def test_sim_solto_na_tela_nao_e_clicado_antes_de_voltar_ao_lobby(tmp_path):
    r = Roteiro(tmp_path)
    r.em_partida_saindo()
    r.tick(None, Linha("SIM", 900, 500, 60, 40, 0.9))
    assert len(r.cliques()) == 1  # só o Jogar


def test_desiste_e_fecha_o_menu_se_nada_aparece(tmp_path):
    r = Roteiro(tmp_path)
    r.em_partida_saindo()
    for _ in range(4):
        r.tick()
    assert r.m.fase == Fase.EM_PARTIDA
    assert r.entrada.acoes.count(("tocar", "esc")) == 2
