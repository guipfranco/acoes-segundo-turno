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
    assert fd.foto_do_item(com_org, mapa) == {"url": "https://s/divulgacao/AAA.jpg", "credito": "Divulgação de @ptdiadema no Instagram",
                                              "pagina": "https://www.instagram.com/p/AAA/"}
    assert fd.foto_do_item(sem_org, mapa)["credito"] == "Divulgação original no Instagram"
    assert fd.foto_do_item({"link": "https://www.instagram.com/p/BBB/"}, mapa) is None
    assert fd.foto_do_item({"link": ""}, mapa) is None
    itens = pa.com_foto([dict(com_org), {"link": "", "organizacao": None}], mapa)
    assert itens[0]["foto"]["url"].endswith("AAA.jpg") and itens[1]["foto"] is None


def test_pendentes_sem_repetir_e_sem_o_que_ja_tem():
    itens = [{"link": "https://www.instagram.com/p/AAA/"}, {"link": "https://www.instagram.com/reel/BBB/"},
             {"link": "https://www.instagram.com/p/AAA/?x=1"}, {"link": "https://x.com/q"}, {"link": "https://www.instagram.com/p/CCC/"}]
    assert fd.pendentes(itens, {"CCC": {"url": "u"}}) == ["AAA", "BBB"]


def test_reduzir_limita_largura_e_gera_jpeg():
    from PIL import Image
    out = fd.reduzir(jpeg(1440, 1800))
    im = Image.open(io.BytesIO(out))
    assert im.format == "JPEG" and im.size == (720, 900)
    assert Image.open(io.BytesIO(fd.reduzir(jpeg(400, 500)))).size == (400, 500)


def test_processar_coleta_sobe_e_registra(tmp_path):
    enviados = {}

    def subir(base, chave, nome, dados):
        enviados[nome] = len(dados)
        return f"{base}/storage/v1/object/public/divulgacao/{nome}"

    def baixar(url):
        if "quebrada" in url:
            raise OSError("404")
        return jpeg(1000, 1000)

    coleta = [{"codigo": "AAA", "img": "https://cdn/a.jpg", "url": "https://www.instagram.com/ptdiadema/p/AAA/"},
              {"codigo": "BBB", "img": "https://cdn/quebrada.jpg", "url": ""}, {"codigo": "CCC", "img": None}]
    mapa = {}
    novas, falhas = fd.processar_coleta(coleta, mapa, "https://proj", "k", pasta=tmp_path, baixar=baixar, subir=subir)
    assert novas == 1 and [f[0] for f in falhas] == ["BBB", "CCC"]
    assert mapa == {"AAA": {"url": "https://proj/storage/v1/object/public/divulgacao/AAA.jpg", "perfil": "ptdiadema"}}
    assert (tmp_path / "AAA.jpg").exists() and "AAA.jpg" in enviados


def test_migracao_cria_bucket_publico_e_importa_foto_sem_apagar():
    sql = (RAIZ / "supabase" / "migrations" / "20261009000003_foto_divulgacao.sql").read_text(encoding="utf-8")
    assert "insert into storage.buckets" in sql and "'divulgacao', 'divulgacao', true" in sql
    assert "foto_url = coalesce(excluded.foto_url, acao.foto_url)" in sql
    assert "nullif(it->'foto'->>'url', '')" in sql
