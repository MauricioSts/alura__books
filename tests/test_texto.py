"""Leitura de texto: lógica com leitor fixo e o OCR real sobre telas desenhadas."""
import random

import cv2
import numpy as np
import pytest

from wheres_the_duck.captura import Quadro
from wheres_the_duck.config import PADROES_TEXTO, Config
from wheres_the_duck.deteccao import Detector
from wheres_the_duck.entrada import EntradaSimulada
from wheres_the_duck.foco import FocoSimulado
from wheres_the_duck.maquina import Fase, Maquina
from wheres_the_duck.recompensas import ArquivoRecompensas
from wheres_the_duck.registro import Registro
from wheres_the_duck.texto import LeitorFixo, LeitorRapidOCR, Linha, compactar, contem, linha_igual

TELA = Quadro(np.full((720, 1280, 3), 50, np.uint8))


def linha(texto, x=600, y=600, altura=40):
    return Linha(texto, x, y, len(texto) * 20, altura, 0.9)


def detector(tmp_path, *linhas):
    return Detector(tmp_path / "vazia", leitor=LeitorFixo(list(linhas)), padroes=PADROES_TEXTO)


# ---------------------------------------------------------------- comparação
def test_compactar_tira_acento_espaco_e_caixa():
    assert compactar("Você encontrou!") == "VOCEENCONTROU"
    assert compactar("ACESSO À LOJA PIRATA") == "ACESSOALOJAPIRATA"


def test_botao_exige_a_linha_inteira():
    assert linha_igual("JOGAR", "JOGAR")
    assert not linha_igual("JOGARNOVAMENTE", "JOGAR")
    assert linha_igual("ERESGATAR", "RESGATAR")  # tecla de atalho junto


def test_contem_tolera_erro_em_texto_longo():
    assert contem("XXVOCEENCONTR0UXX", "VOCEENCONTROU")
    assert not contem("POCAODEESCUDO", "VOCEENCONTROU")


# ---------------------------------------------------------------- detector
def test_sem_template_localiza_pelo_texto_e_soma_offset(tmp_path):
    det = detector(tmp_path, linha("JOGAR", 1000, 600))
    prep = det.preparar(Quadro(TELA.imagem, 1920, 0))
    achado = det.localizar(prep, "jogar")
    assert achado and (achado.x, achado.y) == (1000 + 50 + 1920, 620)


def test_jogar_nao_casa_com_jogar_novamente(tmp_path):
    det = detector(tmp_path, linha("JOGAR NOVAMENTE"))
    prep = det.preparar(TELA)
    assert det.localizar(prep, "jogar") is None
    assert det.localizar(prep, "jogar_novamente") is not None


def test_varios_jogar_escolhe_o_maior(tmp_path):
    det = detector(tmp_path, linha("JOGAR", 100, 20, altura=18), linha("JOGAR", 1000, 620, altura=60))
    achado = det.localizar(det.preparar(TELA), "jogar")
    assert achado.y == 650


def test_ocr_roda_uma_vez_por_ciclo(tmp_path):
    det = detector(tmp_path, linha("RESGATAR"))
    prep = det.preparar(TELA)
    for nome in ("jogar", "resgatar", "continuar", "espectando", "fim_partida"):
        det.localizar(prep, nome)
    assert det.leitor.chamadas == 1


def test_template_recortado_tem_prioridade(tmp_path):
    from tests.conftest import Cena

    cena = Cena(tmp_path / "t", nomes=["jogar"])
    det = Detector(cena.pasta, leitor=LeitorFixo([linha("JOGAR")]), padroes=PADROES_TEXTO)
    assert not det.por_texto("jogar") and det.por_texto("resgatar")
    assert det.localizar(det.preparar(TELA), "jogar") is None  # o template não está na tela


def test_texto_quebrado_em_duas_linhas(tmp_path):
    det = detector(tmp_path, linha("VOCÊ ENCONTROU", y=100), linha("ACESSO À LOJA", y=150), linha("PIRATA", y=200))
    prep = det.preparar(TELA)
    assert det.localizar(prep, "aviso_encontrou")
    tipo, _ = det.classificar(prep, ["acesso_pirata", "gizmo"], 0.8)
    assert tipo == "acesso_pirata"


def test_ocr_com_erro_nao_derruba(tmp_path):
    class Quebrado(LeitorFixo):
        def ler(self, imagem):
            raise RuntimeError("modelo corrompido")

    det = Detector(tmp_path / "v", leitor=Quebrado(), padroes=PADROES_TEXTO)
    assert det.localizar(det.preparar(TELA), "jogar") is None
    assert "corrompido" in det.erro_leitura


def test_sem_leitor_e_sem_template_nada_e_disponivel(tmp_path):
    det = Detector(tmp_path / "v", padroes=PADROES_TEXTO)
    assert not det.disponivel("jogar") and det.localizar(det.preparar(TELA), "jogar") is None


# ---------------------------------------------------------------- máquina sem nenhum template
class Roteiro:
    def __init__(self, tmp_path):
        self.leitor = LeitorFixo()
        self.cfg = Config()
        self.cfg.navegacao.ativa = False  # navegação tem testes próprios
        self.det = Detector(tmp_path / "vazia", leitor=self.leitor, padroes=self.cfg.textos.padroes)
        self.entrada = EntradaSimulada()
        self.rec = ArquivoRecompensas(tmp_path / "cap", tmp_path / "rec.json")
        self.m = Maquina(self.cfg, self.det, self.entrada, FocoSimulado(True), Registro(), self.rec,
                         rng=random.Random(3))
        self.agora = 100.0

    def tick(self, *linhas, dt=1.5):
        self.leitor.linhas = list(linhas)
        self.agora += dt
        self.m.tick(TELA, self.agora)

    def cliques(self):
        return [a for a in self.entrada.acoes if a[0] == "clicar"]


def test_ciclo_completo_so_com_leitura_de_texto(tmp_path):
    r = Roteiro(tmp_path)
    r.tick(linha("JOGAR", 1000, 600))
    assert r.m.fase == Fase.FILA and r.m.partidas == 1 and len(r.cliques()) == 1
    r.tick(linha("PULAR", 600, 650))
    assert r.m.fase == Fase.ONIBUS
    r.tick(linha("VOCÊ ENCONTROU", y=100), linha("ACESSO À LOJA PIRATA", y=150), dt=60)
    assert r.m.por_tipo == {"acesso_pirata": 1}
    assert r.rec.alerta_pendente()["tipo"] == "acesso_pirata"


def test_pular_escrito_no_lobby_nao_vira_onibus(tmp_path):
    r = Roteiro(tmp_path)
    r.tick(linha("PULAR"))
    assert r.m.fase == Fase.LOBBY and r.entrada.acoes == []


def test_loja_pirata_no_lobby_nao_e_recompensa(tmp_path):
    r = Roteiro(tmp_path)
    r.tick(linha("LOJA PIRATA"))
    assert r.m.tesouros == 0


def test_fim_inferido_precisa_de_dois_ciclos_e_nao_vale_espectando(tmp_path):
    r = Roteiro(tmp_path)
    r.tick(linha("JOGAR"))
    r.tick(dt=200)  # fila sem ônibus: assume partida
    assert r.m.fase == Fase.EM_PARTIDA
    for _ in range(4):
        r.tick(linha("RETORNAR AO LOBBY", 900, 650), linha("ESPECTANDO JogadorX", 500, 600))
    assert r.m.fase == Fase.ESPECTANDO and len(r.cliques()) == 1  # só o clique em Jogar
    r.tick(linha("RETORNAR AO LOBBY", 900, 650))  # um ciclo só: ainda não sai
    assert r.m.fase != Fase.LOBBY and len(r.cliques()) == 1
    r.tick(linha("RETORNAR AO LOBBY", 900, 650), dt=3)
    assert r.m.fase == Fase.LOBBY and len(r.cliques()) == 2


def test_saida_pelo_esc_funciona_por_texto(tmp_path):
    r = Roteiro(tmp_path)
    r.cfg.automacao.tempo_max_partida_min = 1
    r.tick(linha("JOGAR"))
    r.tick(dt=200)
    r.tick(dt=61)
    assert r.m.fase == Fase.SAINDO
    r.tick(linha("SAIR DA PARTIDA", 300, 500), dt=3)
    r.tick(linha("CONFIRMAR", 640, 400), dt=3)
    assert r.m.fase == Fase.LOBBY


# ---------------------------------------------------------------- OCR de verdade
@pytest.mark.skipif(not LeitorRapidOCR.disponivel(), reason="rapidocr_onnxruntime não instalado")
def test_ocr_real_le_tela_desenhada(tmp_path):
    img = np.full((1080, 1920, 3), 55, np.uint8)
    img[:, :, 1] += (np.arange(1920) % 32).astype(np.uint8)
    cv2.rectangle(img, (1500, 940), (1860, 1040), (40, 200, 250), -1)
    cv2.putText(img, "JOGAR", (1560, 1015), cv2.FONT_HERSHEY_DUPLEX, 2.4, (20, 20, 20), 5)
    cv2.putText(img, "VOCE ENCONTROU", (700, 300), cv2.FONT_HERSHEY_DUPLEX, 1.6, (255, 255, 255), 3)
    cv2.putText(img, "ACESSO A LOJA PIRATA", (640, 380), cv2.FONT_HERSHEY_DUPLEX, 1.8, (80, 210, 250), 4)
    det = Detector(tmp_path / "v", leitor=LeitorRapidOCR(1280), padroes=PADROES_TEXTO)
    prep = det.preparar(Quadro(img))
    jogar = det.localizar(prep, "jogar")
    assert jogar and 1520 < jogar.x < 1840 and 950 < jogar.y < 1040
    assert det.localizar(prep, "aviso_encontrou")
    assert det.classificar(prep, ["acesso_pirata", "gizmo"], 0.8)[0] == "acesso_pirata"
    assert det.localizar(prep, "resgatar") is None


def test_modo_espectador_e_espera_de_reinicio_longa_volta_ao_lobby(tmp_path):
    """Como no jogo: 'MODO ESPECTADOR' + 'Realocando… / Esperando para ser reiniciado'."""
    r = Roteiro(tmp_path)
    r.tick(linha("JOGAR"))
    r.tick(dt=200)
    assert r.m.fase == Fase.EM_PARTIDA
    morto = (linha("MODOESPECTADOR", 572, 22), linha("Realocando..", 604, 451),
             linha("ESPERANDOPARASERREINICIADO", 534, 520))
    r.tick(*morto)
    assert r.m.fase == Fase.ESPECTANDO
    for _ in range(100):  # 150 s esperando: ainda não
        r.tick(*morto)
    assert r.m.fase == Fase.ESPECTANDO
    for _ in range(25):  # passa de 3 min
        r.tick(*morto)
        if r.m.fase == Fase.SAINDO:
            break
    assert r.m.fase == Fase.SAINDO and ("tocar", "esc") in r.entrada.acoes
    r.tick(linha("VOLTAR AO LOBBY", 820, 620))
    r.tick()
    r.tick()
    assert r.m.fase == Fase.LOBBY


def test_espera_de_reinicio_desligada(tmp_path):
    r = Roteiro(tmp_path)
    r.cfg.automacao.tempo_max_reinicio_min = 0
    r.tick(linha("JOGAR"))
    r.tick(dt=200)
    for _ in range(200):
        r.tick(linha("MODO ESPECTADOR"), linha("REALOCANDO"))
    assert r.m.fase == Fase.ESPECTANDO
