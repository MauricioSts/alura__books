import { useEffect, useRef, useState, type PointerEvent as EventoPonteiro } from "react";
import { api } from "../api";
import { Cabecalho, Secao } from "../componentes";
import type { InfoTemplate } from "../tipos";

const GRUPOS: { id: InfoTemplate["grupo"]; titulo: string; nota: string }[] = [
  { id: "principal", titulo: "Principais", nota: "Nada aqui é obrigatório: sem recorte, o app reconhece o estado lendo o texto da tela. Recorte só o que a leitura de texto não pegar (veja em Detecção → Testar detecção agora)." },
  { id: "recompensa", titulo: "Tipos de recompensa", nota: "Opcionais. Servem para classificar o print; sem eles a recompensa é salva como “não identificada”." },
  { id: "extra", titulo: "Extras", nota: "Opcionais. Ajudam a fechar pop-ups e a capturar telas de tesouro sem botão." },
];

interface Selecao { x: number; y: number; l: number; a: number }

function Recortador({ info, fechar, aoSalvar }: { info: InfoTemplate; fechar: () => void; aoSalvar: (l: InfoTemplate[]) => void }) {
  const [captura, setCaptura] = useState<{ largura: number; altura: number; carimbo: number } | null>(null);
  const [contagem, setContagem] = useState(0);
  const [sel, setSel] = useState<Selecao | null>(null);
  const [erro, setErro] = useState("");
  const origem = useRef<{ x: number; y: number } | null>(null);
  const img = useRef<HTMLImageElement>(null);

  const capturar = async (atraso: number) => {
    setErro("");
    setSel(null);
    for (let i = atraso; i > 0; i--) {
      setContagem(i);
      await new Promise((ok) => setTimeout(ok, 1000));
    }
    setContagem(-1);
    try {
      const r = await api.enviar<{ largura: number; altura: number }>("POST", "/api/captura?atraso=0");
      setCaptura({ ...r, carimbo: Date.now() });
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setContagem(0);
    }
  };

  // Converte a posição do ponteiro para pixels reais da captura.
  const ponto = (e: EventoPonteiro) => {
    const caixa = img.current!.getBoundingClientRect();
    const fx = captura!.largura / caixa.width;
    const fy = captura!.altura / caixa.height;
    return {
      x: Math.min(captura!.largura, Math.max(0, (e.clientX - caixa.left) * fx)),
      y: Math.min(captura!.altura, Math.max(0, (e.clientY - caixa.top) * fy)),
    };
  };
  const descer = (e: EventoPonteiro) => {
    if (!captura) return;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    origem.current = ponto(e);
    setSel(null);
  };
  const mover = (e: EventoPonteiro) => {
    if (!origem.current) return;
    const p = ponto(e);
    setSel({
      x: Math.min(origem.current.x, p.x), y: Math.min(origem.current.y, p.y),
      l: Math.abs(p.x - origem.current.x), a: Math.abs(p.y - origem.current.y),
    });
  };
  const soltar = () => { origem.current = null; };

  const salvar = async () => {
    if (!sel) return;
    try {
      aoSalvar(await api.enviar<InfoTemplate[]>("POST", `/api/templates/${info.nome}/recorte`, {
        x: Math.round(sel.x), y: Math.round(sel.y), largura: Math.round(sel.l), altura: Math.round(sel.a),
      }));
      fechar();
    } catch (e) {
      setErro((e as Error).message);
    }
  };

  const valida = sel && sel.l >= 6 && sel.a >= 6;
  return (
    <div className="modal">
      <div className="modal-caixa">
        <header>
          <div>
            <h2>Recortar: {info.rotulo}</h2>
            <p>{info.dica}</p>
          </div>
          <button className="botao fantasma" onClick={fechar}>Fechar</button>
        </header>
        <div className="linha-acoes">
          <button className="botao" disabled={contagem !== 0} onClick={() => capturar(5)}>
            {contagem > 0 ? `Capturando em ${contagem}… vá para o jogo` : contagem < 0 ? "Capturando…" : "Capturar tela em 5 s"}
          </button>
          <button className="botao fantasma" disabled={contagem !== 0} onClick={() => capturar(0)}>Capturar agora</button>
          <span className="nota">Depois arraste um retângulo sobre o botão. Recorte justo, sem áreas que mudam (fundo animado, números).</span>
        </div>
        {erro && <div className="aviso erro bloco">{erro}</div>}
        {captura && (
          <div className="recorte-area" onPointerDown={descer} onPointerMove={mover} onPointerUp={soltar}>
            <img ref={img} src={`/api/captura/imagem?c=${captura.carimbo}`} alt="Captura da tela" draggable={false} />
            {sel && (
              <div className="recorte-sel" style={{
                left: `${(sel.x / captura.largura) * 100}%`, top: `${(sel.y / captura.altura) * 100}%`,
                width: `${(sel.l / captura.largura) * 100}%`, height: `${(sel.a / captura.altura) * 100}%`,
              }} />
            )}
          </div>
        )}
        <footer>
          <span className="mono">{sel ? `${Math.round(sel.l)} × ${Math.round(sel.a)} px` : "nenhuma seleção"}</span>
          <button className="botao" disabled={!valida} onClick={salvar}>Salvar como template</button>
        </footer>
      </div>
    </div>
  );
}

export default function Templates() {
  const [lista, setLista] = useState<InfoTemplate[]>([]);
  const [erro, setErro] = useState("");
  const [recortando, setRecortando] = useState<InfoTemplate | null>(null);

  useEffect(() => {
    api.get<InfoTemplate[]>("/api/templates").then(setLista).catch((e) => setErro(e.message));
  }, []);

  const enviar = async (nome: string, arquivo: File | undefined) => {
    if (!arquivo) return;
    setErro("");
    try {
      setLista(await api.arquivo<InfoTemplate[]>(`/api/templates/${nome}`, arquivo));
    } catch (e) {
      setErro((e as Error).message);
    }
  };
  const remover = async (nome: string) => {
    try {
      setLista(await api.enviar<InfoTemplate[]>("DELETE", `/api/templates/${nome}`));
    } catch (e) {
      setErro((e as Error).message);
    }
  };

  const principais = lista.filter((t) => t.grupo === "principal");
  const prontos = principais.filter((t) => t.configurado || t.por_texto).length;

  return (
    <>
      <Cabecalho titulo="Templates" sub="Recortes dos botões, feitos por você, na resolução e no idioma em que joga.">
        <span className={`selo grande ${prontos === principais.length && prontos > 0 ? "verde" : ""}`}>
          {prontos} de {principais.length} reconhecíveis (recorte ou texto)
        </span>
      </Cabecalho>
      {erro && <div className="aviso erro bloco">{erro}</div>}
      {GRUPOS.map((g) => (
        <Secao key={g.id} titulo={g.titulo} nota={g.nota}>
          <div className="templates">
            {lista.filter((t) => t.grupo === g.id).map((t) => (
              <article key={t.nome} className={`template ${t.configurado || t.por_texto ? "ok" : "falta"}`}>
                <div className="template-previa">
                  {t.configurado
                    ? <img src={`/api/templates/${t.nome}/imagem?v=${t.versao}`} alt={`Template ${t.rotulo}`} />
                    : <span>{t.por_texto ? "lido por texto" : "faltando"}</span>}
                </div>
                <div className="template-corpo">
                  <div className="template-titulo">
                    <strong>{t.rotulo}</strong>
                    <span className={`selo ${t.configurado || t.por_texto ? "verde" : "ambar"}`}>
                      {t.configurado ? "recortado" : t.por_texto ? "por texto" : "faltando"}
                    </span>
                  </div>
                  <code>{t.nome}.png</code>
                  <p>{t.por_texto ? `Reconhecido pelo texto: ${t.textos.join(" · ")}. Recorte só se não funcionar.` : t.dica}</p>
                  <div className="template-acoes">
                    <button className="botao pequeno" onClick={() => setRecortando(t)}>Recortar da tela</button>
                    <label className="botao pequeno fantasma">
                      Enviar PNG
                      <input type="file" accept="image/png,image/jpeg" hidden
                        onChange={(e) => { void enviar(t.nome, e.target.files?.[0]); e.target.value = ""; }} />
                    </label>
                    {t.configurado && <button className="botao pequeno perigo" onClick={() => remover(t.nome)}>Remover</button>}
                  </div>
                </div>
              </article>
            ))}
          </div>
        </Secao>
      ))}
      {recortando && <Recortador info={recortando} fechar={() => setRecortando(null)} aoSalvar={setLista} />}
    </>
  );
}
