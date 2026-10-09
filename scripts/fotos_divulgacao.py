"""Imagem da divulgação original (post do Instagram) como foto das ações importadas.

O Instagram só mostra o post a quem está logado, então a coleta é feita num navegador logado (Claude in
Chrome): para cada código de post, abrir https://www.instagram.com/p/<código>/ e ler as metas og:image e og:url.
Fazer devagar (uma página a cada poucos segundos): o Instagram devolve 429 se for rápido.

Uso:
  python scripts/fotos_divulgacao.py pendentes             # códigos de post das ações a publicar ainda sem foto
  python scripts/fotos_divulgacao.py coleta ARQ.json       # baixa, reduz e sobe as imagens coletadas
                                                           # ARQ.json: [{"codigo", "img", "url"}] (og:image, og:url)

As imagens vão para o bucket público `divulgacao` do Supabase Storage (migração 20261009000003), com o mesmo
destino de scripts/publicar_acoes.py. O mapa código -> foto fica em levantamento/fotos-divulgacao.json (fora do
git) e é lido pelo publicar_acoes.py, que manda a foto junto com a ação. Cópias locais em levantamento/divulgacao/.
"""
import argparse
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bora_lula as bl  # noqa: E402

RAIZ = bl.RAIZ
MAPA = RAIZ / "levantamento" / "fotos-divulgacao.json"
PASTA_IMG = RAIZ / "levantamento" / "divulgacao"
BUCKET = "divulgacao"
LARGURA = 720
RE_POST = re.compile(r"instagram\.com/(?:[A-Za-z0-9_.]+/)?(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)")
RE_PERFIL = re.compile(r"instagram\.com/([A-Za-z0-9_.]+)/(?:p|reel|tv)/")


class Falha(Exception):
    pass


def codigo_do_link(link):
    m = RE_POST.search(link or "")
    return m.group(1) if m else None


def perfil_do_og(url):
    """og:url vem como https://www.instagram.com/<perfil>/reel/<código>/ quando o post é de um perfil."""
    m = RE_PERFIL.search(url or "")
    return m.group(1) if m and m.group(1) not in ("p", "reel", "reels", "tv") else None


def carregar_mapa(arq=MAPA):
    return json.loads(Path(arq).read_text(encoding="utf-8")) if Path(arq).exists() else {}


def foto_do_item(item, mapa):
    """{url, credito, pagina} para o item da importação, ou None. O @ do perfil só aparece no crédito quando a ação
    tem organização pública reconhecida; sem isso o perfil pode ser de pessoa comum e o crédito fica genérico."""
    cod = codigo_do_link(item.get("link"))
    f = mapa.get(cod) if cod else None
    if not f or not f.get("url"):
        return None
    perfil = f.get("perfil")
    credito = f"Divulgação de @{perfil} no Instagram" if perfil and item.get("organizacao") else "Divulgação original no Instagram"
    return {"url": f["url"], "credito": credito, "pagina": item["link"]}


def pendentes(itens, mapa):
    vistos = []
    for it in itens:
        cod = codigo_do_link(it.get("link"))
        if cod and cod not in mapa and cod not in vistos:
            vistos.append(cod)
    return vistos


def reduzir(bruto, largura=LARGURA):
    """JPEG de até `largura` px de largura, qualidade 80, sem metadados."""
    from PIL import Image
    im = Image.open(io.BytesIO(bruto)).convert("RGB")
    if im.width > largura:
        im = im.resize((largura, round(im.height * largura / im.width)), Image.LANCZOS)
    saida = io.BytesIO()
    im.save(saida, "JPEG", quality=80, optimize=True, progressive=True)
    return saida.getvalue()


def baixar(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def destino_storage():
    """(url do projeto, chave de serviço). Local: SUPABASE_URL + SUPABASE_SERVICE_KEY. Produção: a chave de serviço é
    lida pela Management API com SUPABASE_ACCESS_TOKEN e só fica na memória."""
    import ir_ao_ar
    ir_ao_ar.ler_env()
    url, chave = os.environ.get("SUPABASE_URL", "").strip(), os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
    if url and chave:
        return url.rstrip("/"), chave
    if not os.environ.get("SUPABASE_ACCESS_TOKEN", "").strip():
        raise Falha("defina SUPABASE_URL + SUPABASE_SERVICE_KEY (local) ou SUPABASE_ACCESS_TOKEN (produção)")
    ref = ir_ao_ar.ARQ_REF.read_text().strip()
    chaves = ir_ao_ar.ok(*ir_ao_ar.chamar("GET", f"/projects/{ref}/api-keys?reveal=true"), "listar chaves")
    for k in chaves:
        if (k.get("name") == "service_role" or k.get("type") == "secret") and k.get("api_key"):
            return f"https://{ref}.supabase.co", k["api_key"]
    raise Falha("não achei a chave de serviço do projeto")


def subir(base, chave, nome, dados):
    req = urllib.request.Request(f"{base}/storage/v1/object/{BUCKET}/{nome}", data=dados, method="POST",
                                 headers={"Authorization": "Bearer " + chave, "apikey": chave, "Content-Type": "image/jpeg",
                                          "x-upsert": "true", "Cache-Control": "max-age=604800"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            r.read()
    except urllib.error.HTTPError as e:
        raise Falha(f"upload {nome}: HTTP {e.code} {e.read().decode(errors='replace')[:200]}")
    return f"{base}/storage/v1/object/public/{BUCKET}/{nome}"


def processar_coleta(coleta, mapa, base, chave, pasta=PASTA_IMG, baixar=baixar, subir=subir):
    """Baixa, reduz e sobe cada imagem coletada; devolve (novas, falhas). Atualiza `mapa` no lugar."""
    pasta.mkdir(parents=True, exist_ok=True)
    novas, falhas = 0, []
    for c in coleta:
        cod, img = c.get("codigo"), c.get("img")
        if not cod or not img:
            falhas.append((cod, "sem imagem"))
            continue
        try:
            dados = reduzir(baixar(img))
        except Exception as e:  # noqa: BLE001 - imagem quebrada ou link vencido: segue para a próxima
            falhas.append((cod, f"download: {e}"))
            continue
        (pasta / f"{cod}.jpg").write_bytes(dados)
        url = subir(base, chave, f"{cod}.jpg", dados)
        mapa[cod] = {"url": url, "perfil": perfil_do_og(c.get("url"))}
        novas += 1
    return novas, falhas


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    pp = sub.add_parser("pendentes")
    pp.add_argument("--itens", nargs="*", help="publicar-*.json (padrão: os mais recentes de cada fonte)")
    pc = sub.add_parser("coleta")
    pc.add_argument("arquivo")
    args = p.parse_args(argv)
    mapa = carregar_mapa()
    try:
        if args.cmd == "pendentes":
            arqs = args.itens or [str(sorted((RAIZ / "levantamento").glob(f"publicar-{f}-*.json"))[-1])
                                  for f in ("bora-lula", "redes") if list((RAIZ / "levantamento").glob(f"publicar-{f}-*.json"))]
            itens = [it for a in arqs for it in json.loads(Path(a).read_text(encoding="utf-8"))]
            print(json.dumps(pendentes(itens, mapa)))
            return 0
        coleta = json.loads(Path(args.arquivo).read_text(encoding="utf-8"))
        base, chave = destino_storage()
        novas, falhas = processar_coleta(coleta, mapa, base, chave)
        MAPA.parent.mkdir(parents=True, exist_ok=True)
        MAPA.write_text(json.dumps(mapa, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{novas} imagens novas no bucket {BUCKET}; {len(mapa)} no mapa; {len(falhas)} falhas")
        for cod, motivo in falhas:
            print(f"  {cod}: {motivo}")
    except Falha as e:
        print("ERRO: " + str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
