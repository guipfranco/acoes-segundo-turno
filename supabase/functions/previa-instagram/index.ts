// Puxa a arte de um post do Instagram para a imagem de uma ação cadastrada pelo app.
// Mesmo caminho de scripts/fotos_divulgacao.py: a prévia de link do post (meta og:image), que o Instagram entrega
// sem login a quem se identifica como robô de prévia. A imagem é copiada para o bucket `fotos-acoes`, na pasta de
// quem pediu (o link do CDN do Instagram expira), e a função devolve o endereço público.
// Só quem entrou chama (o JWT é conferido pelo Supabase e aqui de novo, para saber a pasta).
import { createClient } from "jsr:@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const AGENTE_PREVIA = "Mozilla/5.0 (compatible; acoes-segundo-turno link preview; +https://github.com/guipfranco/acoes-segundo-turno)";
const RE_POST = /instagram\.com\/(?:[A-Za-z0-9_.]+\/)?(?:p|reel|reels|tv)\/([A-Za-z0-9_-]+)/;
const LIMITE = 2 * 1024 * 1024;

const resposta = (corpo: unknown, status = 200) =>
  new Response(JSON.stringify(corpo), { status, headers: { ...CORS, "Content-Type": "application/json" } });
const erro = (codigo: string, status = 400) => resposta({ erro: codigo }, status);

function ogImage(html: string): string | null {
  const m = html.match(/<meta[^>]+property="og:image"[^>]+content="([^"]*)"/) ||
    html.match(/<meta[^>]+content="([^"]*)"[^>]+property="og:image"/);
  return m ? m[1].replaceAll("&amp;", "&") : null;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return erro("metodo", 405);
  const url = Deno.env.get("SUPABASE_URL")!;
  const usuario = createClient(url, Deno.env.get("SUPABASE_ANON_KEY")!, {
    global: { headers: { Authorization: req.headers.get("Authorization") ?? "" } },
  });
  const { data: quem } = await usuario.auth.getUser();
  if (!quem?.user) return erro("precisa_entrar", 401);

  let link = "";
  try { link = String((await req.json()).link ?? ""); } catch { /* corpo inválido */ }
  const codigo = link.match(RE_POST)?.[1];
  if (!codigo) return erro("link_instagram_invalido");

  const pagina = await fetch(`https://www.instagram.com/p/${codigo}/`, { headers: { "User-Agent": AGENTE_PREVIA } });
  if (pagina.status === 429) return erro("instagram_ocupado", 503);
  const img = pagina.ok ? ogImage(await pagina.text()) : null;
  if (!img) return erro("instagram_sem_imagem", 404);

  const bruto = await fetch(img, { headers: { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" } });
  const tipo = bruto.headers.get("content-type") ?? "";
  if (!bruto.ok || !tipo.startsWith("image/")) return erro("instagram_sem_imagem", 404);
  const dados = new Uint8Array(await bruto.arrayBuffer());
  if (dados.byteLength > LIMITE) return erro("imagem_grande");

  const servico = createClient(url, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
  const nome = `${quem.user.id}/ig-${codigo}.jpg`;
  const { error } = await servico.storage.from("fotos-acoes").upload(nome, dados, { contentType: "image/jpeg", upsert: true });
  if (error) return erro("falha_envio", 500);
  // na pilha local o SUPABASE_URL de dentro do contêiner é http://kong:8000; o navegador enxerga 127.0.0.1:54321
  const publica = servico.storage.from("fotos-acoes").getPublicUrl(nome).data.publicUrl.replace("http://kong:8000", "http://127.0.0.1:54321");
  return resposta({ url: publica });
});
