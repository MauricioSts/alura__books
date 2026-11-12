"""Barras de vida da squad, detecção de bot preso e saída quando sozinho sem recorte."""
import json

import cv2
import numpy as np

from tests.conftest import Banco
from wheres_the_duck.captura import Quadro
from wheres_the_duck.config import ArmazemConfig, REGIAO_SQUAD_PADRAO
from wheres_the_duck.maquina import Fase
from wheres_the_duck.visao import barras_de_vida, contar_companheiros_vivos, diferenca, miniatura_cenario

REGIAO = list(REGIAO_SQUAD_PADRAO)
VERDE, AZUL, VERMELHO = (60, 200, 60), (230, 150, 40), (40, 40, 230)


def tela_squad(vivos=3, largura=1920, altura=1080, cenario=0, extras=()):
    img = np.full((altura, largura, 3), 45, np.uint8)
    # cenário: um padrão que "anda" conforme o deslocamento
    # Blocos grandes, como prédios e árvores; reduzidos, ainda mudam quando a câmera anda.
    rng = np.random.default_rng(7)
    blocos = rng.integers(0, 255, ((altura // 60) + 1, (largura + 1200) // 60 + 1), dtype=np.uint8)
    textura = cv2.resize(blocos, (blocos.shape[1] * 60, blocos.shape[0] * 60), interpolation=cv2.INTER_NEAREST)
    for canal in range(3):
        img[:, :, canal] = textura[:altura, cenario:cenario + largura] // 2 + 30
    escala = altura / 1080
    for i in range(vivos):
        x = int(1250 * largura / 1920)
        y = int((90 + 70 * i) * escala)
        cv2.rectangle(img, (x, y), (x + int(150 * escala), y + int(9 * escala)), VERDE, -1)
        cv2.rectangle(img, (x, y + int(12 * escala)), (x + int(110 * escala), y + int(19 * escala)), AZUL, -1)
    for cor, x, y in extras:
        cv2.rectangle(img, (x, y), (x + 150, y + 9), cor, -1)
    return img


# ---------------------------------------------------------------- barras
def test_conta_um_companheiro_por_linha_vida_e_escudo_juntos():
    for n in range(4):
        assert contar_companheiros_vivos(tela_squad(n), REGIAO) == n


def test_funciona_em_outra_resolucao():
    assert contar_companheiros_vivos(tela_squad(2, 1280, 720), REGIAO) == 2


def test_derrubado_ainda_conta_como_vivo():
    img = tela_squad(0, extras=[(VERMELHO, 1250, 100)])
    assert contar_companheiros_vivos(img, REGIAO) == 1


def test_barra_fora_da_regiao_e_formas_que_nao_sao_barra_sao_ignoradas():
    img = tela_squad(0, extras=[(VERDE, 200, 900)])  # vida do próprio bot, embaixo à esquerda
    cv2.rectangle(img, (1300, 300), (1360, 360), VERDE, -1)  # quadrado verde (mapa, árvore)
    assert barras_de_vida(img, REGIAO) == []


# ---------------------------------------------------------------- movimento da tela
def test_miniatura_detecta_cenario_parado_e_em_movimento():
    a = miniatura_cenario(tela_squad(3, cenario=0))
    assert diferenca(a, miniatura_cenario(tela_squad(3, cenario=0))) < 0.5
    assert diferenca(a, miniatura_cenario(tela_squad(3, cenario=40))) > 3
    assert diferenca(None, a) == 255.0


# ---------------------------------------------------------------- máquina
def partida_sem_template_de_icone(tmp_path):
    b = Banco(tmp_path, nomes=["jogar", "pular_onibus", "sair_partida", "confirmar_sair", "espectando"])
    b.tick("jogar")
    b.tick("pular_onibus")
    b.animar(b.cfg.salto.atraso_max_s + 1)
    b.animar(b.cfg.salto.tempo_planando_s + 1)
    assert b.maquina.fase == Fase.EM_PARTIDA
    return b


def tick_imagem(b, img, dt=1.5):
    b.agora += dt
    b.maquina.tick(Quadro(img), b.agora)


def test_sozinho_pelas_barras_sai_pelo_menu(tmp_path):
    b = partida_sem_template_de_icone(tmp_path)
    tick_imagem(b, tela_squad(2, 1280, 720, cenario=10))
    tick_imagem(b, tela_squad(0, 1280, 720, cenario=20))
    tick_imagem(b, tela_squad(0, 1280, 720, cenario=30))
    assert b.maquina.fase == Fase.EM_PARTIDA
    tick_imagem(b, tela_squad(0, 1280, 720, cenario=40))
    assert b.maquina.fase == Fase.SAINDO


def test_sem_nunca_ver_barras_nao_sai(tmp_path):
    """HUD diferente ou região errada: sem ter visto colegas, não conclui que está sozinho."""
    b = partida_sem_template_de_icone(tmp_path)
    for i in range(8):
        tick_imagem(b, tela_squad(0, 1280, 720, cenario=10 * i))
    assert b.maquina.fase == Fase.EM_PARTIDA


def test_um_colega_vivo_segura_o_bot_na_partida(tmp_path):
    b = partida_sem_template_de_icone(tmp_path)
    for i in range(8):
        tick_imagem(b, tela_squad(1, 1280, 720, cenario=10 * i))
    assert b.maquina.fase == Fase.EM_PARTIDA


def test_barras_desligadas(tmp_path):
    b = partida_sem_template_de_icone(tmp_path)
    b.cfg.deteccao.barras_vida = False
    tick_imagem(b, tela_squad(2, 1280, 720))
    for i in range(5):
        tick_imagem(b, tela_squad(0, 1280, 720, cenario=10 * i))
    assert b.maquina.fase == Fase.EM_PARTIDA


def test_preso_andando_pula_e_muda_de_direcao(tmp_path):
    b = partida_sem_template_de_icone(tmp_path)
    m = b.maquina
    # força um comportamento que anda
    while not m.movimento.andando:
        m.movimento.abandonar()
        b.animar(0.1)
        if not m.movimento.andando:
            m.movimento._fim = 0
    parada = tela_squad(2, 1280, 720, cenario=0)
    b.entrada.acoes.clear()
    tick_imagem(b, parada)
    tick_imagem(b, parada)
    tick_imagem(b, parada)
    msgs = [l["msg"] for l in b.registro.linhas()]
    assert any("Preso em obstáculo" in m_ for m_ in msgs)
    assert ("tocar", "space") in b.entrada.acoes
    assert any(a[0] == "mover" and abs(a[1]) >= 90 * b.cfg.movimento.pixels_por_grau for a in b.entrada.acoes)


def test_andando_de_verdade_nao_e_preso(tmp_path):
    b = partida_sem_template_de_icone(tmp_path)
    for i in range(10):
        b.animar(1.4)
        tick_imagem(b, tela_squad(2, 1280, 720, cenario=15 * i), dt=0.1)
    assert not any("Preso" in l["msg"] for l in b.registro.linhas())


def test_planeio_termina_cedo_se_ja_esta_parado_no_chao(tmp_path):
    b = Banco(tmp_path, nomes=["jogar", "pular_onibus"])
    b.tick("jogar")
    b.tick("pular_onibus")
    b.animar(b.cfg.salto.atraso_max_s + 1)
    assert b.maquina.fase == Fase.PLANANDO
    for i in range(6):  # caindo: cenário mudando
        tick_imagem(b, tela_squad(2, 1280, 720, cenario=20 * i), dt=2.5)
    assert b.maquina.fase == Fase.PLANANDO
    parada = tela_squad(2, 1280, 720, cenario=200)
    for _ in range(3):
        tick_imagem(b, parada)
    assert b.maquina.fase == Fase.EM_PARTIDA
    assert "w" not in b.entrada.teclas_pressionadas


# ---------------------------------------------------------------- config
def test_regiao_antiga_padrao_e_migrada_mas_regiao_editada_nao(tmp_path):
    arq = tmp_path / "config.json"
    arq.write_text(json.dumps({"deteccao": {"regiao_squad": [0.0, 0.0, 0.28, 0.5]}}), encoding="utf-8")
    assert ArmazemConfig(arq).atual.deteccao.regiao_squad == REGIAO
    arq.write_text(json.dumps({"deteccao": {"regiao_squad": [0.1, 0.1, 0.2, 0.3]}}), encoding="utf-8")
    assert ArmazemConfig(arq).atual.deteccao.regiao_squad == [0.1, 0.1, 0.2, 0.3]
