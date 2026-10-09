import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import bora_lula as bl  # noqa: E402
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
    assert pa.item_do_feed(feed_item(cidade="", uf=""), LUGARES) == (None, "sem cidade")
    assert pa.item_do_feed(feed_item(cidade="Xyz", uf="SP"), LUGARES) == (None, "sem cidade reconhecida")
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
    assert [i["fonte_id"] for i in itens] == ["1", "6", "7"]
    assert itens[1]["lugar_nome"] == "Diadema"
    assert revisao == [("2", "Ato pelo Lula na praça", "duplicata do id 1"), ("5", "Sem cidade", "sem cidade")]


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
        linha(titulo="Outra", link="https://x/9"),                   # mesmo link do feed
        linha(titulo="Do feed", texto_original="[fonte: agenda Bora Lula]"),
        linha(titulo="Sem Lula", lula_explicito="não"),
        linha(titulo="Fraca", confianca="baixa"),
        linha(titulo="Passou", data="2026-10-01"),
        linha(titulo="Live", online="sim", cidade="", uf="", tipo="live", hora=""),
        linha(titulo="Sem cidade", cidade="", uf=""),
    ]
    itens, revisao = pa.itens_do_consolidado(linhas, LUGARES, feed_itens, hoje="2026-10-09")
    assert [i["titulo"] for i in itens] == ["Plenária das mulheres", "Live"]
    pl = itens[0]
    assert pl["organizacao"] == "Juventude PT Recife" and pl["organizacao_tipo"] == "partido"
    assert pl["bairro"] == "Boa Vista" and pl["lugar_nome"] == "Boa Vista" and pl["inicio"] == "2026-10-11T15:00" and pl["tipo"] == "encontro"
    assert len(pl["fonte_id"]) == 16 and "Varredura" in pl["descricao"]
    assert itens[1]["online"] is True and itens[1]["inicio"] == "2026-10-11T09:00"
    motivos = {t: m for _, t, m in revisao}
    assert motivos["Caminhada com Lula no centro"] == "já está no feed Bora Lula (id 9)"
    assert motivos["Outra"] == "já está no feed Bora Lula (id 9)"
    assert motivos["Plenária das mulheres"] == "repetido no consolidado"
    assert motivos["Do feed"] == "já vem do feed Bora Lula"
    assert motivos["Sem Lula"] == "sem Lula explícito" and motivos["Fraca"] == "confiança baixa"
    assert motivos["Sem cidade"] == "sem cidade" and "Passou" not in motivos


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
    linhas = [
        linha(titulo="Camisetaço no Vidigal", cidade="Rio de Janeiro", uf="RJ", bairro="", hora="17:00", link=card),
        linha(titulo="Bandeiraço no Vidigal", cidade="Rio de Janeiro", uf="RJ", bairro="", hora="17:30", link=card),
        linha(titulo="Caminhada Macaé com Lula", cidade="Macaé", uf="RJ", bairro="", hora="17:00", link=card),
        # mesma hora e cidade, outro lugar: outra ação
        linha(titulo="Adesivaço na Prefeitura", cidade="Macaé", uf="RJ", bairro="", hora="17:00", link=card,
              endereco="Sinal em frente à Prefeitura"),
        # a mesma ação do card vista por outra frente, com outro título: continua repetida
        linha(frente="x", titulo="Caminhada em Macaé", cidade="Macaé", uf="RJ", bairro="", hora="17:00", link=card),
        linha(titulo="Plenária das mulheres", link="https://x/p"),
    ]
    itens, revisao = pa.itens_do_consolidado(linhas, LUGARES, hoje="2026-10-09")
    assert [i["titulo"] for i in itens] == ["Camisetaço no Vidigal", "Bandeiraço no Vidigal", "Caminhada Macaé com Lula",
                                            "Adesivaço na Prefeitura", "Plenária das mulheres"]
    assert [m for _, _, m in revisao] == ["repetido no consolidado"]
    # link de um post só: o id continua sendo o do link, como antes (não muda o que já está publicado)
    assert itens[4]["fonte_id"] == pa.id_redes(linhas[5])
