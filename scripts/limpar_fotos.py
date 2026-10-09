"""Apaga do bucket público `fotos-acoes` as imagens que nenhuma ação nem organização usa mais.

Quem envia a imagem no cadastro (passo 3 de 4) e desiste antes de concluir deixa o arquivo no bucket; ação recusada
ou excluída na Fila também deixa o dela. Este script lista os objetos do bucket, compara com `acao.foto_url` e
`organizacao.foto_url` e apaga o que ninguém referencia e tem mais de 24 h (a margem evita apagar a foto de um
cadastro que está sendo preenchido agora).

Uso:
  python scripts/limpar_fotos.py             # ensaio: lista o que apagaria, não mexe em nada
  python scripts/limpar_fotos.py --aplicar   # apaga
  python scripts/limpar_fotos.py --horas 48  # margem maior

Destino como em scripts/fotos_divulgacao.py: SUPABASE_URL + SUPABASE_SERVICE_KEY (pilha local) ou
SUPABASE_ACCESS_TOKEN (produção, a chave de serviço é lida pela Management API e fica só na memória).
"""
import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fotos_divulgacao as fd  # noqa: E402

BUCKET = "fotos-acoes"
HORAS = 24
PAGINA = 1000
LOTE = 100


class Falha(Exception):
    pass


def _pedir(metodo, url, chave, corpo=None):
    req = urllib.request.Request(url, data=json.dumps(corpo).encode() if corpo is not None else None, method=metodo,
                                 headers={"Authorization": "Bearer " + chave, "apikey": chave, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode() or "null")
    except urllib.error.HTTPError as e:
        raise Falha(f"{metodo} {url}: HTTP {e.code} {e.read().decode(errors='replace')[:200]}")


def listar_objetos(base, chave, bucket=BUCKET, prefixo="", pedir=_pedir):
    """Todos os objetos do bucket, com pasta: [{"name": "<uid>/<arquivo>", "created_at": ...}]. A listagem do Storage
    mostra só um nível; pasta (entrada sem id) é percorrida por dentro."""
    saida, deslocamento = [], 0
    while True:
        pagina = pedir("POST", f"{base}/storage/v1/object/list/{bucket}", chave,
                       {"prefix": prefixo, "limit": PAGINA, "offset": deslocamento, "sortBy": {"column": "name", "order": "asc"}}) or []
        for o in pagina:
            nome = (prefixo + "/" if prefixo else "") + o["name"]
            if o.get("id") is None:  # pasta
                saida.extend(listar_objetos(base, chave, bucket, nome, pedir))
            else:
                saida.append({"name": nome, "created_at": o.get("created_at")})
        if len(pagina) < PAGINA:
            return saida
        deslocamento += PAGINA


def urls_referenciadas(base, chave, pedir=_pedir):
    """Toda foto_url de acao e organizacao que aponta para o bucket (qualquer status: cancelada e suspensa continuam
    guardando a imagem)."""
    urls = set()
    for tabela in ("acao", "organizacao"):
        linhas = pedir("GET", f"{base}/rest/v1/{tabela}?select=foto_url&foto_url=like.*{BUCKET}*&limit=100000", chave) or []
        urls.update(l["foto_url"] for l in linhas if l.get("foto_url"))
    return urls


def nome_da_url(url, bucket=BUCKET):
    """Caminho do objeto a partir da url pública (…/object/public/<bucket>/<uid>/<arquivo>?x=y), ou None se não é do bucket."""
    caminho = urllib.parse.urlsplit(str(url or "")).path
    for marca in (f"/object/public/{bucket}/", f"/object/{bucket}/", f"/render/image/public/{bucket}/"):
        if marca in caminho:
            return urllib.parse.unquote(caminho.split(marca, 1)[1]) or None
    return None


def selecionar(objetos, urls, agora=None, horas=HORAS, bucket=BUCKET):
    """Nomes a apagar: objetos sem referência em `urls` e criados há mais de `horas`. Objeto sem data fica."""
    agora = agora or datetime.now(timezone.utc)
    usados = {n for n in (nome_da_url(u, bucket) for u in urls) if n}
    limite = agora - timedelta(hours=horas)
    apagar = []
    for o in objetos:
        if o["name"] in usados or not o.get("created_at"):
            continue
        criado = datetime.fromisoformat(str(o["created_at"]).replace("Z", "+00:00"))
        if criado.tzinfo is None:
            criado = criado.replace(tzinfo=timezone.utc)
        if criado < limite:
            apagar.append(o["name"])
    return sorted(apagar)


def apagar(base, chave, nomes, bucket=BUCKET, pedir=_pedir):
    for i in range(0, len(nomes), LOTE):
        pedir("DELETE", f"{base}/storage/v1/object/{bucket}", chave, {"prefixes": nomes[i:i + LOTE]})
    return len(nomes)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--aplicar", action="store_true", help="apaga de verdade (sem isso só lista)")
    p.add_argument("--horas", type=float, default=HORAS, help=f"só apaga o que tem mais de N horas (padrão {HORAS})")
    p.add_argument("--bucket", default=BUCKET)
    args = p.parse_args(argv)
    try:
        base, chave = fd.destino_storage()
        objetos = listar_objetos(base, chave, args.bucket)
        urls = urls_referenciadas(base, chave)
        nomes = selecionar(objetos, urls, horas=args.horas, bucket=args.bucket)
        print(f"bucket {args.bucket}: {len(objetos)} objetos, {len(urls)} urls referenciadas, {len(nomes)} sem uso há mais de {args.horas:g} h")
        for n in nomes:
            print("  " + n)
        if not args.aplicar:
            print("ensaio: nada apagado (use --aplicar)")
            return 0
        print(f"apagados: {apagar(base, chave, nomes, args.bucket)}")
    except (Falha, fd.Falha) as e:
        print("ERRO: " + str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
