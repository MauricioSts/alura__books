import { useEffect, useState } from "react";
import { api, urlCaptura } from "./api";
import { pararAlarme, tocarAlarme } from "./som";
import type { Recompensa } from "./tipos";

/** Alerta em tela cheia: só some (e o som só para) quando o usuário confirma. */
export default function AlertaPirata({ item }: { item: Recompensa }) {
  const [enviando, setEnviando] = useState(false);
  const pirata = item.tipo === "acesso_pirata";

  useEffect(() => {
    tocarAlarme();
    return pararAlarme;
  }, []);

  const confirmar = async () => {
    setEnviando(true);
    try {
      await api.enviar("POST", "/api/alerta/confirmar");
      pararAlarme();
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className={`alerta-pirata ${pirata ? "" : "incerto"}`} role="alertdialog" aria-modal="true">
      <div className="alerta-caixa">
        <div className="alerta-selo">{pirata ? "1 em 137.500" : "confira o print"}</div>
        <h1>{pirata ? "Acesso à Loja Pirata encontrado!" : "Recompensa não identificada"}</h1>
        <p className="alerta-quando">
          {item.data} às {item.hora} · partida nº {item.partida}
        </p>
        <img src={urlCaptura(item.depois ?? item.antes)} alt="Print da recompensa" />
        {pirata ? (
          <p className="alerta-lembrete">
            Lembrete: o token precisa ser <strong>ativado na loja até 15/12/2026</strong>. Abra o jogo
            e confira com seus próprios olhos antes de qualquer coisa.
          </p>
        ) : (
          <p className="alerta-lembrete">
            Nenhum template de recompensa bateu com esta tela. <strong>Pode ser o Acesso à Loja Pirata</strong>:
            olhe o print. Se for uma recompensa comum, recorte o template dela na tela Templates para
            este alerta não tocar de novo. O vigia continua rodando.
          </p>
        )}
        <button className="botao ouro" onClick={confirmar} disabled={enviando}>
          Vi o alerta — silenciar e fechar
        </button>
        <small>
          {pirata
            ? "Os prints ficam no Histórico e numa cópia extra em capturas/acesso_pirata."
            : "O print fica no Histórico. Dá para desligar este alerta em Automação."}
        </small>
      </div>
    </div>
  );
}
