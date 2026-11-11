import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { Ampliado, Cabecalho, CartaoRecompensa, FaixaPirata, Secao } from "../componentes";
import type { Recompensa, Sessao } from "../tipos";
import { duracao, rotuloTipo, TIPOS_RECOMPENSA } from "../tipos";

const dataHora = (iso: string | null) =>
  iso ? new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" }) : "em andamento";

export default function Historico({ recompensasAoVivo }: { recompensasAoVivo: Recompensa[] }) {
  const [sessoes, setSessoes] = useState<Sessao[]>([]);
  const [filtro, setFiltro] = useState("todas");
  const [aberto, setAberto] = useState<string | null>(null);

  // Recarrega as sessões sempre que chega uma recompensa nova.
  useEffect(() => {
    api.get<{ sessoes: Sessao[] }>("/api/historico").then((h) => setSessoes(h.sessoes)).catch(() => undefined);
  }, [recompensasAoVivo.length]);

  // O Acesso à Loja Pirata fica sempre no topo da galeria.
  const galeria = useMemo(() => {
    const lista = filtro === "todas" ? recompensasAoVivo : recompensasAoVivo.filter((r) => r.tipo === filtro);
    return [...lista].sort((a, b) =>
      Number(b.tipo === "acesso_pirata") - Number(a.tipo === "acesso_pirata") || b.quando.localeCompare(a.quando));
  }, [recompensasAoVivo, filtro]);

  const contagem = (tipo: string) => recompensasAoVivo.filter((r) => r.tipo === tipo).length;

  return (
    <>
      <Cabecalho titulo="Histórico" sub="Sessões anteriores e todos os prints de recompensa salvos neste computador." />
      <FaixaPirata itens={recompensasAoVivo} aoAbrir={setAberto} />

      <Secao titulo="Galeria de recompensas" nota="Cada registro guarda o print de antes do clique em Resgatar e o de depois.">
        <div className="filtros">
          <button className={filtro === "todas" ? "ativo" : ""} onClick={() => setFiltro("todas")}>
            Todas <em>{recompensasAoVivo.length}</em>
          </button>
          {TIPOS_RECOMPENSA.map((t) => (
            <button key={t.nome} className={filtro === t.nome ? "ativo" : ""} onClick={() => setFiltro(t.nome)}>
              {t.rotulo} <em>{contagem(t.nome)}</em>
            </button>
          ))}
        </div>
        {galeria.length === 0
          ? <p className="vazio">Nenhum print {filtro === "todas" ? "salvo ainda" : "desse tipo"}.</p>
          : <div className="galeria">{galeria.map((r) => <CartaoRecompensa key={r.id} item={r} aoAbrir={setAberto} />)}</div>}
      </Secao>

      <Secao titulo="Sessões">
        {sessoes.length === 0 ? <p className="vazio">Nenhuma sessão registrada.</p> : (
          <table className="tabela compacta">
            <thead>
              <tr><th>Início</th><th>Modo</th><th>Duração</th><th>Partidas</th><th>Tesouros</th><th>Recompensas</th><th>Encerramento</th></tr>
            </thead>
            <tbody>
              {sessoes.map((s) => (
                <tr key={s.id}>
                  <td>{dataHora(s.inicio)}</td>
                  <td><span className="selo">{s.modo}</span></td>
                  <td className="mono">{s.fim ? duracao(s.duracao_s) : "—"}</td>
                  <td className="mono">{s.partidas}</td>
                  <td className="mono">{s.tesouros}</td>
                  <td>{Object.entries(s.por_tipo).map(([t, n]) => `${n}× ${rotuloTipo(t)}`).join(", ") || "—"}</td>
                  <td>{s.fim ? s.motivo : "em andamento"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Secao>
      <Ampliado arquivo={aberto} fechar={() => setAberto(null)} />
    </>
  );
}
