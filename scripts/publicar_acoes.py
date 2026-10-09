"""Publica no Supabase as ações de fontes públicas: a agenda "Bora Lula" do Comitê Popular e o consolidado
da varredura das redes. Idempotente: reimportar atualiza, o que sumiu da fonte vira "encerrada"
(função SQL importar_acoes, migração 20261009000001).

Uso:
  python scripts/publicar_acoes.py bora-lula                       # baixa o feed e ENSAIA (não grava)
  python scripts/publicar_acoes.py bora-lula --aplicar             # grava no banco
  python scripts/publicar_acoes.py bora-lula --de ARQ.json         # usa um feed já baixado
  python scripts/publicar_acoes.py redes --de ARQ.csv [--feed ARQ.json] [--aplicar]
                                                                   # consolidado das redes, sem o que já está no feed

Destino (variáveis de ambiente ou .env na raiz, nunca no repo), na ordem em que são procuradas:
  SUPABASE_URL + SUPABASE_SERVICE_KEY     REST com a chave de serviço (pilha local do `npx supabase start`)
  SUPABASE_ACCESS_TOKEN (+ ref do projeto em supabase/.temp/project-ref ou --ref)
                                          Management API, como em scripts/ir_ao_ar.py (produção)

O ensaio escreve em levantamento/ (fora do git): publicar-<fonte>-<data>.json com os itens que iriam para o
banco e revisao-<fonte>-<data>.csv com o que ficou de fora e por quê.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bora_lula as bl  # noqa: E402

RAIZ = bl.RAIZ
ATE = "2026-10-25"
FONTE_REDES = "Varredura pública das redes (Instagram, Facebook, X, Telegram e sites de organizações)"


class Falha(Exception):
    pass


# ---- conversão: feed Bora Lula ----

def chave_ato(data, uf, cidade, inicio, local):
    """Mesmo ato publicado duas vezes com títulos diferentes: mesma data, cidade, hora e local."""
    local = re.sub(r"\W+", " ", bl.sem_acento(local)).strip()
    if not local:
        return None
    return (data, uf, bl.sem_acento(cidade), inicio, local)


def descricao_de(atividade, plataforma, fonte):
    d = (atividade or "").strip()
    if plataforma:
        d += f" ({plataforma})"
    return d + "\n\nFonte: " + fonte + "."


def item_do_feed(x, lugares):
    """Converte um item do feed em item para importar_acoes. Devolve (item, None) ou (None, motivo)."""
    online = bool(x.get("online"))
    cidade, uf = (x.get("cidade") or "").strip(), (x.get("uf") or "").strip()
    local, endereco = (x.get("local") or "").strip(), (x.get("endereco") or "").strip()
    h_ini, h_fim = bl.faixa(x.get("hora"), x.get("hora_ord"))
    data = x["data"]
    item = {
        "fonte_id": str(x["id"]), "titulo": (x.get("atividade") or "Ação")[:120], "tipo": bl.tipo_mapa(x.get("tipo")),
        "organizacao": (x.get("organizacao") or "").strip() or None, "link": (x.get("link") or "").strip(),
        "inicio": f"{data}T{h_ini}", "fim": f"{data}T{h_fim}",
    }
    item["organizacao_tipo"] = bl.tipo_org(item["organizacao"]) if item["organizacao"] else None
    if online:
        item.update(online=True, lugar_nome=None, bairro=None, cidade=None, lat=None, lon=None, lugar_aproximado=False)
    else:
        r = bl.resolver_lugar(cidade, uf, lugares)
        if not r:
            return None, "sem cidade reconhecida" if cidade else "sem cidade"
        cidade, bairro, c = r
        item.update(online=False, lugar_nome=(local or endereco or cidade)[:120],
                    bairro=(bairro or bl.bairro_do_endereco(endereco, cidade)) or None,
                    cidade=cidade, lat=c[0], lon=c[1], lugar_aproximado=True)
    item["descricao"] = descricao_de(x.get("atividade"), x.get("plataforma"), bl.FONTE)
    return item, None


def itens_do_feed(feed, lugares, hoje=None, ate=ATE):
    """(itens, revisao). revisao: lista de (fonte_id, título, motivo) do que ficou de fora."""
    hoje = hoje or feed.get("hoje") or date.today().isoformat()
    itens, revisao, vistos = [], [], {}
    for x in sorted(feed.get("acoes", []), key=lambda a: a["id"]):
        data = x.get("data") or ""
        if not (hoje <= data <= ate):
            continue
        item, motivo = item_do_feed(x, lugares)
        if not item:
            revisao.append((str(x["id"]), x.get("atividade") or "", motivo))
            continue
        k = chave_ato(data, x.get("uf"), x.get("cidade"), item["inicio"], x.get("local")) if not item["online"] else None
        if k and k in vistos:
            revisao.append((str(x["id"]), x.get("atividade") or "", f"duplicata do id {vistos[k]}"))
            continue
        if k:
            vistos[k] = x["id"]
        itens.append(item)
    return itens, revisao


# ---- conversão: consolidado das redes ----

TIPOS_REDES = {"panfletagem": "panfletagem", "adesivaco": "adesivaço", "bandeiraco": "bandeiraço",
               "roda de conversa": "roda de conversa", "corpo a corpo": "porta a porta",
               "distribuicao de material": "panfletagem", "banquinha": "panfletagem"}


def tipo_redes(tipo):
    t = bl.sem_acento(tipo)
    for k, v in TIPOS_REDES.items():
        if k in t:
            return v
    return "outro"


def id_redes(r):
    base = (r.get("link") or "").strip() or f"{r.get('titulo')}|{r.get('data')}|{r.get('cidade')}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]


ORG_RUIM = ("nao identificado", "perfil", "criador de conteudo", "@", "moradores", "grupo)", "divulga")
ORG_BOA = ("comite", "coletivo", "frente", "uje", "ujs", "une", "uee", "dce", "campanha", "pedalula", "judias", "retomada",
           "revista", "sambistas", "entidades", "mstc", "com lula", "jpt", "pretas", "linha de frente", "ocupacao")


def limpar_org(texto):
    """Só organização pública reconhecível vira organização; pessoa comum, perfil ou "não identificado" fica de fora."""
    org = (texto or "").split(";")[0]
    org = re.split(r",?\s*divulgad[oa] por", org, flags=re.I)[0]
    org = re.sub(r"\s*\((página|perfil|canal|site oficial)[^)]*\)\s*$", "", org, flags=re.I).strip(" ,")
    n = bl.sem_acento(org)
    if not org or any(k in n for k in ORG_RUIM):
        return None
    tipo = bl.tipo_org(org)
    if tipo == "coletivo" and not any(k in n for k in ORG_BOA):
        return None
    fora = re.sub(r"\(.*?\)", "", org)
    if tipo == "mandato" and re.search(r",| e ", fora):
        return None  # lista de pessoas, não um mandato
    org = re.sub(r"\)\s*,.*$", ")", org)  # "Sigla (X), entidades e tal" -> "Sigla (X)"
    if tipo != "mandato":  # parêntese final só fica se for sigla; "(com Fulana e Beltrano)" cai
        org = re.sub(r"\s*\((?=[^)]*[a-z]{2})[^)]*\)\s*$", "", org).strip(" ,")
    return org[:120]


def item_da_rede(r, lugares):
    if "bora lula" in bl.sem_acento(r.get("texto_original")):
        return None, "já vem do feed Bora Lula"
    if bl.sem_acento(r.get("lula_explicito")) != "sim":
        return None, "sem Lula explícito"
    if bl.sem_acento(r.get("confianca")) == "baixa":
        return None, "confiança baixa"
    online = bl.sem_acento(r.get("online")) == "sim"
    cidade, uf = (r.get("cidade") or "").strip(), (r.get("uf") or "").strip()
    endereco, bairro = (r.get("endereco") or "").strip(), (r.get("bairro") or "").strip()
    hora = (r.get("hora") or "").strip()
    h_ini, h_fim = bl.faixa(hora, None) if hora else ("09:00", "11:00")
    data = r["data"]
    org = limpar_org(r.get("organizador"))
    item = {
        "fonte_id": id_redes(r), "titulo": (r.get("titulo") or "Ação")[:120], "tipo": tipo_redes(r.get("tipo")),
        "organizacao": org or None, "organizacao_tipo": bl.tipo_org(org) if org else None,
        "link": (r.get("link") or "").strip(), "inicio": f"{data}T{h_ini}", "fim": f"{data}T{h_fim}",
    }
    if online:
        item.update(online=True, lugar_nome=None, bairro=None, cidade=None, lat=None, lon=None, lugar_aproximado=False)
    else:
        res = bl.resolver_lugar(cidade, uf, lugares)
        if not res:
            return None, "sem cidade reconhecida" if cidade else "sem cidade"
        cidade, bairro_df, c = res
        item.update(online=False, lugar_nome=(endereco or bairro or bairro_df or cidade)[:120],
                    bairro=(bairro or bairro_df or bl.bairro_do_endereco(endereco, cidade)) or None,
                    cidade=cidade, lat=c[0], lon=c[1], lugar_aproximado=True)
    item["descricao"] = descricao_de(r.get("titulo"), "", FONTE_REDES)
    return item, None


def tokens(s):
    return {t for t in re.sub(r"\W+", " ", bl.sem_acento(s)).split() if len(t) > 2}


def parecidos(a, b):
    ta, tb = tokens(a), tokens(b)
    return bool(ta and tb) and len(ta & tb) / len(ta | tb) >= 0.5


def repetido_no_feed(item, itens_feed):
    """Mesmo link, ou mesma data+cidade com título parecido."""
    link = item["link"].rstrip("/")
    for f in itens_feed:
        if link and f["link"].rstrip("/") == link:
            return f["fonte_id"]
        if f["inicio"][:10] == item["inicio"][:10] and bl.sem_acento(f["cidade"]) == bl.sem_acento(item["cidade"]) \
                and parecidos(f["titulo"], item["titulo"]):
            return f["fonte_id"]
    return None


def itens_do_consolidado(linhas, lugares, itens_feed=(), hoje=None, ate=ATE):
    hoje = hoje or date.today().isoformat()
    itens, revisao, vistos = [], [], set()
    for r in linhas:
        data = r.get("data") or ""
        if not (hoje <= data <= ate):
            continue
        item, motivo = item_da_rede(r, lugares)
        if not item:
            revisao.append((r.get("frente", ""), r.get("titulo", ""), motivo))
            continue
        dup = repetido_no_feed(item, itens_feed)
        if dup:
            revisao.append((r.get("frente", ""), r.get("titulo", ""), f"já está no feed Bora Lula (id {dup})"))
            continue
        if item["fonte_id"] in vistos:
            revisao.append((r.get("frente", ""), r.get("titulo", ""), "repetido no consolidado"))
            continue
        vistos.add(item["fonte_id"])
        itens.append(item)
    return itens, revisao


# ---- destino ----

def sql_importar(fonte, itens, encerrar=True):
    corpo = json.dumps(itens, ensure_ascii=False)
    tag = "$itens$"
    if tag in corpo:
        raise Falha("os itens contêm a tag de citação do SQL")
    return f"select importar_acoes('{fonte}', {tag}{corpo}{tag}::jsonb, {'true' if encerrar else 'false'}) as r"


def _http(metodo, url, corpo, cab):
    req = urllib.request.Request(url, data=json.dumps(corpo).encode(), headers={**cab, "Content-Type": "application/json"}, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read().decode() or "null")
    except urllib.error.HTTPError as e:
        texto = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(texto)
        except ValueError:
            return e.code, texto


def destino():
    import ir_ao_ar
    ir_ao_ar.ler_env()
    url, chave = os.environ.get("SUPABASE_URL", "").strip(), os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
    if url and chave:
        return "rest", url, chave
    token = os.environ.get("SUPABASE_ACCESS_TOKEN", "").strip()
    if token:
        return "management", None, token
    raise Falha("defina SUPABASE_URL + SUPABASE_SERVICE_KEY (local) ou SUPABASE_ACCESS_TOKEN (produção)")


def publicar(fonte, itens, encerrar=True, ref=None):
    modo, url, chave = destino()
    if modo == "rest":
        st, resp = _http("POST", url.rstrip("/") + "/rest/v1/rpc/importar_acoes",
                         {"fonte": fonte, "itens": itens, "encerrar_faltantes": encerrar},
                         {"apikey": chave, "Authorization": "Bearer " + chave})
    else:
        import ir_ao_ar
        ref = ref or (ir_ao_ar.ARQ_REF.read_text().strip() if ir_ao_ar.ARQ_REF.exists() else None)
        if not ref:
            raise Falha("não sei o ref do projeto: passe --ref")
        st, resp = _http("POST", f"{ir_ao_ar.API}/projects/{ref}/database/query", {"query": sql_importar(fonte, itens, encerrar)},
                         {"Authorization": "Bearer " + chave})
        if 200 <= st < 300 and isinstance(resp, list) and resp:
            resp = resp[0].get("r")
    if not 200 <= st < 300:
        raise Falha(f"importar_acoes: HTTP {st} {resp}")
    return resp


# ---- linha de comando ----

def resumo(itens, revisao):
    por_uf = {}
    for i in itens:
        k = "online" if i["online"] else i["cidade"]
        por_uf[k] = por_uf.get(k, 0) + 1
    top = ", ".join(f"{k} {v}" for k, v in sorted(por_uf.items(), key=lambda kv: -kv[1])[:8])
    motivos = {}
    for _, _, m in revisao:
        m = re.sub(r"\s*\(.*|\s*\d+$", "", m)
        motivos[m] = motivos.get(m, 0) + 1
    fora = ", ".join(f"{m} {n}" for m, n in sorted(motivos.items(), key=lambda kv: -kv[1]))
    return f"{len(itens)} para publicar ({top}); {len(revisao)} de fora: {fora or 'nada'}"


def gravar_ensaio(fonte, itens, revisao):
    hoje = datetime.now().strftime("%Y-%m-%d")
    pasta = RAIZ / "levantamento"
    pasta.mkdir(exist_ok=True)
    arq_itens = pasta / f"publicar-{fonte}-{hoje}.json"
    arq_itens.write_text(json.dumps(itens, ensure_ascii=False, indent=1), encoding="utf-8")
    arq_rev = pasta / f"revisao-{fonte}-{hoje}.csv"
    with arq_rev.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "titulo", "motivo"])
        w.writerows(revisao)
    return arq_itens, arq_rev


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("fonte", choices=["bora-lula", "redes"])
    p.add_argument("--de", help="feed JSON (bora-lula) ou CSV consolidado (redes); bora-lula sem --de baixa o feed")
    p.add_argument("--feed", help="redes: feed JSON para não repetir o que já está nele")
    p.add_argument("--hoje", help="AAAA-MM-DD (padrão: hoje, ou o campo hoje do feed)")
    p.add_argument("--ate", default=ATE)
    p.add_argument("--aplicar", action="store_true", help="grava no banco (sem isso só ensaia)")
    p.add_argument("--sem-encerrar", action="store_true", help="não encerra o que sumiu da fonte")
    p.add_argument("--ref", help="ref do projeto (Management API)")
    args = p.parse_args(argv)
    lugares = bl.carregar_lugares()
    try:
        if args.fonte == "bora-lula":
            if args.de:
                feed = json.loads(Path(args.de).read_text(encoding="utf-8"))
            else:
                arq, feed = bl.baixar()
                print(f"feed guardado em {arq}")
            itens, revisao = itens_do_feed(feed, lugares, hoje=args.hoje, ate=args.ate)
        else:
            if not args.de:
                p.error("redes precisa de --de ARQ.csv")
            with open(args.de, encoding="utf-8", newline="") as f:
                linhas = list(csv.DictReader(f))
            itens_feed = []
            if args.feed:
                feed = json.loads(Path(args.feed).read_text(encoding="utf-8"))
                itens_feed, _ = itens_do_feed(feed, lugares, hoje=args.hoje, ate=args.ate)
            itens, revisao = itens_do_consolidado(linhas, lugares, itens_feed, hoje=args.hoje, ate=args.ate)
        print(resumo(itens, revisao))
        arq_itens, arq_rev = gravar_ensaio(args.fonte, itens, revisao)
        print(f"itens: {arq_itens}\nrevisão: {arq_rev}")
        if not args.aplicar:
            print("ensaio: nada gravado (use --aplicar)")
            return 0
        r = publicar(args.fonte, itens, encerrar=not args.sem_encerrar, ref=args.ref)
        print(f"gravado: {r}")
    except Falha as e:
        print("ERRO: " + str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
