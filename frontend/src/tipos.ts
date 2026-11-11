export type Fase =
  | "parado" | "lobby" | "fila" | "onibus" | "planando" | "em_partida" | "espectando" | "saindo";

export interface Recompensa {
  id: string;
  tipo: string;
  score: number;
  data: string;
  hora: string;
  quando: string;
  partida: number;
  sessao: string;
  gatilho: string;
  antes: string;
  depois: string | null;
  confirmado: boolean;
}

export interface Estado {
  rodando: boolean;
  modo: string;
  fase: Fase;
  pausado: boolean;
  em_foco: boolean;
  partidas: number;
  partidas_hora: number;
  tesouros: number;
  por_tipo: Record<string, number>;
  tempo_partida_s: number;
  tempo_sessao_s: number;
  comportamento: string;
  simulacao: { quadro: number; total: number; arquivo?: string } | null;
  ultimo_motivo: string;
  alerta_pirata: Recompensa | null;
}

export interface LinhaLog {
  hora: string;
  nivel: "info" | "aviso" | "erro" | "destaque";
  msg: string;
}

export interface Sessao {
  id: string;
  inicio: string;
  fim: string | null;
  modo: string;
  partidas: number;
  tesouros: number;
  por_tipo: Record<string, number>;
  duracao_s: number;
  motivo: string;
}

export interface InfoTemplate {
  nome: string;
  grupo: "principal" | "extra" | "recompensa";
  rotulo: string;
  dica: string;
  configurado: boolean;
  versao: number;
  chance: number | null;
}

export interface PesoDuracao { peso: number; duracao_min_s: number; duracao_max_s: number }

export interface Config {
  porta: number;
  automacao: {
    tempo_max_partida_min: number;
    sair_quando_sozinho: boolean;
    num_companheiros: number;
    intervalo_checagem_s: number;
    cooldown_clique_s: number;
    cooldown_jogar_s: number;
    ciclos_sozinho: number;
    tempo_fila_max_s: number;
    apos_acesso_pirata: "parar" | "continuar";
    alertar_nao_identificada: boolean;
  };
  salto: {
    atraso_min_s: number;
    atraso_max_s: number;
    angulo_graus: number;
    abrir_planador_cedo: boolean;
    tempo_planando_s: number;
  };
  movimento: {
    limite_inatividade_s: number;
    intervalo_espectando_s: number;
    pixels_por_grau: number;
    tecla_agachar: string;
    agachar_alternado: boolean;
    tecla_correr: string;
    tecla_picareta: string;
    esconder: PesoDuracao;
    reposicionar: PesoDuracao;
    rondar: PesoDuracao;
    coletar: PesoDuracao;
    olhar: PesoDuracao;
  };
  deteccao: {
    limiar: number;
    limiar_recompensa: number;
    escala: number;
    regiao_squad: number[];
    monitor: number;
    titulo_janela: string;
  };
}

export interface ResultadoTeste {
  resultados: {
    nome: string; rotulo: string; grupo: string; configurado: boolean;
    score: number | null; detectado: boolean; x: number | null; y: number | null;
  }[];
  companheiros_mortos: number;
  largura: number;
  altura: number;
}

export const TIPOS_RECOMPENSA: { nome: string; rotulo: string; chance: number | null }[] = [
  { nome: "acesso_pirata", rotulo: "Acesso à Loja Pirata", chance: 137500 },
  { nome: "traje_dourado", rotulo: "Traje Dourado Semanal", chance: 1562500 },
  { nome: "veiculo", rotulo: "Veículo e Decalque", chance: 7813 },
  { nome: "picareta_costas", rotulo: "Picareta ou Acessório", chance: 568 },
  { nome: "faixa", rotulo: "Faixa de Improviso", chance: 391 },
  { nome: "tela_carregamento", rotulo: "Tela de Carregamento", chance: 272 },
  { nome: "gizmo", rotulo: "Gizmo", chance: 127 },
  { nome: "nao_identificada", rotulo: "Não identificada", chance: null },
];

export const rotuloTipo = (tipo: string) =>
  TIPOS_RECOMPENSA.find((t) => t.nome === tipo)?.rotulo ?? tipo;

export const ROTULO_FASE: Record<string, string> = {
  parado: "Parado",
  pausado: "Pausado — jogo fora de foco",
  lobby: "No lobby",
  fila: "Entrando na partida",
  onibus: "No ônibus",
  planando: "Planando",
  em_partida: "Em partida",
  espectando: "Espectando",
  saindo: "Saindo da partida",
};

export function duracao(segundos: number): string {
  const s = Math.max(0, Math.round(segundos));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  const dois = (n: number) => String(n).padStart(2, "0");
  return h > 0 ? `${h}:${dois(m)}:${dois(r)}` : `${dois(m)}:${dois(r)}`;
}
