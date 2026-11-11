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
      <path d="M16 5 L27 27 H5 Z" fill="none" stroke="var(--ambar)" strokeWidth="2.2" strokeLinejoin="round" />
      <path d="M16 5 V13" stroke="var(--ambar)" strokeWidth="2.2" strokeLinecap="round" />
      <circle cx="16" cy="20" r="3.2" fill="var(--mar)" />
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
            <strong>Atalaia</strong>
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
