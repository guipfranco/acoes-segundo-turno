"""Publica no Supabase as ações de fontes públicas: a agenda "Bora Lula" do Comitê Popular e o consolidado
da varredura das redes. Idempotente: reimportar atualiza, o que sumiu da fonte vira "encerrada"
(função SQL importar_acoes, migrações 20261009000001 e 20261009000002). O endereço vira ponto exato pelo
Nominatim (OpenStreetMap), com cache em levantamento/geocache.json; organização reconhecível ganha o logo
(Wikimedia Commons, scripts/bora_lula.py LOGOS).

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
import fotos_divulgacao as fd  # noqa: E402

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


def item_do_feed(x, lugares, geo=None):
    """Converte um item do feed em item para importar_acoes. Devolve (item, None) ou (None, motivo)."""
    online = bool(x.get("online"))
    cidade, uf = (x.get("cidade") or "").strip(), (x.get("uf") or "").strip()
    local, endereco = (x.get("local") or "").strip(), (x.get("endereco") or "").strip()
    h_ini, h_fim = bl.faixa(x.get("hora"), x.get("hora_ord"))
    data = x["data"]
    link_bruto = (x.get("link") or "").strip()
    item = {
        "fonte_id": str(x["id"]), "titulo": (x.get("atividade") or "Ação")[:120], "tipo": bl.tipo_mapa(x.get("tipo"), x.get("atividade")),
        "organizacao": (x.get("organizacao") or "").strip() or None, "link": bl.link_valido(link_bruto),
        "inicio": f"{data}T{h_ini}", "fim": f"{data}T{h_fim}",
    }
    if link_bruto and not item["link"]:  # sem link válido o contato vira organizador_chama (importar_acoes)
        item["aviso"] = bl.aviso_link(link_bruto)
    item["organizacao_tipo"] = bl.tipo_org(item["organizacao"]) if item["organizacao"] else None
    item["organizacao_foto"] = bl.logo_org(item["organizacao"]) if item["organizacao"] else None
    if online:
        item.update(online=True, lugar_nome=None, bairro=None, cidade=None, lat=None, lon=None, lugar_aproximado=False)
    else:
        r = bl.resolver_lugar(cidade, uf, lugares)
        if not r:
            return None, "sem cidade reconhecida" if cidade else "sem cidade"
        cidade, bairro, c = r
        lat, lon, precisao = bl.localizar(geo, endereco, local, cidade, uf, c)
        item.update(online=False, lugar_nome=(local or endereco or cidade)[:120],
                    bairro=(bairro or bl.bairro_do_endereco(endereco, cidade)) or None,
                    cidade=cidade, lat=lat, lon=lon, lugar_aproximado=precisao == "cidade")
    item["descricao"] = descricao_de(x.get("atividade"), x.get("plataforma"), bl.FONTE)
    return item, None


def itens_do_feed(feed, lugares, hoje=None, ate=ATE, geo=None):
    """(itens, revisao). revisao: lista de (fonte_id, título, motivo) do que ficou de fora."""
    hoje = hoje or feed.get("hoje") or date.today().isoformat()
    itens, revisao, vistos = [], [], {}
    for x in sorted(feed.get("acoes", []), key=lambda a: a["id"]):
        data = x.get("data") or ""
        if not (hoje <= data <= ate):
            continue
        item, motivo = item_do_feed(x, lugares, geo)
        if not item:
            revisao.append((str(x["id"]), x.get("atividade") or "", motivo))
            continue
        k = chave_ato(data, x.get("uf"), x.get("cidade"), item["inicio"], x.get("local")) if not item["online"] else None
        if k and k in vistos:
            revisao.append((str(x["id"]), x.get("atividade") or "", f"duplicata do id {vistos[k]}"))
            continue
        if k:
            vistos[k] = x["id"]
        anotar_aviso(item, revisao, str(x["id"]), x.get("atividade") or "")
        itens.append(item)
    return itens, revisao


def anotar_aviso(item, revisao, ident, titulo):
    """O item entra mesmo assim, mas o aviso vai para a fila de revisão (revisao-*.csv) com o prefixo "aviso:"."""
    aviso = item.pop("aviso", None)
    if aviso:
        revisao.append((ident, titulo, "aviso: " + aviso))


# ---- conversão: consolidado das redes ----

TIPOS_REDES = {"panfletagem": "panfletagem", "adesivaco": "adesivaço", "bandeiraco": "bandeiraço",
               "roda de conversa": "encontro", "plenaria": "encontro", "encontro": "encontro", "corpo a corpo": "porta a porta",
               "distribuicao de material": "panfletagem", "banquinha": "panfletagem", "caminhada": "caminhada",
               "carreata": "caminhada", "ato": "ato", "cultural": "cultural", "sarau": "cultural"}


def tipo_redes(tipo, titulo=""):
    t = bl.sem_acento(tipo)
    for k, v in TIPOS_REDES.items():
        if re.search(r"\b" + k, t):  # início de palavra: "ato" não casa com "contato"
            return v
    return bl.tipo_pelo_titulo(titulo)


def id_redes(link, inicio, cidade, titulo):
    """Id estável: só da própria linha (link, início normalizado, cidade resolvida, título), nunca das outras linhas."""
    base = "|".join([link, inicio, bl.sem_acento(cidade or "online"), " ".join(sorted(tokens(titulo)))])
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]


ORG_RUIM = ("nao identificado", "perfil", "criador de conteudo", "@", "moradores", "grupo)", "divulga")
ORG_BOA = ("comite", "coletivo", "frente", "uje", "ujs", "une", "uee", "dce", "campanha", "pedalula", "judias", "retomada",
           "revista", "sambistas", "entidades", "mstc", "com lula", "jpt", "pretas", "linha de frente", "ocupacao")


def limpar_org(texto):
    """Só organização pública reconhecível vira organização; pessoa comum, perfil ou "não identificado" fica de fora."""
    org = (texto or "").split(";")[0]
    org = re.split(r",?\s*divulgad[oa] por\b", org, flags=re.I)[0]
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


def item_da_rede(r, lugares, geo=None):
    if "bora lula" in bl.sem_acento(r.get("texto_original")):
        return None, "já vem do feed Bora Lula"
    if bl.sem_acento(r.get("lula_explicito")) != "sim":
        return None, "sem Lula explícito"
    if bl.sem_acento(r.get("confianca")) == "baixa":
        return None, "confiança baixa"
    online = bl.sem_acento(r.get("online")) == "sim"
    cidade, uf = (r.get("cidade") or "").strip(), (r.get("uf") or "").strip()
    cidade = re.sub(r"\s*[-/,]\s*[A-Za-z]{2}$", "", cidade)  # "Recife - PE" -> "Recife"
    endereco, bairro = (r.get("endereco") or "").strip(), (r.get("bairro") or "").strip()
    hora = (r.get("hora") or "").strip()
    h_ini, h_fim = bl.faixa(hora, None) if hora else ("09:00", "11:00")
    data = r["data"]
    org = limpar_org(r.get("organizador"))
    link_bruto = (r.get("link") or "").strip()
    item = {
        "fonte_id": None, "titulo": (r.get("titulo") or "Ação")[:120], "tipo": tipo_redes(r.get("tipo"), r.get("titulo")),
        "organizacao": org or None, "organizacao_tipo": bl.tipo_org(org) if org else None,
        "organizacao_foto": bl.logo_org(org) if org else None, "link": bl.link_valido(link_bruto), "inicio": f"{data}T{h_ini}", "fim": f"{data}T{h_fim}",
    }
    if link_bruto and not item["link"]:
        item["aviso"] = bl.aviso_link(link_bruto)
    if online:
        item.update(online=True, lugar_nome=None, bairro=None, cidade=None, lat=None, lon=None, lugar_aproximado=False)
    else:
        res = bl.resolver_lugar(cidade, uf, lugares)
        if not res:
            return None, "sem cidade reconhecida" if cidade else "sem cidade"
        cidade, bairro_df, c = res
        lat, lon, precisao = bl.localizar(geo, endereco, "", cidade, uf, c)
        item.update(online=False, lugar_nome=(endereco or bairro or bairro_df or cidade)[:120],
                    bairro=(bairro or bairro_df or bl.bairro_do_endereco(endereco, cidade)) or None,
                    cidade=cidade, lat=lat, lon=lon, lugar_aproximado=precisao == "cidade")
    item["fonte_id"] = id_redes(item["link"], item["inicio"], item["cidade"], item["titulo"])
    item["descricao"] = descricao_de(r.get("titulo"), "", FONTE_REDES)
    return item, None


def tokens(s):
    return {t for t in re.sub(r"\W+", " ", bl.sem_acento(s)).split() if len(t) > 2}


def parecidos(a, b):
    ta, tb = tokens(a), tokens(b)
    return bool(ta and tb) and len(ta & tb) / len(ta | tb) >= 0.5


# palavras de campanha que todo ato tem e não distinguem um do outro
COMUNS = {"lula", "com", "pela", "pelo", "para", "contra", "ato", "democracia", "frente", "concentracao", "praca", "rua",
          "centro", "campanha", "turno", "todos", "nos", "das", "dos", "uma", "estudantes", "estudantil",
          # tipo de ação também não distingue: duas plenárias da virada na mesma hora podem ser em lugares diferentes
          "plenaria", "virada", "caminhada", "panfletagem", "panfletaco", "adesivaco", "bandeiraco", "carreata", "marcha",
          "mobilizacao", "assembleia", "encontro", "reuniao", "passeata", "grande", "geral", "nacional", "dia"}


def marcas(item):
    """Palavras do título e do lugar que identificam o ato, sem cidade, bairro e palavras comuns."""
    fora = tokens(item.get("cidade") or "") | tokens(item.get("bairro") or "") | COMUNS
    return tokens(f'{item["titulo"]} {item.get("lugar_nome") or ""}') - fora


def mesmo_ato(a, b, hora_explicita=True, link_basta=True):
    """Mesmo link no mesmo início e cidade; ou mesma data+cidade com título parecido; ou mesmo início+cidade com título
    ou lugar em comum (só com hora explícita). Sem link_basta (duas linhas das redes), o mesmo link só conta se as
    palavras próprias não se contradizem."""
    if a["inicio"][:10] != b["inicio"][:10] or bl.sem_acento(a["cidade"]) != bl.sem_acento(b["cidade"]):
        return False
    link = a["link"].rstrip("/")
    if link and link == b["link"].rstrip("/") and a["inicio"] == b["inicio"]:
        ma, mb = marcas(a), marcas(b)
        if link_basta or not (ma and mb) or ma & mb:  # card com Vidigal e Rocinha na mesma hora: duas ações
            return True
    if parecidos(a["titulo"], b["titulo"]):
        return True
    return hora_explicita and not (a["online"] or b["online"]) and a["inicio"] == b["inicio"] and bool(marcas(a) & marcas(b))


def repetido_no_feed(item, itens_feed, hora_explicita=True):
    for f in itens_feed:
        if mesmo_ato(f, item, hora_explicita):
            return f["fonte_id"]
    return None


def itens_do_consolidado(linhas, lugares, itens_feed=(), hoje=None, ate=ATE, geo=None):
    hoje = hoje or date.today().isoformat()
    itens, revisao, aceitas = [], [], []  # aceitas: (frente, item)
    for r in linhas:
        data = r.get("data") or ""
        if not (hoje <= data <= ate):
            continue
        item, motivo = item_da_rede(r, lugares, geo)
        if not item:
            revisao.append((r.get("frente", ""), r.get("titulo", ""), motivo))
            continue
        hora_explicita = bool((r.get("hora") or "").strip())
        dup = repetido_no_feed(item, itens_feed, hora_explicita)
        if dup:
            revisao.append((r.get("frente", ""), r.get("titulo", ""), f"já está no feed Bora Lula (id {dup})"))
            continue
        frente = r.get("frente", "")
        # linhas do mesmo post lidas pela mesma frente são ações diferentes do card; só o id igual repete
        if any(o["fonte_id"] == item["fonte_id"]
               or (not (f == frente and o["link"] and o["link"] == item["link"]) and mesmo_ato(o, item, hora_explicita, False))
               for f, o in aceitas):
            revisao.append((frente, r.get("titulo", ""), "repetido no consolidado"))
            continue
        aceitas.append((frente, item))
        anotar_aviso(item, revisao, frente, r.get("titulo", ""))
        itens.append(item)
    return itens, revisao


def encerramentos_com_inscricao(itens, com_inscricao):
    """Ids com inscrição ativa que a importação encerraria por não estarem mais na lista."""
    return sorted(set(com_inscricao) - {i["fonte_id"] for i in itens})


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


def consultar_sql(sql, ref=None):
    """Roda SQL na produção pela Management API."""
    import ir_ao_ar
    _, _, token = destino()
    ref = ref or (ir_ao_ar.ARQ_REF.read_text().strip() if ir_ao_ar.ARQ_REF.exists() else None)
    if not ref:
        raise Falha("não sei o ref do projeto: passe --ref")
    st, resp = _http("POST", f"{ir_ao_ar.API}/projects/{ref}/database/query", {"query": sql}, {"Authorization": "Bearer " + token})
    if not 200 <= st < 300:
        raise Falha(f"SQL na produção: HTTP {st} {resp}")
    return resp


def ids_com_inscricao(fonte, hoje, ref=None):
    """fonte_ids publicados com inscrição ativa ("Eu vou") em turno de hoje em diante (o que já passou sai da lista da
    importação de qualquer jeito). None quando não dá para consultar (pilha local via REST)."""
    if destino()[0] == "rest":
        return None
    sql = ("select distinct a.fonte_id from acao a join turno t on t.acao = a.id join inscricao i on i.turno = t.id "
           f"where a.fonte = '{fonte}' and a.status = 'publicada' and i.cancelada_em is null and t.inicio >= '{hoje}'")
    return {x["fonte_id"] for x in consultar_sql(sql, ref)}


def publicar(fonte, itens, encerrar=True, ref=None):
    modo, url, chave = destino()
    if modo == "rest":
        st, resp = _http("POST", url.rstrip("/") + "/rest/v1/rpc/importar_acoes",
                         {"fonte": fonte, "itens": itens, "encerrar_faltantes": encerrar},
                         {"apikey": chave, "Authorization": "Bearer " + chave})
        if not 200 <= st < 300:
            raise Falha(f"importar_acoes: HTTP {st} {resp}")
        return resp
    resp = consultar_sql(sql_importar(fonte, itens, encerrar), ref)
    return resp[0].get("r") if isinstance(resp, list) and resp else resp


# ---- linha de comando ----

def com_foto(itens, mapa):
    """Põe em cada item a imagem da divulgação original já coletada (scripts/fotos_divulgacao.py). Foto ou logo cuja
    url não é https (nem a pilha local) é descartada, com aviso: só https vira <img> no app."""
    for it in itens:
        it["foto"] = fd.foto_do_item(it, mapa)
        for campo in ("foto", "organizacao_foto"):
            f = it.get(campo)
            if f and not bl.foto_valida(f.get("url")):
                print(f"AVISO: {campo} descartada em {it.get('fonte_id')} (url não é https): {str(f.get('url'))[:60]}", file=sys.stderr)
                it[campo] = None
    return itens


def resumo(itens, revisao):
    por_uf = {}
    for i in itens:
        k = "online" if i["online"] else i["cidade"]
        por_uf[k] = por_uf.get(k, 0) + 1
    top = ", ".join(f"{k} {v}" for k, v in sorted(por_uf.items(), key=lambda kv: -kv[1])[:8])
    exatas = sum(1 for i in itens if not i["online"] and not i["lugar_aproximado"])
    com_logo = sum(1 for i in itens if i.get("organizacao_foto"))
    com_img = sum(1 for i in itens if i.get("foto"))
    top += f"; {exatas} com ponto exato, {com_logo} com logo da organização, {com_img} com imagem da divulgação"
    motivos, avisos = {}, 0
    for _, _, m in revisao:
        if m.startswith("aviso:"):
            avisos += 1
            continue
        m = re.sub(r"\s*\(.*|\s*\d+$", "", m)
        motivos[m] = motivos.get(m, 0) + 1
    fora = ", ".join(f"{m} {n}" for m, n in sorted(motivos.items(), key=lambda kv: -kv[1]))
    texto = f"{len(itens)} para publicar ({top}); {len(revisao) - avisos} de fora: {fora or 'nada'}"
    if avisos:
        texto += f". AVISO: {avisos} links descartados por não serem http/https (veja revisao-*.csv)"
    return texto


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
    p.add_argument("--sem-geocodificar", action="store_true", help="não consulta o Nominatim: tudo no centro da cidade")
    p.add_argument("--sem-fotos", action="store_true", help="não busca a imagem dos posts novos (usa só as já coletadas)")
    p.add_argument("--forcar", action="store_true", help="encerra mesmo ação com inscrição ativa (quem marcou Eu vou perde)")
    args = p.parse_args(argv)
    lugares = bl.carregar_lugares()
    geo = None if args.sem_geocodificar else bl.Geocodificador()
    try:
        if args.fonte == "bora-lula":
            if args.de:
                feed = json.loads(Path(args.de).read_text(encoding="utf-8"))
            else:
                arq, feed = bl.baixar()
                print(f"feed guardado em {arq}")
            itens, revisao = itens_do_feed(feed, lugares, hoje=args.hoje, ate=args.ate, geo=geo)
        else:
            if not args.de:
                p.error("redes precisa de --de ARQ.csv")
            with open(args.de, encoding="utf-8", newline="") as f:
                linhas = list(csv.DictReader(f))
            itens_feed = []
            if args.feed:
                feed = json.loads(Path(args.feed).read_text(encoding="utf-8"))
                itens_feed, _ = itens_do_feed(feed, lugares, hoje=args.hoje, ate=args.ate)
            itens, revisao = itens_do_consolidado(linhas, lugares, itens_feed, hoje=args.hoje, ate=args.ate, geo=geo)
        if geo:
            geo.salvar()
            print(f"geocodificação: {geo.consultas} consultas novas ao Nominatim, cache em {bl.GEOCACHE}")
        if args.aplicar and not args.sem_encerrar:  # antes das fotos: se travar, nada foi gravado nem subido
            inscritas = ids_com_inscricao(args.fonte, args.hoje or date.today().isoformat(), args.ref)
            perdidas = encerramentos_com_inscricao(itens, inscritas or ())
            if inscritas is None:
                print("AVISO: pilha local, sem checar inscrições antes de encerrar", file=sys.stderr)
            elif perdidas and not args.forcar:
                raise Falha(f"{len(perdidas)} ações com inscrição ativa seriam encerradas ({', '.join(perdidas[:10])}); "
                            "nada gravado. Confira o consolidado ou use --sem-encerrar; --forcar encerra assim mesmo")
        mapa = fd.carregar_mapa()
        if args.aplicar and not args.sem_fotos:
            try:
                mapa, novas, falhas = fd.buscar_fotos(itens, mapa)
                print(f"fotos: {novas} imagens novas, {len(falhas)} posts sem imagem (apagados ou privados)")
            except (fd.Falha, OSError) as e:  # sem foto não impede publicar
                print(f"AVISO: busca de fotos falhou ({e}); publicando com as imagens já coletadas", file=sys.stderr)
        com_foto(itens, mapa)
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
