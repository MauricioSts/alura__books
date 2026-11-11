import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { Ampliado, Cabecalho, CartaoRecompensa, FaixaPirata } from "../componentes";
import type { Estado, LinhaLog, Recompensa } from "../tipos";
import { duracao, ROTULO_FASE, TIPOS_RECOMPENSA } from "../tipos";

interface Props {
  estado: Estado;
  log: LinhaLog[];
  recompensas: Recompensa[];
  irPara: (aba: string) => void;
}

const MODOS = [
  { id: "real", rotulo: "Real", dica: "Captura a tela e envia teclado e mouse ao jogo." },
  { id: "ensaio", rotulo: "Ensaio", dica: "Captura a tela de verdade, mas só registra no log o que faria." },
  { id: "simulacao", rotulo: "Simulação", dica: "Roda sobre uma pasta de screenshots, sem jogo aberto." },
];

export default function Painel({ estado, log, recompensas, irPara }: Props) {
  const [modo, setModo] = useState(() => localStorage.getItem("wheres_the_duck.modo") ?? "real");
  const [pasta, setPasta] = useState(() => localStorage.getItem("wheres_the_duck.pasta") ?? "");
  const [repetir, setRepetir] = useState(2);
  const [erro, setErro] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [aberto, setAberto] = useState<string | null>(null);
  const caixaLog = useRef<HTMLDivElement>(null);
  const fase = estado.rodando && estado.pausado ? "pausado" : estado.fase;

  useEffect(() => { localStorage.setItem("wheres_the_duck.modo", modo); }, [modo]);
  useEffect(() => { localStorage.setItem("wheres_the_duck.pasta", pasta); }, [pasta]);
  // Rola só a caixa do log (scrollIntoView arrastaria a página inteira junto).
  useEffect(() => {
    const caixa = caixaLog.current;
    if (caixa) caixa.scrollTop = caixa.scrollHeight;
  }, [log.length]);

  const alternar = async () => {
    setErro("");
    setOcupado(true);
    try {
      if (estado.rodando) await api.enviar("POST", "/api/parar");
      else await api.enviar("POST", "/api/iniciar", { modo, pasta: pasta || null, repetir });
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setOcupado(false);
    }
  };

  const cartoes = [
    { rotulo: "Partidas", valor: String(estado.partidas) },
    { rotulo: "Partidas por hora", valor: estado.partidas_hora ? estado.partidas_hora.toFixed(1) : "—" },
    { rotulo: "Tesouros", valor: String(estado.tesouros), destaque: estado.tesouros > 0 },
    { rotulo: "Tempo da partida", valor: estado.tempo_partida_s ? duracao(estado.tempo_partida_s) : "—" },
    { rotulo: "Tempo da sessão", valor: estado.rodando ? duracao(estado.tempo_sessao_s) : "—" },
  ];

  return (
    <>
      <Cabecalho titulo="Painel" sub="Estado do vigia, contadores da sessão e o que ele está vendo." />
      <FaixaPirata itens={recompensas} aoAbrir={setAberto} />

      <section className={`comando fase-${fase}`}>
        <div className="comando-estado">
          <span className="rotulo-mini">Estado atual</span>
          <div className="estado-grande"><i /> {ROTULO_FASE[fase] ?? fase}</div>
          <div className="estado-detalhes">
            <span className={`indicador ${estado.em_foco ? "ok" : "fora"}`}>
              <i /> {estado.em_foco ? "Fortnite em foco" : "Fortnite fora de foco"}
            </span>
            {estado.rodando && <span className="etiqueta">modo {estado.modo}</span>}
            {estado.comportamento && <span className="etiqueta">{estado.comportamento}</span>}
            {estado.simulacao && (
              <span className="etiqueta">quadro {estado.simulacao.quadro}/{estado.simulacao.total}</span>
            )}
            {!estado.rodando && estado.ultimo_motivo && (
              <span className="etiqueta">última parada: {estado.ultimo_motivo}</span>
            )}
          </div>
        </div>
        <div className="comando-acao">
          <button className={`botao-mestre ${estado.rodando ? "parar" : "iniciar"}`} onClick={alternar} disabled={ocupado}>
            {estado.rodando ? "Parar" : "Iniciar"}
            <small>ou aperte F8</small>
          </button>
        </div>
        {!estado.rodando && (
          <div className="comando-modo">
            <div className="segmentos">
              {MODOS.map((m) => (
                <button key={m.id} className={modo === m.id ? "ativo" : ""} onClick={() => setModo(m.id)}>
                  {m.rotulo}
                </button>
              ))}
            </div>
            <p>{MODOS.find((m) => m.id === modo)?.dica}{modo === "real" && " O F8 sempre inicia neste modo."}</p>
            {modo === "simulacao" && (
              <div className="linha-sim">
                <input type="text" placeholder="C:\caminho\da\pasta\de\screenshots" value={pasta}
                  onChange={(e) => setPasta(e.target.value)} />
                <label>ciclos por imagem
                  <input type="number" min={1} max={200} value={repetir}
                    onChange={(e) => setRepetir(Math.max(1, Number(e.target.value) || 1))} />
                </label>
              </div>
            )}
          </div>
        )}
        {erro && <div className="aviso erro bloco">{erro}</div>}
      </section>

      <div className="cartoes">
        {cartoes.map((c) => (
          <div key={c.rotulo} className={`cartao ${c.destaque ? "destaque" : ""}`}>
            <span>{c.rotulo}</span>
            <strong>{c.valor}</strong>
          </div>
        ))}
      </div>

      <section className="secao">
        <h2>Recompensas por tipo <small>nesta sessão</small></h2>
        <div className="tipos">
          {TIPOS_RECOMPENSA.map((t) => {
            const n = estado.por_tipo[t.nome] ?? 0;
            return (
              <div key={t.nome} className={`tipo ${t.nome === "acesso_pirata" ? "pirata" : ""} ${n ? "tem" : ""}`}>
                <strong>{n}</strong>
                <span>{t.rotulo}</span>
                <em>{t.chance ? `1 em ${t.chance.toLocaleString("pt-BR")}` : "sem template"}</em>
              </div>
            );
          })}
        </div>
      </section>

      <div className="duas-colunas">
        <section className="secao">
          <h2>Recompensas <small>feed em tempo real</small></h2>
          {recompensas.length === 0 ? (
            <p className="vazio">Nenhuma recompensa capturada ainda. Quando uma tela de tesouro aparecer,
              o print entra aqui na hora.</p>
          ) : (
            <div className="feed">
              {recompensas.slice(0, 8).map((r) => <CartaoRecompensa key={r.id} item={r} aoAbrir={setAberto} />)}
              {recompensas.length > 8 && (
                <button className="link" onClick={() => irPara("historico")}>Ver todas no Histórico</button>
              )}
            </div>
          )}
        </section>
        <section className="secao">
          <h2>Log ao vivo</h2>
          <div className="log" ref={caixaLog}>
            {log.length === 0 && <p className="vazio">Sem eventos por enquanto.</p>}
            {log.map((l, i) => (
              <div key={i} className={`linha ${l.nivel}`}>
                <time>{l.hora}</time>
                <span>{l.msg}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
      <Ampliado arquivo={aberto} fechar={() => setAberto(null)} />
    </>
  );
}
