import numpy as np

from atalaia.captura import Quadro
from atalaia.deteccao import Detector


def test_localiza_e_converte_coordenadas_com_escala(cena):
    det = Detector(cena.pasta, escala=0.5, limiar=0.82)
    achado = det.localizar(det.preparar(cena.tela(("jogar", 1000, 600))), "jogar")
    assert achado is not None and achado.score > 0.95
    assert abs(achado.x - 1048) <= 2 and abs(achado.y - 624) <= 2
    assert abs(achado.largura - 96) <= 2 and abs(achado.altura - 48) <= 2


def test_posicao_impar_ainda_e_encontrada(cena):
    det = Detector(cena.pasta, escala=0.5, limiar=0.82)
    achado = det.localizar(det.preparar(cena.tela(("resgatar", 333, 201))), "resgatar")
    assert achado is not None
    assert abs(achado.x - 381) <= 3 and abs(achado.y - 225) <= 3


def test_soma_o_offset_do_monitor(cena):
    det = Detector(cena.pasta, escala=0.5, limiar=0.82)
    achado = det.localizar(det.preparar(cena.tela(("jogar", 200, 100), offset=(1920, -300))), "jogar")
    assert abs(achado.x - (248 + 1920)) <= 2 and abs(achado.y - (124 - 300)) <= 2


def test_escala_cheia_tambem_funciona(cena):
    det = Detector(cena.pasta, escala=1.0, limiar=0.9)
    achado = det.localizar(det.preparar(cena.tela(("continuar", 640, 360))), "continuar")
    assert (achado.x, achado.y) == (688, 384)


def test_nao_detecta_o_que_nao_esta_na_tela(cena):
    det = Detector(cena.pasta, escala=0.5, limiar=0.82)
    prep = det.preparar(cena.tela("jogar"))
    assert det.localizar(prep, "resgatar") is None
    assert det.pontuar(prep, "resgatar").score < 0.6


def test_template_ausente_nao_quebra(tmp_path, cena):
    det = Detector(tmp_path / "pasta_que_nao_existe")
    prep = det.preparar(cena.tela("jogar"))
    assert det.localizar(prep, "jogar") is None
    assert det.pontuar(prep, "jogar") is None
    assert det.contar(prep, "companheiro_morto") == 0
    assert det.classificar(prep, ["gizmo"], 0.8) == (None, 0.0)
    assert not det.tem("jogar")


def test_arquivo_corrompido_e_template_chapado_sao_ignorados(tmp_path):
    import cv2

    (tmp_path / "jogar.png").write_bytes(b"isto nao e um png")
    cv2.imwrite(str(tmp_path / "continuar.png"), np.full((40, 80, 3), 128, np.uint8))
    det = Detector(tmp_path)
    assert det.nomes() == []


def test_template_maior_que_a_tela(cena):
    det = Detector(cena.pasta, escala=1.0)
    pequeno = Quadro(np.zeros((20, 20, 3), np.uint8))
    assert det.pontuar(det.preparar(pequeno), "jogar") is None
    assert det.contar(det.preparar(pequeno), "jogar") == 0


def test_tela_chapada_nao_gera_falso_positivo(cena):
    det = Detector(cena.pasta, escala=0.5)
    preta = Quadro(np.zeros((720, 1280, 3), np.uint8))
    assert det.localizar(det.preparar(preta), "jogar") is None


def test_conta_icones_sem_contar_sobreposicoes(cena):
    det = Detector(cena.pasta, escala=0.5, limiar=0.82)
    regiao = [0.0, 0.0, 0.28, 0.5]
    for n in range(4):
        assert det.contar(det.preparar(cena.tela(*cena.mortos(n))), "companheiro_morto", regiao) == n


def test_contagem_respeita_a_regiao(cena):
    det = Detector(cena.pasta, escala=0.5, limiar=0.82)
    tela = cena.tela(("companheiro_morto", 40, 60), ("companheiro_morto", 900, 500))
    prep = det.preparar(tela)
    assert det.contar(prep, "companheiro_morto", [0.0, 0.0, 0.28, 0.5]) == 1
    assert det.contar(prep, "companheiro_morto") == 2


def test_classifica_pela_melhor_pontuacao(cena):
    det = Detector(cena.pasta, escala=0.5)
    tipos = ["acesso_pirata", "gizmo", "faixa"]
    assert det.classificar(det.preparar(cena.tela("gizmo")), tipos, 0.8)[0] == "gizmo"
    assert det.classificar(det.preparar(cena.tela("jogar")), tipos, 0.8)[0] is None


def test_recarregar_enxerga_template_novo(tmp_path, cena):
    import cv2
    from tests.conftest import padrao

    det = Detector(tmp_path / "vazia")
    assert not det.tem("jogar")
    (tmp_path / "vazia").mkdir()
    cv2.imwrite(str(tmp_path / "vazia" / "jogar.png"), padrao("jogar"))
    det.recarregar()
    assert det.tem("jogar")
