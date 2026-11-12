import random

import pytest

from wheres_the_duck.comportamentos import GerenciadorMovimento
from wheres_the_duck.config import Movimento
from wheres_the_duck.entrada import EntradaSimulada
from wheres_the_duck.maquina import Fase
from tests.conftest import Banco


def perto(clique, centro, folga=3):
    return abs(clique[1] - centro[0]) <= folga and abs(clique[2] - centro[1]) <= folga


def entrar_em_partida(b: Banco):
    """Lobby -> Jogar -> ônibus -> salto -> planeio -> em partida."""
    b.tick("jogar")
    b.tick("pular_onibus")
    b.animar(b.cfg.salto.atraso_max_s + 1)
    b.animar(b.cfg.salto.tempo_planando_s + 1)
    assert b.maquina.fase == Fase.EM_PARTIDA
    b.tick()  # um ciclo com a tela livre libera o movimento
    b.maquina.movimento.abandonar()
    b.entrada.soltar_tudo()
    b.entrada.acoes.clear()


# ---------------------------------------------------------------- foco
def test_fora_de_foco_nao_envia_input(banco):
    banco.foco.valor = False
    banco.tick("jogar", "resgatar")
    banco.animar(5)
    assert banco.entrada.acoes == []
    assert banco.maquina.pausado and banco.maquina.partidas == 0


def test_perder_o_foco_solta_as_teclas_e_nao_faz_mais_nada(banco):
    entrar_em_partida(banco)
    banco.animar(30)
    banco.entrada.tecla_baixo("w")
    banco.entrada.acoes.clear()
    banco.foco.valor = False
    banco.animar(20)
    banco.tick("jogar")
    assert banco.entrada.teclas_pressionadas == set() and not banco.entrada.mouse_pressionado
    assert set(banco.entrada.nomes()) <= {"soltar", "mouse_cima"}
    banco.foco.valor = True
    banco.tick()
    assert not banco.maquina.pausado


# ---------------------------------------------------------------- lobby e partidas
def test_jogar_clica_conta_partida_e_respeita_cooldown(banco):
    banco.tick("jogar")
    assert len(banco.cliques()) == 1 and perto(banco.cliques()[0], banco.centro())
    assert banco.maquina.partidas == 1 and banco.maquina.fase == Fase.FILA
    for _ in range(8):  # 12s: ainda dentro do cooldown de 15s
        banco.tick("jogar")
    assert len(banco.cliques()) == 1
    banco.tick("jogar", dt=4)
    assert len(banco.cliques()) == 2
    assert banco.maquina.partidas == 1  # a fila não virou partida, não conta de novo


def test_fila_sem_onibus_vira_partida_depois_do_limite(banco):
    banco.tick("jogar")
    banco.tick(dt=banco.cfg.automacao.tempo_fila_max_s + 1)
    assert banco.maquina.fase == Fase.EM_PARTIDA


def test_sem_evidencia_de_partida_nao_ha_movimento(banco):
    for _ in range(10):
        banco.tick()
        banco.animar(3)
    assert banco.entrada.acoes == [] and banco.maquina.fase == Fase.LOBBY


def test_popup_continuar_e_fechar(banco):
    banco.tick("continuar")
    assert perto(banco.cliques()[0], banco.centro())
    banco.tick("fechar", dt=5)
    assert len(banco.cliques()) == 2


def test_cooldown_entre_cliques(banco):
    banco.tick("continuar")
    banco.tick("continuar", dt=1.0)
    assert len(banco.cliques()) == 1
    banco.tick("continuar", dt=1.5)
    assert len(banco.cliques()) == 2


# ---------------------------------------------------------------- prioridade
def test_resgatar_vem_antes_de_tudo(banco):
    banco.tick("resgatar", "fim_partida", "jogar_novamente", "jogar", "continuar")
    assert len(banco.cliques()) == 1 and perto(banco.cliques()[0], banco.centro(0))
    assert banco.maquina.tesouros == 1 and banco.maquina.partidas == 0


def test_fim_vem_antes_do_lobby_e_prefere_jogar_novamente(banco):
    banco.tick("fim_partida", "jogar_novamente", "retornar_lobby", "jogar")
    assert perto(banco.cliques()[0], banco.centro(1))
    assert banco.maquina.partidas == 1 and banco.maquina.fase == Fase.FILA


def test_fim_sem_jogar_novamente_volta_ao_lobby(banco):
    entrar_em_partida(banco)
    banco.tick("fim_partida", "retornar_lobby")
    assert perto(banco.cliques()[0], banco.centro(1))
    assert banco.maquina.fase == Fase.LOBBY and banco.maquina.inicio_partida is None


def test_retornar_ao_lobby_sozinho_nao_e_tela_de_fim(banco):
    """Esse botão também aparece enquanto se assiste a um companheiro."""
    entrar_em_partida(banco)
    banco.tick("retornar_lobby", "espectando")
    assert banco.cliques() == [] and banco.maquina.fase == Fase.ESPECTANDO


def test_lobby_vem_antes_de_popup(banco):
    banco.tick("jogar", "continuar")
    assert len(banco.cliques()) == 1 and perto(banco.cliques()[0], banco.centro(0))


# ---------------------------------------------------------------- salto e pouso
def test_nao_pula_assim_que_o_aviso_aparece(banco):
    banco.tick("jogar")
    banco.tick("pular_onibus")
    assert banco.maquina.fase == Fase.ONIBUS
    banco.entrada.acoes.clear()
    banco.animar(banco.cfg.salto.atraso_min_s - 1)
    assert banco.entrada.acoes == []


def test_salto_gira_a_camera_segura_w_e_abre_o_planador(banco):
    banco.tick("jogar")
    banco.tick("pular_onibus")
    banco.entrada.acoes.clear()
    banco.animar(banco.cfg.salto.atraso_max_s + 0.5)
    acoes = banco.entrada.acoes
    assert acoes[0] == ("tocar", "space")
    assert acoes[1][0] == "mover" and abs(acoes[1][1]) == 90 * banco.cfg.movimento.pixels_por_grau
    assert acoes[2] == ("segurar", "w")
    banco.animar(2)
    assert banco.entrada.acoes[3] == ("tocar", "space")  # planador aberto cedo
    assert banco.maquina.fase == Fase.PLANANDO and "w" in banco.entrada.teclas_pressionadas
    banco.animar(banco.cfg.salto.tempo_planando_s)
    assert banco.maquina.fase == Fase.EM_PARTIDA


def test_planador_cedo_desligado(tmp_path):
    b = Banco(tmp_path, salto__abrir_planador_cedo=False)
    b.tick("jogar")
    b.tick("pular_onibus")
    b.entrada.acoes.clear()
    b.animar(b.cfg.salto.atraso_max_s + 5)
    assert b.entrada.nomes().count("tocar") == 1


def test_lado_do_salto_e_atraso_variam(tmp_path):
    lados, atrasos = set(), set()
    for semente in range(12):
        b = Banco(tmp_path / str(semente), semente=semente)
        b.tick("jogar")
        b.tick("pular_onibus")
        atraso = b.maquina._t_salto - b.agora
        assert b.cfg.salto.atraso_min_s <= atraso <= b.cfg.salto.atraso_max_s
        atrasos.add(round(atraso, 2))
        b.entrada.acoes.clear()
        b.animar(b.cfg.salto.atraso_max_s + 0.5)
        lados.add(b.entrada.acoes[1][1] > 0)
    assert lados == {True, False} and len(atrasos) > 6


def test_aviso_do_onibus_so_agenda_um_salto(banco):
    banco.tick("jogar")
    banco.tick("pular_onibus")
    primeiro = banco.maquina._t_salto
    banco.tick("pular_onibus")
    assert banco.maquina._t_salto == primeiro


# ---------------------------------------------------------------- saída
def test_sozinho_por_tres_ciclos_sai_pelo_menu(banco):
    entrar_em_partida(banco)
    banco.tick(*banco.cena.mortos(3))
    banco.tick(*banco.cena.mortos(3))
    assert banco.maquina.fase == Fase.EM_PARTIDA
    banco.entrada.soltar_tudo()
    banco.entrada.acoes.clear()
    banco.tick(*banco.cena.mortos(3))
    assert banco.maquina.fase == Fase.SAINDO
    assert ("tocar", "esc") in banco.entrada.acoes
    banco.tick("sair_partida", dt=3)
    banco.tick("confirmar_sair", dt=3)
    assert len(banco.cliques()) == 2 and banco.maquina.fase == Fase.LOBBY


def test_contagem_de_sozinho_zera_se_alguem_esta_vivo(banco):
    entrar_em_partida(banco)
    for n in (3, 3, 2, 3, 3):
        banco.tick(*banco.cena.mortos(n))
    assert banco.maquina.fase == Fase.EM_PARTIDA


def test_espectando_nao_sai_mesmo_com_todos_os_icones(banco):
    entrar_em_partida(banco)
    for _ in range(6):
        banco.tick("espectando", *banco.cena.mortos(3))
    assert banco.maquina.fase == Fase.ESPECTANDO
    assert ("tocar", "esc") not in banco.entrada.acoes


def test_sair_quando_sozinho_desligado(tmp_path):
    b = Banco(tmp_path, automacao__sair_quando_sozinho=False)
    entrar_em_partida(b)
    for _ in range(6):
        b.tick(*b.cena.mortos(3))
    assert b.maquina.fase == Fase.EM_PARTIDA


def test_numero_de_companheiros_configuravel(tmp_path):
    b = Banco(tmp_path, automacao__num_companheiros=2)
    entrar_em_partida(b)
    for _ in range(3):
        b.tick(*b.cena.mortos(2))
    assert b.maquina.fase == Fase.SAINDO


def test_tempo_maximo_de_partida(tmp_path):
    b = Banco(tmp_path, automacao__tempo_max_partida_min=5)
    entrar_em_partida(b)
    b.tick("espectando")
    assert b.maquina.fase == Fase.ESPECTANDO
    b.tick("espectando", dt=300)
    assert b.maquina.fase == Fase.SAINDO


def test_tempo_maximo_zero_fica_desligado(banco):
    entrar_em_partida(banco)
    banco.tick(dt=36000)
    assert banco.maquina.fase == Fase.EM_PARTIDA


def test_saida_desiste_se_o_menu_nao_aparece(banco):
    entrar_em_partida(banco)
    for _ in range(3):
        banco.tick(*banco.cena.mortos(3))
    assert banco.maquina.fase == Fase.SAINDO
    for _ in range(4):
        banco.tick()
    assert banco.maquina.fase == Fase.EM_PARTIDA
    assert banco.entrada.acoes.count(("tocar", "esc")) == 2  # abriu e fechou o menu


# ---------------------------------------------------------------- templates ausentes
def test_sem_nenhum_template_nada_quebra(tmp_path):
    b = Banco(tmp_path, nomes=[])
    for _ in range(5):
        b.tick("jogar", "resgatar", "fim_partida", *b.cena.mortos(3))
        b.animar(2)
    assert b.entrada.acoes == []


def test_sem_templates_de_saida_nao_aperta_esc(tmp_path):
    b = Banco(tmp_path, nomes=["jogar", "pular_onibus", "companheiro_morto"])
    entrar_em_partida(b)
    for _ in range(5):
        b.tick(*b.cena.mortos(3))
    assert ("tocar", "esc") not in b.entrada.acoes and b.maquina.fase == Fase.EM_PARTIDA


# ---------------------------------------------------------------- movimento
TECLAS_PERMITIDAS = {"w", "a", "s", "d", "shift", "ctrl", "space", "f"}


def test_movimento_em_partida_so_usa_o_permitido(banco):
    entrar_em_partida(banco)
    banco.animar(900)
    nomes = set()
    for acao in banco.entrada.acoes:
        if acao[0] in ("segurar", "soltar", "tocar"):
            assert acao[1] in TECLAS_PERMITIDAS, acao
        assert acao[0] != "clicar"
    vistos = {l["msg"].split()[1] for l in banco.registro.linhas() if l["msg"].startswith("Comportamento:")}
    assert vistos == {"esconder", "reposicionar", "rondar", "coletar", "olhar"}


def test_botao_do_mouse_so_e_segurado_depois_de_selecionar_a_picareta(banco):
    entrar_em_partida(banco)
    banco.animar(2400)
    acoes = banco.entrada.acoes
    baixos = [i for i, a in enumerate(acoes) if a[0] == "mouse_baixo"]
    assert baixos
    for i in baixos:
        assert acoes[i - 1] == ("tocar", "f")


def test_nunca_fica_sem_input_alem_do_limite_de_inatividade(banco):
    entrar_em_partida(banco)
    ultimo, maior = banco.agora, 0.0
    for _ in range(9000):
        antes = len(banco.entrada.acoes)
        banco.animar(0.1)
        if len(banco.entrada.acoes) > antes:
            ultimo = banco.agora
        elif not banco.entrada.teclas_pressionadas and not banco.entrada.mouse_pressionado:
            maior = max(maior, banco.agora - ultimo)
    assert maior < banco.cfg.movimento.limite_inatividade_s * 0.5


def test_esconder_fica_abaixo_do_limite_de_inatividade():
    cfg = Movimento(limite_inatividade_s=30)
    cfg.esconder.duracao_min_s, cfg.esconder.duracao_max_s = 100, 200
    for nome in ("reposicionar", "rondar", "coletar", "olhar"):
        getattr(cfg, nome).peso = 0
    g = GerenciadorMovimento(EntradaSimulada(), cfg, random.Random(1))
    g.passo(0.0)
    assert g.nome_atual == "esconder" and g._fim <= 30 * 0.8


def test_pesos_zerados_caem_no_olhar():
    cfg = Movimento()
    for nome in ("esconder", "reposicionar", "rondar", "coletar", "olhar"):
        getattr(cfg, nome).peso = 0
    g = GerenciadorMovimento(EntradaSimulada(), cfg, random.Random(1))
    g.passo(0.0)
    assert g.nome_atual == "olhar"


def test_espectando_reduz_ao_minimo_de_input(banco):
    entrar_em_partida(banco)
    banco.tick("espectando")
    banco.entrada.acoes.clear()
    banco.animar(200)
    assert set(banco.entrada.nomes()) == {"mover"}
    assert 3 <= len(banco.entrada.acoes) <= 6  # um toque de mouse a cada ~40s


def test_revivido_cai_do_ceu_segura_w_e_abre_o_planador(banco):
    entrar_em_partida(banco)
    banco.tick("espectando")
    banco.tick()
    assert banco.maquina.fase == Fase.ESPECTANDO  # um ciclo sem o indicador ainda não basta
    banco.tick()
    assert banco.maquina.fase == Fase.PLANANDO
    banco.entrada.acoes.clear()
    banco.animar(2)
    assert "w" in banco.entrada.teclas_pressionadas and ("tocar", "space") in banco.entrada.acoes
    banco.animar(banco.cfg.salto.tempo_planando_renascer_s)
    assert banco.maquina.fase == Fase.EM_PARTIDA


def test_parar_solta_todas_as_teclas(banco):
    entrar_em_partida(banco)
    banco.animar(120)
    banco.entrada.tecla_baixo("w")
    banco.entrada.mouse_baixo()
    banco.maquina.parar()
    assert banco.entrada.teclas_pressionadas == set() and not banco.entrada.mouse_pressionado


# ---------------------------------------------------------------- recompensas
def test_print_antes_do_clique_e_outro_depois(banco):
    banco.tick("jogar")
    banco.tick("resgatar", "gizmo", dt=5)
    item = banco.recompensas.listar()[0]
    assert item["tipo"] == "gizmo" and item["partida"] == 1 and item["depois"] is None
    assert (banco.recompensas.pasta / item["antes"]).is_file()
    assert banco.entrada.nomes().count("clicar") == 2  # Jogar e Resgatar
    banco.tick(dt=3)
    item = banco.recompensas.listar()[0]
    assert item["depois"] and (banco.recompensas.pasta / item["depois"]).is_file()
    assert [e["depois"] is not None for e in banco.eventos] == [False, True]
    assert banco.maquina.tesouros == 1 and banco.maquina.por_tipo == {"gizmo": 1}


def test_recompensa_sem_template_fica_como_nao_identificada(banco):
    banco.tick("resgatar_tudo")
    item = banco.recompensas.listar()[0]
    assert item["tipo"] == "nao_identificada" and item["gatilho"] == "resgatar_tudo"
    assert (banco.recompensas.pasta / item["antes"]).is_file()


def test_aviso_sem_botao_salva_um_print_so(banco):
    entrar_em_partida(banco)
    for _ in range(4):
        banco.tick("aviso_encontrou", "faixa")
    assert banco.maquina.tesouros == 1 and banco.cliques() == []
    assert banco.recompensas.listar()[0]["tipo"] == "faixa"
    banco.tick()
    banco.tick("aviso_encontrou", "tela_carregamento")
    assert banco.maquina.por_tipo == {"faixa": 1, "tela_carregamento": 1}


def test_acesso_pirata_copia_extra_alerta_e_parada(banco):
    banco.tick("resgatar", "acesso_pirata")
    assert banco.maquina.pedido_parada is None  # ainda falta o print de depois
    banco.tick(dt=3)
    assert banco.maquina.pedido_parada
    item = banco.recompensas.listar()[0]
    assert item["tipo"] == "acesso_pirata" and item["confirmado"] is False
    for nome in (item["antes"], item["depois"]):
        assert (banco.recompensas.pasta_pirata / nome).is_file()
    assert banco.recompensas.alerta_pendente()["id"] == item["id"]
    banco.recompensas.confirmar_alertas()
    assert banco.recompensas.alerta_pendente() is None


def test_acesso_pirata_pode_continuar_farmando(tmp_path):
    b = Banco(tmp_path, automacao__apos_acesso_pirata="continuar")
    b.tick("resgatar", "acesso_pirata")
    b.tick(dt=3)
    assert b.maquina.pedido_parada is None and b.maquina.por_tipo == {"acesso_pirata": 1}


def test_tela_dourada_sem_botao_tambem_e_capturada(banco):
    banco.tick("acesso_pirata")
    assert banco.recompensas.listar()[0]["tipo"] == "acesso_pirata"
    assert banco.maquina.pedido_parada and banco.cliques() == []


@pytest.mark.parametrize("tipo", ["traje_dourado", "veiculo", "picareta_costas", "faixa",
                                  "tela_carregamento", "gizmo", "acesso_pirata"])
def test_classifica_cada_tipo(tmp_path, tipo):
    b = Banco(tmp_path)
    b.tick("resgatar", tipo)
    assert b.maquina.por_tipo == {tipo: 1}


def test_tela_de_resgate_travada_nao_conta_varios_tesouros(banco):
    for _ in range(8):
        banco.tick("resgatar", "gizmo")
    assert banco.maquina.tesouros == 1 and len(banco.cliques()) >= 3
    assert len(banco.recompensas.listar()) == 1


def test_duas_recompensas_seguidas_diferentes_contam_duas(banco):
    banco.tick("resgatar", "gizmo")
    banco.tick("resgatar", "faixa", dt=3)
    assert banco.maquina.por_tipo == {"gizmo": 1, "faixa": 1}
    assert banco.recompensas.listar()[0]["depois"]


def test_nao_se_move_por_cima_de_tela_de_recompensa_ou_de_fim(banco):
    entrar_em_partida(banco)
    banco.tick("resgatar", "gizmo")
    banco.entrada.acoes.clear()
    banco.animar(10)  # logo após o clique, sem novo ciclo: nada de movimento
    assert banco.entrada.acoes == []
    banco.tick("fim_partida", dt=0.1)  # tela de fim sem botão reconhecido
    banco.animar(10)
    assert banco.entrada.acoes == []
    banco.tick()
    banco.animar(10)
    assert banco.entrada.acoes != []


def test_recompensa_nao_identificada_dispara_alerta_mas_nao_para(banco):
    """Sem o template do token (só existe depois de vê-lo uma vez), o aviso não pode passar batido."""
    entrar_em_partida(banco)
    banco.tick("aviso_encontrou")
    pendente = banco.recompensas.alerta_pendente()
    assert pendente and pendente["tipo"] == "nao_identificada"
    assert banco.maquina.pedido_parada is None
    banco.tick()  # o aviso some
    banco.tick("aviso_encontrou", "gizmo", dt=30)  # identificada: não gera alerta novo
    assert banco.recompensas.listar()[1]["confirmado"] is True


def test_alerta_de_nao_identificada_pode_ser_desligado(tmp_path):
    b = Banco(tmp_path, automacao__alertar_nao_identificada=False)
    b.tick("resgatar")
    assert b.recompensas.alerta_pendente() is None and b.maquina.tesouros == 1


def test_aviso_do_token_sem_botao_durante_a_partida(banco):
    """O caso real: faixa 'Você encontrou / Acesso à Loja Pirata' no meio do jogo, sem botão."""
    entrar_em_partida(banco)
    banco.tick("aviso_encontrou", "acesso_pirata")
    item = banco.recompensas.listar()[0]
    assert item["tipo"] == "acesso_pirata" and banco.cliques() == []
    assert banco.recompensas.alerta_pendente()["tipo"] == "acesso_pirata"
    assert banco.maquina.pedido_parada
