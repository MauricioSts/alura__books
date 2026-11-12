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
    # O template do Acesso à Loja Pirata só pode ser recortado depois de vê-lo uma vez.
    # Até lá, o jeito de não perder o aviso é alertar em toda recompensa sem template.
    alertar_nao_identificada: bool = True


class Salto(BaseModel):
    atraso_min_s: float = Field(28, ge=0, le=120)
    atraso_max_s: float = Field(40, ge=0, le=120)
    angulo_graus: float = Field(90, ge=0, le=180)
    abrir_planador_cedo: bool = True
    # Tempo segurando W depois do salto (o app não enxerga o chão).
    tempo_planando_s: float = Field(80, ge=5, le=300)


class PesoDuracao(BaseModel):
    peso: float = Field(1, ge=0, le=100)
    duracao_min_s: float = Field(4, ge=0.5, le=600)
    duracao_max_s: float = Field(10, ge=0.5, le=600)


class Movimento(BaseModel):
    # Limite de inatividade presumido do jogo; "esconder" nunca passa de 80% disso.
    limite_inatividade_s: float = Field(60, ge=10, le=600)
    intervalo_espectando_s: float = Field(40, ge=5, le=300)
    # Quantos pixels de mouse equivalem a 1 grau de câmera (depende da sensibilidade).
    pixels_por_grau: float = Field(10, ge=0.5, le=200)
    tecla_agachar: str = "ctrl"
    agachar_alternado: bool = True
    tecla_correr: str = "shift"
    tecla_picareta: str = "f"
    esconder: PesoDuracao = PesoDuracao(peso=4, duracao_min_s=15, duracao_max_s=40)
    reposicionar: PesoDuracao = PesoDuracao(peso=2, duracao_min_s=3, duracao_max_s=8)
    rondar: PesoDuracao = PesoDuracao(peso=2, duracao_min_s=5, duracao_max_s=12)
    coletar: PesoDuracao = PesoDuracao(peso=1, duracao_min_s=3, duracao_max_s=7)
    olhar: PesoDuracao = PesoDuracao(peso=2, duracao_min_s=3, duracao_max_s=8)


class Deteccao(BaseModel):
    limiar: float = Field(0.82, ge=0.3, le=0.99)
    limiar_recompensa: float = Field(0.80, ge=0.3, le=0.99)
    escala: float = Field(0.5, ge=0.2, le=1.0)
    # Região da lista da squad em frações da tela: x, y, largura, altura.
    regiao_squad: list[float] = Field(default=[0.0, 0.0, 0.28, 0.5], min_length=4, max_length=4)
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
    "sair_partida": ["SAIR DA PARTIDA", "SAIR"],
    "confirmar_sair": ["CONFIRMAR", "SIM"],
    "espectando": ["ESPECTANDO", "ASSISTINDO"],
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


class Config(BaseModel):
    porta: int = Field(8765, ge=1024, le=65535)
    automacao: Automacao = Automacao()
    salto: Salto = Salto()
    movimento: Movimento = Movimento()
    deteccao: Deteccao = Deteccao()
    textos: Textos = Textos()


class ArmazemConfig:
    """Guarda a configuração em memória e no disco. Arquivo corrompido volta ao padrão."""

    def __init__(self, caminho: Path):
        self.caminho = Path(caminho)
        self._trava = threading.Lock()
        self._config = self._ler()

    def _ler(self) -> Config:
        if self.caminho.exists():
            try:
                return Config.model_validate(json.loads(self.caminho.read_text(encoding="utf-8")))
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
