import { useEffect, useState } from "react";
import { useConexao } from "./conexao";
import { destravarAudio } from "./som";
import { ROTULO_FASE } from "./tipos";
import AlertaPirata from "./AlertaPirata";
import Painel from "./paginas/Painel";
import Automacao from "./paginas/Automacao";
import Deteccao from "./paginas/Deteccao";
import Templates from "./paginas/Templates";
import Historico from "./paginas/Historico";

const ABAS = [
  { id: "painel", rotulo: "Painel" },
  { id: "automacao", rotulo: "Automação" },
  { id: "deteccao", rotulo: "Detecção" },
  { id: "templates", rotulo: "Templates" },
  { id: "historico", rotulo: "Histórico" },
] as const;
type Aba = (typeof ABAS)[number]["id"];

export function Marca() {
  return (
    <svg viewBox="0 0 32 32" width="30" height="30" aria-hidden="true">
      <ellipse cx="14" cy="21" rx="10" ry="6.5" fill="var(--ambar)" />
      <circle cx="21" cy="11.5" r="5" fill="var(--ambar)" />
      <path d="M25.5 10 L31 12 L25.5 14 Z" fill="var(--coral)" />
      <circle cx="22" cy="10.5" r="1" fill="var(--fundo)" />
      <path d="M8 21 Q13 25 18 21" fill="none" stroke="var(--fundo)" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

export default function App() {
  const [aba, setAba] = useState<Aba>("painel");
  const conexao = useConexao();
  const { estado } = conexao;
  const fase = estado.rodando && estado.pausado ? "pausado" : estado.fase;

  useEffect(() => {
    const destravar = () => destravarAudio();
    window.addEventListener("pointerdown", destravar, { once: true });
    return () => window.removeEventListener("pointerdown", destravar);
  }, []);

  return (
    <div className="casco">
      <aside className="lateral">
        <div className="marca">
          <Marca />
          <div>
            <strong>Where's the Duck</strong>
            <span>vigia de partidas</span>
          </div>
        </div>
        <nav>
          {ABAS.map((a) => (
            <button key={a.id} className={aba === a.id ? "ativa" : ""} onClick={() => setAba(a.id)}>
              {a.rotulo}
            </button>
          ))}
        </nav>
        <div className="rodape-lateral">
          <div className={`pilula fase-${fase}`}>
            <i /> {ROTULO_FASE[fase] ?? fase}
          </div>
          <div className={`ligacao ${conexao.conectado ? "ok" : "fora"}`}>
            {conexao.conectado ? "Conectado ao motor local" : "Reconectando…"}
          </div>
          <kbd>F8</kbd> <small>inicia ou para tudo</small>
        </div>
      </aside>
      <main className="conteudo">
        {aba === "painel" && <Painel {...conexao} irPara={(a) => setAba(a as Aba)} />}
        {aba === "automacao" && <Automacao />}
        {aba === "deteccao" && <Deteccao />}
        {aba === "templates" && <Templates />}
        {aba === "historico" && <Historico recompensasAoVivo={conexao.recompensas} />}
      </main>
      {estado.alerta_pirata && <AlertaPirata item={estado.alerta_pirata} />}
    </div>
  );
}
