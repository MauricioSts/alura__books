// Alarme gerado com Web Audio (nenhum arquivo de som, nenhuma conexão externa).

let contexto: AudioContext | null = null;
let temporizador: number | null = null;

function obterContexto(): AudioContext | null {
  try {
    contexto = contexto ?? new AudioContext();
    if (contexto.state === "suspended") void contexto.resume();
    return contexto;
  } catch {
    return null;
  }
}

/** Navegadores só liberam áudio depois de um gesto; chame no primeiro clique. */
export function destravarAudio(): void {
  obterContexto();
}

function nota(ctx: AudioContext, frequencia: number, inicio: number, duracao: number): void {
  const osc = ctx.createOscillator();
  const ganho = ctx.createGain();
  osc.type = "triangle";
  osc.frequency.value = frequencia;
  ganho.gain.setValueAtTime(0.0001, inicio);
  ganho.gain.exponentialRampToValueAtTime(0.35, inicio + 0.02);
  ganho.gain.exponentialRampToValueAtTime(0.0001, inicio + duracao);
  osc.connect(ganho).connect(ctx.destination);
  osc.start(inicio);
  osc.stop(inicio + duracao + 0.05);
}

function fanfarra(): void {
  const ctx = obterContexto();
  if (!ctx) return;
  const t = ctx.currentTime;
  [523.25, 659.25, 783.99, 1046.5].forEach((f, i) => nota(ctx, f, t + i * 0.16, 0.3));
  nota(ctx, 1318.5, t + 0.72, 0.6);
}

export function tocarAlarme(): void {
  if (temporizador !== null) return;
  fanfarra();
  temporizador = window.setInterval(fanfarra, 1800);
}

export function pararAlarme(): void {
  if (temporizador !== null) {
    window.clearInterval(temporizador);
    temporizador = null;
  }
}
