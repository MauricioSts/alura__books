"""Tempestade, zona segura no mapa, tiros a esmo e pesos novos."""
import json
import random

import cv2
import numpy as np

from tests.test_navegacao import Partida, distancia
from wheres_the_duck.captura import Quadro
from wheres_the_duck.comportamentos import GerenciadorMovimento
from wheres_the_duck.config import ArmazemConfig, Movimento
from wheres_the_duck.entrada import EntradaSimulada
from wheres_the_duck.maquina import Fase
from wheres_the_duck.visao import achar_zona_segura, na_tempestade


def mapa(centro=(1100, 480), raio=180, largura=1920, altura=1080):
    """Mapa aberto: ilha esverdeada, água azul, tempestade roxa e o círculo branco da zona."""
    img = np.full((altura, largura, 3), (120, 70, 20), np.uint8)  # água
    cv2.circle(img, (960, 540), 430, (60, 140, 70), -1)            # ilha
    rng = np.random.default_rng(3)
    for _ in range(40):  # estradas, rios e detalhes do mapa
        p1 = tuple(int(v) for v in rng.integers((560, 140), (1360, 940)))
        p2 = tuple(int(v) for v in rng.integers((560, 140), (1360, 940)))
        cv2.line(img, p1, p2, (90, 160, 170), 3)
    roxo = img.copy()
    roxo[:] = (150, 40, 130)
    mascara = np.ones((altura, largura), np.uint8)
    cv2.circle(mascara, centro, raio + 120, 0, -1)
    img[mascara == 1] = (0.5 * img[mascara == 1] + 0.5 * roxo[mascara == 1]).astype(np.uint8)
    cv2.circle(img, centro, raio, (255, 255, 255), 3)
    return img


def tela_tempestade():
    img = np.full((1080, 1920, 3), (90, 110, 90), np.uint8)
    cv2.rectangle(img, (0, 0), (1919, 1079), (170, 40, 150), 420)  # bordas roxas
    return img


# ---------------------------------------------------------------- detectores
def test_acha_o_circulo_da_zona_segura():
    for centro, raio in (((1100, 480), 180), ((800, 650), 90), ((960, 540), 300)):
        achado = achar_zona_segura(mapa(centro, raio))
        assert achado, centro
        x, y, r = achado
        assert abs(x - centro[0]) <= 8 and abs(y - centro[1]) <= 8 and abs(r - raio) <= 12


def test_sem_circulo_nao_inventa():
    img = mapa()
    cv2.circle(img, (1100, 480), 180, (60, 140, 70), 5)  # apaga o anel
    assert achar_zona_segura(img) is None
    assert achar_zona_segura(np.zeros((720, 1280, 3), np.uint8)) is None


def test_tela_roxa_e_tempestade_tela_normal_nao():
    assert na_tempestade(tela_tempestade())
    assert not na_tempestade(np.full((1080, 1920, 3), (90, 110, 90), np.uint8))


# ---------------------------------------------------------------- fluxo
def test_depois_do_salto_marca_o_centro_da_zona_segura(tmp_path):
    p = Partida(tmp_path, seguir_zona=True)
    p.saltar()
    p.animar(2.5 + 1.4)       # abriu o mapa
    assert p.m.nav.marcando
    p.tick(img=mapa((1100, 480), 180), dt=0.1)
    cliques = [a for a in p.entrada.acoes if a[0] == "clicar_meio"]
    assert cliques and abs(cliques[-1][1] - 1100) <= 8 and abs(cliques[-1][2] - 480) <= 8
    p.animar(2)
    assert p.m.nav.ativo and not p.m.nav.marcando
    assert any("zona segura" in l["msg"] for l in p.m.log.linhas())


def test_sem_zona_no_mapa_marca_o_meio(tmp_path):
    p = Partida(tmp_path, seguir_zona=True)
    p.saltar()
    p.animar(2.5 + 1.4)
    p.tick(dt=0.1)            # tela sem círculo
    p.animar(5)
    assert ("clicar_meio", 960, 540) in p.entrada.acoes and p.m.nav.ativo


def test_remarca_de_tempos_em_tempos(tmp_path):
    p = Partida(tmp_path, seguir_zona=True, intervalo_zona_s=120)
    p.saltar()
    p.animar(p.cfg.salto.tempo_planando_s + 1)  # ~78 s desde a primeira marcação
    abertas = p.entrada.acoes.count(("tocar", "m"))
    p.tick(distancia(500, 960), dt=30)
    p.animar(1)
    assert p.entrada.acoes.count(("tocar", "m")) == abertas
    p.tick(distancia(480, 960), dt=20)
    p.animar(1)
    assert p.entrada.acoes.count(("tocar", "m")) == abertas + 1


def test_dentro_da_tempestade_remarca_na_hora(tmp_path):
    p = Partida(tmp_path, seguir_zona=True, intervalo_zona_s=600)
    p.saltar()
    p.animar(p.cfg.salto.tempo_planando_s + 1)
    abertas = p.entrada.acoes.count(("tocar", "m"))
    p.tick(img=tela_tempestade(), dt=25)
    p.tick(img=tela_tempestade())
    p.animar(1)
    assert p.entrada.acoes.count(("tocar", "m")) == abertas + 1
    assert any("tempestade" in l["msg"] for l in p.m.log.linhas())
    assert p.m.fase == Fase.EM_PARTIDA


# ---------------------------------------------------------------- tiros a esmo
def test_atirar_pega_arma_e_da_rajadas_andando():
    cfg = Movimento()
    for nome in ("esconder", "reposicionar", "rondar", "coletar", "olhar"):
        getattr(cfg, nome).peso = 0
    entrada = EntradaSimulada()
    g = GerenciadorMovimento(entrada, cfg, random.Random(4))
    t = 0.0
    while t < 8:
        g.passo(t)
        t += 0.1
    nomes = entrada.nomes()
    assert g.nome_atual == "atirar"
    assert any(a[0] == "tocar" and a[1] in "12345" for a in entrada.acoes)
    assert nomes.count("mouse_baixo") >= 2 and nomes.count("mouse_cima") >= 1
    assert any(a[0] == "segurar" and a[1] in "wasd" for a in entrada.acoes)
    g.atual.encerrar()
    assert not entrada.mouse_pressionado


# ---------------------------------------------------------------- pesos
def test_pesos_antigos_padrao_viram_os_novos(tmp_path):
    arq = tmp_path / "config.json"
    antigo = {n: {"peso": p, "duracao_min_s": 4, "duracao_max_s": 10}
              for n, p in {"esconder": 4, "reposicionar": 2, "rondar": 2, "coletar": 1, "olhar": 2}.items()}
    arq.write_text(json.dumps({"movimento": antigo}), encoding="utf-8")
    mov = ArmazemConfig(arq).atual.movimento
    assert mov.esconder.peso == Movimento().esconder.peso < mov.reposicionar.peso
    editado = dict(antigo, esconder={"peso": 9, "duracao_min_s": 4, "duracao_max_s": 10})
    arq.write_text(json.dumps({"movimento": editado}), encoding="utf-8")
    assert ArmazemConfig(arq).atual.movimento.esconder.peso == 9


def test_padroes_antigos_errados_sao_atualizados(tmp_path):
    arq = tmp_path / "config.json"
    arq.write_text(json.dumps({
        "salto": {"atraso_min_s": 28, "atraso_max_s": 40},
        "navegacao": {"botao_marcar": "esquerdo"},
        "movimento": {"tecla_correr": "shift"},
    }), encoding="utf-8")
    cfg = ArmazemConfig(arq).atual
    assert (cfg.salto.atraso_min_s, cfg.salto.atraso_max_s) == (3, 10)
    assert cfg.navegacao.botao_marcar == "meio" and cfg.movimento.tecla_correr == ""
    arq.write_text(json.dumps({"salto": {"atraso_min_s": 20, "atraso_max_s": 25}}), encoding="utf-8")
    assert ArmazemConfig(arq).atual.salto.atraso_min_s == 20  # editado à mão: mantido
