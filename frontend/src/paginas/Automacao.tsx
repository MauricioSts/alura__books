import { useState } from "react";
import { api } from "../api";
import { BarraSalvar, Cabecalho, Campo, Chave, Numero, Secao, useConfig } from "../componentes";
import type { PesoDuracao } from "../tipos";

const COMPORTAMENTOS: { id: "esconder" | "reposicionar" | "rondar" | "coletar" | "olhar"; rotulo: string; desc: string }[] = [
  { id: "esconder", rotulo: "Esconder", desc: "Agacha e fica parado, com pequenos ajustes de câmera." },
  { id: "reposicionar", rotulo: "Reposicionar", desc: "Corre numa direção por alguns segundos, vira e para." },
  { id: "rondar", rotulo: "Rondar", desc: "Anda agachado em trajetos curtos, mudando de direção." },
  { id: "coletar", rotulo: "Coletar", desc: "Bate com a picareta no que estiver à frente." },
  { id: "olhar", rotulo: "Olhar em volta", desc: "Giro lento de câmera, sem andar." },
];

export default function Automacao() {
  const { config, definir, salvar, sujo, aviso } = useConfig();
  const [testeDiscord, setTesteDiscord] = useState<{ ok: boolean; texto: string } | null>(null);
  if (!config) return <Cabecalho titulo="Automação" sub="Carregando…" />;
  const { automacao: a, salto: s, movimento: m, discord: dc, navegacao: nv } = config;

  const testarDiscord = async () => {
    setTesteDiscord(null);
    try {
      const r = await api.enviar<{ mensagem: string }>("POST", "/api/discord/testar", { webhook_url: dc.webhook_url });
      setTesteDiscord({ ok: true, texto: r.mensagem });
    } catch (e) {
      setTesteDiscord({ ok: false, texto: (e as Error).message });
    }
  };

  return (
    <>
      <Cabecalho titulo="Automação" sub="Ritmo do vigia, salto do ônibus e movimentação em partida.">
        <BarraSalvar sujo={sujo} salvar={salvar} aviso={aviso} />
      </Cabecalho>

      <Secao titulo="Partida">
        <div className="grade">
          <Campo rotulo="Tempo máximo por partida" ajuda="0 desliga. Ao atingir, sai pelo menu ESC.">
            <Numero valor={a.tempo_max_partida_min} min={0} aoMudar={(v) => definir("automacao.tempo_max_partida_min", v)} sufixo="min" />
          </Campo>
          <Campo rotulo="Tempo máximo esperando reinício" ajuda="Morto em “Realocando… / Esperando para ser reiniciado” por mais que isso: volta ao lobby. 0 desliga.">
            <Numero valor={a.tempo_max_reinicio_min} min={0} max={60} passo={0.5} aoMudar={(v) => definir("automacao.tempo_max_reinicio_min", v)} sufixo="min" />
          </Campo>
          <Campo rotulo="Número de companheiros" ajuda="Em Esquadrão são 3.">
            <Numero valor={a.num_companheiros} min={1} max={3} aoMudar={(v) => definir("automacao.num_companheiros", v)} />
          </Campo>
          <Campo rotulo="Intervalo de checagem" ajuda="Tempo entre uma leitura de tela e outra.">
            <Numero valor={a.intervalo_checagem_s} min={0.3} max={10} passo={0.1} aoMudar={(v) => definir("automacao.intervalo_checagem_s", v)} sufixo="s" />
          </Campo>
          <Campo rotulo="Cooldown após clique" ajuda="Espera mínima entre dois cliques.">
            <Numero valor={a.cooldown_clique_s} min={0.2} max={30} passo={0.1} aoMudar={(v) => definir("automacao.cooldown_clique_s", v)} sufixo="s" />
          </Campo>
          <Campo rotulo="Cooldown do botão Jogar">
            <Numero valor={a.cooldown_jogar_s} min={1} max={120} aoMudar={(v) => definir("automacao.cooldown_jogar_s", v)} sufixo="s" />
          </Campo>
          <Campo rotulo="Ciclos seguidos para sair sozinho" ajuda="Evita sair por causa de uma leitura errada.">
            <Numero valor={a.ciclos_sozinho} min={1} max={20} aoMudar={(v) => definir("automacao.ciclos_sozinho", v)} />
          </Campo>
        </div>
        <Chave ligado={a.sair_quando_sozinho} aoMudar={(v) => definir("automacao.sair_quando_sozinho", v)}
          rotulo="Sair da partida quando sobrar só o bot vivo" />
      </Secao>

      <Secao titulo="Depois do Acesso à Loja Pirata" nota="O que fazer quando o prêmio principal for capturado.">
        <div className="segmentos largos">
          <button className={a.apos_acesso_pirata === "parar" ? "ativo" : ""} onClick={() => definir("automacao.apos_acesso_pirata", "parar")}>
            Parar tudo (padrão)
          </button>
          <button className={a.apos_acesso_pirata === "continuar" ? "ativo" : ""} onClick={() => definir("automacao.apos_acesso_pirata", "continuar")}>
            Continuar farmando
          </button>
        </div>
        <div style={{ marginTop: 12 }}>
          <Chave ligado={a.alertar_nao_identificada} aoMudar={(v) => definir("automacao.alertar_nao_identificada", v)}
            rotulo="Alertar com som quando aparecer uma recompensa sem template (pode ser o Acesso à Loja Pirata)" />
        </div>
      </Secao>

      <Secao titulo="Avisos no Discord" nota="Opcional e desligado por padrão. Quando uma recompensa é capturada, o app manda o aviso (e o print) para o webhook do seu canal. É a única conexão para fora do PC; a URL fica só no config.json deste computador.">
        <Chave ligado={dc.ativo} aoMudar={(v) => definir("discord.ativo", v)} rotulo="Avisar no Discord quando achar uma recompensa" />
        <div className="grade" style={{ marginTop: 12 }}>
          <Campo rotulo="URL do webhook" ajuda="Discord: Configurações do canal → Integrações → Webhooks → Copiar URL do webhook.">
            <input type="text" value={dc.webhook_url} placeholder="https://discord.com/api/webhooks/…"
              onChange={(e) => definir("discord.webhook_url", e.target.value.trim())} />
          </Campo>
          <Campo rotulo="Menção no Acesso à Loja Pirata" ajuda="Ex.: @everyone ou <@seu-id>. Só é usada no aviso do token.">
            <input type="text" value={dc.mencao} onChange={(e) => definir("discord.mencao", e.target.value)} />
          </Campo>
        </div>
        <div className="segmentos largos">
          {([["todas", "Todas as recompensas"], ["sem_gizmo", "Tudo menos gizmo"], ["so_pirata", "Só o Acesso à Loja Pirata"]] as const).map(([id, rotulo]) => (
            <button key={id} className={dc.filtro === id ? "ativo" : ""} onClick={() => definir("discord.filtro", id)}>{rotulo}</button>
          ))}
        </div>
        <div style={{ marginTop: 12 }}>
          <Chave ligado={dc.enviar_print} aoMudar={(v) => definir("discord.enviar_print", v)} rotulo="Mandar o print junto" />
        </div>
        <div className="linha-acoes" style={{ marginTop: 8 }}>
          <button className="botao fantasma" onClick={testarDiscord} disabled={!dc.webhook_url}>Enviar mensagem de teste</button>
          {testeDiscord && <span className={`aviso ${testeDiscord.ok ? "ok" : "erro"}`}>{testeDiscord.texto}</span>}
        </div>
      </Secao>

      <Secao titulo="Salto e pouso" nota="O bot espera um tempo aleatório para saltar no trecho final da rota, vira a câmera para um lado e plana para longe do ônibus.">
        <div className="grade">
          <Campo rotulo="Atraso mínimo do salto" ajuda="Contado a partir do aviso de pular.">
            <Numero valor={s.atraso_min_s} min={0} max={120} aoMudar={(v) => definir("salto.atraso_min_s", v)} sufixo="s" />
          </Campo>
          <Campo rotulo="Atraso máximo do salto">
            <Numero valor={s.atraso_max_s} min={0} max={120} aoMudar={(v) => definir("salto.atraso_max_s", v)} sufixo="s" />
          </Campo>
          <Campo rotulo="Ângulo da câmera" ajuda="Para a esquerda ou direita, sorteado.">
            <Numero valor={s.angulo_graus} min={0} max={180} aoMudar={(v) => definir("salto.angulo_graus", v)} sufixo="°" />
          </Campo>
          <Campo rotulo="Tempo segurando W" ajuda="O app não enxerga o chão; segura W por esse tempo.">
            <Numero valor={s.tempo_planando_s} min={5} max={300} aoMudar={(v) => definir("salto.tempo_planando_s", v)} sufixo="s" />
          </Campo>
          <Campo rotulo="Planeio depois de ser revivido" ajuda="Ao voltar do modo espectador (reinício), segura W e abre o planador por esse tempo.">
            <Numero valor={s.tempo_planando_renascer_s} min={5} max={300} aoMudar={(v) => definir("salto.tempo_planando_renascer_s", v)} sufixo="s" />
          </Campo>
          <Campo rotulo="Pixels de mouse por grau" ajuda="Depende da sua sensibilidade. Ajuste até 90° virar 90°.">
            <Numero valor={m.pixels_por_grau} min={0.5} max={200} passo={0.5} aoMudar={(v) => definir("movimento.pixels_por_grau", v)} sufixo="px" />
          </Campo>
        </div>
        <Chave ligado={s.abrir_planador_cedo} aoMudar={(v) => definir("salto.abrir_planador_cedo", v)}
          rotulo="Abrir o planador cedo para planar mais longe" />
      </Secao>

      <Secao titulo="Ir até o meio do mapa" nota="Depois do salto e depois de ser revivido, ainda no ar: abre o mapa, marca o centro e fecha. Depois vira a câmera na direção da distância da marcação (“350 m”) que aparece na tela, planando e correndo até lá. Assim ele não vai reto para o mar.">
        <Chave ligado={nv.ativa} aoMudar={(v) => definir("navegacao.ativa", v)} rotulo="Marcar o meio do mapa e seguir a marcação" />
        <div className="grade" style={{ marginTop: 12 }}>
          <Campo rotulo="Tecla do mapa">
            <input type="text" value={nv.tecla_mapa} onChange={(e) => definir("navegacao.tecla_mapa", e.target.value.trim().toLowerCase())} />
          </Campo>
          <Campo rotulo="Centro da ilha no mapa (x)" ajuda="Fração da largura da tela, com o mapa aberto. 0,5 = meio.">
            <Numero valor={nv.centro_mapa[0]} min={0} max={1} passo={0.01} aoMudar={(v) => definir("navegacao.centro_mapa", [v, nv.centro_mapa[1]])} />
          </Campo>
          <Campo rotulo="Centro da ilha no mapa (y)" ajuda="Fração da altura da tela, com o mapa aberto.">
            <Numero valor={nv.centro_mapa[1]} min={0} max={1} passo={0.01} aoMudar={(v) => definir("navegacao.centro_mapa", [nv.centro_mapa[0], v])} />
          </Campo>
          <Campo rotulo="Parar a esta distância" ajuda="Perto assim do centro, volta aos movimentos normais.">
            <Numero valor={nv.chegada_m} min={10} max={500} aoMudar={(v) => definir("navegacao.chegada_m", v)} sufixo="m" />
          </Campo>
        </div>
        <div className="segmentos largos">
          <button className={nv.botao_marcar === "esquerdo" ? "ativo" : ""} onClick={() => definir("navegacao.botao_marcar", "esquerdo")}>Marcar com o botão esquerdo</button>
          <button className={nv.botao_marcar === "direito" ? "ativo" : ""} onClick={() => definir("navegacao.botao_marcar", "direito")}>Marcar com o botão direito</button>
        </div>
      </Secao>

      <Secao titulo="Movimentação em partida" nota="Comportamentos sorteados pelo peso; peso 0 desliga. Nunca atira, constrói nem segue jogadores.">
        <table className="tabela">
          <thead>
            <tr><th>Comportamento</th><th>Peso</th><th>Duração mínima</th><th>Duração máxima</th></tr>
          </thead>
          <tbody>
            {COMPORTAMENTOS.map((c) => {
              const v: PesoDuracao = m[c.id];
              return (
                <tr key={c.id}>
                  <td><strong>{c.rotulo}</strong><span>{c.desc}</span></td>
                  <td><Numero valor={v.peso} min={0} max={100} passo={0.5} aoMudar={(n) => definir(`movimento.${c.id}.peso`, n)} /></td>
                  <td><Numero valor={v.duracao_min_s} min={0.5} max={600} aoMudar={(n) => definir(`movimento.${c.id}.duracao_min_s`, n)} sufixo="s" /></td>
                  <td><Numero valor={v.duracao_max_s} min={0.5} max={600} aoMudar={(n) => definir(`movimento.${c.id}.duracao_max_s`, n)} sufixo="s" /></td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <div className="grade">
          <Campo rotulo="Limite de inatividade presumido" ajuda="Esconder nunca passa de 80% desse tempo.">
            <Numero valor={m.limite_inatividade_s} min={10} max={600} aoMudar={(v) => definir("movimento.limite_inatividade_s", v)} sufixo="s" />
          </Campo>
          <Campo rotulo="Sensibilidade de 'preso'" ajuda="Se o cenário mudar menos que isso em 2 leituras seguidas enquanto anda, o bot pula e muda de direção. Maior = desvia mais cedo.">
            <Numero valor={m.limiar_preso} min={0.2} max={30} passo={0.1} aoMudar={(v) => definir("movimento.limiar_preso", v)} />
          </Campo>
          <Campo rotulo="Input mínimo ao espectar" ajuda="Um pequeno movimento de mouse a cada intervalo.">
            <Numero valor={m.intervalo_espectando_s} min={5} max={300} aoMudar={(v) => definir("movimento.intervalo_espectando_s", v)} sufixo="s" />
          </Campo>
          <Campo rotulo="Tecla de agachar">
            <input type="text" value={m.tecla_agachar} onChange={(e) => definir("movimento.tecla_agachar", e.target.value.trim().toLowerCase())} />
          </Campo>
          <Campo rotulo="Tecla de correr">
            <input type="text" value={m.tecla_correr} onChange={(e) => definir("movimento.tecla_correr", e.target.value.trim().toLowerCase())} />
          </Campo>
          <Campo rotulo="Tecla da picareta">
            <input type="text" value={m.tecla_picareta} onChange={(e) => definir("movimento.tecla_picareta", e.target.value.trim().toLowerCase())} />
          </Campo>
        </div>
        <Chave ligado={m.agachar_alternado} aoMudar={(v) => definir("movimento.agachar_alternado", v)}
          rotulo="Agachar é alternado (um toque agacha, outro levanta)" />
      </Secao>
    </>
  );
}
