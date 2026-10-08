from pathlib import Path
import re

RAIZ = Path(__file__).resolve().parents[1]
HTML = (RAIZ / "mockup" / "index.html").read_text(encoding="utf-8")


def test_tem_as_cinco_telas():
    for nome in ["telaInicio", "telaAcao", "telaCriar", "telaMinhas", "telaFila"]:
        assert f"function {nome}" in HTML, nome


def test_nav_e_doar():
    assert 'id="app"' in HTML
    assert "<nav" in HTML
    assert "Doar" in HTML
import json

DADOS_JS = (RAIZ / "mockup" / "dados.js").read_text(encoding="utf-8") if (RAIZ / "mockup" / "dados.js").exists() else ""


def carregar_dados():
    # dados.js é "window.DADOS = {...};" com JSON puro dentro
    corpo = DADOS_JS.split("=", 1)[1].strip().rstrip(";")
    return json.loads(corpo)


def test_dados_tem_pelo_menos_12_acoes_e_todas_com_turno():
    d = carregar_dados()
    assert len(d["acoes"]) >= 12
    acoes_com_turno = {t["acao"] for t in d["turnos"]}
    for a in d["acoes"]:
        assert a["id"] in acoes_com_turno, a["titulo"]


def test_dados_cobrem_os_tipos_e_os_status():
    d = carregar_dados()
    tipos = {a["tipo"] for a in d["acoes"]}
    assert tipos >= {"panfletagem", "adesivaço", "roda de conversa", "ligatona", "porta a porta", "bandeiraço"}
    status = {a["status"] for a in d["acoes"]}
    assert status >= {"publicada", "em análise", "recusada", "encerrada"}


def test_dados_sem_telefone_real():
    for p in carregar_dados()["pessoas"]:
        assert re.fullmatch(r"\(11\) 9x{4}-x{4}", p["telefone"]), p


def test_dados_tem_verificada_e_nao_verificada_e_eu_sou_organizador():
    d = carregar_dados()
    assert {o["verificada"] for o in d["organizacoes"]} == {True, False}
    eu = next(p for p in d["pessoas"] if p["id"] == d["config"]["eu"])
    assert eu["papel"] == "organizador"


def test_inicio_tem_filtros_abas_e_helpers():
    for s in ["function fmtData", "function turnosFuturos", "function vaoNa", "function distanciaKm",
              "data-quando=\"${k}\"", "'fds'", "data-aba=\"mapa\"",
              "Ainda não tem ação perto de você", "Área prioritária", "leaflet"]:
        assert s in HTML, s


def test_acao_com_turno_passado_fica_fora_da_lista():
    d = carregar_dados()
    hoje = d["config"]["hoje"]
    futuros = {t["acao"] for t in d["turnos"] if t["inicio"][:10] >= hoje}
    a10 = next(a for a in d["acoes"] if a["id"] == 10)
    assert a10["status"] == "publicada" and 10 not in futuros
    assert "turnosFuturos(a.id).length" in HTML  # filtro da lista exige turno futuro
