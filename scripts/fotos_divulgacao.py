"""Imagem da divulgação original (post do Instagram) como foto das ações importadas.

A imagem vem da página de embed do post (/p/<código>/embed/captioned/), que o Instagram entrega sem login a quem se
identifica como robô de prévia, com a arte inteira na proporção original (quase sempre 4:5). A prévia de link
(og:image, a mesma que o WhatsApp mostra) é só o plano B: ela vem recortada em quadrado e corta o texto dos cartazes.
Sem conta, sem navegador. Uma página a cada 3 s; se o Instagram devolver 429, o script para e guarda o que já coletou.

Uso:
  python scripts/fotos_divulgacao.py pendentes               # códigos de post das ações a publicar ainda sem foto
  python scripts/fotos_divulgacao.py coletar                 # lê a prévia de cada pendente, baixa, reduz e grava
  python scripts/fotos_divulgacao.py coleta ARQ.json         # o mesmo a partir de [{"codigo", "img", "url"}] já lidos
  python scripts/fotos_divulgacao.py migrar-pages [--max N] [--aplicar]
                                                             # tira do bucket do Supabase o que já está publicado
  python scripts/fotos_divulgacao.py refazer [--max N]       # (antigo) troca og:image recortado pela arte inteira no bucket

Onde as imagens ficam (desde 2026-10-09): em fotos/divulgacao/ na RAIZ do repo, servidas pelo GitHub Pages em
BASE_PAGES/<código>.jpg (arte inteira, até 1080 px) e BASE_PAGES/<código>-mini.jpg (480 px, para os cards). Assim o
tráfego de imagens não passa pelo Supabase (plano Free, 5 GB/mês de saída). O endereço gravado no banco só pode
apontar para arquivo que o Pages já serve: por isso `publicar_acoes.py --aplicar` e `migrar-pages --aplicar` param se
houver foto nova ainda não commitada e enviada para a master (`fotos_pendentes`) e conferem por HEAD que o Pages já
responde cada mini que vai para o banco (`publicadas_no_pages`). Rotina: rodar, commit + push de fotos/, esperar o
workflow do Pages, rodar de novo.

O bucket público `divulgacao` (migração 20261009000003) só segue para o que ainda não migrou; `migrar-pages` sem
--aplicar baixa cada imagem de lá (não do Instagram) e gera os dois arquivos; com --aplicar NÃO gera nada: só aponta
para o Pages as ações cujos dois arquivos já existem em fotos/divulgacao/ (os demais ficam para a rodada sem --aplicar).
O mapa código -> foto fica em levantamento/fotos-divulgacao.json (fora do git) e é lido pelo publicar_acoes.py, que
manda a foto junto com a ação. Entrada do mapa: {url, mini, perfil, inteira, pages}.
"""
import argparse
import html
import io
import subprocess
import time
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bora_lula as bl  # noqa: E402

RAIZ = bl.RAIZ
MAPA = RAIZ / "levantamento" / "fotos-divulgacao.json"
PASTA_IMG = RAIZ / "levantamento" / "divulgacao"   # cópias locais do fluxo antigo (refazer)
PASTA_PAGES = RAIZ / "fotos" / "divulgacao"        # o que o GitHub Pages serve (versionado)
BASE_PAGES = "https://guipfranco.github.io/acoes-segundo-turno/fotos/divulgacao"
BUCKET = "divulgacao"
LARGURA = 1080
LARGURA_MINI = 480
QUALIDADE = 80
QUALIDADE_MINI = 78
RE_POST = re.compile(r"instagram\.com/(?:[A-Za-z0-9_.]+/)?(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)")
RE_PERFIL = re.compile(r"instagram\.com/([A-Za-z0-9_.]+)/(?:p|reel|tv)/")
RE_BUCKET = re.compile(r"/storage/v1/object/public/" + BUCKET + "/")  # bucket do Supabase (produção ou pilha local)
MSG_PENDENTES = ("fotos novas em fotos/divulgacao ainda não foram commitadas e enviadas para a master; "
                 "faça commit + push e rode de novo")
MSG_NAO_GERADO = "ainda não gerado: rode sem --aplicar, commite e envie"


class Falha(Exception):
    pass


def codigo_do_link(link):
    m = RE_POST.search(link or "")
    return m.group(1) if m else None


def perfil_do_og(url):
    """og:url vem como https://www.instagram.com/<perfil>/reel/<código>/ quando o post é de um perfil."""
    m = RE_PERFIL.search(url or "")
    return m.group(1) if m and m.group(1) not in ("p", "reel", "reels", "tv") else None


AGENTE_PREVIA = "Mozilla/5.0 (compatible; acoes-segundo-turno link preview; +https://github.com/guipfranco/acoes-segundo-turno)"
PAUSA = 3.0


class Limite(Exception):
    """O Instagram pediu para ir mais devagar (429)."""


def og_da_pagina(texto):
    """{img, url} das metas og:image e og:url do HTML."""
    def meta(prop):
        m = re.search(r'<meta[^>]+property="og:' + prop + r'"[^>]+content="([^"]*)"', texto) or             re.search(r'<meta[^>]+content="([^"]*)"[^>]+property="og:' + prop + '"', texto)
        return html.unescape(m.group(1)) if m else None
    return {"img": meta("image"), "url": meta("url")}


RE_MIDIA_EMBED = re.compile(r'<img[^>]*class="EmbeddedMediaImage"[^>]*>')
RE_RECORTE = re.compile(r"stp=c\d")
MAX_EMBED = 1080


def do_embed(texto):
    """{img, perfil} da página de embed. O srcset da mídia traz a arte inteira em vários tamanhos e também versões
    recortadas em quadrado (stp=c...); fica a maior inteira de até 1080 px, ou a menor inteira se todas passarem."""
    tag = RE_MIDIA_EMBED.search(texto or "")
    if not tag:
        return {"img": None, "perfil": None}
    srcset = re.search(r'srcset="([^"]*)"', tag.group(0))
    opcoes = []
    for parte in re.split(r",\s*(?=https?://)", html.unescape(srcset.group(1)) if srcset else ""):
        url, _, larg = parte.strip().rpartition(" ")
        if url and larg.endswith("w") and larg[:-1].isdigit() and not RE_RECORTE.search(url):
            opcoes.append((int(larg[:-1]), url))
    if not opcoes:
        return {"img": None, "perfil": None}
    cabem = [o for o in opcoes if o[0] <= MAX_EMBED]
    m = re.search(r'class="UsernameText">([A-Za-z0-9_.]+)<', texto)
    return {"img": (max(cabem) if cabem else min(opcoes))[1], "perfil": m.group(1) if m else None}


def ler_pagina(url):
    """HTML da página pedida como robô de prévia; None se não existir. 429 vira Limite."""
    req = urllib.request.Request(url, headers={"User-Agent": AGENTE_PREVIA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise Limite()
        return None


def previa(codigo):
    """Imagem do post: a arte inteira do embed; sem ela, o og:image recortado da página do post."""
    emb = do_embed(ler_pagina(f"https://www.instagram.com/p/{codigo}/embed/captioned/"))
    if emb["img"]:
        return {"codigo": codigo, "img": emb["img"], "perfil": emb["perfil"], "url": None, "inteira": True}
    texto = ler_pagina(f"https://www.instagram.com/p/{codigo}/")
    og = og_da_pagina(texto) if texto else {"img": None, "url": None}
    return dict(og, codigo=codigo, inteira=False)


def coletar(codigos, ler=previa, pausa=PAUSA, dormir=time.sleep):
    """Prévia de cada código, com pausa entre eles. Para no primeiro 429 e devolve o que já tinha."""
    saida = []
    for i, c in enumerate(codigos):
        if i:
            dormir(pausa)
        try:
            saida.append(ler(c))
        except Limite:
            print(f"Instagram pediu pausa (429) depois de {i} posts; rode de novo mais tarde", file=sys.stderr)
            break
    return saida


def carregar_mapa(arq=None):
    arq = Path(arq or sys.modules[__name__].MAPA)
    return json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else {}


def gravar_mapa(mapa, arq=None):
    arq = Path(arq or sys.modules[__name__].MAPA)
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text(json.dumps(mapa, ensure_ascii=False, indent=1), encoding="utf-8")


def foto_do_item(item, mapa):
    """{url, mini, credito, pagina} para o item da importação, ou None. `mini` é None enquanto a foto ainda está no
    bucket (antes do migrar-pages). O @ do perfil só aparece no crédito quando a ação tem organização pública
    reconhecida; sem isso o perfil pode ser de pessoa comum e o crédito fica genérico."""
    cod = codigo_do_link(item.get("link"))
    f = mapa.get(cod) if cod else None
    if not f or not f.get("url"):
        return None
    perfil = f.get("perfil")
    credito = f"Divulgação de @{perfil} no Instagram" if perfil and item.get("organizacao") else "Divulgação original no Instagram"
    return {"url": f["url"], "mini": f.get("mini") or None, "credito": credito, "pagina": item["link"]}


def pendentes(itens, mapa):
    vistos = []
    for it in itens:
        cod = codigo_do_link(it.get("link"))
        if cod and cod not in mapa and cod not in vistos:
            vistos.append(cod)
    return vistos


def reduzir(bruto, largura=LARGURA, qualidade=QUALIDADE):
    """JPEG de até `largura` px de largura (nunca amplia), sem metadados."""
    from PIL import Image
    im = Image.open(io.BytesIO(bruto)).convert("RGB")
    if im.width > largura:
        im = im.resize((largura, round(im.height * largura / im.width)), Image.LANCZOS)
    saida = io.BytesIO()
    im.save(saida, "JPEG", quality=qualidade, optimize=True, progressive=True)
    return saida.getvalue()


def baixar(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


# ---- GitHub Pages: fotos/divulgacao/ na raiz do repo ----

def urls_pages(cod):
    return f"{BASE_PAGES}/{cod}.jpg", f"{BASE_PAGES}/{cod}-mini.jpg"


def gravar_pages(cod, bruto, pasta=None):
    """Grava <código>.jpg (arte inteira) e <código>-mini.jpg (cards) em fotos/divulgacao/; devolve (url, mini)."""
    pasta = Path(pasta or sys.modules[__name__].PASTA_PAGES)
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / f"{cod}.jpg").write_bytes(reduzir(bruto))
    (pasta / f"{cod}-mini.jpg").write_bytes(reduzir(bruto, LARGURA_MINI, QUALIDADE_MINI))
    return urls_pages(cod)


def _git(args):
    r = subprocess.run(["git", *args], cwd=str(RAIZ), capture_output=True, text=True)
    if r.returncode:
        raise Falha(f"git {' '.join(args)}: {r.stderr.strip()[:200]}")
    return r.stdout


def fotos_pendentes(git=_git):
    """MSG_PENDENTES se há foto em fotos/ ainda não commitada ou ainda não enviada para a master do origin; senão None.
    Só o que já está na master é servido pelo Pages, então o banco não pode apontar para foto pendente."""
    if git(["status", "--porcelain", "fotos/"]).strip() or git(["log", "origin/master..HEAD", "--", "fotos/"]).strip():
        return MSG_PENDENTES
    return None


def _head(url):
    """Status HTTP de um HEAD (0 se a rede falhar)."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": AGENTE_PREVIA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except (urllib.error.URLError, OSError):
        return 0


def publicadas_no_pages(codigos, head=None):
    """Confere por HEAD que BASE_PAGES/<código>-mini.jpg responde 200 para cada código; devolve os que não respondem.
    O git diz que a foto está na master, mas o workflow do Pages pode ainda não ter terminado."""
    head = head or sys.modules[__name__]._head
    return [cod for cod in codigos if head(urls_pages(cod)[1]) != 200]


def exigir_no_pages(codigos, head=None):
    """Falha se o Pages ainda não serve alguma das minis."""
    faltam = publicadas_no_pages(codigos, head=head)
    if faltam:
        raise Falha(f"o Pages ainda não serve {len(faltam)} fotos (ex.: {faltam[0]}); espere o workflow terminar e rode de novo")


def codigos_no_pages(itens):
    """Códigos de post dos itens cuja foto (url ou mini) aponta para o Pages: são os que o banco vai referenciar."""
    cods = []
    for it in itens:
        f = it.get("foto") or {}
        if any(str(f.get(k) or "").startswith(BASE_PAGES + "/") for k in ("url", "mini")):
            cod = codigo_do_link(it.get("link"))
            if cod and cod not in cods:
                cods.append(cod)
    return cods


def processar_coleta(coleta, mapa, pasta=None, baixar=None):
    """Baixa, reduz e grava em fotos/divulgacao/ cada imagem coletada; devolve (novas, falhas). Atualiza `mapa` no lugar."""
    mod = sys.modules[__name__]
    baixar = baixar or mod.baixar
    novas, falhas = 0, []
    for c in coleta:
        cod, img = c.get("codigo"), c.get("img")
        if not cod or not img:
            falhas.append((cod, "sem imagem"))
            continue
        try:
            url, mini = gravar_pages(cod, baixar(img), pasta)
        except Exception as e:  # noqa: BLE001 - imagem quebrada ou link vencido: segue para a próxima
            falhas.append((cod, f"download: {e}"))
            continue
        mapa[cod] = {"url": url, "mini": mini, "perfil": c.get("perfil") or perfil_do_og(c.get("url")),
                     "inteira": bool(c.get("inteira")), "pages": True}
        novas += 1
    return novas, falhas


def no_bucket(mapa):
    """Códigos cuja foto ainda está no bucket do Supabase (ainda não migrou para o Pages)."""
    return [c for c, f in mapa.items() if f.get("url") and RE_BUCKET.search(f["url"])]


def gerados(cod, pasta=None):
    """True se os dois arquivos (<código>.jpg e <código>-mini.jpg) já existem em fotos/divulgacao/."""
    pasta = Path(pasta or sys.modules[__name__].PASTA_PAGES)
    return (pasta / f"{cod}.jpg").exists() and (pasta / f"{cod}-mini.jpg").exists()


def migrar_pages(mapa, codigos=None, aplicar=False, base_chave=None, pasta=None, baixar=None, trocar=None):
    """Sem aplicar (ensaio): para cada foto ainda no bucket, baixa de lá e grava os dois arquivos em fotos/divulgacao/
    (pula o que já existe), para o commit + push. Com aplicar NÃO gera nada: só aponta as ações (foto_url +
    foto_mini_url) para o Pages e atualiza o mapa para os códigos cujos dois arquivos já existem; os demais entram em
    falhas com MSG_NAO_GERADO. Devolve (geradas, trocadas, falhas)."""
    mod = sys.modules[__name__]
    pasta = Path(pasta or mod.PASTA_PAGES)
    baixar, trocar = baixar or mod.baixar, trocar or mod.trocar_nas_acoes
    geradas, trocadas, falhas = 0, 0, []
    for cod in (no_bucket(mapa) if codigos is None else codigos):
        velha = mapa[cod]["url"]
        if not gerados(cod, pasta):
            if aplicar:
                falhas.append((cod, MSG_NAO_GERADO))
                continue
            try:
                gravar_pages(cod, baixar(velha), pasta)
            except Exception as e:  # noqa: BLE001 - imagem sumiu do bucket: fica como está
                falhas.append((cod, f"download: {e}"))
                continue
            geradas += 1
        if not aplicar:
            continue
        url, mini = urls_pages(cod)
        base, chave = base_chave
        trocar(base, chave, velha, url, mini)
        mapa[cod] = dict(mapa[cod], url=url, mini=mini, pages=True)
        trocadas += 1
    return geradas, trocadas, falhas


# ---- Supabase Storage (fluxo antigo: refazer) ----

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


def recortadas(mapa):
    """Códigos cuja imagem guardada ainda é o og:image recortado (de antes do embed)."""
    return [c for c, f in mapa.items() if f.get("url") and not f.get("inteira")]


def trocar_nas_acoes(base, chave, velha, nova, mini=None):
    """Aponta para a imagem nova toda ação que usava a velha (e grava a mini, quando há); devolve quantas mudaram."""
    corpo = {"foto_url": nova}
    if mini is not None:
        corpo["foto_mini_url"] = mini
    req = urllib.request.Request(f"{base}/rest/v1/acao?foto_url=eq.{urllib.parse.quote(velha, safe='')}",
                                 data=json.dumps(corpo).encode(), method="PATCH",
                                 headers={"Authorization": "Bearer " + chave, "apikey": chave, "Content-Type": "application/json",
                                          "Prefer": "return=representation"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return len(json.loads(r.read() or b"[]"))
    except urllib.error.HTTPError as e:
        raise Falha(f"trocar foto nas ações: HTTP {e.code} {e.read().decode(errors='replace')[:200]}")


def refazer(mapa, base, chave, codigos=None, ler=previa, pasta=None, baixar=None, subir=None, trocar=None,
            pausa=PAUSA, dormir=time.sleep):
    """(Fluxo antigo, no bucket.) Troca as imagens recortadas pela arte inteira do embed. Sobe com nome novo
    (<código>-inteira.jpg, para não pegar a cópia antiga no cache de quem já abriu o app) e aponta as ações para ela.
    Devolve (novas, falhas); post sem imagem inteira (apagado, privado, vídeo sem capa) fica com a que tem."""
    mod = sys.modules[__name__]
    pasta, baixar, subir, trocar = pasta or mod.PASTA_IMG, baixar or mod.baixar, subir or mod.subir, trocar or mod.trocar_nas_acoes
    pasta.mkdir(parents=True, exist_ok=True)
    novas, falhas = 0, []
    for c in coletar(recortadas(mapa) if codigos is None else codigos, ler=ler, pausa=pausa, dormir=dormir):
        cod = c["codigo"]
        if not c.get("inteira") or not c.get("img"):
            falhas.append((cod, "sem imagem inteira"))
            continue
        try:
            dados = reduzir(baixar(c["img"]))
        except Exception as e:  # noqa: BLE001 - link vencido: fica a antiga
            falhas.append((cod, f"download: {e}"))
            continue
        (pasta / f"{cod}.jpg").write_bytes(dados)
        url = subir(base, chave, f"{cod}-inteira.jpg", dados)
        trocar(base, chave, mapa[cod]["url"], url)
        mapa[cod] = dict(mapa[cod], url=url, perfil=mapa[cod].get("perfil") or c.get("perfil"), inteira=True)
        novas += 1
    return novas, falhas


def buscar_fotos(itens, mapa=None, ler=previa):
    """Tenta a imagem de todo post ainda sem foto entre os itens, grava em fotos/divulgacao/ e salva o mapa.
    Devolve (mapa, novas, falhas). Chamado pelo publicar_acoes.py antes de publicar; post apagado ou privado só
    fica de fora. Foto nova precisa de commit + push antes de ir para o banco (fotos_pendentes)."""
    mapa = carregar_mapa() if mapa is None else mapa
    cods = pendentes(itens, mapa)
    if not cods:
        return mapa, 0, []
    print(f"fotos: {len(cods)} posts sem imagem, lendo a prévia (~{round(len(cods) * PAUSA / 60)} min)")
    coleta = coletar(cods, ler=ler)
    novas, falhas = processar_coleta(coleta, mapa)
    gravar_mapa(mapa)
    return mapa, novas, falhas


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    pp = sub.add_parser("pendentes")
    pp.add_argument("--itens", nargs="*", help="publicar-*.json (padrão: os mais recentes de cada fonte)")
    pc = sub.add_parser("coleta")
    pc.add_argument("arquivo")
    pr = sub.add_parser("coletar")
    pr.add_argument("--itens", nargs="*", help="publicar-*.json (padrão: os mais recentes de cada fonte)")
    pr.add_argument("--max", type=int, default=0, help="no máximo N posts nesta rodada")
    pm = sub.add_parser("migrar-pages", help="baixa do bucket o que ainda está lá e gera fotos/divulgacao/; --aplicar troca no banco")
    pm.add_argument("--max", type=int, default=0, help="no máximo N fotos nesta rodada")
    pm.add_argument("--aplicar", action="store_true",
                    help="não gera nada: aponta para o Pages as ações cujos dois arquivos já existem (commitados, enviados e servidos)")
    pz = sub.add_parser("refazer")
    pz.add_argument("--max", type=int, default=0, help="no máximo N posts nesta rodada")
    args = p.parse_args(argv)
    mapa = carregar_mapa()
    try:
        if args.cmd == "migrar-pages":
            cods = no_bucket(mapa)
            cods = cods[:args.max] if args.max else cods
            print(f"{len(cods)} fotos ainda no bucket {BUCKET}")
            base_chave = None
            if args.aplicar:
                pend = fotos_pendentes()
                if pend:
                    raise Falha(pend)
                exigir_no_pages([c for c in cods if gerados(c)])  # o workflow do Pages precisa ter terminado
                base_chave = destino_storage()
            try:
                geradas, trocadas, falhas = migrar_pages(mapa, codigos=cods, aplicar=args.aplicar, base_chave=base_chave)
            finally:
                if args.aplicar:
                    gravar_mapa(mapa)
            nao_gerados = [cod for cod, motivo in falhas if motivo == MSG_NAO_GERADO]
            falhas = [f for f in falhas if f[1] != MSG_NAO_GERADO]
            print(f"{geradas} geradas em fotos/divulgacao; {trocadas} ações apontadas para o Pages; {len(falhas)} falhas")
            for cod, motivo in falhas:
                print(f"  {cod}: {motivo}")
            if nao_gerados:
                print(f"{len(nao_gerados)} ainda não gerados: rode sem --aplicar, commite e envie ({', '.join(nao_gerados)})")
            if not args.aplicar:
                print("ensaio: nada mudou no banco. Faça commit + push de fotos/, espere o Pages e rode com --aplicar")
            return 0
        if args.cmd == "refazer":
            cods = recortadas(mapa)
            cods = cods[:args.max] if args.max else cods
            print(f"{len(cods)} imagens recortadas para trocar (~{round(len(cods) * PAUSA / 60)} min)")
            base, chave = destino_storage()
            try:
                novas, falhas = refazer(mapa, base, chave, codigos=cods)
            finally:
                gravar_mapa(mapa)
            print(f"{novas} imagens trocadas pela arte inteira; {len(recortadas(mapa))} ainda recortadas; {len(falhas)} falhas")
            for cod, motivo in falhas:
                print(f"  {cod}: {motivo}")
            return 0
        if args.cmd in ("pendentes", "coletar"):
            arqs = args.itens or [str(sorted((RAIZ / "levantamento").glob(f"publicar-{f}-*.json"))[-1])
                                  for f in ("bora-lula", "redes") if list((RAIZ / "levantamento").glob(f"publicar-{f}-*.json"))]
            itens = [it for a in arqs for it in json.loads(Path(a).read_text(encoding="utf-8"))]
            cods = pendentes(itens, mapa)
            if args.cmd == "pendentes":
                print(json.dumps(cods))
                return 0
            cods = cods[:args.max] if args.max else cods
            print(f"{len(cods)} posts para ler (~{round(len(cods) * PAUSA / 60)} min)")
            coleta = coletar(cods)
        else:
            coleta = json.loads(Path(args.arquivo).read_text(encoding="utf-8"))
        novas, falhas = processar_coleta(coleta, mapa)
        gravar_mapa(mapa)
        print(f"{novas} imagens novas em fotos/divulgacao; {len(mapa)} no mapa; {len(falhas)} falhas")
        if novas:
            print("faça commit + push de fotos/ e espere o Pages antes de publicar no banco")
        for cod, motivo in falhas:
            print(f"  {cod}: {motivo}")
    except Falha as e:
        print("ERRO: " + str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
