import { useCallback, useEffect, useState, type ReactNode } from "react";
import { api, urlCaptura } from "./api";
import type { Config, Recompensa } from "./tipos";
import { rotuloTipo } from "./tipos";

export function Cabecalho({ titulo, sub, children }: { titulo: string; sub?: string; children?: ReactNode }) {
  return (
    <header className="cabecalho">
      <div>
        <h1>{titulo}</h1>
        {sub && <p>{sub}</p>}
      </div>
      <div className="cabecalho-acoes">{children}</div>
    </header>
  );
}

export function Secao({ titulo, nota, children }: { titulo: string; nota?: string; children: ReactNode }) {
  return (
    <section className="secao">
      <h2>{titulo}</h2>
      {nota && <p className="nota">{nota}</p>}
      {children}
    </section>
  );
}

export function Campo({ rotulo, ajuda, children }: { rotulo: string; ajuda?: string; children: ReactNode }) {
  return (
    <label className="campo">
      <span className="campo-rotulo">{rotulo}</span>
      {children}
      {ajuda && <span className="campo-ajuda">{ajuda}</span>}
    </label>
  );
}

export function Numero(props: {
  valor: number; aoMudar: (v: number) => void; min?: number; max?: number; passo?: number; sufixo?: string;
}) {
  const [texto, setTexto] = useState(String(props.valor));
  useEffect(() => setTexto(String(props.valor)), [props.valor]);
  return (
    <span className="numero">
      <input
        type="number" value={texto} min={props.min} max={props.max} step={props.passo ?? 1}
        onChange={(e) => {
          setTexto(e.target.value);
          const n = Number(e.target.value);
          if (e.target.value !== "" && Number.isFinite(n)) props.aoMudar(n);
        }}
      />
      {props.sufixo && <em>{props.sufixo}</em>}
    </span>
  );
}

export function Chave({ ligado, aoMudar, rotulo }: { ligado: boolean; aoMudar: (v: boolean) => void; rotulo: string }) {
  return (
    <button type="button" role="switch" aria-checked={ligado} className={`chave ${ligado ? "ligada" : ""}`}
      onClick={() => aoMudar(!ligado)}>
      <i /> <span>{rotulo}</span>
    </button>
  );
}

/** Carrega o config.json, mantém uma cópia editável e salva pela API. */
export function useConfig() {
  const [config, setConfig] = useState<Config | null>(null);
  const [sujo, setSujo] = useState(false);
  const [aviso, setAviso] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);

  useEffect(() => {
    api.get<Config>("/api/config").then(setConfig).catch((e) => setAviso({ tipo: "erro", texto: e.message }));
  }, []);

  const definir = useCallback((caminho: string, valor: unknown) => {
    setConfig((atual) => {
      if (!atual) return atual;
      const copia = structuredClone(atual) as unknown as Record<string, any>;
      const partes = caminho.split(".");
      let alvo = copia;
      for (const parte of partes.slice(0, -1)) alvo = alvo[parte];
      alvo[partes[partes.length - 1]] = valor;
      return copia as unknown as Config;
    });
    setSujo(true);
    setAviso(null);
  }, []);

  const salvar = useCallback(async () => {
    if (!config) return;
    try {
      setConfig(await api.enviar<Config>("PUT", "/api/config", config));
      setSujo(false);
      setAviso({ tipo: "ok", texto: "Configuração salva. Vale a partir do próximo Iniciar." });
    } catch (e) {
      setAviso({ tipo: "erro", texto: (e as Error).message });
    }
  }, [config]);

  return { config, definir, salvar, sujo, aviso };
}

export function BarraSalvar({ sujo, salvar, aviso }: Pick<ReturnType<typeof useConfig>, "sujo" | "salvar" | "aviso">) {
  return (
    <div className="barra-salvar">
      {aviso && <span className={`aviso ${aviso.tipo}`}>{aviso.texto}</span>}
      <button className="botao" disabled={!sujo} onClick={salvar}>
        {sujo ? "Salvar alterações" : "Tudo salvo"}
      </button>
    </div>
  );
}

export function CartaoRecompensa({ item, aoAbrir }: { item: Recompensa; aoAbrir: (arquivo: string) => void }) {
  const pirata = item.tipo === "acesso_pirata";
  return (
    <article className={`recompensa ${pirata ? "pirata" : ""}`}>
      <button className="recompensa-img" onClick={() => aoAbrir(item.depois ?? item.antes)}>
        <img src={urlCaptura(item.antes)} alt={`Print: ${rotuloTipo(item.tipo)}`} loading="lazy" />
      </button>
      <div className="recompensa-info">
        <strong>{rotuloTipo(item.tipo)}</strong>
        <span>{item.data} · {item.hora} · partida nº {item.partida}</span>
        <span className="recompensa-links">
          <button onClick={() => aoAbrir(item.antes)}>antes</button>
          {item.depois ? <button onClick={() => aoAbrir(item.depois!)}>depois</button> : <em>depois: aguardando</em>}
        </span>
      </div>
    </article>
  );
}

export function Ampliado({ arquivo, fechar }: { arquivo: string | null; fechar: () => void }) {
  useEffect(() => {
    if (!arquivo) return;
    const tecla = (e: KeyboardEvent) => e.key === "Escape" && fechar();
    window.addEventListener("keydown", tecla);
    return () => window.removeEventListener("keydown", tecla);
  }, [arquivo, fechar]);
  if (!arquivo) return null;
  return (
    <div className="ampliado" onClick={fechar}>
      <img src={urlCaptura(arquivo)} alt="Print ampliado" />
      <span>{arquivo} — clique para fechar</span>
    </div>
  );
}

export function FaixaPirata({ itens, aoAbrir }: { itens: Recompensa[]; aoAbrir: (arquivo: string) => void }) {
  const piratas = itens.filter((r) => r.tipo === "acesso_pirata");
  if (piratas.length === 0) return null;
  const ultimo = piratas[0];
  return (
    <div className="faixa-pirata">
      <div>
        <strong>Acesso à Loja Pirata conquistado</strong>
        <span>
          {piratas.length > 1 ? `${piratas.length} registros · último em ` : ""}
          {ultimo.data} às {ultimo.hora}, partida nº {ultimo.partida}. Ative o token na loja até 15/12/2026.
        </span>
      </div>
      <button className="botao ouro pequeno" onClick={() => aoAbrir(ultimo.depois ?? ultimo.antes)}>Ver print</button>
    </div>
  );
}
