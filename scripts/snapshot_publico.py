#!/usr/bin/env python3
"""Baixa as views públicas do Supabase e grava um publico.json para o GitHub Pages.

Quem só olha a vitrine lê esse arquivo em vez de bater no Supabase (plano Free, 5 GB/mês de saída).
Roda no workflow .github/workflows/pages.yml de hora em hora e a cada push; o app (app/api-supabase.js)
usa o arquivo se ele tiver menos de 3 h e cai no Supabase se não tiver.

    python scripts/snapshot_publico.py _site/publico.json [--config app/config.js]

Só leitura, com a chave anon de app/config.js (pública por desenho; o RLS protege o banco). O workflow passa
`--config` com o config.js da origin/master, para o snapshot ler sempre o banco de produção, seja qual for a branch
que disparou. Só urllib.
As linhas vão CRUAS, como as views entregam: o app mapeia com deAcao/deTurno/deOrg.
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_JS = RAIZ / "app" / "config.js"
PAGINA = 1000  # pedimos 1000 por vez pelo cabeçalho Range; o servidor pode devolver menos (max-rows), então só paramos na página vazia
BRASILIA = timezone(timedelta(hours=-3))  # sem horário de verão desde 2019

# view -> (select, order); o order garante paginação estável
VIEWS = {
    "configuracao": ("configuracao_publica", "chave,valor", "chave"),
    "organizacoes": ("organizacao_publica", "id,nome,tipo,verificada,foto_url,foto_credito,foto_pagina", "id"),
    "acoes": ("acao_publica", "*", "id"),
    "turnos": ("turno_publico", "*", "id"),
}


def ler_config(texto):
    """URL e chave anon de app/config.js (window.CONFIG = { supabase: { url: '...', anonKey: '...' } })."""
    url = re.search(r"""url\s*:\s*['"]([^'"]+)['"]""", texto)
    chave = re.search(r"""anonKey\s*:\s*['"]([^'"]+)['"]""", texto)
    if not url or not chave:
        raise SystemExit("app/config.js sem url ou anonKey do Supabase")
    return url.group(1).rstrip("/"), chave.group(1)


def hoje_brasilia(agora=None):
    return (agora or datetime.now(timezone.utc)).astimezone(BRASILIA).strftime("%Y-%m-%d")


def buscar_http(url, cabecalhos):
    """GET simples: devolve (status, corpo em bytes). 416 (Range fora) conta como página vazia."""
    req = urllib.request.Request(url, headers=cabecalhos)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        if e.code == 416:
            return 416, b"[]"
        raise


def baixar_view(buscar, base, anon, view, select, order, filtros=(), pagina=PAGINA):
    """Lê a view inteira pedindo `pagina` linhas por vez, até vir uma página VAZIA. Página curta não encerra: o
    servidor pode limitar em menos linhas que o pedido (max-rows), e o próximo Range começa onde a anterior parou."""
    params = [("select", select), ("order", order)] + list(filtros)
    url = f"{base}/rest/v1/{view}?" + "&".join(f"{k}={v}" for k, v in params)
    linhas = []
    inicio = 0
    while True:
        status, corpo = buscar(url, {
            "apikey": anon, "Authorization": f"Bearer {anon}", "Accept": "application/json",
            "Range-Unit": "items", "Range": f"{inicio}-{inicio + pagina - 1}",
        })
        if status not in (200, 206, 416):
            raise RuntimeError(f"{view}: HTTP {status}")
        lote = json.loads(corpo or b"[]")
        if not isinstance(lote, list):
            raise RuntimeError(f"{view}: resposta inesperada: {str(lote)[:200]}")
        if not lote:
            return linhas
        linhas.extend(lote)
        inicio += len(lote)


def montar_snapshot(buscar, base, anon, hoje=None, agora=None):
    agora = agora or datetime.now(timezone.utc)
    hoje = hoje or hoje_brasilia(agora)
    saida = {"geradoEm": agora.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    for campo, (view, select, order) in VIEWS.items():
        filtros = [("inicio", f"gte.{hoje}T00:00:00")] if view == "turno_publico" else []
        saida[campo] = baixar_view(buscar, base, anon, view, select, order, filtros)
    return saida


def main(argv):
    p = argparse.ArgumentParser(description="grava o publico.json da vitrine a partir das views públicas do Supabase")
    p.add_argument("destino", help="caminho do publico.json (ex.: _site/publico.json)")
    p.add_argument("--config", default=str(CONFIG_JS), help="config.js de onde ler url e anonKey (padrão: app/config.js)")
    args = p.parse_args(argv[1:])
    base, anon = ler_config(Path(args.config).read_text(encoding="utf-8"))
    snapshot = montar_snapshot(buscar_http, base, anon)
    destino = Path(args.destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{destino}: {len(snapshot['acoes'])} ações, {len(snapshot['turnos'])} turnos, "
          f"{len(snapshot['organizacoes'])} organizações, {destino.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
