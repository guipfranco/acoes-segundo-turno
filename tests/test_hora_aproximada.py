"""Divulgação sem hora ("Noite - Giro nos Bares"): faixa aproximada marcada como tal, em vez de 9h às 11h."""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import bora_lula as bl  # noqa: E402
import publicar_acoes as pa  # noqa: E402

LUGARES = bl.carregar_lugares()


def test_periodo_do_texto():
    assert bl.periodo_do_texto("Noite - Giro nos Bares. Pontos: Pinheiros") == ("19:00", "23:00")
    assert bl.periodo_do_texto("Panfletagem à tarde na feira") == ("14:00", "18:00")
    assert bl.periodo_do_texto("De manhã, na estação") == ("09:00", "12:00")
    assert bl.periodo_do_texto("Caminhada no centro") is None
    assert bl.periodo_do_texto("") is None
    assert bl.periodo_do_texto("anoitecer") is None  # só a palavra inteira


def test_faixa_aproximada_exata_quando_tem_hora_ou_dia_todo():
    assert bl.faixa_aproximada("15:30", "Noite") == ("15:30", "17:30", False)
    assert bl.faixa_aproximada("10h às 18h", "") == ("10:00", "18:00", False)
    assert bl.faixa_aproximada("Dia todo", "") == ("09:00", "18:00", False)


def test_faixa_aproximada_no_feed_usa_hora_ord_e_so_cai_no_periodo_sem_ela():
    assert bl.faixa_aproximada("Noite", "x", 19.5) == ("19:30", "21:30", False)
    assert bl.faixa_aproximada("Noite", "x", None) == ("19:00", "23:00", True)
    feed, _ = pa.item_do_feed(_feed(hora="Noite", hora_ord=None), LUGARES)
    assert feed["inicio"] == "2026-10-10T19:00" and feed["hora_aproximada"] is True
    feed, _ = pa.item_do_feed(_feed(hora="9h", hora_ord=9), LUGARES)
    assert feed["inicio"] == "2026-10-10T09:00" and feed["hora_aproximada"] is False
    d = bl.converter({"acoes": [_feed(hora="Noite", hora_ord=None), _feed(id=2)]}, LUGARES, hoje="2026-10-09")
    assert [t["horaAproximada"] for t in d["turnos"]] == [True, False]


def _feed(**k):
    base = {"id": 1, "data": "2026-10-10", "hora": "9h", "hora_ord": 9, "uf": "SP", "cidade": "Diadema", "local": "Praça da Moça",
            "endereco": "Praça da Moça, 10 - Centro", "atividade": "Panfletagem no centro", "tipo": "Panfletagem",
            "organizacao": "PT de Diadema", "link": "https://www.instagram.com/p/x/", "online": False, "plataforma": ""}
    base.update(k)
    return base


def test_faixa_aproximada_pelo_periodo_ou_sem_hora():
    assert bl.faixa_aproximada("Noite", "") == ("19:00", "23:00", True)
    assert bl.faixa_aproximada("", "Noite Giro nos Bares Pontos: Pinheiros (Largo da Batata)") == ("19:00", "23:00", True)
    assert bl.faixa_aproximada("", "Plenária do bairro") == ("09:00", "18:00", True)
    assert bl.faixa_aproximada(None, None) == ("09:00", "18:00", True)


def _linha(**k):
    base = {"frente": "orgsp-a", "titulo": "Giro nos Bares (Pinheiros e Vila Mariana)", "tipo": "corpo a corpo", "data": "2026-10-09",
            "hora": "", "cidade": "São Paulo", "uf": "SP", "bairro": "Pinheiros; Vila Mariana", "endereco": "Largo da Batata",
            "organizador": "JPT São Paulo", "lula_explicito": "sim", "online": "não", "link": "https://www.instagram.com/jptsaopaulo/",
            "texto_original": "Noite Giro nos Bares Pontos: Pinheiros (Largo da Batata) e Vila Mariana", "confianca": "média"}
    base.update(k)
    return base


def test_item_da_rede_sem_hora_usa_o_periodo_do_texto_e_marca_aproximada():
    item, motivo = pa.item_da_rede(_linha(), LUGARES)
    assert motivo is None
    assert item["inicio"] == "2026-10-09T19:00" and item["fim"] == "2026-10-09T23:00" and item["hora_aproximada"] is True
    exato, _ = pa.item_da_rede(_linha(hora="15:30"), LUGARES)
    assert exato["inicio"] == "2026-10-09T15:30" and exato["hora_aproximada"] is False
    nada, _ = pa.item_da_rede(_linha(texto_original="Giro nos bares"), LUGARES)
    assert nada["inicio"] == "2026-10-09T09:00" and nada["fim"] == "2026-10-09T18:00" and nada["hora_aproximada"] is True


def test_hora_aproximada_vai_no_json_da_importacao():
    item, _ = pa.item_da_rede(_linha(), LUGARES)
    assert '"hora_aproximada": true' in pa.sql_importar("redes", [item])
