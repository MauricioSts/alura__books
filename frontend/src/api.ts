// Cliente da API local. Tudo fica em 127.0.0.1; não há chamadas externas.

async function tratar<T>(resposta: Response): Promise<T> {
  if (!resposta.ok) {
    let detalhe = `Erro ${resposta.status}`;
    try {
      const corpo = await resposta.json();
      if (corpo?.detail) detalhe = String(corpo.detail);
    } catch { /* corpo sem JSON */ }
    throw new Error(detalhe);
  }
  return resposta.json() as Promise<T>;
}

export const api = {
  get: <T,>(caminho: string) => fetch(caminho).then((r) => tratar<T>(r)),
  enviar: <T,>(metodo: string, caminho: string, corpo?: unknown) =>
    fetch(caminho, {
      method: metodo,
      headers: corpo === undefined ? undefined : { "Content-Type": "application/json" },
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
    }).then((r) => tratar<T>(r)),
  arquivo: <T,>(caminho: string, arquivo: Blob) =>
    fetch(caminho, { method: "PUT", headers: { "Content-Type": "image/png" }, body: arquivo })
      .then((r) => tratar<T>(r)),
};

export const urlCaptura = (arquivo: string) => `/api/capturas/${encodeURIComponent(arquivo)}`;
