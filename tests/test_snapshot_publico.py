import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import snapshot_publico as sp  # noqa: E402


def test_le_url_e_chave_anon_do_config_js():
    texto = "window.CONFIG = { supabase: { url: 'https://abc.supabase.co/', anonKey: 'sb_publishable_x' } };"
    assert sp.ler_config(texto) == ("https://abc.supabase.co", "sb_publishable_x")
    assert sp.ler_config((RAIZ / "app" / "config.js").read_text(encoding="utf-8"))[0].startswith("https://")


def test_hoje_em_brasilia():
    # 01:30 UTC ainda é o dia anterior em Brasília (UTC-3)
    assert sp.hoje_brasilia(datetime(2026, 10, 10, 1, 30, tzinfo=timezone.utc)) == "2026-10-09"
    assert sp.hoje_brasilia(datetime(2026, 10, 10, 3, 0, tzinfo=timezone.utc)) == "2026-10-10"


def servidor_falso(tabelas, max_linhas=None):
    """Simula a REST do Supabase: respeita select/order/filtro de inicio e o cabeçalho Range. `max_linhas` imita o
    servidor que corta a página em menos linhas do que o Range pediu (max-rows do PostgREST)."""
    chamadas = []

    def buscar(url, cabecalhos):
        chamadas.append((url, cabecalhos))
        partes = urlsplit(url)
        view = partes.path.rsplit("/", 1)[-1]
        q = parse_qs(partes.query)
        assert cabecalhos["apikey"] == "anon" and cabecalhos["Authorization"] == "Bearer anon"
        linhas = list(tabelas[view])
        for filtro in q.get("inicio", []):
            assert filtro.startswith("gte.")
            linhas = [l for l in linhas if l["inicio"] >= filtro[4:]]
        ini, fim = (int(x) for x in cabecalhos["Range"].split("-"))
        pagina = linhas[ini:fim + 1]
        if max_linhas:
            pagina = pagina[:max_linhas]
        if ini and not pagina:
            return 416, b""
        return 206, json.dumps(pagina).encode()

    buscar.chamadas = chamadas
    return buscar


def test_pagina_de_1000_em_1000_ate_vir_pagina_vazia():
    acoes = [{"id": i} for i in range(2350)]
    buscar = servidor_falso({"acao_publica": acoes})
    assert sp.baixar_view(buscar, "https://x", "anon", "acao_publica", "*", "id") == acoes
    ranges = [c[1]["Range"] for c in buscar.chamadas]
    assert ranges == ["0-999", "1000-1999", "2000-2999", "2350-3349"]  # página curta não encerra: só a vazia
    assert "order=id" in buscar.chamadas[0][0] and "select=*" in buscar.chamadas[0][0]


def test_pagina_exata_faz_uma_chamada_a_mais_e_para_no_vazio():
    buscar = servidor_falso({"organizacao_publica": [{"id": i} for i in range(2000)]})
    assert len(sp.baixar_view(buscar, "https://x", "anon", "organizacao_publica", "id", "id")) == 2000
    assert [c[1]["Range"] for c in buscar.chamadas] == ["0-999", "1000-1999", "2000-2999"]


def test_servidor_que_corta_em_menos_linhas_nao_trunca():
    # o PostgREST pode limitar a página (max-rows) abaixo do que o Range pediu: o próximo Range começa onde parou
    acoes = [{"id": i} for i in range(250)]
    buscar = servidor_falso({"acao_publica": acoes}, max_linhas=100)
    assert sp.baixar_view(buscar, "https://x", "anon", "acao_publica", "*", "id") == acoes
    assert [c[1]["Range"] for c in buscar.chamadas] == ["0-999", "100-1099", "200-1199", "250-1249"]


def test_snapshot_filtra_turnos_a_partir_de_hoje_em_brasilia():
    turnos = [
        {"id": 1, "acao": 1, "inicio": "2026-10-08T18:00:00"},
        {"id": 2, "acao": 1, "inicio": "2026-10-09T00:00:00"},
        {"id": 3, "acao": 2, "inicio": "2026-10-20T09:00:00"},
    ]
    buscar = servidor_falso({
        "configuracao_publica": [{"chave": "frase", "valor": "Bora"}],
        "organizacao_publica": [{"id": 1, "nome": "PT"}],
        "acao_publica": [{"id": 1, "titulo": "A", "foto_mini_url": None}, {"id": 2, "titulo": "B"}],
        "turno_publico": turnos,
    })
    agora = datetime(2026, 10, 9, 14, 5, 7, tzinfo=timezone.utc)
    s = sp.montar_snapshot(buscar, "https://x", "anon", agora=agora)
    assert s["geradoEm"] == "2026-10-09T14:05:07Z"
    assert s["configuracao"] == [{"chave": "frase", "valor": "Bora"}]
    assert [o["id"] for o in s["organizacoes"]] == [1]
    assert [a["id"] for a in s["acoes"]] == [1, 2]  # linhas cruas, como a view entrega
    assert [t["id"] for t in s["turnos"]] == [2, 3]
    url_turnos = next(c[0] for c in buscar.chamadas if "turno_publico" in c[0])
    assert "inicio=gte.2026-10-09T00:00:00" in url_turnos


def test_main_grava_o_json_no_caminho_dado(tmp_path, monkeypatch, capsys):
    buscar = servidor_falso({"configuracao_publica": [], "organizacao_publica": [], "acao_publica": [{"id": 9}], "turno_publico": []})
    monkeypatch.setattr(sp, "buscar_http", buscar)
    monkeypatch.setattr(sp, "ler_config", lambda texto: ("https://x", "anon"))
    destino = tmp_path / "site" / "publico.json"
    assert sp.main(["snapshot_publico.py", str(destino)]) == 0
    dados = json.loads(destino.read_text(encoding="utf-8"))
    assert set(dados) == {"geradoEm", "configuracao", "organizacoes", "acoes", "turnos"}
    assert dados["acoes"] == [{"id": 9}]
    assert "1 ações" in capsys.readouterr().out


def test_main_le_o_config_js_indicado_em_config(tmp_path, monkeypatch):
    # o workflow passa o config.js da origin/master, para o snapshot ler produção seja qual for a branch
    lidos = []
    buscar = servidor_falso({"configuracao_publica": [], "organizacao_publica": [], "acao_publica": [], "turno_publico": []})
    monkeypatch.setattr(sp, "buscar_http", lambda url, cab: lidos.append(url) or buscar(url, cab))
    cfg = tmp_path / "config-master.js"
    cfg.write_text("window.CONFIG = { supabase: { url: 'https://master.supabase.co', anonKey: 'anon' } };", encoding="utf-8")
    assert sp.main(["snapshot_publico.py", str(tmp_path / "publico.json"), "--config", str(cfg)]) == 0
    assert lidos and all(u.startswith("https://master.supabase.co/rest/v1/") for u in lidos)
    assert sp.main(["snapshot_publico.py", str(tmp_path / "publico.json"), "--config", str(cfg)]) == 0
    import pytest
    with pytest.raises(SystemExit):
        sp.main(["snapshot_publico.py"])  # destino é obrigatório


def test_erro_http_derruba_o_script():
    import pytest
    with pytest.raises(RuntimeError, match="HTTP 500"):
        sp.baixar_view(lambda u, c: (500, b"erro"), "https://x", "anon", "acao_publica", "*", "id")
