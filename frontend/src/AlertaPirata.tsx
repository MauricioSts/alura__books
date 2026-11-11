import { useEffect, useState } from "react";
import { api, urlCaptura } from "./api";
import { pararAlarme, tocarAlarme } from "./som";
import type { Recompensa } from "./tipos";

/** Alerta em tela cheia: só some (e o som só para) quando o usuário confirma. */
export default function AlertaPirata({ item }: { item: Recompensa }) {
  const [enviando, setEnviando] = useState(false);

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
    <div className="alerta-pirata" role="alertdialog" aria-modal="true">
      <div className="alerta-caixa">
        <div className="alerta-selo">1 em 137.500</div>
        <h1>Acesso à Loja Pirata encontrado!</h1>
        <p className="alerta-quando">
          {item.data} às {item.hora} · partida nº {item.partida}
        </p>
        <img src={urlCaptura(item.depois ?? item.antes)} alt="Print da recompensa" />
        <p className="alerta-lembrete">
          Lembrete: o token precisa ser <strong>ativado na loja até 15/12/2026</strong>. Abra o jogo
          e confira com seus próprios olhos antes de qualquer coisa.
        </p>
        <button className="botao ouro" onClick={confirmar} disabled={enviando}>
          Vi o alerta — silenciar e fechar
        </button>
        <small>Os prints ficam no Histórico e numa cópia extra em capturas/acesso_pirata.</small>
      </div>
    </div>
  );
}
