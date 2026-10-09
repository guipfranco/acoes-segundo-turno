import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import bora_lula as bl  # noqa: E402


def test_hora_para_hhmm():
    assert bl.hora_hhmm("9h", 9) == "09:00"
    assert bl.hora_hhmm("9h30", 9.5) == "09:30"
    assert bl.hora_hhmm("19h", 19) == "19:00"
    assert bl.hora_hhmm("", 14.5) == "14:30"
    assert bl.hora_hhmm("", None) == "09:00"
    assert bl.hora_hhmm("Dia todo", -1) == "09:00"


def test_faixa_de_horario():
    assert bl.faixa("10h às 18h", 10) == ("10:00", "18:00")
    assert bl.faixa("12h10 às 13h40", 12.17) == ("12:10", "13:40")
    assert bl.faixa("19h", 19) == ("19:00", "21:00")  # duração padrão de 2h
    assert bl.faixa("Dia todo", -1) == ("09:00", "18:00")
    assert bl.faixa("23h", 23) == ("23:00", "23:59")  # não vira o dia


def test_tipo_do_feed_para_tipo_do_mapa():
    assert bl.tipo_mapa("Panfletagem") == "panfletagem"
    assert bl.tipo_mapa("Adesivaço") == "adesivaço"
    assert bl.tipo_mapa("Bandeiraço") == "bandeiraço"
    assert bl.tipo_mapa("Encontro") == "roda de conversa"
    assert bl.tipo_mapa("Caminhada") == "outro"
    assert bl.tipo_mapa("Ato") == "outro"
    assert bl.tipo_mapa("") == "outro"


def test_geocodifica_por_cidade_e_uf():
    lugares = bl.carregar_lugares()
    lat, lon = bl.coordenada("São Paulo", "SP", lugares)
    assert -24 < lat < -23 and -47 < lon < -46
    assert bl.coordenada("Sào Paulo", "SP", lugares) == (lat, lon)  # acento errado no feed
    assert bl.coordenada("", "RS", lugares) is None
    assert bl.coordenada("Cidade Inexistente", "SP", lugares) is None


def test_converte_feed_para_formato_do_mockup():
    feed = {
        "hoje": "2026-10-08",
        "acoes": [
            {"id": 1, "data": "2026-10-10", "hora": "9h", "hora_ord": 9, "uf": "SP", "cidade": "Diadema",
             "local": "Praça da Moça", "endereco": "Praça da Moça, Centro", "atividade": "Panfletagem no centro",
             "tipo": "Panfletagem", "organizacao": "PT de Diadema", "link": "https://www.instagram.com/p/x/",
             "online": False, "plataforma": ""},
            {"id": 2, "data": "2026-10-07", "hora": "", "hora_ord": None, "uf": "", "cidade": "", "local": "",
             "endereco": "", "atividade": "Já passou", "tipo": "Ato", "organizacao": "", "link": "",
             "online": False, "plataforma": ""},
            {"id": 3, "data": "2026-10-12", "hora": "20h", "hora_ord": 20, "uf": "", "cidade": "", "local": "",
             "endereco": "", "atividade": "Live nacional", "tipo": "Outro", "organizacao": "UNE", "link": "",
             "online": True, "plataforma": "YouTube"},
        ],
    }
    d = bl.converter(feed, bl.carregar_lugares(), hoje="2026-10-08")
    ids = [a["id"] for a in d["acoes"]]
    assert ids == [1, 3]  # a do dia 7 fica de fora
    a1 = d["acoes"][0]
    assert a1["tipo"] == "panfletagem" and a1["status"] == "publicada"
    assert a1["lugar"]["cidade"] == "Diadema" and a1["lugar"]["nome"] == "Praça da Moça"
    assert a1["lugar"]["lat"] is not None
    assert a1["organizacao"] is not None
    assert d["organizacoes"][0]["nome"] == "PT de Diadema"
    t1 = [t for t in d["turnos"] if t["acao"] == 1][0]
    assert t1["inicio"] == "2026-10-10T09:00" and t1["fim"] == "2026-10-10T11:00"
    a3 = d["acoes"][1]
    assert a3["lugar"]["online"] is True and a3["lugar"]["lat"] is None
    assert "comitepopular" in a3["descricao"] or "Bora Lula" in a3["descricao"]
    assert d["config"]["hoje"] == "2026-10-08"
    # pessoa de apoio existe para o mockup não quebrar em pessoa(organizador)
    assert any(p["id"] == a1["organizador"] for p in d["pessoas"])


def test_serializa_como_dados_js():
    js = bl.dados_js({"config": {"hoje": "2026-10-08"}, "acoes": []})
    assert js.startswith("window.DADOS = ")
    json.loads(js.split("=", 1)[1].strip().rstrip(";"))
