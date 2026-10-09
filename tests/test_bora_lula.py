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
    assert bl.tipo_mapa("Encontro") == "encontro"
    assert bl.tipo_mapa("Caminhada") == "caminhada"
    assert bl.tipo_mapa("Ato") == "ato"
    assert bl.tipo_mapa("Cultural") == "cultural"
    assert bl.tipo_mapa("") == "outro"
    # tipo "Outro" no feed: o título decide
    assert bl.tipo_mapa("Outro", "Plenária de Mobilização Cajamar") == "encontro"
    assert bl.tipo_mapa("Outro", "Carreata Carapicuíba quer Lula") == "caminhada"
    assert bl.tipo_mapa("Outro", "Ato unificado pela Democracia") == "ato"
    assert bl.tipo_mapa("Outro", "Pintura de Camiseta") == "outro"
    assert bl.tipo_mapa("Panfletagem", "Plenária") == "panfletagem"  # tipo do feed conhecido vence o título


def test_geocodifica_por_cidade_e_uf():
    lugares = bl.carregar_lugares()
    lat, lon = bl.coordenada("São Paulo", "SP", lugares)
    assert -24 < lat < -23 and -47 < lon < -46
    assert bl.coordenada("Sào Paulo", "SP", lugares) == (lat, lon)  # acento errado no feed
    assert bl.coordenada("", "RS", lugares) is None
    assert bl.coordenada("Cidade Inexistente", "SP", lugares) is None
    assert bl.coordenada("Brasília (Ceilândia)", "DF", lugares) is not None
    assert bl.resolver_lugar("Ceilândia (Brasília)", "DF", lugares)[:2] == ("Brasília", "Ceilândia")
    assert bl.resolver_lugar("Campo Grande", "RJ", lugares) is None


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


def geo_falso(respostas):
    """Geocodificador sem rede nem cache em disco: consulta -> resultado fixo."""
    return bl.Geocodificador(arquivo=None, consultar=lambda q: respostas.get(q, []))


def test_localizar_usa_endereco_depois_local_e_cai_no_centro(tmp_path):
    centro = (-23.686, -46.623)
    predio = [{"lat": "-23.6900", "lon": "-46.6200", "category": "building", "type": "yes", "name": "Praça da Moça",
               "address": {"city": "Diadema", "ISO3166-2-lvl4": "BR-SP"}}]
    rua = [{"lat": "-23.6950", "lon": "-46.6250", "category": "highway", "type": "residential", "addresstype": "road",
            "name": "Rua X", "address": {"road": "Rua X", "town": "Diadema", "ISO3166-2-lvl4": "BR-SP"}}]
    outra_uf = [{"lat": "-8.0", "lon": "-34.9", "category": "building", "name": "Y", "address": {"city": "Recife", "ISO3166-2-lvl4": "BR-PE"}}]
    so_cidade = [{"lat": "-23.686", "lon": "-46.623", "category": "boundary", "type": "administrative", "name": "Diadema", "address": {"city": "Diadema"}}]
    geo = geo_falso({"Praça da Moça, 10 - Centro, Diadema, SP, Brasil": predio, "Rua X, Diadema, SP, Brasil": rua,
                     "Longe, Diadema, SP, Brasil": outra_uf, "Vago, Diadema, SP, Brasil": so_cidade})
    assert bl.localizar(geo, "Praça da Moça, 10 - Centro", "Praça", "Diadema", "SP", centro) == (-23.69, -46.62, "endereco")
    assert bl.localizar(geo, "", "Rua X", "Diadema", "SP", centro) == (-23.695, -46.625, "rua")
    assert bl.localizar(geo, "Longe", "", "Diadema", "SP", centro) == (centro[0], centro[1], "cidade")  # outra UF: ignora
    assert bl.localizar(geo, "Vago", "", "Diadema", "SP", centro) == (centro[0], centro[1], "cidade")  # só achou a cidade
    assert bl.localizar(geo, "Diadema", "", "Diadema", "SP", centro) == (centro[0], centro[1], "cidade")  # endereço = cidade: nem consulta
    assert bl.localizar(None, "Praça da Moça, 10 - Centro", "", "Diadema", "SP", centro) == (centro[0], centro[1], "cidade")
    # cache em disco: a segunda instância não consulta
    arq = tmp_path / "geocache.json"
    g1 = bl.Geocodificador(arquivo=arq, consultar=lambda q: predio)
    assert bl.localizar(g1, "Praça da Moça, 10 - Centro", "", "Diadema", "SP", centro)[2] == "endereco" and g1.consultas == 1
    g1.salvar()

    def nao_consulta(q):
        raise AssertionError("consultou a rede com cache cheio")
    g2 = bl.Geocodificador(arquivo=arq, consultar=nao_consulta)
    assert bl.localizar(g2, "Praça da Moça, 10 - Centro", "", "Diadema", "SP", centro)[2] == "endereco" and g2.consultas == 0
    # falha de rede (None) não entra no cache
    g3 = bl.Geocodificador(arquivo=None, consultar=lambda q: None)
    assert bl.localizar(g3, "Praça da Moça, 10 - Centro", "", "Diadema", "SP", centro)[2] == "cidade" and g3.cache == {}


def test_variantes_do_endereco_vao_do_completo_ao_simples():
    assert bl.variantes("Rua Generina Vale, 860 (por trás da Ligzarb) - Centro") == [
        "Rua Generina Vale, 860 (por trás da Ligzarb) - Centro", "Rua Generina Vale, 860 - Centro", "Rua Generina Vale, 860", "Rua Generina Vale"]
    assert bl.variantes("Gervasio Pires com Av. Conde da Boa Vista") == ["Gervasio Pires com Av. Conde da Boa Vista", "Gervasio Pires"]
    assert bl.variantes("UnB") == []  # curto demais: nem consulta
    assert bl.variantes(" Praça da Moça ") == ["Praça da Moça"]
    # a forma simples só é consultada quando a completa falha
    pedidos = []

    def consultar(q):
        pedidos.append(q)
        return [{"lat": "-6.46", "lon": "-37.10", "category": "highway", "addresstype": "road", "name": "Rua Generina Vale",
                 "address": {"city": "Caicó", "ISO3166-2-lvl4": "BR-RN"}}] if q.startswith("Rua Generina Vale, 860,") else []
    geo = bl.Geocodificador(arquivo=None, consultar=consultar)
    assert bl.localizar(geo, "Rua Generina Vale, 860 (por trás da Ligzarb) - Centro", "Comitê", "Caicó", "RN", (-6.45, -37.09))[2] == "rua"
    assert pedidos == ["Rua Generina Vale, 860 (por trás da Ligzarb) - Centro, Caicó, RN, Brasil", "Rua Generina Vale, 860 - Centro, Caicó, RN, Brasil",
                       "Rua Generina Vale, 860, Caicó, RN, Brasil"]


def test_mesma_cidade_aceita_por_nome_ou_distancia():
    centro = (-15.78, -47.93)  # Brasília
    perto = {"lat": "-15.82", "lon": "-48.11", "address": {"town": "Ceilândia", "ISO3166-2-lvl4": "BR-DF"}}
    longe = {"lat": "-16.68", "lon": "-49.25", "address": {"city": "Goiânia", "ISO3166-2-lvl4": "BR-GO"}}
    assert bl.mesma_cidade(perto, "Brasília", "DF", centro) is True
    assert bl.mesma_cidade(longe, "Brasília", "DF", centro) is False
    assert bl.precisao_de({"category": "amenity", "name": "Sede", "address": {}}) == "endereco"
    assert bl.precisao_de({"category": "boundary", "name": "Avenida Barão de Maruim", "address": {}}) == "rua"
    assert bl.precisao_de({"category": "boundary", "name": "Diadema", "address": {}}) is None


def test_logo_da_organizacao_reconhecivel():
    assert "Partido_dos_Trabalhadores" in bl.logo_org("PT de Diadema")["url"]
    assert "via Wikimedia Commons" in bl.logo_org("Juventude do PT Santa Maria, Levante RS")["credito"]
    assert "Partido_dos_Trabalhadores" in bl.logo_org("Juventude do PT Santa Maria, Levante RS")["url"]  # o primeiro do nome vence
    assert "Partido_dos_Trabalhadores" in bl.logo_org("JPT")["url"]
    assert "PSOL" in bl.logo_org("Bancada Feminista do PSOL")["url"]
    assert "Estudantes" in bl.logo_org("UNE/ANPG")["url"]
    assert "MTST" in bl.logo_org("MTST Zona Leste")["url"] and "MST-logo" in bl.logo_org("MST Bahia")["url"]
    assert "Levante" in bl.logo_org("Levante Popular da Juventude Espírito Santo")["url"]
    assert "CUT" in bl.logo_org("CUT")["url"] and "PCdoB" in bl.logo_org("PCdoB Recife")["url"]
    assert bl.logo_org("Sergipe pela Democracia") is None
    assert bl.logo_org("Comitê Popular") is None
    assert bl.logo_org("Apto 13") is None  # "pt" só como palavra inteira
    assert bl.logo_org("") is None
    assert bl.logo_org("PT de Diadema")["pagina"].startswith("https://commons.wikimedia.org/wiki/File:")


def test_converter_com_geocodificador_marca_precisao_e_logo():
    feed = {"hoje": "2026-10-08", "acoes": [
        {"id": 1, "data": "2026-10-10", "hora": "9h", "hora_ord": 9, "uf": "SP", "cidade": "Diadema", "local": "Praça da Moça",
         "endereco": "Praça da Moça, 10 - Centro", "atividade": "Panfletagem", "tipo": "Panfletagem", "organizacao": "PT de Diadema",
         "link": "", "online": False, "plataforma": ""}]}
    predio = [{"lat": "-23.6900", "lon": "-46.6200", "category": "amenity", "name": "Praça da Moça", "address": {"city": "Diadema", "ISO3166-2-lvl4": "BR-SP"}}]
    d = bl.converter(feed, bl.carregar_lugares(), hoje="2026-10-08", geo=geo_falso({"Praça da Moça, 10 - Centro, Diadema, SP, Brasil": predio}))
    assert d["acoes"][0]["lugar"]["precisao"] == "endereco" and d["acoes"][0]["lugar"]["lat"] == -23.69
    assert d["organizacoes"][0]["foto"]["url"].startswith("https://commons.wikimedia.org/wiki/Special:Redirect/file/")
    sem = bl.converter(feed, bl.carregar_lugares(), hoje="2026-10-08")
    assert sem["acoes"][0]["lugar"]["precisao"] == "cidade"
    assert "1 com ponto exato" in bl.resumo(d) and "1 com logo" in bl.resumo(d)


def test_link_que_nao_e_http_e_descartado_com_aviso():
    assert bl.link_valido("https://www.instagram.com/p/x/") == "https://www.instagram.com/p/x/"
    assert bl.link_valido(" HTTP://site.org/a ") == "HTTP://site.org/a"
    for ruim in ["javascript:alert(1)", "data:text/html;base64,AAAA", "www.site.org", "(11) 99999-9999", "", None, "ftp://x/y"]:
        assert bl.link_valido(ruim) == "", ruim
    assert bl.foto_valida("https://cdn/x.jpg") == "https://cdn/x.jpg"
    assert bl.foto_valida("http://127.0.0.1:54321/storage/v1/object/public/divulgacao/a.jpg").startswith("http://127.0.0.1")
    for ruim in ["http://cdn/x.jpg", "javascript:alert(1)", "data:image/png;base64,AAAA", "", None]:
        assert bl.foto_valida(ruim) == "", ruim
    feed = {"hoje": "2026-10-08", "acoes": [
        {"id": 1, "data": "2026-10-10", "hora": "9h", "hora_ord": 9, "uf": "SP", "cidade": "Diadema", "local": "Praça", "endereco": "",
         "atividade": "Panfletagem", "tipo": "Panfletagem", "organizacao": "", "link": "javascript:alert(1)", "online": False, "plataforma": ""},
        {"id": 2, "data": "2026-10-10", "hora": "9h", "hora_ord": 9, "uf": "SP", "cidade": "Diadema", "local": "Praça", "endereco": "",
         "atividade": "Ato", "tipo": "Ato", "organizacao": "", "link": "https://x/2", "online": False, "plataforma": ""}]}
    d = bl.converter(feed, bl.carregar_lugares(), hoje="2026-10-08")
    a1, a2 = d["acoes"]
    assert a1["link"] == "" and a1["contatoLink"] is None and a1["contatoTipo"] == "organizador_chama"
    assert "javascript:" not in a1["descricao"] and a1["aviso"].startswith("link descartado")
    assert a2["link"] == "https://x/2" and a2["contatoTipo"] == "divulgacao" and "aviso" not in a2
    assert "AVISO: 1 links descartados" in bl.resumo(d) and "ids 1" in bl.resumo(d)
