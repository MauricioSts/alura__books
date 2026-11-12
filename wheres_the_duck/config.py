"""Configuração do app: modelos com valores padrão, leitura e gravação do config.json."""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class Automacao(BaseModel):
    tempo_max_partida_min: float = Field(0, ge=0, description="0 = desligado")
    sair_quando_sozinho: bool = True
    num_companheiros: int = Field(3, ge=1, le=3)
    intervalo_checagem_s: float = Field(1.5, ge=0.3, le=10)
    cooldown_clique_s: float = Field(2.0, ge=0.2, le=30)
    cooldown_jogar_s: float = Field(15.0, ge=1, le=120)
    ciclos_sozinho: int = Field(3, ge=1, le=20)
    # Depois de clicar em Jogar, se o aviso do ônibus não for visto nesse tempo,
    # o app assume que a partida já começou.
    tempo_fila_max_s: float = Field(120, ge=20, le=600)
    apos_acesso_pirata: Literal["parar", "continuar"] = "parar"
    # Morto esperando o reinício ("Realocando…") por mais que isso: volta ao lobby. 0 = desligado.
    tempo_max_reinicio_min: float = Field(3, ge=0, le=60)
    # O template do Acesso à Loja Pirata só pode ser recortado depois de vê-lo uma vez.
    # Até lá, o jeito de não perder o aviso é alertar em toda recompensa sem template.
    alertar_nao_identificada: bool = True


class Salto(BaseModel):
    # Saltar logo: planando já na direção da zona segura (saltar no fim da rota deixava o bot no gás).
    atraso_min_s: float = Field(3, ge=0, le=120)
    atraso_max_s: float = Field(10, ge=0, le=120)
    angulo_graus: float = Field(90, ge=0, le=180)
    abrir_planador_cedo: bool = True
    # Tempo segurando W depois do salto (o app não enxerga o chão).
    tempo_planando_s: float = Field(80, ge=5, le=300)
    # Depois de ser revivido (reinício na van): cai do céu, segura W e abre o planador.
    tempo_planando_renascer_s: float = Field(35, ge=5, le=300)


class PesoDuracao(BaseModel):
    peso: float = Field(1, ge=0, le=100)
    duracao_min_s: float = Field(4, ge=0.5, le=600)
    duracao_max_s: float = Field(10, ge=0.5, le=600)


class Movimento(BaseModel):
    # Limite de inatividade presumido do jogo; "esconder" nunca passa de 80% disso.
    limite_inatividade_s: float = Field(60, ge=10, le=600)
    # Mudança média mínima do cenário entre dois ciclos para considerar que o bot está andando.
    limiar_preso: float = Field(1.5, ge=0.2, le=30)
    intervalo_espectando_s: float = Field(40, ge=5, le=300)
    # Quantos pixels de mouse equivalem a 1 grau de câmera (depende da sensibilidade).
    pixels_por_grau: float = Field(10, ge=0.5, le=200)
    tecla_agachar: str = "ctrl"
    agachar_alternado: bool = True
    # Vazio: o jogo já corre por padrão ("Correr por padrão"); segurar Shift faria andar devagar.
    tecla_correr: str = ""
    tecla_picareta: str = "f"
    # Teclas das armas no inventário (o "atirar" escolhe uma delas).
    teclas_armas: list[str] = Field(default=["1", "2", "3", "4", "5"], min_length=1, max_length=10)
    esconder: PesoDuracao = PesoDuracao(peso=1, duracao_min_s=6, duracao_max_s=15)
    reposicionar: PesoDuracao = PesoDuracao(peso=4, duracao_min_s=4, duracao_max_s=10)
    rondar: PesoDuracao = PesoDuracao(peso=3, duracao_min_s=5, duracao_max_s=12)
    coletar: PesoDuracao = PesoDuracao(peso=1, duracao_min_s=3, duracao_max_s=6)
    olhar: PesoDuracao = PesoDuracao(peso=1, duracao_min_s=2, duracao_max_s=5)
    atirar: PesoDuracao = PesoDuracao(peso=2, duracao_min_s=4, duracao_max_s=9)


# Pesos padrão de versões anteriores: quem não mexeu recebe os novos (mais movimento).
PESOS_ANTIGOS = {"esconder": 4, "reposicionar": 2, "rondar": 2, "coletar": 1, "olhar": 2}


REGIAO_SQUAD_PADRAO = (0.0, 0.55, 0.3, 0.45)
# Padrões de versões anteriores: migrados para o atual se o usuário não os editou.
REGIOES_SQUAD_ANTIGAS = ([0.0, 0.0, 0.28, 0.5], [0.6, 0.0, 0.3, 0.5])


class Navegacao(BaseModel):
    """Marcar o meio do mapa e seguir a marcação depois do salto e depois de ser revivido."""

    ativa: bool = True
    tecla_mapa: str = "m"
    # Onde fica o centro da ilha com o mapa aberto, em frações da tela.
    centro_mapa: list[float] = Field(default=[0.5, 0.5], min_length=2, max_length=2)
    # Padrão do jogo no PC: botão do meio (roda). Se a marcação não aparecer, tenta os outros.
    botao_marcar: Literal["meio", "esquerdo", "direito"] = "meio"
    chegada_m: int = Field(60, ge=10, le=500)
    # Fugir da tempestade: marca o centro da zona segura (círculo branco no mapa).
    seguir_zona: bool = True
    intervalo_zona_s: float = Field(75, ge=20, le=600)
    ciclos_sem_alvo: int = Field(8, ge=2, le=60)
    tentativas: int = Field(3, ge=1, le=6)


class Deteccao(BaseModel):
    limiar: float = Field(0.82, ge=0.3, le=0.99)
    limiar_recompensa: float = Field(0.80, ge=0.3, le=0.99)
    escala: float = Field(0.5, ge=0.2, le=1.0)
    # Região da lista da squad em frações da tela: x, y, largura, altura.
    # Região da lista da squad (canto inferior esquerdo por padrão, onde também fica a vida do bot).
    regiao_squad: list[float] = Field(default=list(REGIAO_SQUAD_PADRAO), min_length=4, max_length=4)
    # Sem o recorte do ícone de eliminado: sozinho = nenhuma barra de vida de companheiro na região.
    barras_vida: bool = True
    # A lista da squad mostra você mesmo (no topo). Vivo e sozinho = só a sua linha tem barra.
    lista_inclui_voce: bool = True
    monitor: int = Field(1, ge=1, le=8)
    titulo_janela: str = "Fortnite"


class Textos(BaseModel):
    """Leitura de textos da tela: substitui os templates que não foram recortados."""

    ativo: bool = True
    largura_leitura: int = Field(1280, ge=640, le=3840)
    confianca_minima: float = Field(0.5, ge=0.1, le=1.0)
    # Para cada estado, os textos (em qualquer caixa, com ou sem acento) que o identificam.
    padroes: dict[str, list[str]] = Field(default_factory=lambda: {k: list(v) for k, v in PADROES_TEXTO.items()})


# Palpites para o jogo em português do Brasil. Edite na tela Detecção se o seu jogo mostrar outro texto.
PADROES_TEXTO: dict[str, list[str]] = {
    "jogar": ["JOGAR"],
    "resgatar": ["RESGATAR"],
    "resgatar_tudo": ["RESGATAR TUDO"],
    "fim_partida": ["ESQUADRÃO ELIMINADO", "SQUAD ELIMINADO", "VOCÊ FICOU EM", "SEU ESQUADRÃO FICOU EM"],
    "jogar_novamente": ["JOGAR NOVAMENTE"],
    "retornar_lobby": ["RETORNAR AO LOBBY", "VOLTAR AO LOBBY"],
    "continuar": ["CONTINUAR"],
    "fechar": ["FECHAR"],
    "pular_onibus": ["PULAR", "SALTAR", "PULAR DO ÔNIBUS", "SALTAR DO ÔNIBUS"],
    "sair_partida": ["VOLTAR AO LOBBY", "RETORNAR AO LOBBY", "SAIR DA PARTIDA", "SAIR"],
    "confirmar_sair": ["CONFIRMAR", "SIM"],
    "espectando": ["MODO ESPECTADOR", "ESPECTANDO", "ASSISTINDO"],
    "aguardando_reinicio": ["ESPERANDO PARA SER REINICIADO", "REALOCANDO"],
    "tesouro_encontrado": ["TESOURO ENCONTRADO"],
    "aviso_encontrou": ["VOCÊ ENCONTROU", "ACESSO DESBLOQUEADO"],
    "acesso_pirata": ["LOJA PIRATA"],
    "traje_dourado": ["TRAJE DOURADO"],
    "veiculo": ["VEÍCULO", "DECALQUE"],
    "picareta_costas": ["PICARETA", "ACESSÓRIO PARA AS COSTAS", "MOCHILA"],
    "faixa": ["FAIXA DE IMPROVISO"],
    "tela_carregamento": ["TELA DE CARREGAMENTO"],
    "gizmo": ["GIZMO"],
}

# Botões: a linha lida precisa ser o texto inteiro (evita "JOGAR" casar com "JOGAR NOVAMENTE").
# Os demais estados basta o texto aparecer em algum lugar da tela.
BOTOES_TEXTO = {"jogar", "resgatar", "resgatar_tudo", "jogar_novamente", "retornar_lobby",
                "continuar", "fechar", "pular_onibus", "sair_partida", "confirmar_sair"}


class Discord(BaseModel):
    """Aviso opcional no Discord. Desligado por padrão; a URL fica só no config.json local."""

    ativo: bool = False
    webhook_url: str = ""
    filtro: Literal["todas", "sem_gizmo", "so_pirata"] = "todas"
    enviar_print: bool = True
    # Ex.: "@everyone" ou "<@123456789>" — usada só no aviso do Acesso à Loja Pirata.
    mencao: str = ""


class Config(BaseModel):
    porta: int = Field(8765, ge=1024, le=65535)
    automacao: Automacao = Automacao()
    salto: Salto = Salto()
    movimento: Movimento = Movimento()
    deteccao: Deteccao = Deteccao()
    textos: Textos = Textos()
    discord: Discord = Discord()
    navegacao: Navegacao = Navegacao()


class ArmazemConfig:
    """Guarda a configuração em memória e no disco. Arquivo corrompido volta ao padrão."""

    def __init__(self, caminho: Path):
        self.caminho = Path(caminho)
        self._trava = threading.Lock()
        self._config = self._ler()

    def _ler(self) -> Config:
        if self.caminho.exists():
            try:
                dados = json.loads(self.caminho.read_text(encoding="utf-8"))
                det = dados.get("deteccao") if isinstance(dados, dict) else None
                # Padrões antigos que estavam errados para o jogo atual: atualiza se não foram mexidos.
                salto = dados.get("salto") if isinstance(dados, dict) else None
                if isinstance(salto, dict) and salto.get("atraso_min_s") == 28 and salto.get("atraso_max_s") == 40:
                    salto.pop("atraso_min_s"), salto.pop("atraso_max_s")
                nav = dados.get("navegacao") if isinstance(dados, dict) else None
                if isinstance(nav, dict) and nav.get("botao_marcar") == "esquerdo":
                    nav.pop("botao_marcar")
                mov0 = dados.get("movimento") if isinstance(dados, dict) else None
                if isinstance(mov0, dict) and mov0.get("tecla_correr") == "shift":
                    mov0.pop("tecla_correr")
                mov = dados.get("movimento") if isinstance(dados, dict) else None
                if isinstance(mov, dict) and all(
                        isinstance(mov.get(n), dict) and mov[n].get("peso") == p for n, p in PESOS_ANTIGOS.items()):
                    for nome in PESOS_ANTIGOS:
                        mov.pop(nome, None)  # volta aos padrões novos
                if isinstance(det, dict) and det.get("regiao_squad") in REGIOES_SQUAD_ANTIGAS:
                    # Região padrão de versão anterior (lugar errado): atualiza só se não foi mexida.
                    det["regiao_squad"] = list(REGIAO_SQUAD_PADRAO)
                cfg = Config.model_validate(dados)
                self._gravar(cfg)
                return cfg
            except Exception:
                # Mantém uma cópia do arquivo problemático e segue com os padrões.
                try:
                    self.caminho.replace(self.caminho.with_suffix(".invalido.json"))
                except OSError:
                    pass
        cfg = Config()
        self._gravar(cfg)
        return cfg

    def _gravar(self, cfg: Config) -> None:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self.caminho.write_text(
            json.dumps(cfg.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8"
        )

    @property
    def atual(self) -> Config:
        with self._trava:
            return self._config

    def salvar(self, dados: dict) -> Config:
        cfg = Config.model_validate(dados)
        with self._trava:
            self._config = cfg
            self._gravar(cfg)
        return cfg
