"""Baixa a agenda "Bora Lula" do Comitê Popular e converte para o formato do app (modo exemplo).

Uso:
  python scripts/bora_lula.py                 # baixa, guarda cópia datada e gera levantamento/dados-bora-lula.js
  python scripts/bora_lula.py --de ARQ.json   # converte um JSON já baixado
  python scripts/bora_lula.py --para SAIDA.js # muda o destino

A saída vai para levantamento/ (fora do git) porque o repo é público e os dados de exemplo versionados
não podem ter organizações reais. Sem dependências além da biblioteca padrão.
"""
import argparse
import json
import re
import sys
import unicodedata
import urllib.request
from datetime import date, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
URL_FEED = "https://comitepopular.org.br/wp-content/uploads/agenda-bora-lula/acoes.js"
PASTA = RAIZ / "levantamento" / "bora-lula"
SAIDA_PADRAO = RAIZ / "levantamento" / "dados-bora-lula.js"
LUGARES_JS = RAIZ / "app" / "lugares.js"
DADOS_JS = RAIZ / "app" / "dados.js"
FONTE = "Agenda Bora Lula do Comitê Popular (comitepopular.org.br/agenda)"
DURACAO_PADRAO_H = 2

# Tipos revistos em 2026-10-09 (migração 20261009000010): no feed real, "Encontro", "Ato" e "Caminhada" somam
# mais da metade das ações; antes Ato, Caminhada e Cultural caíam em "outro".
TIPOS = {
    "panfletagem": "panfletagem",
    "adesivaco": "adesivaço",
    "bandeiraco": "bandeiraço",
    "encontro": "encontro",
    "ato": "ato",
    "caminhada": "caminhada",
    "cultural": "cultural",
}

# Quando o tipo do feed é "Outro" (ou vazio), o título costuma dizer o que é. A ordem importa: a primeira que casa vence.
TIPOS_TITULO = [
    (r"plenari|assembleia|reuniao|encontro|roda de conversa|conversa", "encontro"),
    (r"carreata|caminhada|marcha|arrastao|bicicletada|motociata", "caminhada"),
    (r"panfleta|banquinha|distribuicao de material", "panfletagem"),
    (r"bandeiraco", "bandeiraço"),
    (r"adesivaco", "adesivaço"),
    (r"sarau|show|oficina|festival|samba|cineclube|cultura|musica|hip hop", "cultural"),
    (r"\bato\b|manifestacao|mobilizacao", "ato"),
    (r"porta a porta|corpo a corpo", "porta a porta"),
    (r"ligatona|telefonaco", "ligatona"),
]


def sem_acento(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def tipo_pelo_titulo(titulo):
    t = sem_acento(titulo)
    for padrao, tipo in TIPOS_TITULO:
        if re.search(padrao, t):
            return tipo
    return "outro"


def tipo_mapa(tipo_feed, titulo=""):
    tipo = TIPOS.get(sem_acento(tipo_feed), "outro")
    return tipo_pelo_titulo(titulo) if tipo == "outro" else tipo


def hora_hhmm(hora, hora_ord):
    m = re.match(r"\s*(\d{1,2})\s*[h:]\s*(\d{2})?", str(hora or ""))
    if m:
        return f"{int(m.group(1)):02d}:{int(m.group(2) or 0):02d}"
    if hora_ord is not None and 0 <= hora_ord < 24:
        h = int(hora_ord)
        return f"{h:02d}:{int(round((hora_ord - h) * 60)):02d}"
    return "09:00"


def faixa(hora, hora_ord):
    """(início, fim) em HH:MM. Aceita "10h às 18h", "19h" (fim = início + 2h) e "Dia todo"."""
    if sem_acento(hora) == "dia todo":
        return "09:00", "18:00"
    partes = re.split(r"\s+(?:as|às|a|-|–)\s+", str(hora or ""), maxsplit=1)
    inicio = hora_hhmm(partes[0], hora_ord)
    if len(partes) == 2 and re.match(r"\s*\d{1,2}\s*[h:]", partes[1]):
        return inicio, hora_hhmm(partes[1], None)
    h, m = map(int, inicio.split(":"))
    h_fim = h + DURACAO_PADRAO_H
    return inicio, ("23:59" if h_fim >= 24 else f"{h_fim:02d}:{m:02d}")


def bairro_do_endereco(endereco, cidade=""):
    """Bairro no fim do endereço ("Av. X, 704 - Centro"). Nada se tiver número, UF/CEP ou for a própria cidade."""
    m = re.search(r"[-–,]\s*([^-–,\d]{3,40})\s*$", str(endereco or ""))
    if not m:
        return ""
    b = m.group(1).strip()
    if sem_acento(b) == sem_acento(cidade) or re.fullmatch(r"[A-Z]{2}", b):
        return ""
    return b


PARTIDOS = ("pt ", "pt-", "psol", "pcdob", "pdt", "psb", "rede ", "pv ", "pco", "up ", "pstu", "partido ")
MANDATOS = ("mandato", "vereador", "deputad", "dep.", "senador", "governador", "prefeit", "gabinete")
MOVIMENTOS = ("movimento", "mst", "mtst", "une ", "ubes", "cut ", "ctb", "sindicato", "frente", "central", "levante", "juventude")


def tipo_org(nome):
    n = sem_acento(nome) + " "
    if n.startswith(PARTIDOS) or " pt " in n or n.startswith("diretorio"):
        return "partido"
    if any(k in n for k in MANDATOS):
        return "mandato"
    if any(k in n for k in MOVIMENTOS):
        return "movimento"
    return "coletivo"


def chave_cidade(s):
    """Chave de busca do município: sem acento, hífen, apóstrofo e parênteses ("Santa Bárbara d'Oeste" = "... do Oeste")."""
    s = sem_acento(s).replace("'", " ").replace("-", " ").replace("–", " ")
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return re.sub(r"\bd (?=[aeiou])", "do ", s)


def carregar_lugares():
    """Índice (chave_cidade, uf) -> (lat, lon) a partir de app/lugares.js (municípios do IBGE)."""
    txt = LUGARES_JS.read_text(encoding="utf-8")
    txt = txt.split("LUGARES_BR", 1)[1]
    corpo = txt[txt.index("["): txt.rindex("]") + 1]
    indice = {}
    for nome, uf, lat, lon, tipo in json.loads(corpo):
        if tipo == "d":  # distritos de São Paulo não são municípios
            continue
        indice.setdefault((chave_cidade(nome), uf), (lat, lon))
    return indice


def coordenada(cidade, uf, lugares):
    if not cidade:
        return None
    return lugares.get((chave_cidade(cidade), uf))


def resolver_lugar(cidade, uf, lugares):
    """(cidade oficial, bairro sugerido, (lat, lon)) ou None. Região administrativa do DF vira Brasília."""
    c = coordenada(cidade, uf, lugares)
    limpa = re.sub(r"\s*\(.*?\)", "", str(cidade or "")).strip()
    if c:
        return limpa, "", c
    if uf == "DF" and limpa:
        return "Brasília", limpa, coordenada("Brasília", "DF", lugares)
    return None


def baixar(destino_pasta=PASTA):
    req = urllib.request.Request(URL_FEED, headers={"User-Agent": "Mozilla/5.0 acoes-segundo-turno"})
    with urllib.request.urlopen(req, timeout=60) as r:
        bruto = r.read()
    destino_pasta.mkdir(parents=True, exist_ok=True)
    arq = destino_pasta / (datetime.now().strftime("%Y-%m-%d-%H%M") + ".json")
    arq.write_bytes(bruto)
    return arq, json.loads(bruto.decode("utf-8"))


def _config_base():
    if DADOS_JS.exists():
        txt = DADOS_JS.read_text(encoding="utf-8")
        try:
            return json.loads(txt.split("=", 1)[1].strip().rstrip(";")).get("config", {})
        except (ValueError, IndexError):
            pass
    return {}


def converter(feed, lugares, hoje=None, ate="2026-10-25"):
    hoje = hoje or feed.get("hoje") or date.today().isoformat()
    config = dict(_config_base())
    config["hoje"] = hoje
    config["fonte"] = FONTE
    organizacoes, idx_org = [], {}
    pessoa_feed = {"id": 1, "nome": "Agenda Bora Lula", "papel": "organizador", "organizacao": None,
                   "telefone": "", "bloqueada": False}
    acoes, turnos = [], []
    for item in feed.get("acoes", []):
        data = item.get("data") or ""
        if not (hoje <= data <= ate):
            continue
        nome_org = (item.get("organizacao") or "").strip()
        org_id = None
        if nome_org:
            if nome_org not in idx_org:
                idx_org[nome_org] = len(organizacoes) + 1
                organizacoes.append({"id": idx_org[nome_org], "nome": nome_org, "tipo": tipo_org(nome_org), "verificada": False})
            org_id = idx_org[nome_org]
        online = bool(item.get("online"))
        cidade = (item.get("cidade") or "").strip()
        uf = (item.get("uf") or "").strip()
        local = (item.get("local") or "").strip()
        endereco = (item.get("endereco") or "").strip()
        if online:
            lugar = {"nome": "Online", "bairro": "Online", "cidade": "Online", "lat": None, "lon": None, "online": True}
        else:
            c = coordenada(cidade, uf, lugares)
            lugar = {"nome": local or endereco or cidade or "A confirmar", "bairro": bairro_do_endereco(endereco, cidade), "cidade": cidade or "A confirmar",
                     "uf": uf, "endereco": endereco, "lat": c[0] if c else None, "lon": c[1] if c else None,
                     "precisao": "cidade" if c else "nenhuma"}
        h_ini, h_fim = faixa(item.get("hora"), item.get("hora_ord"))
        inicio, fim = f"{data}T{h_ini}", f"{data}T{h_fim}"
        link = (item.get("link") or "").strip()
        descricao = (item.get("atividade") or "").strip()
        if item.get("plataforma"):
            descricao += f" ({item['plataforma']})"
        descricao += f"\n\nFonte: {FONTE}."
        if link:
            descricao += f" Divulgação original: {link}"
        acoes.append({
            "id": item["id"], "titulo": (item.get("atividade") or "Ação")[:120], "tipo": tipo_mapa(item.get("tipo"), item.get("atividade")),
            "tipoOrigem": item.get("tipo") or "", "descricao": descricao, "organizador": pessoa_feed["id"],
            "organizacao": org_id, "lugar": lugar, "detalhe": "", "contatoTipo": "divulgacao" if link else "organizador_chama", "contatoWhatsapp": None, "contatoLink": link or None, "status": "publicada",
            "motivoRecusa": None, "prioritaria": False, "criadaEm": hoje, "foto": None, "fonte": "bora-lula", "link": link,
        })
        turnos.append({"id": len(turnos) + 1, "acao": item["id"], "inicio": inicio, "fim": fim, "lotacao": None})
    return {"config": config, "organizacoes": organizacoes, "pessoas": [pessoa_feed], "acoes": acoes,
            "turnos": turnos, "inscricoes": [], "areasPrioritarias": []}


def dados_js(d):
    return "window.DADOS = " + json.dumps(d, ensure_ascii=False, indent=1) + ";\n"


def resumo(d):
    por_uf, sem_coord = {}, 0
    for a in d["acoes"]:
        uf = a["lugar"].get("uf", "online" if a["lugar"].get("online") else "")
        por_uf[uf] = por_uf.get(uf, 0) + 1
        if not a["lugar"].get("online") and a["lugar"]["lat"] is None:
            sem_coord += 1
    top = ", ".join(f"{k or '?'} {v}" for k, v in sorted(por_uf.items(), key=lambda kv: -kv[1])[:8])
    return f"{len(d['acoes'])} ações, {len(d['organizacoes'])} organizações, {sem_coord} sem coordenada. Por UF: {top}"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--de", help="JSON já baixado, em vez de baixar")
    p.add_argument("--para", default=str(SAIDA_PADRAO), help="arquivo .js de saída")
    p.add_argument("--hoje", help="AAAA-MM-DD (padrão: campo hoje do feed)")
    args = p.parse_args(argv)
    if args.de:
        feed = json.loads(Path(args.de).read_text(encoding="utf-8"))
        origem = args.de
    else:
        arq, feed = baixar()
        origem = str(arq)
    d = converter(feed, carregar_lugares(), hoje=args.hoje)
    Path(args.para).parent.mkdir(parents=True, exist_ok=True)
    Path(args.para).write_text(dados_js(d), encoding="utf-8")
    print(f"feed: {origem} ({len(feed.get('acoes', []))} itens, hoje={feed.get('hoje')})")
    print(f"saída: {args.para}")
    print(resumo(d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
