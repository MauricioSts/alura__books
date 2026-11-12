import { useState } from "react";
import { api } from "../api";
import { BarraSalvar, Cabecalho, Campo, Chave, Numero, Secao, useConfig } from "../componentes";

const ROTULOS_TEXTO: Record<string, string> = {
  jogar: "Botão Jogar", resgatar: "Resgatar", resgatar_tudo: "Resgatar tudo", fim_partida: "Tela de fim",
  jogar_novamente: "Jogar novamente", retornar_lobby: "Retornar ao lobby", continuar: "Continuar",
  fechar: "Fechar", pular_onibus: "Pular do ônibus", sair_partida: "Voltar ao lobby (menu ESC)",
  confirmar_sair: "Confirmar saída", espectando: "Espectando", tesouro_encontrado: "Tesouro encontrado",
  aguardando_reinicio: "Esperando reinício",
  aviso_encontrou: "Aviso Você encontrou", acesso_pirata: "Acesso à Loja Pirata",
  traje_dourado: "Traje Dourado", veiculo: "Veículo e Decalque", picareta_costas: "Picareta ou Costas",
  faixa: "Faixa de Improviso", tela_carregamento: "Tela de Carregamento", gizmo: "Gizmo",
};
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
  const t = config.textos;

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

      <Secao titulo="Leitura de texto" nota="Sem precisar recortar nada: o app lê os textos da tela (no próprio PC, sem internet) e reconhece cada estado pelas palavras abaixo. Um template recortado, se existir, tem prioridade sobre o texto.">
        <Chave ligado={t.ativo} aoMudar={(v) => definir("textos.ativo", v)} rotulo="Ler os textos da tela quando não houver template" />
        <div className="grade" style={{ marginTop: 12 }}>
          <Campo rotulo="Largura de leitura" ajuda="A tela é reduzida para essa largura antes de ler. Menor = mais rápido, letras pequenas somem.">
            <Numero valor={t.largura_leitura} min={640} max={3840} passo={64} aoMudar={(v) => definir("textos.largura_leitura", v)} sufixo="px" />
          </Campo>
          <Campo rotulo="Confiança mínima" ajuda="Textos lidos com confiança menor são ignorados.">
            <Numero valor={t.confianca_minima} min={0.1} max={1} passo={0.05} aoMudar={(v) => definir("textos.confianca_minima", v)} />
          </Campo>
        </div>
        <details className="padroes">
          <summary>Palavras que identificam cada estado (edite se o seu jogo mostrar outro texto)</summary>
          <p className="nota">Um texto por linha. Maiúsculas, acentos e espaços não importam. Botões precisam bater com a linha inteira; os outros estados basta aparecer em algum lugar da tela.</p>
          <div className="grade">
            {Object.keys(ROTULOS_TEXTO).map((nome) => (
              <Campo key={nome} rotulo={ROTULOS_TEXTO[nome]}>
                <textarea rows={3} value={(t.padroes[nome] ?? []).join("\n")}
                  onChange={(e) => definir("textos.padroes", { ...t.padroes, [nome]: e.target.value.split("\n") })}
                  onBlur={(e) => definir("textos.padroes", { ...t.padroes, [nome]: e.target.value.split("\n").map((x) => x.trim()).filter(Boolean) })} />
              </Campo>
            ))}
          </div>
        </details>
      </Secao>

      <Secao titulo="Região da squad" nota="Onde fica a lista dos companheiros (por padrão, o canto inferior esquerdo), em frações da tela. O app conta ali as barras de vida e escudo dos colegas: quando nenhuma aparece por alguns ciclos e o bot não está espectando, ele sai da partida. Confira com o teste abaixo, durante uma partida.">
        <Chave ligado={d.barras_vida} aoMudar={(v) => definir("deteccao.barras_vida", v)}
          rotulo="Saber se sobrou sozinho pelas barras de vida dos colegas (sem recorte)" />
        <Chave ligado={d.lista_inclui_voce} aoMudar={(v) => definir("deteccao.lista_inclui_voce", v)}
          rotulo="A lista da squad mostra você mesmo (no topo)" />
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
              Tela de {teste.largura}×{teste.altura}. Linhas com barra de vida na região da squad:{" "}
              <strong>{teste.companheiros_vivos}</strong>
              {teste.ignora_propria && " (inclui a sua; com a squad completa e todos vivos, o certo é 4)"}
              {teste.fonte_sozinho === "template" && <> · ícones de eliminado: <strong>{teste.companheiros_mortos}</strong></>}.
            </p>
            <div className="previa-squad">
              <img src={`/api/deteccao/squad.png?c=${teste.largura}-${Date.now()}`} alt="Região da squad com as barras encontradas" />
              <span className="nota">Recorte da região da squad. Cada barra contada aparece contornada em laranja. Se a lista dos colegas não estiver aqui dentro, ajuste a região acima.</span>
            </div>
            {teste.erro_leitura && <div className="aviso erro bloco">Falha na leitura de texto: {teste.erro_leitura}</div>}
            <table className="tabela compacta">
              <thead><tr><th>Estado</th><th>Fonte</th><th>Score</th><th></th><th>Posição</th><th>Resultado</th></tr></thead>
              <tbody>
                {teste.resultados.map((r) => (
                  <tr key={r.nome} className={!r.configurado ? "apagado" : ""}>
                    <td><strong>{r.rotulo}</strong><span>{r.nome}</span></td>
                    <td><span className="selo">{r.fonte === "template" ? "recorte" : r.fonte === "texto" ? "texto" : "—"}</span></td>
                    <td className="mono">{r.score === null ? "—" : r.score.toFixed(3)}</td>
                    <td className="col-barra">
                      <div className="barra"><i className={r.detectado ? "ok" : ""} style={{ width: `${Math.max(0, r.score ?? 0) * 100}%` }} /></div>
                    </td>
                    <td className="mono">{r.detectado ? `${r.x}, ${r.y}` : "—"}</td>
                    <td>
                      {!r.configurado ? <span className="selo cinza">sem template nem texto</span>
                        : r.detectado ? <span className="selo verde">detectado</span>
                        : <span className="selo">não está na tela</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {teste.leitura_ativa && (
              <>
                <h2 style={{ marginTop: 8 }}>Textos lidos na tela</h2>
                <p className="nota">É isto que o app enxerga. Se um botão aparece aqui escrito de outro jeito, copie para as palavras do estado acima.</p>
                <div className="textos-lidos">
                  {teste.textos.length === 0 ? <span className="vazio">nenhum texto lido</span>
                    : teste.textos.map((x, i) => <span key={i} title={`confiança ${x.confianca}`}>{x.texto}</span>)}
                </div>
              </>
            )}
          </>
        )}
      </Secao>
    </>
  );
}
