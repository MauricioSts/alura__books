import { useState } from "react";
import { api } from "../api";
import { BarraSalvar, Cabecalho, Campo, Numero, Secao, useConfig } from "../componentes";
import type { ResultadoTeste } from "../tipos";

const EIXOS = ["x", "y", "largura", "altura"];

export default function Deteccao() {
  const { config, definir, salvar, sujo, aviso } = useConfig();
  const [teste, setTeste] = useState<ResultadoTeste | null>(null);
  const [erro, setErro] = useState("");
  const [contagem, setContagem] = useState(0);
  const [atraso, setAtraso] = useState(3);

  if (!config) return <Cabecalho titulo="Detecção" sub="Carregando…" />;
  const d = config.deteccao;

  const testar = async () => {
    setErro("");
    if (sujo) await salvar();
    for (let i = atraso; i > 0; i--) {
      setContagem(i);
      await new Promise((ok) => setTimeout(ok, 1000));
    }
    setContagem(-1);
    try {
      setTeste(await api.enviar<ResultadoTeste>("POST", "/api/deteccao/testar"));
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setContagem(0);
    }
  };

  const regiao = (i: number, v: number) => {
    const nova = [...d.regiao_squad];
    nova[i] = v;
    definir("deteccao.regiao_squad", nova);
  };

  return (
    <>
      <Cabecalho titulo="Detecção" sub="Como o vigia compara a tela com os seus recortes.">
        <BarraSalvar sujo={sujo} salvar={salvar} aviso={aviso} />
      </Cabecalho>

      <Secao titulo="Comparação">
        <div className="grade">
          <Campo rotulo="Limiar de confiança" ajuda="Score mínimo (0 a 1) para considerar um botão encontrado.">
            <Numero valor={d.limiar} min={0.3} max={0.99} passo={0.01} aoMudar={(v) => definir("deteccao.limiar", v)} />
          </Campo>
          <Campo rotulo="Limiar das recompensas" ajuda="Usado para classificar o tipo de recompensa.">
            <Numero valor={d.limiar_recompensa} min={0.3} max={0.99} passo={0.01} aoMudar={(v) => definir("deteccao.limiar_recompensa", v)} />
          </Campo>
          <Campo rotulo="Escala" ajuda="Tela e templates são reduzidos por esse fator. Menor = mais rápido, menos preciso.">
            <Numero valor={d.escala} min={0.2} max={1} passo={0.05} aoMudar={(v) => definir("deteccao.escala", v)} />
          </Campo>
          <Campo rotulo="Monitor" ajuda="1 é o principal. Prefira jogar no monitor principal.">
            <Numero valor={d.monitor} min={1} max={8} aoMudar={(v) => definir("deteccao.monitor", v)} />
          </Campo>
          <Campo rotulo="Título da janela do jogo" ajuda="O vigia só age quando a janela em primeiro plano contém esse texto.">
            <input type="text" value={d.titulo_janela} onChange={(e) => definir("deteccao.titulo_janela", e.target.value)} />
          </Campo>
        </div>
      </Secao>

      <Secao titulo="Região da squad" nota="Onde ficam os nomes dos companheiros (canto superior esquerdo), em frações da tela. É só ali que os ícones de eliminado são contados.">
        <div className="regiao">
          <div className="grade estreita">
            {EIXOS.map((eixo, i) => (
              <Campo key={eixo} rotulo={eixo}>
                <Numero valor={d.regiao_squad[i]} min={0} max={1} passo={0.01} aoMudar={(v) => regiao(i, v)} />
              </Campo>
            ))}
          </div>
          <div className="mini-tela" aria-hidden="true">
            <div style={{
              left: `${d.regiao_squad[0] * 100}%`, top: `${d.regiao_squad[1] * 100}%`,
              width: `${d.regiao_squad[2] * 100}%`, height: `${d.regiao_squad[3] * 100}%`,
            }} />
          </div>
        </div>
      </Secao>

      <Secao titulo="Testar detecção agora" nota="Tira um print da tela e mostra o score de cada template. Não clica em nada nem envia teclas. Use a contagem para trocar para a janela do jogo.">
        <div className="linha-acoes">
          <button className="botao" onClick={testar} disabled={contagem !== 0}>
            {contagem > 0 ? `Capturando em ${contagem}…` : contagem < 0 ? "Analisando…" : "Testar detecção agora"}
          </button>
          <label className="inline">espera
            <Numero valor={atraso} min={0} max={15} aoMudar={setAtraso} sufixo="s" />
          </label>
        </div>
        {erro && <div className="aviso erro bloco">{erro}</div>}
        {teste && (
          <>
            <p className="nota">
              Tela de {teste.largura}×{teste.altura}. Ícones de companheiro eliminado na região da squad:{" "}
              <strong>{teste.companheiros_mortos}</strong>.
            </p>
            <table className="tabela compacta">
              <thead><tr><th>Template</th><th>Score</th><th></th><th>Posição</th><th>Resultado</th></tr></thead>
              <tbody>
                {teste.resultados.map((r) => (
                  <tr key={r.nome} className={!r.configurado ? "apagado" : ""}>
                    <td><strong>{r.rotulo}</strong><span>{r.nome}</span></td>
                    <td className="mono">{r.score === null ? "—" : r.score.toFixed(3)}</td>
                    <td className="col-barra">
                      <div className="barra"><i className={r.detectado ? "ok" : ""} style={{ width: `${Math.max(0, r.score ?? 0) * 100}%` }} /></div>
                    </td>
                    <td className="mono">{r.detectado ? `${r.x}, ${r.y}` : "—"}</td>
                    <td>
                      {!r.configurado ? <span className="selo cinza">sem template</span>
                        : r.detectado ? <span className="selo verde">detectado</span>
                        : <span className="selo">não está na tela</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </Secao>
    </>
  );
}
