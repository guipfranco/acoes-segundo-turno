"""Regras do banco: só rodam com SUPABASE_URL, SUPABASE_ANON_KEY e SUPABASE_SERVICE_KEY no ambiente
(banco local do `npx supabase start`). Cada teste cria seus próprios usuários e ação."""
import urllib.parse
import uuid
import pytest

import supabase_cliente as sb

pytestmark = pytest.mark.skipif(not (sb.ANON and sb.SERVICE), reason="Supabase local não configurado")


@pytest.fixture
def cenario():
    tag = uuid.uuid4().hex[:8]
    org_id = sb.criar_usuario(f"org-{tag}@t.local", "Org Teste")
    a_id = sb.criar_usuario(f"a-{tag}@t.local", "Pessoa A")
    b_id = sb.criar_usuario(f"b-{tag}@t.local", "Pessoa B")
    r = sb.admin("PATCH", f"/rest/v1/pessoa?id=eq.{org_id}", {"papel": "organizador", "telefone": "(11) 90000-0000"})
    assert r.status == 200, r.corpo
    r = sb.admin("POST", "/rest/v1/acao", {"titulo": f"Teste {tag}", "tipo": "panfletagem", "organizador": org_id,
        "lugar_nome": "Praça", "bairro": "Centro", "cidade": "São Paulo", "lat": -23.5, "lon": -46.6,
        "detalhe": "camisa vermelha", "contato_tipo": "link_grupo", "contato_link": "https://chat.whatsapp.com/x", "status": "publicada"})
    assert r.status == 201, r.corpo
    acao = r.corpo[0]["id"]
    r = sb.admin("POST", "/rest/v1/turno", {"acao": acao, "inicio": "2099-01-01T09:00:00", "fim": "2099-01-01T12:00:00"})
    assert r.status == 201, r.corpo
    turno = r.corpo[0]["id"]
    return {"org": org_id, "a": a_id, "b": b_id, "acao": acao, "turno": turno,
            "jwt_a": sb.entrar(f"a-{tag}@t.local"), "jwt_b": sb.entrar(f"b-{tag}@t.local"), "jwt_org": sb.entrar(f"org-{tag}@t.local")}


def test_anon_ve_so_a_view_publica_sem_detalhe(cenario):
    r = sb.chamar("GET", f"/rest/v1/acao_publica?id=eq.{cenario['acao']}")
    assert r.status == 200 and len(r.corpo) == 1
    assert "detalhe" not in r.corpo[0] and "contato_link" not in r.corpo[0]
    assert r.corpo[0]["organizador_nome"] == "Org Teste"
    r = sb.chamar("GET", f"/rest/v1/acao?id=eq.{cenario['acao']}")
    assert r.status == 200 and r.corpo == []  # RLS: tabela vazia para anon
    r = sb.chamar("GET", "/rest/v1/pessoa")
    assert r.status == 200 and r.corpo == []


def test_pessoa_ve_so_a_si_e_nao_muda_papel(cenario):
    r = sb.chamar("GET", "/rest/v1/pessoa", jwt=cenario["jwt_a"])
    assert [p["id"] for p in r.corpo] == [cenario["a"]]
    r = sb.chamar("PATCH", f"/rest/v1/pessoa?id=eq.{cenario['a']}", {"papel": "moderador"}, jwt=cenario["jwt_a"])
    assert r.status >= 400
    r = sb.chamar("GET", "/rest/v1/pessoa", jwt=cenario["jwt_a"])
    assert r.corpo[0]["papel"] == "participante"


def test_inscrever_exige_entrar_e_telefone_e_devolve_combinado(cenario):
    t = cenario["turno"]
    assert sb.rpc("inscrever", {"turno_id": t}).corpo["message"] == "precisa_entrar"
    assert sb.rpc("inscrever", {"turno_id": t}, jwt=cenario["jwt_a"]).corpo["message"] == "sem_telefone"
    assert sb.rpc("salvar_telefone", {"telefone": "123"}, jwt=cenario["jwt_a"]).corpo["message"] == "telefone_invalido"
    r = sb.rpc("salvar_telefone", {"telefone": "11988887777"}, jwt=cenario["jwt_a"])
    assert r.status == 200 and r.corpo["telefone"] == "(11) 98888-7777"
    antes = sb.rpc("acao_para_mim", {"acao_id": cenario["acao"]}, jwt=cenario["jwt_a"]).corpo
    assert antes == {"inscrita": [], "combinado": None}
    r = sb.rpc("inscrever", {"turno_id": t}, jwt=cenario["jwt_a"])
    assert r.status == 200, r.corpo
    assert r.corpo["combinado"] == {"detalhe": "camisa vermelha", "contato": {"tipo": "link_grupo", "whatsapp": None, "link": "https://chat.whatsapp.com/x"}}
    depois = sb.rpc("acao_para_mim", {"acao_id": cenario["acao"]}, jwt=cenario["jwt_a"]).corpo
    assert depois["inscrita"] == [t] and depois["combinado"]["detalhe"] == "camisa vermelha"
    assert sb.chamar("GET", f"/rest/v1/turno_publico?id=eq.{t}").corpo[0]["vao"] == 1
    # repetir não duplica
    sb.rpc("inscrever", {"turno_id": t}, jwt=cenario["jwt_a"])
    assert sb.chamar("GET", f"/rest/v1/turno_publico?id=eq.{t}").corpo[0]["vao"] == 1
    # B não vê a inscrição de A nem o combinado
    assert sb.chamar("GET", "/rest/v1/inscricao", jwt=cenario["jwt_b"]).corpo == []
    assert sb.rpc("acao_para_mim", {"acao_id": cenario["acao"]}, jwt=cenario["jwt_b"]).corpo["combinado"] is None
    # minhas inscrições
    minhas = sb.rpc("minhas_inscricoes", {}, jwt=cenario["jwt_a"]).corpo
    assert len(minhas) == 1 and minhas[0]["turno"]["id"] == t and "detalhe" not in minhas[0]["acao"]
    # desistir e reinscrever
    assert sb.rpc("desistir", {"turno_id": t}, jwt=cenario["jwt_a"]).status in (200, 204)
    assert sb.chamar("GET", f"/rest/v1/turno_publico?id=eq.{t}").corpo[0]["vao"] == 0
    assert sb.rpc("acao_para_mim", {"acao_id": cenario["acao"]}, jwt=cenario["jwt_a"]).corpo["combinado"] is None
    assert sb.rpc("inscrever", {"turno_id": t}, jwt=cenario["jwt_a"]).status == 200
    assert sb.chamar("GET", f"/rest/v1/turno_publico?id=eq.{t}").corpo[0]["vao"] == 1


def test_lotado_bloqueada_passado_e_nao_publicada(cenario):
    t, a = cenario["turno"], cenario["acao"]
    sb.rpc("salvar_telefone", {"telefone": "11988887777"}, jwt=cenario["jwt_a"])
    sb.rpc("salvar_telefone", {"telefone": "11977776666"}, jwt=cenario["jwt_b"])
    sb.admin("PATCH", f"/rest/v1/turno?id=eq.{t}", {"lotacao": 1})
    assert sb.rpc("inscrever", {"turno_id": t}, jwt=cenario["jwt_a"]).status == 200
    assert sb.rpc("inscrever", {"turno_id": t}, jwt=cenario["jwt_b"]).corpo["message"] == "lotado"
    sb.admin("PATCH", f"/rest/v1/pessoa?id=eq.{cenario['b']}", {"bloqueada": True})
    assert sb.rpc("inscrever", {"turno_id": t}, jwt=cenario["jwt_b"]).corpo["message"] == "bloqueada"
    r = sb.admin("POST", "/rest/v1/turno", {"acao": a, "inicio": "2020-01-01T09:00:00", "fim": "2020-01-01T12:00:00"})
    assert sb.rpc("inscrever", {"turno_id": r.corpo[0]["id"]}, jwt=cenario["jwt_a"]).corpo["message"] == "turno_passado"
    sb.admin("PATCH", f"/rest/v1/acao?id=eq.{a}", {"status": "rascunho"})
    assert sb.rpc("inscrever", {"turno_id": t}, jwt=cenario["jwt_a"]).corpo["message"] == "nao_publicada"
    # despublicada: inscrito deixa de ver o combinado; organizador continua vendo
    assert sb.rpc("acao_para_mim", {"acao_id": a}, jwt=cenario["jwt_a"]).corpo["combinado"] is None
    assert sb.rpc("acao_para_mim", {"acao_id": a}, jwt=cenario["jwt_org"]).corpo["combinado"]["detalhe"] == "camisa vermelha"
    assert sb.chamar("GET", f"/rest/v1/acao_publica?id=eq.{a}").corpo == []


def test_organizador_ve_a_propria_acao_na_tabela_mas_nao_as_dos_outros(cenario):
    r = sb.chamar("GET", "/rest/v1/acao?select=id", jwt=cenario["jwt_org"])
    assert [x["id"] for x in r.corpo] == [cenario["acao"]]
    assert sb.chamar("GET", "/rest/v1/acao?select=id", jwt=cenario["jwt_a"]).corpo == []
    # ninguém cria ação pela API neste plano
    r = sb.chamar("POST", "/rest/v1/acao", {"titulo": "x", "tipo": "outro", "organizador": cenario["org"], "online": True}, jwt=cenario["jwt_org"])
    assert r.status >= 400


VIEWS = ["acao_publica", "turno_publico", "organizacao_publica", "configuracao_publica"]


def _vaquinha():
    return sb.chamar("GET", "/rest/v1/configuracao_publica?chave=eq.vaquinha").corpo


def test_views_publicas_nao_aceitam_escrita(cenario):
    antes = _vaquinha()
    for jwt in (None, cenario["jwt_a"]):
        for v in VIEWS:
            filtro = "chave=eq.vaquinha" if v == "configuracao_publica" else "id=gt.0"
            corpo = {"valor": "https://golpe.example"} if v == "configuracao_publica" else {"nome": "x"} if v == "organizacao_publica" else {"titulo": "x"}
            assert sb.chamar("PATCH", f"/rest/v1/{v}?{filtro}", corpo, jwt=jwt).status >= 400, (v, "PATCH")
            assert sb.chamar("POST", f"/rest/v1/{v}", corpo, jwt=jwt).status >= 400, (v, "POST")
            assert sb.chamar("DELETE", f"/rest/v1/{v}?{filtro}", jwt=jwt).status >= 400, (v, "DELETE")
    assert _vaquinha() == antes
    assert sb.chamar("GET", f"/rest/v1/acao_publica?id=eq.{cenario['acao']}").corpo[0]["titulo"].startswith("Teste ")


def test_escrita_direta_nas_tabelas_e_negada(cenario):
    sb.rpc("salvar_telefone", {"telefone": "11988887777"}, jwt=cenario["jwt_a"])
    r = sb.chamar("POST", "/rest/v1/inscricao", {"pessoa": cenario["a"], "turno": cenario["turno"]}, jwt=cenario["jwt_a"])
    assert r.status >= 400
    assert sb.chamar("PATCH", f"/rest/v1/turno?id=eq.{cenario['turno']}", {"lotacao": 99}, jwt=cenario["jwt_org"]).status >= 400
    assert sb.chamar("PATCH", f"/rest/v1/pessoa?id=eq.{cenario['a']}", {"bloqueada": True}, jwt=cenario["jwt_a"]).status >= 400
    assert sb.chamar("GET", f"/rest/v1/turno_publico?id=eq.{cenario['turno']}").corpo[0]["vao"] == 0


def test_anon_nao_chama_rpcs_de_sessao(cenario):
    assert sb.rpc("salvar_telefone", {"telefone": "11988887777"}).status in (401, 403)
    assert sb.rpc("desistir", {"turno_id": cenario["turno"]}).status in (401, 403)
    assert sb.rpc("minhas_inscricoes", {}).status in (401, 403)


def _item(fonte_id, **extra):
    base = {"fonte_id": fonte_id, "titulo": f"Importada {fonte_id}", "tipo": "panfletagem", "descricao": "Fonte: teste.",
            "organizacao": "Org Importada Teste", "organizacao_tipo": "movimento", "online": False, "lugar_nome": "Centro",
            "bairro": "", "cidade": "Diadema", "lat": -23.68, "lon": -46.62, "lugar_aproximado": True,
            "link": "https://www.instagram.com/p/x/", "inicio": "2099-02-01T09:00", "fim": "2099-02-01T11:00"}
    base.update(extra)
    return base


def test_importar_acoes_e_idempotente_e_encerra_o_que_sumiu(cenario):
    fonte = "teste-" + uuid.uuid4().hex[:8]
    r = sb.rpc("importar_acoes", {"fonte": fonte, "itens": [_item("a"), _item("b", link="", online=True, lat=None, lon=None, lugar_nome=None)]}, jwt=sb.SERVICE)
    assert r.status == 200, r.corpo
    assert r.corpo == {"inseridas": 2, "atualizadas": 0, "encerradas": 0}
    pub = sb.chamar("GET", f"/rest/v1/acao_publica?fonte=eq.{fonte}&order=titulo").corpo
    assert [a["titulo"] for a in pub] == ["Importada a", "Importada b"]
    a, b = pub
    assert a["organizador_nome"] == "Agenda Bora Lula" and a["lugar_aproximado"] is True
    assert a["contato_tipo"] == "divulgacao" and a["link_divulgacao"] == "https://www.instagram.com/p/x/"
    assert b["online"] is True and b["contato_tipo"] == "organizador_chama" and b["link_divulgacao"] is None
    assert "contato_link" not in a
    org = sb.chamar("GET", "/rest/v1/organizacao_publica?nome=eq.Org%20Importada%20Teste").corpo
    assert len(org) == 1 and org[0]["tipo"] == "movimento" and org[0]["verificada"] is False and org[0]["foto_url"] is None
    turnos = sb.chamar("GET", f"/rest/v1/turno_publico?acao=eq.{a['id']}").corpo
    assert [t["inicio"] for t in turnos] == ["2099-02-01T09:00:00"]

    # reimporta só "a" com horário novo: "a" atualiza no lugar (mesmo turno), "b" encerra
    r = sb.rpc("importar_acoes", {"fonte": fonte, "itens": [_item("a", inicio="2099-02-01T10:00", fim="2099-02-01T12:00")]}, jwt=sb.SERVICE)
    assert r.corpo == {"inseridas": 0, "atualizadas": 1, "encerradas": 1}
    turnos2 = sb.chamar("GET", f"/rest/v1/turno_publico?acao=eq.{a['id']}").corpo
    assert [(t["id"], t["inicio"]) for t in turnos2] == [(turnos[0]["id"], "2099-02-01T10:00:00")]
    assert [x["titulo"] for x in sb.chamar("GET", f"/rest/v1/acao_publica?fonte=eq.{fonte}").corpo] == ["Importada a"]

    # "b" volta ao feed: republica sem duplicar
    r = sb.rpc("importar_acoes", {"fonte": fonte, "itens": [_item("a"), _item("b")]}, jwt=sb.SERVICE)
    assert r.corpo == {"inseridas": 0, "atualizadas": 2, "encerradas": 0}
    assert len(sb.chamar("GET", f"/rest/v1/acao_publica?fonte=eq.{fonte}").corpo) == 2

    # recusa do moderador é respeitada numa reimportação
    assert sb.admin("PATCH", f"/rest/v1/acao?id=eq.{b['id']}", {"status": "recusada", "motivo_recusa": "x"}).status == 200
    sb.rpc("importar_acoes", {"fonte": fonte, "itens": [_item("a"), _item("b")]}, jwt=sb.SERVICE)
    assert sb.admin("GET", f"/rest/v1/acao?id=eq.{b['id']}&select=status").corpo == [{"status": "recusada"}]


def test_importar_acoes_so_pela_chave_de_servico_e_divulgacao_nao_tem_inscricao(cenario):
    fonte = "teste-" + uuid.uuid4().hex[:8]
    assert sb.rpc("importar_acoes", {"fonte": fonte, "itens": [_item("a")]}).status >= 400
    assert sb.rpc("importar_acoes", {"fonte": fonte, "itens": [_item("a")]}, jwt=cenario["jwt_org"]).status >= 400
    assert sb.chamar("GET", f"/rest/v1/acao_publica?fonte=eq.{fonte}").corpo == []
    r = sb.rpc("importar_acoes", {"fonte": fonte, "itens": [_item("a")]}, jwt=sb.SERVICE)
    assert r.status == 200, r.corpo
    acao = sb.chamar("GET", f"/rest/v1/acao_publica?fonte=eq.{fonte}").corpo[0]["id"]
    turno = sb.chamar("GET", f"/rest/v1/turno_publico?acao=eq.{acao}").corpo[0]["id"]
    sb.rpc("salvar_telefone", {"telefone": "11988887777"}, jwt=cenario["jwt_a"])
    assert sb.rpc("inscrever", {"turno_id": turno}, jwt=cenario["jwt_a"]).corpo["message"] == "sem_inscricao"


def test_importar_acoes_grava_logo_da_organizacao_sem_apagar_o_que_ja_tem(cenario):
    fonte = "teste-" + uuid.uuid4().hex[:8]
    nome = "Org Logo " + fonte
    logo = {"url": "https://commons.wikimedia.org/wiki/Special:Redirect/file/X.svg?width=400", "credito": "X, via Wikimedia Commons",
            "pagina": "https://commons.wikimedia.org/wiki/File:X.svg"}
    r = sb.rpc("importar_acoes", {"fonte": fonte, "itens": [_item("a", organizacao=nome, organizacao_foto=logo, lugar_aproximado=False)]}, jwt=sb.SERVICE)
    assert r.status == 200, r.corpo
    org = sb.chamar("GET", f"/rest/v1/organizacao_publica?nome=eq.{urllib.parse.quote(nome)}").corpo[0]
    assert org["foto_url"] == logo["url"] and org["foto_credito"] == logo["credito"] and org["foto_pagina"] == logo["pagina"]
    acao = sb.chamar("GET", f"/rest/v1/acao_publica?fonte=eq.{fonte}").corpo[0]
    assert acao["lugar_aproximado"] is False
    # reimportar sem logo (ou com outro) não apaga nem troca o que já está gravado
    sb.rpc("importar_acoes", {"fonte": fonte, "itens": [_item("a", organizacao=nome, organizacao_foto=None)]}, jwt=sb.SERVICE)
    sb.rpc("importar_acoes", {"fonte": fonte, "itens": [_item("a", organizacao=nome, organizacao_foto=dict(logo, url="https://outro"))]}, jwt=sb.SERVICE)
    org = sb.chamar("GET", f"/rest/v1/organizacao_publica?nome=eq.{urllib.parse.quote(nome)}").corpo[0]
    assert org["foto_url"] == logo["url"]


def test_importar_acoes_grava_foto_da_divulgacao_e_nao_apaga_sem_foto(cenario):
    fonte = "teste-" + uuid.uuid4().hex[:8]
    foto = {"url": "http://127.0.0.1:54321/storage/v1/object/public/divulgacao/X.jpg", "credito": "Divulgação original no Instagram",
            "pagina": "https://www.instagram.com/p/x/"}
    assert sb.rpc("importar_acoes", {"fonte": fonte, "itens": [_item("a", foto=foto)]}, jwt=sb.SERVICE).status == 200
    a = sb.chamar("GET", f"/rest/v1/acao_publica?fonte=eq.{fonte}").corpo[0]
    assert (a["foto_url"], a["foto_credito"], a["foto_pagina"]) == (foto["url"], foto["credito"], foto["pagina"])
    sb.rpc("importar_acoes", {"fonte": fonte, "itens": [_item("a", foto=None)]}, jwt=sb.SERVICE)
    assert sb.chamar("GET", f"/rest/v1/acao_publica?fonte=eq.{fonte}").corpo[0]["foto_url"] == foto["url"]
    bucket = sb.admin("GET", "/storage/v1/bucket/divulgacao").corpo
    assert bucket["public"] is True
