import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import bora_lula as bl  # noqa: E402
import fotos_divulgacao as fd  # noqa: E402
import publicar_acoes as pa  # noqa: E402

LUGARES = bl.carregar_lugares()


def feed_item(**k):
    base = {"id": 1, "data": "2026-10-10", "hora": "9h", "hora_ord": 9, "uf": "SP", "cidade": "Diadema", "local": "Praça da Moça",
            "endereco": "Praça da Moça, 10 - Centro", "atividade": "Panfletagem no centro", "tipo": "Panfletagem",
            "organizacao": "PT de Diadema", "link": "https://www.instagram.com/p/x/", "online": False, "plataforma": ""}
    base.update(k)
    return base


def test_bairro_do_endereco_e_tipo_org():
    assert bl.bairro_do_endereco("Avenida Barão de Maruim, 704 - Centro", "Aracaju") == "Centro"
    assert bl.bairro_do_endereco("Av. Unisinos, 950 - Cristo Rei, São Leopoldo - RS, 93022-750", "São Leopoldo") == ""
    assert bl.bairro_do_endereco("Rua X, 10 - São Paulo", "São Paulo") == ""
    assert bl.bairro_do_endereco("", "") == ""
    assert bl.tipo_org("PT de Diadema") == "partido"
    assert bl.tipo_org("Mandato Vereadora Rosa") == "mandato"
    assert bl.tipo_org("Movimento dos Trabalhadores Sem Teto") == "movimento"
    assert bl.tipo_org("Sergipe pela Democracia") == "coletivo"


def test_item_do_feed_presencial_online_e_sem_cidade():
    item, motivo = pa.item_do_feed(feed_item(), LUGARES)
    assert motivo is None
    assert item["fonte_id"] == "1" and item["tipo"] == "panfletagem" and item["organizacao_tipo"] == "partido"
    assert item["lugar_nome"] == "Praça da Moça" and item["bairro"] == "Centro" and item["cidade"] == "Diadema"
    assert item["endereco"] == "Praça da Moça, 10 - Centro"  # guardado para o app mostrar, além de achar o ponto
    assert item["lugar_aproximado"] is True and item["lat"] is not None  # sem geocodificador: centro da cidade
    assert item["organizacao_foto"]["url"].startswith("https://commons.wikimedia.org/wiki/Special:Redirect/file/")
    predio = [{"lat": "-23.6900", "lon": "-46.6200", "category": "amenity", "name": "Praça da Moça", "address": {"city": "Diadema", "ISO3166-2-lvl4": "BR-SP"}}]
    geo = bl.Geocodificador(arquivo=None, consultar=lambda q: predio if q.startswith("Praça da Moça, 10") else [])
    exato, _ = pa.item_do_feed(feed_item(), LUGARES, geo)
    assert exato["lugar_aproximado"] is False and (exato["lat"], exato["lon"]) == (-23.69, -46.62)
    assert pa.item_do_feed(feed_item(organizacao="Sergipe pela Democracia"), LUGARES)[0]["organizacao_foto"] is None
    assert item["inicio"] == "2026-10-10T09:00" and item["fim"] == "2026-10-10T11:00"
    assert item["link"] == "https://www.instagram.com/p/x/" and "Fonte:" in item["descricao"]
    on, _ = pa.item_do_feed(feed_item(online=True, cidade="", uf="", plataforma="YouTube"), LUGARES)
    assert on["online"] is True and on["lat"] is None and on["lugar_aproximado"] is False and "(YouTube)" in on["descricao"]
    assert on["endereco"] is None
    # cidade que não reconhecemos: não some, vai para aprovação, sem ponto no mapa e com o que a fonte disse
    sc, motivo = pa.item_do_feed(feed_item(cidade="", uf=""), LUGARES)
    assert motivo is None and sc["status"] == "em análise" and sc["motivo_duvida"] == "sem cidade" and sc["lat"] is None
    xyz, _ = pa.item_do_feed(feed_item(cidade="Xyz", uf="SP"), LUGARES)
    assert (xyz["status"], xyz["motivo_duvida"]) == ("em análise", "sem cidade reconhecida")
    assert xyz["cidade"] == "Xyz - SP" and xyz["lugar_nome"] == "Praça da Moça" and xyz["lat"] is None and xyz["lon"] is None
    assert xyz["endereco"] == "Praça da Moça, 10 - Centro"  # a moderação lê o endereço que a fonte deu
    assert "status" not in item  # a que tem lugar vai ao ar (status padrão da importação)
    df, _ = pa.item_do_feed(feed_item(cidade="Ceilândia", uf="DF", endereco=""), LUGARES)
    assert df["cidade"] == "Brasília" and df["bairro"] == "Ceilândia" and -16 < df["lat"] < -15
    sbo, _ = pa.item_do_feed(feed_item(cidade="Santa Bárbara do Oeste", uf="SP"), LUGARES)
    assert sbo["cidade"] == "Santa Bárbara do Oeste" and sbo["lat"] is not None
    assert pa.item_do_feed(feed_item(cidade="São João del-Rei", uf="MG"), LUGARES)[0]["lat"] is not None


def test_itens_do_feed_filtra_datas_e_duplicatas():
    feed = {"hoje": "2026-10-08", "acoes": [
        feed_item(id=3, data="2026-10-07"),                                    # passou
        feed_item(id=2, atividade="Ato pelo Lula na praça"),                    # mesmo ato do id 1 com outro título
        feed_item(id=1),
        feed_item(id=4, data="2026-10-30"),                                    # depois do 2º turno
        feed_item(id=5, cidade="", uf="", atividade="Sem cidade"),
        feed_item(id=6, local="", endereco="", atividade="Só a cidade"),       # chave vazia: não deduplica
        feed_item(id=7, local="", endereco="", atividade="Só a cidade de novo"),
    ]}
    itens, revisao = pa.itens_do_feed(feed, LUGARES)
    assert [i["fonte_id"] for i in itens] == ["1", "5", "6", "7"]
    assert itens[1]["status"] == "em análise" and itens[2]["lugar_nome"] == "Diadema"
    assert revisao == [("2", "Ato pelo Lula na praça", "duplicata do id 1"), ("5", "Sem cidade", "aprovação: sem cidade")]
    r = pa.resumo(itens, revisao)
    assert "3 para o ar" in r and "1 para aprovação, fora do ar (sem cidade 1)" in r and "1 de fora" in r


def linha(**k):
    base = {"frente": "instagram", "titulo": "Caminhada com Lula no centro", "tipo": "caminhada", "data": "2026-10-11", "hora": "15:00",
            "cidade": "Recife", "uf": "PE", "bairro": "Boa Vista", "endereco": "", "organizador": "Juventude PT Recife (página)",
            "lula_explicito": "sim", "online": "não", "link": "https://www.instagram.com/p/abc/", "texto_original": "texto", "confianca": "alta"}
    base.update(k)
    return base


def test_itens_do_consolidado_filtra_e_deduplica_contra_o_feed():
    feed_itens, _ = pa.itens_do_feed({"hoje": "2026-10-09", "acoes": [
        feed_item(id=9, data="2026-10-11", cidade="Recife", uf="PE", atividade="Caminhada com o Lula pelo centro", link="https://x/9")]}, LUGARES)
    linhas = [
        linha(),                                                     # parecida com a do feed (mesma data e cidade)
        linha(titulo="Plenária das mulheres", tipo="plenária", link="https://x/p"),
        linha(titulo="Plenária das mulheres", tipo="plenária", link="https://x/p"),   # repetida
        linha(titulo="Outra", link="https://x/9", hora="09:00"),     # mesmo link e horário do feed
        linha(titulo="Do feed", texto_original="[fonte: agenda Bora Lula]"),
        linha(titulo="Sem Lula", lula_explicito="não"),
        linha(titulo="Fraca", confianca="baixa"),
        linha(titulo="Passou", data="2026-10-01"),
        linha(titulo="Live", online="sim", cidade="", uf="", tipo="live", hora=""),
        linha(titulo="Sem cidade", cidade="", uf=""),
    ]
    itens, revisao = pa.itens_do_consolidado(linhas, LUGARES, feed_itens, hoje="2026-10-09")
    # sem o Lula escrito vai ao ar; confiança baixa e sem cidade vão para aprovação; nada disso some
    assert [i["titulo"] for i in itens] == ["Plenária das mulheres", "Sem Lula", "Fraca", "Live", "Sem cidade"]
    assert "status" not in itens[1]
    assert (itens[2]["status"], itens[2]["motivo_duvida"]) == ("em análise", "confiança baixa") and itens[2]["lat"] is not None
    assert (itens[4]["status"], itens[4]["motivo_duvida"], itens[4]["lat"]) == ("em análise", "sem cidade", None)
    itens = [i for i in itens if i["titulo"] in ("Plenária das mulheres", "Live")]
    pl = itens[0]
    assert pl["organizacao"] == "Juventude PT Recife" and pl["organizacao_tipo"] == "partido"
    assert pl["endereco"] is None  # a linha não trouxe endereço
    assert pl["bairro"] == "Boa Vista" and pl["lugar_nome"] == "Boa Vista" and pl["inicio"] == "2026-10-11T15:00" and pl["tipo"] == "encontro"
    assert len(pl["fonte_id"]) == 16 and "Varredura" in pl["descricao"]
    assert itens[1]["online"] is True and itens[1]["inicio"] == "2026-10-11T09:00"
    motivos = {t: m for _, t, m in revisao}
    assert motivos["Caminhada com Lula no centro"] == "já está no feed Bora Lula (id 9)"
    assert motivos["Outra"] == "já está no feed Bora Lula (id 9)"
    assert motivos["Plenária das mulheres"] == "repetido no consolidado"
    assert motivos["Do feed"] == "já vem do feed Bora Lula"
    assert "Sem Lula" not in motivos and motivos["Fraca"] == "aprovação: confiança baixa"
    assert motivos["Sem cidade"] == "aprovação: sem cidade" and "Passou" not in motivos


def test_sql_importar_cita_o_json_sem_escapar():
    itens = [{"fonte_id": "1", "titulo": "Ato d'água \"x\""}]
    sql = pa.sql_importar("bora-lula", itens)
    assert sql.startswith("select importar_acoes('bora-lula', $itens$[") and sql.endswith("$itens$::jsonb, true) as r")
    assert json.loads(sql[sql.index("$itens$") + 7: sql.rindex("$itens$")]) == itens


def test_destino_exige_variaveis(monkeypatch):
    import ir_ao_ar
    monkeypatch.setattr(ir_ao_ar, "ARQ_ENV", RAIZ / "nao-existe.env")
    for v in ["SUPABASE_URL", "SUPABASE_SERVICE_KEY", "SUPABASE_ACCESS_TOKEN"]:
        monkeypatch.delenv(v, raising=False)
    import pytest
    with pytest.raises(pa.Falha):
        pa.destino()
    monkeypatch.setenv("SUPABASE_ACCESS_TOKEN", "t")
    assert pa.destino() == ("management", None, "t")
    monkeypatch.setenv("SUPABASE_URL", "http://x")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "s")
    assert pa.destino() == ("rest", "http://x", "s")


def test_limpar_org_so_deixa_organizacao_publica():
    assert pa.limpar_org("Juventude PT Recife (página)") == "Juventude PT Recife"
    assert pa.limpar_org("PT São Bernardo do Campo; DCE UFABC") == "PT São Bernardo do Campo"
    assert pa.limpar_org("Ribeirão Preto com Lula (@ribeiraopretocomlula), divulgado por Fulana") is None  # tem @
    assert pa.limpar_org("Mariana Conti (PSOL, vereadora)") == "Mariana Conti (PSOL, vereadora)"
    assert pa.limpar_org("Campanha Lula (site oficial)") == "Campanha Lula"
    assert pa.limpar_org("PT São Paulo (com Juliana Cardoso e Luna Zarattini)") == "PT São Paulo"
    assert pa.limpar_org("Sambistas do Rio (Teresa Cristina, Neguinho da Beija-Flor)") == "Sambistas do Rio"
    assert pa.limpar_org("PT Rio Preto (PT SJRP)") == "PT Rio Preto (PT SJRP)"
    assert pa.limpar_org("União Estadual dos Estudantes do RN (UEE-RN), entidades estudantis e sindicais") == "União Estadual dos Estudantes do RN (UEE-RN)"
    for ruim in ["não identificado", "perfil local (criador de conteúdo)", "Fulano de Tal", "Fulano (governador), Beltrano e Sicrano",
                 "Moradores do Catete e criador de conteúdo", "", None]:
        assert pa.limpar_org(ruim) is None, ruim


def test_mesma_cidade_data_e_hora_com_algo_em_comum_e_o_mesmo_ato():
    feed_itens, _ = pa.itens_do_feed({"hoje": "2026-10-09", "acoes": [
        feed_item(id=1, data="2026-10-09", hora="17h", hora_ord=17, uf="MG", cidade="Belo Horizonte",
                  atividade="Estudantes nas ruas contra Bolsonaro", local="Praça Afonso Arinos", endereco="", link="https://x/1"),
        feed_item(id=2, data="2026-10-09", hora="17h30", hora_ord=17.5, uf="MG", cidade="São João del-Rei",
                  atividade="Estudantes de MG contra Bolsonaro", local="UFSJ | Universidade Federal de São João del-Rei",
                  endereco="", link="https://x/2"),
    ]}, LUGARES)
    base = dict(data="2026-10-09", uf="MG", bairro="")
    linhas = [
        # outro título, mesmo lugar e hora: duplicata pelo local
        linha(titulo="Ato Estudantes com Lula em Belo Horizonte", cidade="Belo Horizonte", hora="17:00",
              endereco="Praça Afonso Arinos, em frente à Faculdade de Direito", link="https://x/a", **base),
        # outro título, local diz UFSJ: duplicata
        linha(titulo="Caminhada pela democracia em São João del-Rei", cidade="São João del-Rei", hora="17:30",
              endereco="Concentração em frente ao Campus Dom Bosco da UFSJ", link="https://x/b", **base),
        # mesma cidade e hora, nada em comum: é outro ato
        linha(titulo="Panfletagem com Lula na feira", cidade="Belo Horizonte", hora="17:00",
              endereco="Feira do Barreiro", link="https://x/c", **base),
        # mesma cidade, título parecido, outra hora: segue a regra antiga (título parecido derruba)
        linha(titulo="Plenária com Lula no Barreiro", cidade="Belo Horizonte", hora="10:00",
              endereco="Praça Afonso Arinos", link="https://x/d", **base),
    ]
    itens, revisao = pa.itens_do_consolidado(linhas, LUGARES, feed_itens, hoje="2026-10-09")
    motivos = {t: m for _, t, m in revisao}
    assert motivos["Ato Estudantes com Lula em Belo Horizonte"] == "já está no feed Bora Lula (id 1)"
    assert motivos["Caminhada pela democracia em São João del-Rei"] == "já está no feed Bora Lula (id 2)"
    assert [i["titulo"] for i in itens] == ["Panfletagem com Lula na feira", "Plenária com Lula no Barreiro"]


def test_card_com_varias_acoes_no_mesmo_post_vira_uma_acao_por_linha():
    card = "https://www.instagram.com/p/card/"
    rj = dict(cidade="Rio de Janeiro", uf="RJ", bairro="", link=card)
    linhas = [
        linha(titulo="Camisetaço no Vidigal", hora="17:00", **rj),
        linha(titulo="Bandeiraço no Vidigal", hora="17:00", **rj),           # mesma hora, sem endereço: outra ação
        linha(titulo="Bandeiraço na Rocinha", hora="17:00", **rj),
        linha(titulo="Adesivaço no sinal (Prefeitura)", hora="17:00", endereco="Sinal da Prefeitura", **rj),
        linha(titulo="Adesivaço no sinal (Bambuzinho)", hora="17:00", endereco="Sinal do Bambuzinho", **rj),
        # o mesmo post lido por outra frente, com outro título e a hora escrita de outro jeito: repetida
        linha(frente="x", titulo="Camisetaço Vidigal", hora="17h", cidade="Rio de Janeiro - RJ", uf="RJ", bairro="", link=card),
    ]
    itens, revisao = pa.itens_do_consolidado(linhas, LUGARES, hoje="2026-10-09")
    assert [i["titulo"] for i in itens] == [l["titulo"] for l in linhas[:5]]
    assert [(t, m) for _, t, m in revisao] == [("Camisetaço Vidigal", "repetido no consolidado")]


def test_id_depende_so_da_propria_linha():
    l = linha(titulo="Caminhada", link="https://x/card")
    sozinha, _ = pa.itens_do_consolidado([l], LUGARES, hoje="2026-10-09")
    com_outras, _ = pa.itens_do_consolidado([linha(titulo="Outra", hora="10:00", link="https://x/card"),
                                             linha(titulo="Passada", data="2026-10-01", link="https://x/card"), l],
                                            LUGARES, hoje="2026-10-09")
    assert sozinha[0]["fonte_id"] == com_outras[1]["fonte_id"]
    # hora e cidade escritas de outro jeito dão o mesmo id
    outra_grafia, _ = pa.itens_do_consolidado([linha(titulo="Caminhada", link="https://x/card", hora="15h", cidade="Recife - PE")],
                                              LUGARES, hoje="2026-10-09")
    assert outra_grafia[0]["fonte_id"] == sozinha[0]["fonte_id"]


def test_mesmo_ato_em_frentes_e_links_diferentes_com_grafias_diferentes():
    linhas = [linha(titulo="Caminhada com Lula no centro", hora="17:00", link="https://x/a"),
              linha(frente="x", titulo="Caminhada com Lula no Centro do Recife", hora="17h", cidade="Recife - PE", link="https://x/b")]
    # mesma hora e cidade, só o tipo de ação em comum: outra ação
    linhas.append(linha(frente="rj", titulo="Plenária da Virada na Taquara", hora="17:00", endereco="Estrada do Tindiba, 2089",
                        link="https://x/c"))
    linhas.append(linha(frente="pe", titulo="Plenária da Virada do Campo Popular", hora="17:00", endereco="Sindicato dos Bancários",
                        link="https://x/d"))
    itens, revisao = pa.itens_do_consolidado(linhas, LUGARES, hoje="2026-10-09")
    assert len(itens) == 3 and [m for _, _, m in revisao] == ["repetido no consolidado"]


def test_link_do_feed_so_derruba_a_acao_do_mesmo_horario():
    card = "https://www.instagram.com/p/card/"
    feed_itens, _ = pa.itens_do_feed({"hoje": "2026-10-09", "acoes": [
        feed_item(id=7, data="2026-10-11", hora="15h", hora_ord=15, cidade="Recife", uf="PE", atividade="Panfletaço", link=card)]}, LUGARES)
    linhas = [linha(titulo="Panfletagem no Derby", hora="15:00", link=card),
              linha(titulo="Plenária à noite", hora="19:00", link=card)]
    itens, revisao = pa.itens_do_consolidado(linhas, LUGARES, feed_itens, hoje="2026-10-09")
    assert [i["titulo"] for i in itens] == ["Plenária à noite"]
    assert [m for _, _, m in revisao] == ["já está no feed Bora Lula (id 7)"]


def test_trava_nao_encerra_acao_com_inscricao():
    itens = [{"fonte_id": "a"}, {"fonte_id": "b"}]
    assert pa.encerramentos_com_inscricao(itens, {"a", "c", "d"}) == ["c", "d"]
    assert pa.encerramentos_com_inscricao(itens, set()) == []


def test_mesmo_card_frentes_diferentes_acoes_diferentes_na_mesma_hora():
    card = "https://www.instagram.com/p/card/"
    linhas = [linha(frente="rj", titulo="Camisetaço no Vidigal", hora="17:00", cidade="Rio de Janeiro", uf="RJ", bairro="", link=card),
              linha(frente="x", titulo="Bandeiraço na Rocinha", hora="17:00", cidade="Rio de Janeiro", uf="RJ", bairro="", link=card)]
    itens, revisao = pa.itens_do_consolidado(linhas, LUGARES, hoje="2026-10-09")
    assert len(itens) == 2 and revisao == []


def test_trava_so_olha_turnos_de_hoje_em_diante(monkeypatch):
    consultas = []
    monkeypatch.setattr(pa, "consultar_sql", lambda sql, ref=None: consultas.append(sql) or [{"fonte_id": "a"}])
    monkeypatch.setattr(pa, "destino", lambda: ("management", None, "tok"))
    assert pa.ids_com_inscricao("redes", "2026-10-11") == {"a"}
    assert "t.inicio >= '2026-10-11'" in consultas[0] and "a.fonte = 'redes'" in consultas[0]


def test_link_invalido_e_descartado_com_aviso_na_revisao():
    item, motivo = pa.item_do_feed(feed_item(link="javascript:alert(1)"), LUGARES)
    assert motivo is None and item["link"] == "" and item["aviso"].startswith("link descartado")
    assert "aviso" not in pa.item_do_feed(feed_item(), LUGARES)[0]
    assert "aviso" not in pa.item_do_feed(feed_item(link=""), LUGARES)[0]
    feed = {"hoje": "2026-10-08", "acoes": [feed_item(id=1, link="javascript:alert(1)"), feed_item(id=2, local="Outro", link="www.sem-esquema.org")]}
    itens, revisao = pa.itens_do_feed(feed, LUGARES)
    assert [i["link"] for i in itens] == ["", ""] and all("aviso" not in i for i in itens)  # o item vai sem o aviso dentro
    assert revisao == [("1", "Panfletagem no centro", "aviso: link descartado (não é http/https): javascript:alert(1)"),
                       ("2", "Panfletagem no centro", "aviso: link descartado (não é http/https): www.sem-esquema.org")]
    r = pa.resumo(itens, revisao)
    assert "2 para o ar" in r and "0 para aprovação" in r and "0 de fora" in r and "AVISO: 2 links descartados" in r
    # rota redes (CSV): a mesma regra
    itens, revisao = pa.itens_do_consolidado([linha(link="data:text/html,oi"), linha(titulo="Boa", link="https://x/ok")], LUGARES, hoje="2026-10-09")
    assert [i["link"] for i in itens] == ["", "https://x/ok"]
    assert revisao == [("instagram", "Caminhada com Lula no centro", "aviso: link descartado (não é http/https): data:text/html,oi")]
    assert pa.sql_importar("redes", itens).count("javascript") == 0


def test_com_foto_descarta_url_que_nao_e_https(capsys):
    mapa = {"AAA": {"url": "http://cdn/AAA.jpg", "perfil": "x"}, "BBB": {"url": "https://s/divulgacao/BBB.jpg"}}
    itens = [{"fonte_id": "1", "link": "https://www.instagram.com/p/AAA/", "organizacao": None,
              "organizacao_foto": {"url": "javascript:alert(1)", "credito": "", "pagina": ""}},
             {"fonte_id": "2", "link": "https://www.instagram.com/p/BBB/", "organizacao": None,
              "organizacao_foto": {"url": "https://commons.wikimedia.org/x.svg", "credito": "", "pagina": ""}}]
    pa.com_foto(itens, mapa)
    assert itens[0]["foto"] is None and itens[0]["organizacao_foto"] is None
    assert itens[1]["foto"]["url"].endswith("BBB.jpg") and itens[1]["organizacao_foto"]["url"].startswith("https://commons")
    assert capsys.readouterr().err.count("AVISO") == 2


def test_com_foto_passa_a_mini_e_descarta_mini_que_nao_e_https(capsys):
    pages = f"{fd.BASE_PAGES}/AAA.jpg"
    mapa = {"AAA": {"url": pages, "mini": f"{fd.BASE_PAGES}/AAA-mini.jpg", "pages": True},
            "BBB": {"url": "https://s/divulgacao/BBB.jpg"},
            "CCC": {"url": "https://s/divulgacao/CCC.jpg", "mini": "http://cdn/CCC-mini.jpg"}}
    itens = [{"fonte_id": c, "link": f"https://www.instagram.com/p/{c}/", "organizacao": None} for c in ("AAA", "BBB", "CCC")]
    pa.com_foto(itens, mapa)
    assert itens[0]["foto"] == {"url": pages, "mini": f"{fd.BASE_PAGES}/AAA-mini.jpg", "credito": "Divulgação original no Instagram",
                                "pagina": "https://www.instagram.com/p/AAA/"}
    assert itens[1]["foto"]["mini"] is None  # ainda no bucket: só a cheia
    assert itens[2]["foto"]["url"].endswith("CCC.jpg") and itens[2]["foto"]["mini"] is None
    assert capsys.readouterr().err.count("AVISO: mini descartada") == 1


def _rodar_aplicar(tmp_path, monkeypatch, pendentes, sem_fotos=False, no_pages=True, head=200):
    """Roda `bora-lula --de feed --aplicar` com o banco, a busca de fotos, o git e o HEAD no Pages simulados;
    devolve (código, erro, gravações, buscas, heads). Com `no_pages` o item leva foto do Pages (mapa já coletado)."""
    feed = tmp_path / "feed.json"
    feed.write_text(json.dumps({"hoje": "2026-10-09", "acoes": [feed_item(id=1, data="2026-10-10")]}), encoding="utf-8")
    monkeypatch.setattr(pa, "RAIZ", tmp_path)  # o ensaio escreve em <RAIZ>/levantamento
    monkeypatch.setattr(pa, "destino", lambda: ("rest", "http://x", "s"))
    gravacoes, buscas, heads = [], [], []
    monkeypatch.setattr(pa, "publicar", lambda *a, **k: gravacoes.append(a) or {"inseridas": 1})
    mapa = {"x": {"url": f"{fd.BASE_PAGES}/x.jpg", "mini": f"{fd.BASE_PAGES}/x-mini.jpg", "pages": True}} if no_pages else {}
    monkeypatch.setattr(fd, "carregar_mapa", lambda *a: mapa)
    monkeypatch.setattr(fd, "buscar_fotos", lambda itens, mapa: buscas.append(len(itens)) or (mapa, 0, []))
    monkeypatch.setattr(fd, "fotos_pendentes", lambda: fd.MSG_PENDENTES if pendentes else None)
    monkeypatch.setattr(fd, "_head", lambda url: heads.append(url) or head)
    args = ["bora-lula", "--de", str(feed), "--aplicar", "--sem-geocodificar"] + (["--sem-fotos"] if sem_fotos else [])
    import io, contextlib
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        codigo = pa.main(args)
    return codigo, err.getvalue(), gravacoes, buscas, heads


def test_aplicar_para_sem_gravar_quando_ha_fotos_pendentes(tmp_path, monkeypatch):
    codigo, erro, gravacoes, buscas, heads = _rodar_aplicar(tmp_path, monkeypatch, pendentes=True)
    assert codigo == 1 and gravacoes == [] and buscas == [1] and heads == []
    assert "fotos novas em fotos/divulgacao ainda não foram commitadas e enviadas para a master" in erro
    assert list((tmp_path / "levantamento").glob("publicar-bora-lula-*.json"))  # o ensaio ficou gravado para conferir
    codigo, erro, gravacoes, buscas, heads = _rodar_aplicar(tmp_path, monkeypatch, pendentes=False)
    assert codigo == 0 and len(gravacoes) == 1 and gravacoes[0][0] == "bora-lula"
    assert heads == [f"{fd.BASE_PAGES}/x-mini.jpg"]  # conferiu no Pages a mini que vai para o banco
    assert gravacoes[0][1][0]["foto"]["mini"] == f"{fd.BASE_PAGES}/x-mini.jpg"


def test_sem_fotos_so_pula_a_busca_e_a_trava_roda_do_mesmo_jeito(tmp_path, monkeypatch):
    codigo, erro, gravacoes, buscas, heads = _rodar_aplicar(tmp_path, monkeypatch, pendentes=True, sem_fotos=True)
    assert codigo == 1 and gravacoes == [] and buscas == []
    assert "ainda não foram commitadas" in erro
    codigo, erro, gravacoes, buscas, heads = _rodar_aplicar(tmp_path, monkeypatch, pendentes=False, sem_fotos=True)
    assert codigo == 0 and len(gravacoes) == 1 and buscas == [] and len(heads) == 1


def test_aplicar_para_se_o_pages_ainda_nao_serve_a_mini(tmp_path, monkeypatch):
    codigo, erro, gravacoes, buscas, heads = _rodar_aplicar(tmp_path, monkeypatch, pendentes=False, head=404)
    assert codigo == 1 and gravacoes == [] and heads == [f"{fd.BASE_PAGES}/x-mini.jpg"]
    assert "o Pages ainda não serve 1 fotos (ex.: x); espere o workflow terminar e rode de novo" in erro


def test_sem_item_com_foto_do_pages_nao_ha_trava(tmp_path, monkeypatch):
    # nada aponta para o Pages (mapa vazio): nem git nem HEAD são consultados, mesmo com pendência
    codigo, erro, gravacoes, buscas, heads = _rodar_aplicar(tmp_path, monkeypatch, pendentes=True, no_pages=False)
    assert codigo == 0 and len(gravacoes) == 1 and heads == []


def test_baixa_sem_cidade_junta_os_motivos_e_vai_ao_banco_com_status():
    itens, _ = pa.itens_do_consolidado([linha(titulo="Fraca e perdida", confianca="baixa", cidade="Xyz", uf="SP")], LUGARES, hoje="2026-10-09")
    assert itens[0]["motivo_duvida"] == "confiança baixa; sem cidade reconhecida" and itens[0]["status"] == "em análise"
    sql = pa.sql_importar("redes", itens)
    assert "em análise" in sql and "motivo_duvida" in sql


def test_acao_do_feed_sem_post_ganha_a_imagem_do_post_das_redes_que_a_divulga():
    feed_itens, _ = pa.itens_do_feed({"hoje": "2026-10-09", "acoes": [
        feed_item(id=1, data="2026-10-11", cidade="Recife", uf="PE", atividade="Caminhada Recife com Lula", link=""),
        feed_item(id=2, data="2026-10-11", cidade="Recife", uf="PE", atividade="Plenária da juventude", hora="18h", hora_ord=18, link=""),
        feed_item(id=3, data="2026-10-11", cidade="Recife", uf="PE", atividade="Ato no Marco Zero", hora="10h", hora_ord=10,
                  link="https://www.instagram.com/p/PROPRIO/"),
        feed_item(id=4, data="2026-10-11", cidade="Olinda", uf="PE", atividade="Bandeiraço em Olinda", link=""),
        feed_item(id=5, data="2026-10-11", cidade="Olinda", uf="PE", atividade="Panfletagem no Carmo", local="Largo do Carmo", link=""),
        # card de agenda com duas ações em Caruaru: uma linha por ação, mesmo post
        feed_item(id=6, data="2026-10-12", cidade="Caruaru", uf="PE", atividade="Panfletagem na feira de Caruaru", link=""),
        feed_item(id=7, data="2026-10-12", cidade="Caruaru", uf="PE", atividade="Plenária popular de Caruaru", hora="19h", hora_ord=19, link="")]}, LUGARES)
    linhas = [
        linha(titulo="Caminhada com Lula em Recife", hora="9:00", link="https://www.instagram.com/p/CAMINHADA/",
              texto_original="Bora Lula! caminhada"),                     # cita a agenda: serve mesmo assim
        linha(titulo="Juventude se organiza", hora="18:00", link="https://www.instagram.com/p/JUV/"),  # mesmo ato, título outro
        linha(titulo="Ato no Marco Zero", hora="10:00", link="https://www.instagram.com/p/OUTRO/"),    # já tem post próprio
        linha(titulo="Bandeiraço e panfletagem", cidade="Olinda", hora="9:00", endereco="Praça da Moça e Largo do Carmo", link="https://www.instagram.com/p/DOIS/"),  # serve a 4 e 5
        linha(titulo="Caminhada com Lula em Recife", data="2026-10-30", link="https://www.instagram.com/p/DEPOIS/"),  # fora do período
        linha(titulo="Sem post", link="https://x.com/algo"),
        linha(titulo="Panfletagem na feira", cidade="Caruaru", data="2026-10-12", hora="9:00", link="https://www.instagram.com/p/CARD/"),
        linha(titulo="Plenária popular", cidade="Caruaru", data="2026-10-12", hora="19:00", link="https://www.instagram.com/p/CARD/"),
    ]
    posts = pa.posts_das_redes(linhas, LUGARES, hoje="2026-10-09")
    assert sorted(fd.codigo_do_link(p["link"]) for _, p in posts) == ["CAMINHADA", "CARD", "CARD", "DOIS", "JUV", "OUTRO"]
    duvidas = pa.casar_fotos(feed_itens, posts)
    por_id = {i["fonte_id"]: i for i in feed_itens}
    assert por_id["1"]["link_foto"] == "https://www.instagram.com/p/CAMINHADA/" and not por_id["1"]["link"]  # o link segue o do feed
    assert "link_foto" not in por_id["3"]                       # o post do próprio feed manda
    assert por_id["6"]["link_foto"] == por_id["7"]["link_foto"] == "https://www.instagram.com/p/CARD/"  # cada linha do card, uma ação
    assert all("link_foto" not in por_id[k] for k in ("2", "4", "5"))
    assert {d[0]: d[2] for d in duvidas} == {"2": "https://www.instagram.com/p/JUV/", "4": "https://www.instagram.com/p/DOIS/",
                                            "5": "https://www.instagram.com/p/DOIS/"}
    # o Gui confirma uma dúvida e recusa um casamento automático
    for i in feed_itens:
        i.pop("link_foto", None)
    duvidas = pa.casar_fotos(feed_itens, posts, {"2": "https://www.instagram.com/p/JUV/", "1": None})
    assert por_id["2"]["link_foto"] == "https://www.instagram.com/p/JUV/" and "link_foto" not in por_id["1"]
    assert {d[0] for d in duvidas} == {"4", "5"}
    # a imagem sai do post casado, com o crédito apontando para ele
    mapa = {"JUV": {"url": "https://s/divulgacao/JUV.jpg", "perfil": "juventude"}}
    assert sorted(fd.pendentes(feed_itens, {})) == ["CARD", "JUV", "PROPRIO"]
    assert fd.foto_do_item(por_id["2"], mapa)["pagina"] == "https://www.instagram.com/p/JUV/"
