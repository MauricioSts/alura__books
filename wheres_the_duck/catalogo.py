"""Catálogo dos templates que o app conhece. Todos são opcionais."""
from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class InfoTemplate:
    nome: str
    grupo: str  # "principal", "extra" ou "recompensa"
    rotulo: str
    dica: str


PRINCIPAIS = [
    InfoTemplate("jogar", "principal", "Botão Jogar", "Botão amarelo JOGAR do lobby. Recorte só o texto e um pouco do fundo."),
    InfoTemplate("resgatar", "principal", "Botão Resgatar", "Botão RESGATAR da tela de tesouro."),
    InfoTemplate("resgatar_tudo", "principal", "Botão Resgatar tudo", "Botão RESGATAR TUDO, quando há mais de um item."),
    InfoTemplate("fim_partida", "principal", "Tela de fim", "Um trecho fixo da tela que aparece quando o esquadrão inteiro foi eliminado (ex.: a colocação)."),
    InfoTemplate("jogar_novamente", "principal", "Botão Jogar novamente", "Botão JOGAR NOVAMENTE da tela de fim."),
    InfoTemplate("retornar_lobby", "principal", "Botão Retornar ao lobby", "Botão RETORNAR AO LOBBY da tela de fim."),
    InfoTemplate("continuar", "principal", "Botão Continuar", "Botão CONTINUAR de pop-ups."),
    InfoTemplate("pular_onibus", "principal", "Aviso de pular do ônibus", "O aviso de tecla para saltar que aparece quando as portas do ônibus abrem."),
    InfoTemplate("sair_partida", "principal", "Voltar ao lobby (menu ESC)", "Botão de voltar ao lobby / sair da partida, dentro do menu sanduíche do ESC."),
    InfoTemplate("confirmar_sair", "principal", "Confirmar saída", "Botão que confirma a saída da partida."),
    InfoTemplate("companheiro_morto", "principal", "Ícone de companheiro eliminado", "O ícone que aparece ao lado do nome de um companheiro eliminado na lista da squad. Recorte bem justo."),
    InfoTemplate("espectando", "principal", "Indicador de espectador", "Um trecho fixo do HUD que só aparece enquanto você assiste a um companheiro."),
]

EXTRAS = [
    InfoTemplate("menu_sanduiche", "extra", "Menu sanduíche (≡)", "Ícone de três tracinhos do menu ESC. Sem recorte, o app reconhece pelo formato."),
    InfoTemplate("aguardando_reinicio", "extra", "Esperando reinício", "Texto \"Esperando para ser reiniciado\" / \"Realocando\" quando você está morto esperando ser reiniciado."),
    InfoTemplate("fechar", "extra", "Botão Fechar", "Botão FECHAR de pop-ups."),
    InfoTemplate("tesouro_encontrado", "extra", "Tela Tesouro encontrado", "Título da tela de tesouro. Serve para salvar o print mesmo sem botão visível."),
    InfoTemplate("aviso_encontrou", "extra", "Aviso Você encontrou", "Só o texto VOCÊ ENCONTROU do aviso que surge no meio da tela durante a partida. É igual para qualquer recompensa, então dá para recortar no primeiro gizmo."),
]

RECOMPENSAS = [
    InfoTemplate("acesso_pirata", "recompensa", "Acesso à Loja Pirata", "Só o texto ACESSO À LOJA PIRATA do aviso dourado \"Você encontrou\". A mais importante; só dá para recortar depois de ver uma vez."),
    InfoTemplate("traje_dourado", "recompensa", "Traje Dourado Semanal", "Trecho que identifique o traje dourado."),
    InfoTemplate("veiculo", "recompensa", "Veículo e Decalque Semanal", "Trecho que identifique o veículo ou decalque."),
    InfoTemplate("picareta_costas", "recompensa", "Picareta ou Acessório para as Costas", "Trecho que identifique a picareta ou o acessório."),
    InfoTemplate("faixa", "recompensa", "Faixa de Improviso Semanal", "Trecho que identifique a faixa de improviso."),
    InfoTemplate("tela_carregamento", "recompensa", "Tela de Carregamento Semanal", "Trecho que identifique a tela de carregamento."),
    InfoTemplate("gizmo", "recompensa", "Gizmo", "Trecho comum aos cinco tipos de gizmo."),
]

TODOS = PRINCIPAIS + EXTRAS + RECOMPENSAS
NOMES = {t.nome for t in TODOS}
TIPOS_RECOMPENSA = [t.nome for t in RECOMPENSAS]
NAO_IDENTIFICADA = "nao_identificada"

# Chance por baú em partida normal (1 em N), só para exibição.
CHANCES = {
    "traje_dourado": 1_562_500,
    "acesso_pirata": 137_500,
    "veiculo": 7_813,
    "picareta_costas": 568,
    "faixa": 391,
    "tela_carregamento": 272,
    "gizmo": 127,
}


def como_dicts() -> list[dict]:
    return [asdict(t) for t in TODOS]
