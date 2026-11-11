import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import type { Estado, LinhaLog, Recompensa } from "./tipos";

const ESTADO_INICIAL: Estado = {
  rodando: false, modo: "", fase: "parado", pausado: false, em_foco: false, partidas: 0,
  partidas_hora: 0, tesouros: 0, por_tipo: {}, tempo_partida_s: 0, tempo_sessao_s: 0,
  comportamento: "", simulacao: null, ultimo_motivo: "", alerta_pirata: null,
};

/** Estado, log e recompensas em tempo real pelo WebSocket, com reconexão automática. */
export function useConexao() {
  const [estado, setEstado] = useState<Estado>(ESTADO_INICIAL);
  const [log, setLog] = useState<LinhaLog[]>([]);
  const [recompensas, setRecompensas] = useState<Recompensa[]>([]);
  const [conectado, setConectado] = useState(false);
  const vivo = useRef(true);

  const recarregar = useCallback(async () => {
    try {
      const inicial = await api.get<{ estado: Estado; log: LinhaLog[] }>("/api/estado");
      setEstado(inicial.estado);
      setLog(inicial.log);
      const hist = await api.get<{ recompensas: Recompensa[] }>("/api/historico");
      setRecompensas(hist.recompensas);
    } catch { /* backend ainda subindo */ }
  }, []);

  useEffect(() => {
    vivo.current = true;
    let ws: WebSocket | null = null;
    let espera: number | undefined;

    const conectar = () => {
      const protocolo = location.protocol === "https:" ? "wss" : "ws";
      ws = new WebSocket(`${protocolo}://${location.host}/ws`);
      ws.onopen = () => { setConectado(true); void recarregar(); };
      ws.onmessage = (evento) => {
        const msg = JSON.parse(evento.data);
        if (msg.tipo === "estado") setEstado(msg.estado);
        else if (msg.tipo === "log") setLog((l) => [...l.slice(-399), msg.linha]);
        else if (msg.tipo === "recompensa") {
          const item: Recompensa = msg.item;
          if (!item?.id) return;
          setRecompensas((lista) =>
            lista.some((r) => r.id === item.id)
              ? lista.map((r) => (r.id === item.id ? item : r))
              : [item, ...lista]);
        }
      };
      ws.onclose = () => {
        setConectado(false);
        if (vivo.current) espera = window.setTimeout(conectar, 1500);
      };
    };
    conectar();
    return () => {
      vivo.current = false;
      window.clearTimeout(espera);
      ws?.close();
    };
  }, [recarregar]);

  return { estado, log, recompensas, conectado, recarregar };
}
