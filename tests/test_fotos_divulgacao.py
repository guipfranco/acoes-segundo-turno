import io
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import fotos_divulgacao as fd  # noqa: E402
import publicar_acoes as pa  # noqa: E402


def jpeg(largura, altura):
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (largura, altura), (200, 30, 30)).save(b, "PNG")
    return b.getvalue()


def test_codigo_e_perfil():
    assert fd.codigo_do_link("https://www.instagram.com/p/DeJndjwpIW-/?stkn=x") == "DeJndjwpIW-"
    assert fd.codigo_do_link("https://www.instagram.com/reels/DeIQPIvvPAi/") == "DeIQPIvvPAi"
    assert fd.codigo_do_link("https://www.instagram.com/ptportoalegre/reel/DeIQPIvvPAi/") == "DeIQPIvvPAi"
    assert fd.codigo_do_link("https://x.com/a/status/1") is None and fd.codigo_do_link(None) is None
    assert fd.perfil_do_og("https://www.instagram.com/ptportoalegre/reel/DeIQPIvvPAi/") == "ptportoalegre"
    assert fd.perfil_do_og("https://www.instagram.com/p/DeIQPIvvPAi/") is None


def test_foto_do_item_so_credita_perfil_com_organizacao():
    mapa = {"AAA": {"url": "https://s/divulgacao/AAA.jpg", "perfil": "ptdiadema"}}
    com_org = {"link": "https://www.instagram.com/p/AAA/", "organizacao": "PT de Diadema"}
    sem_org = {"link": "https://www.instagram.com/p/AAA/", "organizacao": None}
    # foto ainda no bucket (sem mini): mini vai None
    assert fd.foto_do_item(com_org, mapa) == {"url": "https://s/divulgacao/AAA.jpg", "mini": None,
                                              "credito": "Divulgação de @ptdiadema no Instagram", "pagina": "https://www.instagram.com/p/AAA/"}
    assert fd.foto_do_item(sem_org, mapa)["credito"] == "Divulgação original no Instagram"
    assert fd.foto_do_item({"link": "https://www.instagram.com/p/BBB/"}, mapa) is None
    assert fd.foto_do_item({"link": ""}, mapa) is None
    itens = pa.com_foto([dict(com_org), {"link": "", "organizacao": None}], mapa)
    assert itens[0]["foto"]["url"].endswith("AAA.jpg") and itens[1]["foto"] is None
    # foto já no Pages: a mini vai junto
    pages = {"AAA": {"url": f"{fd.BASE_PAGES}/AAA.jpg", "mini": f"{fd.BASE_PAGES}/AAA-mini.jpg", "perfil": None, "pages": True}}
    assert fd.foto_do_item(sem_org, pages)["mini"] == "https://guipfranco.github.io/acoes-segundo-turno/fotos/divulgacao/AAA-mini.jpg"


def test_pendentes_sem_repetir_e_sem_o_que_ja_tem():
    itens = [{"link": "https://www.instagram.com/p/AAA/"}, {"link": "https://www.instagram.com/reel/BBB/"},
             {"link": "https://www.instagram.com/p/AAA/?x=1"}, {"link": "https://x.com/q"}, {"link": "https://www.instagram.com/p/CCC/"}]
    assert fd.pendentes(itens, {"CCC": {"url": "u"}}) == ["AAA", "BBB"]


def test_reduzir_limita_largura_e_gera_jpeg():
    from PIL import Image
    out = fd.reduzir(jpeg(1440, 1800))
    im = Image.open(io.BytesIO(out))
    assert im.format == "JPEG" and im.size == (1080, 1350)
    assert Image.open(io.BytesIO(fd.reduzir(jpeg(400, 500)))).size == (400, 500)  # nunca amplia
    mini = fd.reduzir(jpeg(1440, 1800), fd.LARGURA_MINI, fd.QUALIDADE_MINI)
    assert Image.open(io.BytesIO(mini)).size == (480, 600) and len(mini) < len(out)


def test_gravar_pages_gera_arte_e_mini_na_pasta(tmp_path):
    from PIL import Image
    url, mini = fd.gravar_pages("AAA", jpeg(1080, 1350), pasta=tmp_path / "fotos")
    assert url == "https://guipfranco.github.io/acoes-segundo-turno/fotos/divulgacao/AAA.jpg"
    assert mini == "https://guipfranco.github.io/acoes-segundo-turno/fotos/divulgacao/AAA-mini.jpg"
    assert Image.open(tmp_path / "fotos" / "AAA.jpg").size == (1080, 1350)
    assert Image.open(tmp_path / "fotos" / "AAA-mini.jpg").size == (480, 600)


def test_processar_coleta_grava_na_pasta_do_pages_e_registra(tmp_path):
    def baixar(url):
        if "quebrada" in url:
            raise OSError("404")
        return jpeg(1000, 1000)

    coleta = [{"codigo": "AAA", "img": "https://cdn/a.jpg", "url": "https://www.instagram.com/ptdiadema/p/AAA/", "inteira": True},
              {"codigo": "BBB", "img": "https://cdn/quebrada.jpg", "url": ""}, {"codigo": "CCC", "img": None}]
    mapa = {}
    novas, falhas = fd.processar_coleta(coleta, mapa, pasta=tmp_path, baixar=baixar)
    assert novas == 1 and [f[0] for f in falhas] == ["BBB", "CCC"]
    assert mapa == {"AAA": {"url": f"{fd.BASE_PAGES}/AAA.jpg", "mini": f"{fd.BASE_PAGES}/AAA-mini.jpg", "perfil": "ptdiadema",
                            "inteira": True, "pages": True}}
    assert (tmp_path / "AAA.jpg").exists() and (tmp_path / "AAA-mini.jpg").exists() and not (tmp_path / "BBB.jpg").exists()


def test_migracao_cria_bucket_publico_e_importa_foto_sem_apagar():
    sql = (RAIZ / "supabase" / "migrations" / "20261009000003_foto_divulgacao.sql").read_text(encoding="utf-8")
    assert "insert into storage.buckets" in sql and "'divulgacao', 'divulgacao', true" in sql
    assert "foto_url = coalesce(excluded.foto_url, acao.foto_url)" in sql
    assert "nullif(it->'foto'->>'url', '')" in sql


def test_og_da_pagina_e_coletar_para_no_429():
    pag = '<meta property="og:image" content="https://cdn/x.jpg?a=1&amp;b=2" /><meta content="https://www.instagram.com/une/p/AAA/" property="og:url">'
    assert fd.og_da_pagina(pag) == {"img": "https://cdn/x.jpg?a=1&b=2", "url": "https://www.instagram.com/une/p/AAA/"}
    assert fd.og_da_pagina("<html></html>") == {"img": None, "url": None}
    pausas = []

    def ler(c):
        if c == "CCC":
            raise fd.Limite()
        return {"codigo": c, "img": "i", "url": "u"}
    assert [x["codigo"] for x in fd.coletar(["AAA", "BBB", "CCC", "DDD"], ler=ler, pausa=3, dormir=pausas.append)] == ["AAA", "BBB"]
    assert pausas == [3, 3]


def test_buscar_fotos_so_le_o_que_falta(tmp_path, monkeypatch):
    monkeypatch.setattr(fd, "MAPA", tmp_path / "mapa.json")
    monkeypatch.setattr(fd, "PASTA_PAGES", tmp_path / "fotos")
    monkeypatch.setattr(fd, "PAUSA", 0)
    monkeypatch.setattr(fd, "baixar", lambda url: jpeg(800, 800))
    monkeypatch.setattr(fd.time, "sleep", lambda s: None)
    lidos = []

    def ler(c):
        lidos.append(c)
        return {"codigo": c, "img": "https://cdn/x.jpg", "url": f"https://www.instagram.com/org/p/{c}/"}
    itens = [{"link": "https://www.instagram.com/p/AAA/"}, {"link": "https://www.instagram.com/p/BBB/"}]
    mapa, novas, falhas = fd.buscar_fotos(itens, {"BBB": {"url": "u"}}, ler=ler)
    assert lidos == ["AAA"] and novas == 1 and falhas == []
    assert mapa["AAA"] == {"url": f"{fd.BASE_PAGES}/AAA.jpg", "mini": f"{fd.BASE_PAGES}/AAA-mini.jpg", "perfil": "org", "inteira": False, "pages": True}
    assert json.loads((tmp_path / "mapa.json").read_text(encoding="utf-8"))["AAA"]["mini"].endswith("/AAA-mini.jpg")
    assert (tmp_path / "fotos" / "AAA.jpg").exists() and (tmp_path / "fotos" / "AAA-mini.jpg").exists()
    assert fd.buscar_fotos(itens, mapa, ler=ler)[1] == 0 and lidos == ["AAA"]


def test_publicar_busca_fotos_ao_aplicar_e_trava_se_houver_pendentes():
    src = (RAIZ / "scripts" / "publicar_acoes.py").read_text(encoding="utf-8")
    assert "if args.aplicar and not args.sem_fotos:" in src and "fd.buscar_fotos(itens, mapa)" in src
    # a trava (git + HEAD no Pages) roda sempre que algum item leva foto do Pages, com ou sem --sem-fotos
    assert "conferir_pages(itens)" in src and src.index("conferir_pages(itens)\n") < src.index("r = publicar(")
    assert "fd.fotos_pendentes()" in src and "fd.exigir_no_pages(cods)" in src and "fd.codigos_no_pages(itens)" in src


def test_codigos_no_pages_so_pega_item_com_foto_do_pages():
    itens = [{"link": "https://www.instagram.com/p/AAA/", "foto": {"url": f"{fd.BASE_PAGES}/AAA.jpg", "mini": None}},
             {"link": "https://www.instagram.com/p/BBB/", "foto": {"url": "https://proj.supabase.co/storage/v1/object/public/divulgacao/BBB.jpg", "mini": None}},
             {"link": "https://www.instagram.com/p/CCC/", "foto": {"url": "https://x/c.jpg", "mini": f"{fd.BASE_PAGES}/CCC-mini.jpg"}},
             {"link": "https://www.instagram.com/p/AAA/", "foto": {"url": f"{fd.BASE_PAGES}/AAA.jpg", "mini": f"{fd.BASE_PAGES}/AAA-mini.jpg"}},
             {"link": "https://x.org", "foto": None}]
    assert fd.codigos_no_pages(itens) == ["AAA", "CCC"]
    assert fd.codigos_no_pages([]) == []


def test_publicadas_no_pages_confere_a_mini_por_head():
    pedidos = []

    def head(url):
        pedidos.append(url)
        return 200 if "AAA" in url or "CCC" in url else 404
    assert fd.publicadas_no_pages(["AAA", "BBB", "CCC", "DDD"], head=head) == ["BBB", "DDD"]
    assert pedidos == [f"{fd.BASE_PAGES}/{c}-mini.jpg" for c in ["AAA", "BBB", "CCC", "DDD"]]
    assert fd.publicadas_no_pages([], head=lambda u: _explode("sem código, sem HEAD")) == []
    fd.exigir_no_pages(["AAA"], head=head)  # tudo servido: passa
    import pytest
    with pytest.raises(fd.Falha, match=r"o Pages ainda não serve 2 fotos \(ex\.: BBB\); espere o workflow terminar e rode de novo"):
        fd.exigir_no_pages(["AAA", "BBB", "DDD"], head=head)


def test_fotos_pendentes_olha_o_git():
    def git_de(status, log):
        return lambda args: status if args[0] == "status" else log
    assert fd.fotos_pendentes(git=git_de("", "")) is None
    assert fd.fotos_pendentes(git=git_de("", "\n")) is None
    assert fd.fotos_pendentes(git=git_de("?? fotos/divulgacao/AAA.jpg\n", "")) == fd.MSG_PENDENTES
    assert fd.fotos_pendentes(git=git_de("", "abc123 Fotos novas\n")) == fd.MSG_PENDENTES
    assert "commit + push" in fd.MSG_PENDENTES and "fotos/divulgacao" in fd.MSG_PENDENTES


def _bucket(cod, sufixo=""):
    return f"https://proj.supabase.co/storage/v1/object/public/divulgacao/{cod}{sufixo}.jpg"


def test_migrar_pages_ensaio_gera_arquivos_e_aplicar_troca_nas_acoes(tmp_path):
    mapa = {"AAA": {"url": _bucket("AAA", "-inteira"), "perfil": "une", "inteira": True},
            "BBB": {"url": _bucket("BBB"), "perfil": None},
            "CCC": {"url": f"{fd.BASE_PAGES}/CCC.jpg", "mini": f"{fd.BASE_PAGES}/CCC-mini.jpg", "pages": True},
            "DDD": {"url": "http://127.0.0.1:54321/storage/v1/object/public/divulgacao/DDD.jpg"}}
    assert fd.no_bucket(mapa) == ["AAA", "BBB", "DDD"]
    baixados, trocas = [], []

    def baixar(url):
        baixados.append(url)
        if "BBB" in url:
            raise OSError("404")
        return jpeg(720, 900)
    # ensaio: baixa do bucket (não do Instagram), gera os dois arquivos, não mexe no banco nem no mapa
    geradas, trocadas, falhas = fd.migrar_pages(mapa, codigos=["AAA", "BBB"], pasta=tmp_path, baixar=baixar, trocar=lambda *a: trocas.append(a))
    assert (geradas, trocadas, falhas) == (1, 0, [("BBB", "download: 404")])
    assert baixados == [_bucket("AAA", "-inteira"), _bucket("BBB")] and trocas == []
    assert (tmp_path / "AAA.jpg").exists() and (tmp_path / "AAA-mini.jpg").exists()
    assert mapa["AAA"]["url"] == _bucket("AAA", "-inteira") and "mini" not in mapa["AAA"]
    # aplicar: não gera nada (BBB, sem os dois arquivos, fica listado como não gerado, sem download);
    # AAA, que já tem os dois, ganha url + mini nas ações e no mapa
    geradas, trocadas, falhas = fd.migrar_pages(mapa, codigos=["AAA", "BBB"], aplicar=True, base_chave=("https://proj", "k"),
                                                pasta=tmp_path, baixar=baixar, trocar=lambda *a: trocas.append(a) or 3)
    assert (geradas, trocadas, falhas) == (0, 1, [("BBB", fd.MSG_NAO_GERADO)]) and len(baixados) == 2
    assert "rode sem --aplicar, commite e envie" in fd.MSG_NAO_GERADO and mapa["BBB"] == {"url": _bucket("BBB"), "perfil": None}
    assert trocas == [("https://proj", "k", _bucket("AAA", "-inteira"), f"{fd.BASE_PAGES}/AAA.jpg", f"{fd.BASE_PAGES}/AAA-mini.jpg")]
    assert mapa["AAA"] == {"url": f"{fd.BASE_PAGES}/AAA.jpg", "mini": f"{fd.BASE_PAGES}/AAA-mini.jpg", "perfil": "une", "inteira": True, "pages": True}
    assert fd.no_bucket(mapa) == ["BBB", "DDD"]


def _explode(msg):
    raise AssertionError(msg)


def test_migrar_pages_aplicar_exige_fotos_commitadas(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(fd, "MAPA", tmp_path / "mapa.json")
    monkeypatch.setattr(fd, "PASTA_PAGES", tmp_path / "fotos")
    (tmp_path / "mapa.json").write_text(json.dumps({"AAA": {"url": _bucket("AAA")}}), encoding="utf-8")
    monkeypatch.setattr(fd, "fotos_pendentes", lambda: fd.MSG_PENDENTES)
    monkeypatch.setattr(fd, "destino_storage", lambda: _explode("não devia chegar no banco"))
    monkeypatch.setattr(fd, "baixar", lambda url: _explode("não devia baixar"))
    assert fd.main(["migrar-pages", "--aplicar"]) == 1
    assert "ainda não foram commitadas" in capsys.readouterr().err
    assert json.loads((tmp_path / "mapa.json").read_text(encoding="utf-8"))["AAA"]["url"] == _bucket("AAA")
    # sem --aplicar é ensaio: gera os arquivos sem olhar o git nem o banco
    monkeypatch.setattr(fd, "baixar", lambda url: jpeg(720, 900))
    assert fd.main(["migrar-pages"]) == 0
    assert (tmp_path / "fotos" / "AAA-mini.jpg").exists()
    assert "ensaio" in capsys.readouterr().out
    assert json.loads((tmp_path / "mapa.json").read_text(encoding="utf-8"))["AAA"]["url"] == _bucket("AAA")


def test_migrar_pages_aplicar_so_troca_o_que_ja_existe_e_o_pages_serve(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(fd, "MAPA", tmp_path / "mapa.json")
    monkeypatch.setattr(fd, "PASTA_PAGES", tmp_path / "fotos")
    (tmp_path / "mapa.json").write_text(json.dumps({"AAA": {"url": _bucket("AAA")}, "BBB": {"url": _bucket("BBB")}}), encoding="utf-8")
    (tmp_path / "fotos").mkdir()
    for nome in ("AAA.jpg", "AAA-mini.jpg", "BBB.jpg"):  # BBB só tem a cheia: não está gerado
        (tmp_path / "fotos" / nome).write_bytes(b"x")
    monkeypatch.setattr(fd, "fotos_pendentes", lambda: None)
    monkeypatch.setattr(fd, "baixar", lambda url: _explode("com --aplicar não se gera nada"))
    trocas = []
    monkeypatch.setattr(fd, "destino_storage", lambda: ("https://proj", "k"))
    monkeypatch.setattr(fd, "trocar_nas_acoes", lambda *a: trocas.append(a) or 1)
    # o Pages ainda não serve a mini de AAA: para antes do banco
    pedidos = []
    monkeypatch.setattr(fd, "_head", lambda url: pedidos.append(url) or 404)
    assert fd.main(["migrar-pages", "--aplicar"]) == 1
    assert "o Pages ainda não serve 1 fotos (ex.: AAA)" in capsys.readouterr().err
    assert pedidos == [f"{fd.BASE_PAGES}/AAA-mini.jpg"] and trocas == []  # BBB nem é consultado: não está gerado
    assert json.loads((tmp_path / "mapa.json").read_text(encoding="utf-8"))["AAA"]["url"] == _bucket("AAA")
    # servido: troca AAA e lista BBB como ainda não gerado
    monkeypatch.setattr(fd, "_head", lambda url: 200)
    assert fd.main(["migrar-pages", "--aplicar"]) == 0
    saida = capsys.readouterr().out
    assert "0 geradas" in saida and "1 ações apontadas" in saida and "0 falhas" in saida
    assert "1 ainda não gerados: rode sem --aplicar, commite e envie (BBB)" in saida
    assert trocas == [("https://proj", "k", _bucket("AAA"), f"{fd.BASE_PAGES}/AAA.jpg", f"{fd.BASE_PAGES}/AAA-mini.jpg")]
    mapa = json.loads((tmp_path / "mapa.json").read_text(encoding="utf-8"))
    assert mapa["AAA"]["url"] == f"{fd.BASE_PAGES}/AAA.jpg" and mapa["BBB"]["url"] == _bucket("BBB")


def test_migracao_60_poe_a_mini_na_view_nas_funcoes_e_na_importacao():
    sql = (RAIZ / "supabase" / "migrations" / "20261009000060_foto_mini.sql").read_text(encoding="utf-8")
    assert "alter table acao add column foto_mini_url text" in sql
    assert sql.count("'foto_mini_url', a.foto_mini_url") == 2  # acao_completa_json e minhas_inscricoes
    assert "a.foto_mini_url\n  from acao a" in sql  # view: coluna nova no fim
    assert "it->'foto'->>'mini'" in sql and "foto_mini !~ re_https" in sql
    assert "foto_mini_url = case when excluded.foto_url is not null then excluded.foto_mini_url else acao.foto_mini_url end" in sql
    assert "create or replace function criar_acao" not in sql
    # hora_aproximada e turno_publico vêm da migração 50 (e a 51 é a de segurança): a 60 roda depois das duas e não as recria
    assert "alter table turno" not in sql and "create or replace view turno_publico" not in sql
    assert "hora_aproximada = aprox" in sql and "20261009000050" in sql and "20261009000051" in sql


def test_cards_do_app_usam_a_mini_e_a_pagina_a_cheia():
    src = (RAIZ / "app" / "index.html").read_text(encoding="utf-8")
    assert "const fotoCard=a=>a.foto.mini||a.foto.url;" in src
    assert "background-image:url('${esc(fotoCard(a))}')" in src
    assert "${imgFoto(a,true)}</div>${creditoFoto(a)}" in src


EMBED = ('<a class="Username" href="https://www.instagram.com/une/?utm_source=ig_embed"><span class="UsernameText">une</span></a>'
         '<img class="EmbeddedMediaImage" alt="Instagram post shared by &#064;une" src="https://cdn/v/a.jpg?stp=dst-jpg_e35_tt6&amp;x=1" '
         'srcset="https://cdn/v/a.jpg?stp=dst-jpg_e35_tt6&amp;x=1 1440w,https://cdn/v/a.jpg?stp=dst-jpg_e35_p1080x1080_tt6&amp;x=1 1080w,'
         'https://cdn/v/a.jpg?stp=dst-jpg_e35_p640x640_tt6&amp;x=1 640w,https://cdn/v/a.jpg?stp=c0.180.1440.1440a_dst-jpg_e35_s1080x1080_tt6&amp;x=1 1080w" />')


def test_embed_da_imagem_inteira_sem_recorte():
    # o srcset traz versões recortadas em quadrado (stp=c...); fica a maior inteira até 1080 px
    assert fd.do_embed(EMBED) == {"img": "https://cdn/v/a.jpg?stp=dst-jpg_e35_p1080x1080_tt6&x=1", "perfil": "une"}
    so_grande = '<img class="EmbeddedMediaImage" srcset="https://cdn/b.jpg?stp=dst-jpg_tt6 1365w" src="https://cdn/b.jpg">'
    assert fd.do_embed(so_grande)["img"] == "https://cdn/b.jpg?stp=dst-jpg_tt6"
    so_recorte = '<img class="EmbeddedMediaImage" src="https://cdn/c.jpg?stp=c0.1.2.2a_s640x640" srcset="https://cdn/c.jpg?stp=c0.1.2.2a_s640x640 640w">'
    assert fd.do_embed(so_recorte) == {"img": None, "perfil": None}
    assert fd.do_embed("<html></html>") == {"img": None, "perfil": None}


def test_previa_prefere_embed_e_cai_na_og(monkeypatch):
    paginas = {"https://www.instagram.com/p/AAA/embed/captioned/": EMBED,
               "https://www.instagram.com/p/BBB/embed/captioned/": "<html></html>",
               "https://www.instagram.com/p/BBB/": '<meta property="og:image" content="https://cdn/q.jpg"><meta property="og:url" content="https://www.instagram.com/org/p/BBB/">'}
    monkeypatch.setattr(fd, "ler_pagina", lambda url: paginas.get(url))
    assert fd.previa("AAA") == {"codigo": "AAA", "img": "https://cdn/v/a.jpg?stp=dst-jpg_e35_p1080x1080_tt6&x=1", "perfil": "une",
                                "url": None, "inteira": True}
    assert fd.previa("BBB") == {"codigo": "BBB", "img": "https://cdn/q.jpg", "url": "https://www.instagram.com/org/p/BBB/", "inteira": False}


def test_refazer_troca_so_as_recortadas_e_atualiza_as_acoes(tmp_path):
    mapa = {"AAA": {"url": "https://proj/storage/v1/object/public/divulgacao/AAA.jpg", "perfil": "une"},
            "BBB": {"url": "https://proj/storage/v1/object/public/divulgacao/BBB.jpg", "perfil": None, "inteira": True},
            "CCC": {"url": "https://proj/storage/v1/object/public/divulgacao/CCC.jpg", "perfil": None}}
    assert fd.recortadas(mapa) == ["AAA", "CCC"]
    trocas = []

    def ler(c):
        return {"codigo": c, "img": "https://cdn/i.jpg", "perfil": "une", "inteira": c == "AAA"}
    novas, falhas = fd.refazer(mapa, "https://proj", "k", ler=ler, pasta=tmp_path, baixar=lambda u: jpeg(1080, 1350),
                               subir=lambda b, k, nome, d: f"{b}/storage/v1/object/public/divulgacao/{nome}",
                               trocar=lambda b, k, velha, nova: trocas.append((velha, nova)) or 2, dormir=lambda s: None)
    assert novas == 1 and falhas == [("CCC", "sem imagem inteira")]
    assert mapa["AAA"] == {"url": "https://proj/storage/v1/object/public/divulgacao/AAA-inteira.jpg", "perfil": "une", "inteira": True}
    assert mapa["CCC"] == {"url": "https://proj/storage/v1/object/public/divulgacao/CCC.jpg", "perfil": None}
    assert trocas == [("https://proj/storage/v1/object/public/divulgacao/AAA.jpg", "https://proj/storage/v1/object/public/divulgacao/AAA-inteira.jpg")]
