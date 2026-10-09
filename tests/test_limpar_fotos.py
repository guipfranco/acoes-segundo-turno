import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import limpar_fotos as lf  # noqa: E402

AGORA = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)
BASE = "https://proj.supabase.co/storage/v1/object/public/fotos-acoes/"


def test_nome_da_url_so_do_bucket():
    assert lf.nome_da_url(BASE + "uid-1/a.jpg") == "uid-1/a.jpg"
    assert lf.nome_da_url(BASE + "uid-1/a%20b.jpg?width=400") == "uid-1/a b.jpg"
    assert lf.nome_da_url("http://127.0.0.1:54321/storage/v1/render/image/public/fotos-acoes/uid/x.webp") == "uid/x.webp"
    assert lf.nome_da_url("https://proj.supabase.co/storage/v1/object/public/divulgacao/AAA.jpg") is None  # outro bucket
    assert lf.nome_da_url("https://commons.wikimedia.org/wiki/Special:Redirect/file/X.svg") is None
    assert lf.nome_da_url(None) is None


def test_selecionar_apaga_so_sem_referencia_e_com_mais_de_24h():
    objetos = [
        {"name": "uid-1/usada.jpg", "created_at": "2026-10-01T10:00:00.000Z"},        # referenciada por ação
        {"name": "uid-2/logo.png", "created_at": "2026-10-01T10:00:00.000Z"},         # referenciada por organização
        {"name": "uid-1/orfa.jpg", "created_at": "2026-10-08T11:00:00.000Z"},         # 25 h: apaga
        {"name": "uid-3/recente.jpg", "created_at": "2026-10-08T13:00:00.000Z"},      # 23 h: cadastro em andamento, fica
        {"name": "uid-4/sem-data.jpg", "created_at": None},                           # sem data: fica
        {"name": "uid-5/antiga.jpg", "created_at": "2026-09-01T00:00:00+00:00"},      # apaga
    ]
    urls = {BASE + "uid-1/usada.jpg?v=2", BASE + "uid-2/logo.png",
            "https://proj.supabase.co/storage/v1/object/public/divulgacao/AAA.jpg"}  # outro bucket não protege nada daqui
    assert lf.selecionar(objetos, urls, agora=AGORA) == ["uid-1/orfa.jpg", "uid-5/antiga.jpg"]
    assert lf.selecionar(objetos, urls, agora=AGORA, horas=48) == ["uid-5/antiga.jpg"]
    assert lf.selecionar([], set(), agora=AGORA) == []


def test_listar_objetos_entra_nas_pastas_e_pagina():
    pedidos = []

    def pedir(metodo, url, chave, corpo=None):
        pedidos.append((metodo, url.rsplit("/", 1)[1], corpo["prefix"], corpo["offset"]))
        if corpo["prefix"] == "":
            return [{"name": "uid-1", "id": None}, {"name": "solta.jpg", "id": "x", "created_at": "2026-10-01T00:00:00Z"}]
        if corpo["offset"] == 0:
            return [{"name": f"f{i}.jpg", "id": str(i), "created_at": "2026-10-01T00:00:00Z"} for i in range(lf.PAGINA)]
        return [{"name": "ultima.jpg", "id": "u", "created_at": "2026-10-01T00:00:00Z"}]
    objetos = lf.listar_objetos("https://proj", "k", pedir=pedir)
    nomes = [o["name"] for o in objetos]
    assert nomes[0] == "uid-1/f0.jpg" and nomes[-2] == "uid-1/ultima.jpg" and nomes[-1] == "solta.jpg"
    assert len(nomes) == lf.PAGINA + 2
    assert pedidos[0] == ("POST", "fotos-acoes", "", 0) and pedidos[1][2:] == ("uid-1", 0) and pedidos[2][2:] == ("uid-1", lf.PAGINA)


def test_apagar_em_lotes_e_urls_referenciadas():
    pedidos = []

    def pedir(metodo, url, chave, corpo=None):
        pedidos.append((metodo, url, corpo))
        if metodo == "GET":
            return [{"foto_url": BASE + "a/1.jpg"}, {"foto_url": None}]
        return None
    assert lf.urls_referenciadas("https://proj", "k", pedir=pedir) == {BASE + "a/1.jpg"}
    assert [u for _, u, _ in pedidos] == ["https://proj/rest/v1/acao?select=foto_url&foto_url=like.*fotos-acoes*&limit=100000",
                                          "https://proj/rest/v1/organizacao?select=foto_url&foto_url=like.*fotos-acoes*&limit=100000"]
    pedidos.clear()
    assert lf.apagar("https://proj", "k", [f"n{i}" for i in range(250)], pedir=pedir) == 250
    assert [(m, u, len(c["prefixes"])) for m, u, c in pedidos] == [("DELETE", "https://proj/storage/v1/object/fotos-acoes", n) for n in (100, 100, 50)]


def test_ensaio_nao_apaga(monkeypatch, capsys):
    monkeypatch.setattr(lf.fd, "destino_storage", lambda: ("https://proj", "k"))
    monkeypatch.setattr(lf, "listar_objetos", lambda b, c, bucket: [{"name": "u/orfa.jpg", "created_at": "2026-01-01T00:00:00Z"}])
    monkeypatch.setattr(lf, "urls_referenciadas", lambda b, c: set())
    apagados = []
    monkeypatch.setattr(lf, "apagar", lambda b, c, nomes, bucket: apagados.extend(nomes) or len(nomes))
    assert lf.main([]) == 0 and apagados == []
    assert "u/orfa.jpg" in capsys.readouterr().out
    assert lf.main(["--aplicar"]) == 0 and apagados == ["u/orfa.jpg"]
