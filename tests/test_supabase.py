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
    # a desistência não some: fica no histórico, marcada
    minhas = sb.rpc("minhas_inscricoes", {}, jwt=cenario["jwt_a"]).corpo
    assert [m["desistiu"] for m in minhas if m["turno"]["id"] == t] == [True]
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


def test_importar_acoes_so_pela_chave_de_servico_e_eu_vou_na_divulgacao_sem_telefone(cenario):
    fonte = "teste-" + uuid.uuid4().hex[:8]
    assert sb.rpc("importar_acoes", {"fonte": fonte, "itens": [_item("a")]}).status >= 400
    assert sb.rpc("importar_acoes", {"fonte": fonte, "itens": [_item("a")]}, jwt=cenario["jwt_org"]).status >= 400
    assert sb.chamar("GET", f"/rest/v1/acao_publica?fonte=eq.{fonte}").corpo == []
    r = sb.rpc("importar_acoes", {"fonte": fonte, "itens": [_item("a")]}, jwt=sb.SERVICE)
    assert r.status == 200, r.corpo
    acao = sb.chamar("GET", f"/rest/v1/acao_publica?fonte=eq.{fonte}").corpo[0]["id"]
    turno = sb.chamar("GET", f"/rest/v1/turno_publico?acao=eq.{acao}").corpo[0]["id"]
    # "Eu vou!" na divulgação só marca presença: não pede telefone e aparece em Minhas inscrições
    sb.criar_usuario(f"semtel-{fonte}@t.local", "Sem Telefone")
    jwt = sb.entrar(f"semtel-{fonte}@t.local")
    r = sb.rpc("inscrever", {"turno_id": turno}, jwt=jwt)
    assert r.status == 200, r.corpo
    minhas = sb.rpc("minhas_inscricoes", {}, jwt=jwt).corpo
    assert [m["turno"]["id"] for m in minhas] == [turno]
    assert minhas[0]["acao"]["fonte"] == fonte and minhas[0]["acao"]["link_divulgacao"]
    assert sb.chamar("GET", f"/rest/v1/turno_publico?id=eq.{turno}").corpo[0]["vao"] == 1


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
    assert a["foto_mini_url"] is None  # foto do bucket, sem mini
    sb.rpc("importar_acoes", {"fonte": fonte, "itens": [_item("a", foto=None)]}, jwt=sb.SERVICE)
    assert sb.chamar("GET", f"/rest/v1/acao_publica?fonte=eq.{fonte}").corpo[0]["foto_url"] == foto["url"]
    bucket = sb.admin("GET", "/storage/v1/bucket/divulgacao").corpo
    assert bucket["public"] is True


def test_importar_acoes_grava_a_mini_do_pages_e_so_a_troca_junto_com_a_foto(cenario):
    fonte = "teste-" + uuid.uuid4().hex[:8]
    base = "https://guipfranco.github.io/acoes-segundo-turno/fotos/divulgacao"
    foto = {"url": f"{base}/X.jpg", "mini": f"{base}/X-mini.jpg", "credito": "Divulgação original no Instagram", "pagina": "https://www.instagram.com/p/x/"}
    r = sb.rpc("importar_acoes", {"fonte": fonte, "itens": [_item("a", foto=foto), _item("b", foto=dict(foto, mini="javascript:alert(1)"))]}, jwt=sb.SERVICE)
    assert r.status == 200, r.corpo
    pub = {x["titulo"]: x for x in sb.chamar("GET", f"/rest/v1/acao_publica?fonte=eq.{fonte}").corpo}
    assert (pub["Importada a"]["foto_url"], pub["Importada a"]["foto_mini_url"]) == (foto["url"], foto["mini"])
    assert pub["Importada b"]["foto_url"] == foto["url"] and pub["Importada b"]["foto_mini_url"] is None  # mini que não é https cai
    # item sem foto não apaga nem a foto nem a mini
    sb.rpc("importar_acoes", {"fonte": fonte, "itens": [_item("a", foto=None), _item("b")]}, jwt=sb.SERVICE)
    a = sb.chamar("GET", f"/rest/v1/acao_publica?fonte=eq.{fonte}&titulo=eq.Importada%20a").corpo[0]
    assert (a["foto_url"], a["foto_mini_url"]) == (foto["url"], foto["mini"])
    # foto nova sobrescreve a mini (inclusive para null, se vier sem)
    nova = {"url": f"{base}/Y.jpg", "credito": "x", "pagina": "https://www.instagram.com/p/y/"}
    sb.rpc("importar_acoes", {"fonte": fonte, "itens": [_item("a", foto=nova), _item("b", foto=dict(nova, mini=f"{base}/Y-mini.jpg"))]}, jwt=sb.SERVICE)
    pub = {x["titulo"]: x for x in sb.chamar("GET", f"/rest/v1/acao_publica?fonte=eq.{fonte}").corpo}
    assert (pub["Importada a"]["foto_url"], pub["Importada a"]["foto_mini_url"]) == (nova["url"], None)
    assert pub["Importada b"]["foto_mini_url"] == f"{base}/Y-mini.jpg"
    # a mini também sai em Minhas inscrições e na ação completa (minhas_acoes / fila)
    sb.criar_usuario(f"mini-{fonte}@t.local", "Mini")
    jwt = sb.entrar(f"mini-{fonte}@t.local")
    turno = sb.chamar("GET", f"/rest/v1/turno_publico?acao=eq.{pub['Importada b']['id']}").corpo[0]["id"]
    assert sb.rpc("inscrever", {"turno_id": turno}, jwt=jwt).status == 200
    assert sb.rpc("minhas_inscricoes", {}, jwt=jwt).corpo[0]["acao"]["foto_mini_url"] == f"{base}/Y-mini.jpg"
    # a coluna nova só está na view pública e na tabela; criar_acao segue sem mini
    assert sb.admin("GET", f"/rest/v1/acao?id=eq.{pub['Importada b']['id']}&select=foto_mini_url").corpo == [{"foto_mini_url": f"{base}/Y-mini.jpg"}]


# imagem servida pelo próprio Storage da pilha local (a única que criar_acao aceita desde a migração 51)
FOTO_BUCKET = f"{sb.URL}/storage/v1/object/public/fotos-acoes/teste/arte.jpg"


def _nova(**extra):
    base = {"titulo": "Criada pelo app", "tipo": "panfletagem", "descricao": "teste", "online": False, "lugar_nome": "Praça",
            "bairro": "Centro", "cidade": "São Paulo", "lat": -23.5, "lon": -46.6, "foto": FOTO_BUCKET,
            "turnos": [{"inicio": "2099-03-01T09:00", "fim": "2099-03-01T11:00"}]}
    base.update(extra)
    return base


def test_criar_acao_nasce_em_analise_e_so_moderador_aprova(cenario):
    assert sb.rpc("criar_acao", {"dados": _nova()}).status >= 400  # anon não chama
    assert sb.rpc("criar_acao", {"dados": _nova()}, jwt=cenario["jwt_b"]).corpo["message"] == "sem_telefone"
    sb.rpc("salvar_telefone", {"telefone": "11977776666"}, jwt=cenario["jwt_b"])
    assert sb.rpc("criar_acao", {"dados": _nova(grupo="https://golpe.com")}, jwt=cenario["jwt_b"]).corpo["message"] == "grupo_invalido"
    assert sb.rpc("criar_acao", {"dados": _nova(foto="")}, jwt=cenario["jwt_b"]).corpo["message"] == "sem_foto"
    assert sb.rpc("criar_acao", {"dados": _nova(foto="javascript:alert(1)")}, jwt=cenario["jwt_b"]).corpo["message"] == "sem_foto"
    assert sb.rpc("criar_acao", {"dados": _nova(turnos=[{"inicio": "2000-01-01T09:00", "fim": "2000-01-01T10:00"}])},
                  jwt=cenario["jwt_b"]).corpo["message"] == "turno_invalido"
    r = sb.rpc("criar_acao", {"dados": _nova(grupo="https://chat.whatsapp.com/abc")}, jwt=cenario["jwt_b"])
    assert r.status == 200 and r.corpo["status"] == "em análise", r.corpo
    novo = r.corpo["id"]
    assert sb.chamar("GET", f"/rest/v1/acao_publica?id=eq.{novo}").corpo == []
    minhas = sb.rpc("minhas_acoes", {}, jwt=cenario["jwt_b"]).corpo
    assert minhas[0]["acao"]["id"] == novo and minhas[0]["acao"]["status"] == "em análise" and len(minhas[0]["turnos"]) == 1
    # quem não é moderador não vê a fila nem aprova
    assert sb.rpc("fila_moderacao", {}, jwt=cenario["jwt_b"]).corpo["message"] == "so_moderador"
    assert sb.rpc("aprovar_acao", {"acao_id": novo}, jwt=cenario["jwt_b"]).corpo["message"] == "so_moderador"
    sb.admin("PATCH", f"/rest/v1/pessoa?id=eq.{cenario['a']}", {"papel": "moderador"})
    fila = sb.rpc("fila_moderacao", {}, jwt=cenario["jwt_a"]).corpo
    item = next(m for m in fila if m["acao"]["id"] == novo)
    assert item["organizador"]["telefone"] == "(11) 97777-6666" and item["acao"]["contato_link"] == "https://chat.whatsapp.com/abc"
    assert sb.rpc("recusar_acao", {"acao_id": novo, "motivo": " "}, jwt=cenario["jwt_a"]).corpo["message"] == "sem_motivo"
    assert sb.rpc("aprovar_acao", {"acao_id": novo}, jwt=cenario["jwt_a"]).status in (200, 204)
    assert len(sb.chamar("GET", f"/rest/v1/acao_publica?id=eq.{novo}").corpo) == 1
    assert sb.rpc("recusar_acao", {"acao_id": novo, "motivo": "pede dinheiro"}, jwt=cenario["jwt_a"]).status in (200, 204)
    assert sb.rpc("minhas_acoes", {}, jwt=cenario["jwt_b"]).corpo[0]["acao"]["motivo_recusa"] == "pede dinheiro"


def test_verificado_publica_direto_e_limite_de_10_por_dia(cenario):
    r = sb.rpc("criar_acao", {"dados": _nova()}, jwt=cenario["jwt_org"])  # papel organizador = verificado
    assert r.status == 200 and r.corpo["status"] == "publicada", r.corpo
    for _ in range(8):  # com a ação que o cenário já criou hoje, chega a 10
        r = sb.rpc("criar_acao", {"dados": _nova()}, jwt=cenario["jwt_org"])
        assert r.status == 200, r.corpo
    assert sb.rpc("criar_acao", {"dados": _nova()}, jwt=cenario["jwt_org"]).corpo["message"] == "limite_diario"


def test_organizador_ve_quem_vai_e_encerra(cenario):
    r = sb.rpc("criar_acao", {"dados": _nova()}, jwt=cenario["jwt_org"])
    novo = r.corpo["id"]
    turno = sb.chamar("GET", f"/rest/v1/turno_publico?acao=eq.{novo}").corpo[0]["id"]
    sb.rpc("salvar_telefone", {"telefone": "11988887777"}, jwt=cenario["jwt_a"])
    assert sb.rpc("inscrever", {"turno_id": turno}, jwt=cenario["jwt_a"]).status == 200
    minhas = sb.rpc("minhas_acoes", {}, jwt=cenario["jwt_org"]).corpo
    t = next(m for m in minhas if m["acao"]["id"] == novo)["turnos"][0]
    assert t["inscritos"] == [{"nome": "Pessoa A", "telefone": "(11) 98888-7777"}]
    assert sb.rpc("encerrar_acao", {"acao_id": novo}, jwt=cenario["jwt_a"]).corpo["message"] == "nao_pode"
    assert sb.rpc("encerrar_acao", {"acao_id": novo}, jwt=cenario["jwt_org"]).status in (200, 204)
    # cancelada continua abrindo pelo link, até para quem não entrou, sem o link do grupo nem o combinado
    vista = sb.rpc("acao_restrita", {"acao_id": novo}).corpo
    assert vista["acao"]["status"] == "encerrada" and "contato_link" not in vista["acao"] and "detalhe" not in vista["acao"]
    turno_novo = next(m for m in sb.rpc("minhas_acoes", {}, jwt=cenario["jwt_org"]).corpo if m["acao"]["id"] == novo)["turnos"][0]
    assert turno_novo["desistiram"] == []


def test_foto_so_na_propria_pasta_do_bucket(cenario):
    jpeg = bytes.fromhex("ffd8ffe000104a46494600010100000100010000ffd9")
    def enviar(caminho):
        import urllib.request, urllib.error
        req = urllib.request.Request(f"{sb.URL}/storage/v1/object/fotos-acoes/{caminho}", data=jpeg, method="POST",
                                     headers={"apikey": sb.ANON, "Authorization": f"Bearer {cenario['jwt_a']}", "Content-Type": "image/jpeg"})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code
    assert enviar(f"{cenario['a']}/teste-{uuid.uuid4().hex[:6]}.jpg") == 200
    assert enviar(f"{cenario['b']}/teste-{uuid.uuid4().hex[:6]}.jpg") in (400, 403)


def test_moderador_suspende_reativa_e_exclui(cenario):
    r = sb.rpc("criar_acao", {"dados": _nova()}, jwt=cenario["jwt_org"])
    novo = r.corpo["id"]
    # quem não modera não suspende; a página da ação fora do ar só abre para quem criou ou modera
    assert sb.rpc("suspender_acao", {"acao_id": novo}, jwt=cenario["jwt_b"]).corpo["message"] == "so_moderador"
    sb.admin("PATCH", f"/rest/v1/pessoa?id=eq.{cenario['a']}", {"papel": "moderador"})
    assert sb.rpc("suspender_acao", {"acao_id": novo, "motivo": "endereço errado"}, jwt=cenario["jwt_a"]).status in (200, 204)
    assert sb.chamar("GET", f"/rest/v1/acao_publica?id=eq.{novo}").corpo == []
    assert sb.rpc("acao_restrita", {"acao_id": novo}, jwt=cenario["jwt_b"]).corpo is None
    vista = sb.rpc("acao_restrita", {"acao_id": novo}, jwt=cenario["jwt_a"]).corpo
    assert vista["acao"]["status"] == "rascunho" and vista["acao"]["motivo_recusa"] == "endereço errado" and len(vista["turnos"]) == 1
    assert sb.rpc("acao_restrita", {"acao_id": novo}, jwt=cenario["jwt_org"]).corpo["acao"]["id"] == novo
    assert any(m["acao"]["id"] == novo for m in sb.rpc("fila_moderacao", {"situacao": "rascunho"}, jwt=cenario["jwt_a"]).corpo)
    assert sb.rpc("reativar_acao", {"acao_id": novo}, jwt=cenario["jwt_a"]).status in (200, 204)
    assert len(sb.chamar("GET", f"/rest/v1/acao_publica?id=eq.{novo}").corpo) == 1
    assert sb.rpc("excluir_acao", {"acao_id": novo}, jwt=cenario["jwt_b"]).corpo["message"] == "so_moderador"
    assert sb.rpc("excluir_acao", {"acao_id": novo}, jwt=cenario["jwt_a"]).status in (200, 204)
    # excluir não apaga: marca 'excluída', some do site, turnos ficam
    assert sb.admin("GET", f"/rest/v1/acao?id=eq.{novo}").corpo[0]["status"] == "excluída"
    assert len(sb.admin("GET", f"/rest/v1/turno?acao=eq.{novo}").corpo) == 1
    assert sb.chamar("GET", f"/rest/v1/acao_publica?id=eq.{novo}").corpo == []
    assert sb.rpc("excluir_acao", {"acao_id": novo}, jwt=cenario["jwt_a"]).corpo["message"] == "nao_pode"
    sb.admin("PATCH", f"/rest/v1/acao?id=eq.{cenario['acao']}", {"fonte": "bora-lula", "fonte_id": f"x-{novo}"})
    # importada suspensa aparece em Suspensas; ação de pessoa bloqueada não volta ao ar
    assert sb.rpc("suspender_acao", {"acao_id": cenario["acao"]}, jwt=cenario["jwt_a"]).status in (200, 204)
    assert any(m["acao"]["id"] == cenario["acao"] for m in sb.rpc("fila_moderacao", {"situacao": "rascunho"}, jwt=cenario["jwt_a"]).corpo)
    sb.admin("PATCH", f"/rest/v1/pessoa?id=eq.{cenario['org']}", {"bloqueada": True})
    assert sb.rpc("reativar_acao", {"acao_id": cenario["acao"]}, jwt=cenario["jwt_a"]).corpo["message"] == "organizador_bloqueado"


def test_so_se_suspende_acao_publicada(cenario):
    sb.rpc("salvar_telefone", {"telefone": "11977776666"}, jwt=cenario["jwt_b"])
    r = sb.rpc("criar_acao", {"dados": _nova()}, jwt=cenario["jwt_b"])
    sb.admin("PATCH", f"/rest/v1/pessoa?id=eq.{cenario['a']}", {"papel": "moderador"})
    assert r.corpo["status"] == "em análise"
    assert sb.rpc("suspender_acao", {"acao_id": r.corpo["id"]}, jwt=cenario["jwt_a"]).corpo["message"] == "nao_pode"


def test_cancelada_em_analise_nao_vira_publica_nem_conta_como_aprovada(cenario):
    sb.rpc("salvar_telefone", {"telefone": "11977776666"}, jwt=cenario["jwt_b"])
    r = sb.rpc("criar_acao", {"dados": _nova()}, jwt=cenario["jwt_b"])
    assert r.corpo["status"] == "em análise"
    assert sb.rpc("encerrar_acao", {"acao_id": r.corpo["id"]}, jwt=cenario["jwt_b"]).status in (200, 204)
    # nunca passou pela moderação: o link não abre para quem não criou
    assert sb.rpc("acao_restrita", {"acao_id": r.corpo["id"]}).corpo is None
    assert sb.rpc("acao_restrita", {"acao_id": r.corpo["id"]}, jwt=cenario["jwt_b"]).corpo["acao"]["status"] == "encerrada"
    sb.admin("PATCH", f"/rest/v1/pessoa?id=eq.{cenario['a']}", {"papel": "moderador"})
    outra = sb.rpc("criar_acao", {"dados": _nova()}, jwt=cenario["jwt_b"]).corpo["id"]
    fila = sb.rpc("fila_moderacao", {"situacao": "em análise"}, jwt=cenario["jwt_a"]).corpo
    assert next(m for m in fila if m["acao"]["id"] == outra)["organizador"]["aprovadas"] == 0


def test_organizacao_nova_liga_existente_vira_pedido_e_selo_publica_direto(cenario):
    tag = uuid.uuid4().hex[:6]
    sb.rpc("salvar_telefone", {"telefone": "11977776666"}, jwt=cenario["jwt_b"])
    assert sb.rpc("salvar_organizacao", {"nome": f"Comitê {tag}", "tipo": "coletivo"}, jwt=cenario["jwt_b"]).corpo["message"] == "link_oficial"
    r = sb.rpc("salvar_organizacao", {"nome": f"Comitê {tag}", "tipo": "coletivo", "link": "https://instagram.com/comite"}, jwt=cenario["jwt_b"])
    assert r.status == 200 and r.corpo["situacao"] == "ligada", r.corpo
    org = r.corpo["id"]
    mo = sb.rpc("minha_organizacao", {}, jwt=cenario["jwt_b"]).corpo
    assert mo["organizacao"]["id"] == org and mo["organizacao"]["minha"] is True and mo["organizacao"]["verificada"] is False
    assert mo["organizacao"]["link_oficial"] == "https://instagram.com/comite"
    # outra pessoa com o mesmo nome (outra caixa) não entra direto: vira pedido
    sb.rpc("salvar_telefone", {"telefone": "11988887777"}, jwt=cenario["jwt_a"])
    r = sb.rpc("salvar_organizacao", {"nome": f"  COMITÊ {tag} ", "tipo": "coletivo", "link": "https://instagram.com/comite"}, jwt=cenario["jwt_a"])
    assert r.corpo["situacao"] == "pedido", r.corpo
    assert sb.rpc("minha_organizacao", {}, jwt=cenario["jwt_a"]).corpo["organizacao"] is None
    # ação em análise usando o id da organização de outra pessoa: o id é ignorado
    a = sb.rpc("criar_acao", {"dados": _nova(organizacao=org)}, jwt=cenario["jwt_a"]).corpo
    assert sb.admin("GET", f"/rest/v1/acao?id=eq.{a['id']}&select=organizacao").corpo == [{"organizacao": None}]
    # nome escrito à mão: liga a ação à organização (cria sem selo se não existe)
    assert sb.rpc("criar_acao", {"dados": _nova(organizacao_nome=f"Coletivo {tag}")}, jwt=cenario["jwt_a"]).corpo["message"] == "link_post"
    a = sb.rpc("criar_acao", {"dados": _nova(organizacao_nome=f"Coletivo {tag}", organizacao_link="https://www.instagram.com/p/abc123/")}, jwt=cenario["jwt_a"]).corpo
    o = sb.admin("GET", f"/rest/v1/acao?id=eq.{a['id']}&select=organizacao(nome,verificada)").corpo[0]["organizacao"]
    assert o == {"nome": f"Coletivo {tag}", "verificada": False}
    # moderação: só moderador vê a fila; aprova o pedido e dá o selo
    assert sb.rpc("fila_organizacoes", {}, jwt=cenario["jwt_b"]).corpo["message"] == "so_moderador"
    sb.admin("PATCH", f"/rest/v1/pessoa?id=eq.{cenario['org']}", {"papel": "moderador"})
    fila = sb.rpc("fila_organizacoes", {}, jwt=cenario["jwt_org"]).corpo
    pedido = next(p for p in fila["pedidos"] if p["organizacao"] == f"Comitê {tag}")
    assert pedido["link"] == "https://instagram.com/comite"
    fa = sb.rpc("fila_moderacao", {}, jwt=cenario["jwt_org"]).corpo
    item = next(m for m in fa if m["acao"]["id"] == a["id"])
    assert item["acao"]["organizacao_link"] == "https://www.instagram.com/p/abc123/" and item["acao"]["organizacao_dados"]["nome"] == f"Coletivo {tag}"
    assert any(x["id"] == org for x in fila["sem_selo"])
    assert sb.rpc("decidir_pedido_organizacao", {"pedido_id": pedido["id"], "aprovar": True}, jwt=cenario["jwt_org"]).status in (200, 204)
    assert sb.rpc("minha_organizacao", {}, jwt=cenario["jwt_a"]).corpo["organizacao"]["id"] == org
    # em nome da minha organização: sem o post da organização anunciando, não vai
    assert sb.rpc("criar_acao", {"dados": _nova(organizacao=org)}, jwt=cenario["jwt_a"]).corpo["message"] == "link_post"
    assert sb.rpc("criar_acao", {"dados": _nova(organizacao=org, organizacao_link="https://www.instagram.com/p/xyz/")},
                  jwt=cenario["jwt_a"]).corpo["status"] == "em análise"
    assert sb.rpc("dar_selo_organizacao", {"organizacao_id": org}, jwt=cenario["jwt_org"]).status in (200, 204)
    assert sb.rpc("criar_acao", {"dados": _nova(organizacao=org)}, jwt=cenario["jwt_a"]).corpo["message"] == "link_post"  # com selo também
    assert sb.rpc("criar_acao", {"dados": _nova(organizacao=org, organizacao_link="https://www.instagram.com/p/xyz/")},
                  jwt=cenario["jwt_a"]).corpo["status"] == "publicada"


def test_foto_da_acao_so_do_proprio_storage(cenario):
    sb.rpc("salvar_telefone", {"telefone": "11977776666"}, jwt=cenario["jwt_b"])
    for fora in ("https://exemplo.org/arte.jpg", "https://ommitzndniqnmsjsjghb.supabase.co.golpe.example/storage/v1/object/public/fotos-acoes/x.jpg",
                 f"{sb.URL}/storage/v1/object/public/outro/x.jpg", "http://127.0.0.1:54321/x/storage/v1/object/public/fotos-acoes/x.jpg"):
        assert sb.rpc("criar_acao", {"dados": _nova(foto=fora)}, jwt=cenario["jwt_b"]).corpo["message"] == "sem_foto", fora
    r = sb.rpc("criar_acao", {"dados": _nova(foto=FOTO_BUCKET)}, jwt=cenario["jwt_b"])
    assert r.status == 200, r.corpo
    assert sb.admin("GET", f"/rest/v1/acao?id=eq.{r.corpo['id']}&select=foto_url").corpo == [{"foto_url": FOTO_BUCKET}]


def test_logo_da_organizacao_fora_do_storage_vira_null(cenario):
    tag = uuid.uuid4().hex[:6]
    r = sb.rpc("salvar_organizacao", {"nome": f"Comitê Logo {tag}", "tipo": "coletivo", "logo": "https://exemplo.org/logo.png",
                                      "link": "https://instagram.com/comite"}, jwt=cenario["jwt_b"])
    assert r.status == 200 and r.corpo["situacao"] == "ligada", r.corpo
    assert sb.rpc("minha_organizacao", {}, jwt=cenario["jwt_b"]).corpo["organizacao"]["foto_url"] is None
    logo = f"{sb.URL}/storage/v1/object/public/fotos-acoes/teste/logo.png"
    r = sb.rpc("salvar_organizacao", {"nome": f"Comitê Logo {tag}", "tipo": "coletivo", "logo": logo, "link": "https://instagram.com/comite"}, jwt=cenario["jwt_b"])
    assert r.status == 200, r.corpo
    assert sb.rpc("minha_organizacao", {}, jwt=cenario["jwt_b"]).corpo["organizacao"]["foto_url"] == logo


def test_importar_acoes_descarta_link_e_foto_que_nao_sao_http(cenario):
    fonte = "teste-" + uuid.uuid4().hex[:8]
    itens = [_item("a", link="javascript:alert(1)", foto={"url": "javascript:alert(2)", "credito": "x", "pagina": "https://www.instagram.com/p/x/"},
                   organizacao="Org Link Ruim " + fonte, organizacao_foto={"url": "data:image/png;base64,AAAA", "credito": "x", "pagina": "x"}),
             _item("b", link="HTTPS://www.instagram.com/p/y/")]
    r = sb.rpc("importar_acoes", {"fonte": fonte, "itens": itens}, jwt=sb.SERVICE)
    assert r.status == 200, r.corpo
    pub = {a["titulo"]: a for a in sb.chamar("GET", f"/rest/v1/acao_publica?fonte=eq.{fonte}").corpo}
    a, b = pub["Importada a"], pub["Importada b"]
    assert a["contato_tipo"] == "organizador_chama" and a["link_divulgacao"] is None and a["foto_url"] is None
    assert sb.admin("GET", f"/rest/v1/acao?id=eq.{a['id']}&select=contato_link").corpo == [{"contato_link": None}]
    assert b["contato_tipo"] == "divulgacao" and b["link_divulgacao"] == "HTTPS://www.instagram.com/p/y/"
    org = sb.chamar("GET", f"/rest/v1/organizacao_publica?nome=eq.{urllib.parse.quote('Org Link Ruim ' + fonte)}").corpo
    assert len(org) == 1 and org[0]["foto_url"] is None


def test_moderador_bloqueia_e_desbloqueia_pessoa(cenario):
    sb.rpc("salvar_telefone", {"telefone": "11977776666"}, jwt=cenario["jwt_b"])
    sb.admin("PATCH", f"/rest/v1/pessoa?id=eq.{cenario['b']}", {"papel": "organizador"})
    publicada = sb.rpc("criar_acao", {"dados": _nova()}, jwt=cenario["jwt_b"]).corpo["id"]
    sb.admin("PATCH", f"/rest/v1/pessoa?id=eq.{cenario['b']}", {"papel": "participante"})
    pendente = sb.rpc("criar_acao", {"dados": _nova()}, jwt=cenario["jwt_b"]).corpo["id"]
    assert len(sb.chamar("GET", f"/rest/v1/acao_publica?id=eq.{publicada}").corpo) == 1
    # participante comum não bloqueia; moderador não bloqueia a si nem outro moderador
    assert sb.rpc("bloquear_pessoa", {"pessoa_id": cenario["b"]}, jwt=cenario["jwt_b"]).corpo["message"] == "so_moderador"
    assert sb.rpc("bloquear_pessoa", {"pessoa_id": cenario["b"]}).status in (401, 403)
    sb.admin("PATCH", f"/rest/v1/pessoa?id=eq.{cenario['a']}", {"papel": "moderador"})
    sb.admin("PATCH", f"/rest/v1/pessoa?id=eq.{cenario['org']}", {"papel": "moderador"})
    assert sb.rpc("bloquear_pessoa", {"pessoa_id": cenario["a"]}, jwt=cenario["jwt_a"]).corpo["message"] == "nao_pode"
    assert sb.rpc("bloquear_pessoa", {"pessoa_id": cenario["org"]}, jwt=cenario["jwt_a"]).corpo["message"] == "nao_pode"
    assert sb.rpc("bloquear_pessoa", {"pessoa_id": cenario["b"], "motivo": "spam"}, jwt=cenario["jwt_a"]).status in (200, 204)
    assert sb.admin("GET", f"/rest/v1/pessoa?id=eq.{cenario['b']}&select=bloqueada").corpo == [{"bloqueada": True}]
    assert sb.chamar("GET", f"/rest/v1/acao_publica?id=eq.{publicada}").corpo == []
    assert sb.admin("GET", f"/rest/v1/acao?id=eq.{publicada}&select=status,motivo_recusa").corpo == [{"status": "rascunho", "motivo_recusa": "spam"}]
    assert sb.admin("GET", f"/rest/v1/acao?id=eq.{pendente}&select=status").corpo == [{"status": "em análise"}]
    assert any(m["acao"]["id"] == publicada and m["organizador"]["bloqueada"] for m in sb.rpc("fila_moderacao", {"situacao": "rascunho"}, jwt=cenario["jwt_a"]).corpo)
    assert sb.rpc("criar_acao", {"dados": _nova()}, jwt=cenario["jwt_b"]).corpo["message"] == "bloqueada"
    assert sb.rpc("reativar_acao", {"acao_id": publicada}, jwt=cenario["jwt_a"]).corpo["message"] == "organizador_bloqueado"
    reg = sb.admin("GET", f"/rest/v1/registro_moderacao?alvo_tipo=eq.pessoa&alvo_id=eq.{cenario['b']}&order=id").corpo
    assert [(r["acao_feita"], r["motivo"]) for r in reg] == [("bloquear", "spam")]
    # desbloquear só desmarca: a ação segue suspensa até o moderador reativar
    assert sb.rpc("desbloquear_pessoa", {"pessoa_id": cenario["b"]}, jwt=cenario["jwt_b"]).corpo["message"] == "so_moderador"
    assert sb.rpc("desbloquear_pessoa", {"pessoa_id": cenario["b"]}, jwt=cenario["jwt_a"]).status in (200, 204)
    assert sb.admin("GET", f"/rest/v1/pessoa?id=eq.{cenario['b']}&select=bloqueada").corpo == [{"bloqueada": False}]
    assert sb.admin("GET", f"/rest/v1/acao?id=eq.{publicada}&select=status").corpo == [{"status": "rascunho"}]
    assert sb.rpc("desbloquear_pessoa", {"pessoa_id": cenario["b"]}, jwt=cenario["jwt_a"]).corpo["message"] == "nao_pode"
    assert sb.rpc("reativar_acao", {"acao_id": publicada}, jwt=cenario["jwt_a"]).status in (200, 204)
    reg = sb.admin("GET", f"/rest/v1/registro_moderacao?alvo_tipo=eq.pessoa&alvo_id=eq.{cenario['b']}&order=id").corpo
    assert [r["acao_feita"] for r in reg] == ["bloquear", "desbloquear"]


def _enviar_foto(cenario, jwt, caminho):
    import urllib.request, urllib.error
    jpeg = bytes.fromhex("ffd8ffe000104a46494600010100000100010000ffd9")
    req = urllib.request.Request(f"{sb.URL}/storage/v1/object/fotos-acoes/{caminho}", data=jpeg, method="POST",
                                 headers={"apikey": sb.ANON, "Authorization": f"Bearer {jwt}", "Content-Type": "image/jpeg"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def test_limite_de_40_fotos_por_pessoa_no_bucket(cenario):
    for i in range(40):
        assert _enviar_foto(cenario, cenario["jwt_b"], f"{cenario['b']}/lote-{i}.jpg") == 200, i
    assert _enviar_foto(cenario, cenario["jwt_b"], f"{cenario['b']}/lote-40.jpg") in (400, 403)
    # a pasta cheia de uma pessoa não trava a outra
    assert _enviar_foto(cenario, cenario["jwt_a"], f"{cenario['a']}/um.jpg") == 200


def test_importar_acoes_grava_hora_aproximada_e_a_view_publica_a_expoe(cenario):
    fonte = "teste-" + uuid.uuid4().hex[:8]
    r = sb.rpc("importar_acoes", {"fonte": fonte, "itens": [_item("a", inicio="2099-02-01T19:00", fim="2099-02-01T23:00", hora_aproximada=True), _item("b")]}, jwt=sb.SERVICE)
    assert r.status == 200, r.corpo
    pub = {a["titulo"]: a["id"] for a in sb.chamar("GET", f"/rest/v1/acao_publica?fonte=eq.{fonte}").corpo}
    ta = sb.chamar("GET", f"/rest/v1/turno_publico?acao=eq.{pub['Importada a']}").corpo[0]
    tb = sb.chamar("GET", f"/rest/v1/turno_publico?acao=eq.{pub['Importada b']}").corpo[0]
    assert ta["hora_aproximada"] is True and ta["inicio"] == "2099-02-01T19:00:00"
    assert tb["hora_aproximada"] is False
    # reimportar com hora certa desmarca
    sb.rpc("importar_acoes", {"fonte": fonte, "itens": [_item("a", inicio="2099-02-01T20:00", fim="2099-02-01T22:00"), _item("b")]}, jwt=sb.SERVICE)
    ta = sb.chamar("GET", f"/rest/v1/turno_publico?acao=eq.{pub['Importada a']}").corpo[0]
    assert ta["hora_aproximada"] is False and ta["inicio"] == "2099-02-01T20:00:00"


def test_inscrever_recusa_turno_que_ja_terminou_hoje_mas_aceita_o_aproximado_do_dia(cenario):
    import datetime
    hoje = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))).strftime("%Y-%m-%d")
    sb.rpc("salvar_telefone", {"telefone": "11988887777"}, jwt=cenario["jwt_a"])
    r = sb.admin("POST", "/rest/v1/turno", {"acao": cenario["acao"], "inicio": f"{hoje}T00:00:00", "fim": f"{hoje}T00:01:00"})
    assert r.status == 201, r.corpo
    assert sb.rpc("inscrever", {"turno_id": r.corpo[0]["id"]}, jwt=cenario["jwt_a"]).corpo["message"] == "turno_passado"
    r = sb.admin("POST", "/rest/v1/turno", {"acao": cenario["acao"], "inicio": f"{hoje}T00:00:00", "fim": f"{hoje}T00:01:00", "hora_aproximada": True})
    assert r.status == 201, r.corpo
    assert sb.rpc("inscrever", {"turno_id": r.corpo[0]["id"]}, jwt=cenario["jwt_a"]).status == 200


def test_feedback_qualquer_pessoa_manda_e_so_moderador_le(cenario):
    # sem entrar: vai sem pessoa; texto curto não vai
    assert sb.rpc("enviar_feedback", {"texto": "oi"}).corpo["message"] == "sem_texto"
    r = sb.rpc("enviar_feedback", {"texto": "  O horário desta ação está errado  ", "contato": " ", "tela": "#/acao/1", "acao_id": cenario["acao"], "navegador": "iOS Safari"})
    assert r.status == 200, r.corpo
    anon_id = r.corpo["id"]
    # logado: vai com a pessoa; ação que não existe vira null
    r = sb.rpc("enviar_feedback", {"texto": "Ideia: lista das online", "contato": "(11) 99999-0000", "acao_id": 999999999}, jwt=cenario["jwt_a"])
    assert r.status == 200, r.corpo
    meu_id = r.corpo["id"]
    # ninguém lê a tabela direto, nem quem mandou
    assert sb.chamar("GET", "/rest/v1/feedback", jwt=cenario["jwt_a"]).corpo == []
    assert sb.chamar("GET", "/rest/v1/feedback").status >= 400 or sb.chamar("GET", "/rest/v1/feedback").corpo == []
    assert sb.rpc("feedbacks", {}).status >= 400  # anon nem chama
    assert sb.rpc("feedbacks", {}, jwt=cenario["jwt_a"]).corpo["message"] == "so_moderador"
    assert sb.rpc("tratar_feedback", {"feedback_id": anon_id}, jwt=cenario["jwt_a"]).corpo["message"] == "so_moderador"
    sb.admin("PATCH", f"/rest/v1/pessoa?id=eq.{cenario['b']}", {"papel": "moderador"})
    pend = {f["id"]: f for f in sb.rpc("feedbacks", {}, jwt=cenario["jwt_b"]).corpo}
    a, m = pend[anon_id], pend[meu_id]
    assert a["texto"] == "O horário desta ação está errado" and a["contato"] is None and a["pessoa"] is None
    assert a["acao"] == cenario["acao"] and a["acao_titulo"].startswith("Teste ") and a["navegador"] == "iOS Safari" and a["tratado_em"] is None
    assert m["pessoa"]["nome"] == "Pessoa A" and m["contato"] == "(11) 99999-0000" and m["acao"] is None
    # tratar tira das pendentes e põe nas tratadas; reabrir volta
    assert sb.rpc("tratar_feedback", {"feedback_id": anon_id}, jwt=cenario["jwt_b"]).status in (200, 204)
    assert anon_id not in {f["id"] for f in sb.rpc("feedbacks", {}, jwt=cenario["jwt_b"]).corpo}
    trat = {f["id"]: f for f in sb.rpc("feedbacks", {"pendentes": False}, jwt=cenario["jwt_b"]).corpo}
    assert trat[anon_id]["tratado_em"] is not None
    assert sb.rpc("tratar_feedback", {"feedback_id": anon_id, "tratado": False}, jwt=cenario["jwt_b"]).status in (200, 204)
    assert anon_id in {f["id"] for f in sb.rpc("feedbacks", {}, jwt=cenario["jwt_b"]).corpo}
    assert sb.rpc("tratar_feedback", {"feedback_id": 999999999}, jwt=cenario["jwt_b"]).corpo["message"] == "nao_pode"


def test_feedback_tem_freio_por_pessoa(cenario):
    for i in range(10):
        assert sb.rpc("enviar_feedback", {"texto": f"mensagem {i}"}, jwt=cenario["jwt_b"]).status == 200
    assert sb.rpc("enviar_feedback", {"texto": "a décima primeira"}, jwt=cenario["jwt_b"]).corpo["message"] == "muitas_mensagens"


def _verificar_todas(cenario, ids):
    for i in ids:
        assert sb.rpc("verificar_acao", {"acao_id": i}, jwt=cenario["jwt_a"]).status in (200, 204)


def test_divulgacao_publica_so_moderador_verifica_e_a_fila_lista_as_nao_verificadas(cenario):
    fonte = "teste-" + uuid.uuid4().hex[:8]
    itens = [_item("a"), _item("b")]
    assert sb.rpc("importar_acoes", {"fonte": fonte, "itens": itens}, jwt=sb.SERVICE).status == 200
    ids = {a["titulo"][-1]: a["id"] for a in sb.chamar("GET", f"/rest/v1/acao_publica?fonte=eq.{fonte}").corpo}
    pub = lambda: {a["titulo"][-1]: a["verificada"] for a in sb.chamar("GET", f"/rest/v1/acao_publica?fonte=eq.{fonte}").corpo}
    assert pub() == {"a": False, "b": False}
    # ação cadastrada no app conta como verificada
    assert all(a["verificada"] for a in sb.chamar("GET", "/rest/v1/acao_publica?fonte=is.null&limit=5").corpo)
    assert sb.rpc("verificar_acao", {"acao_id": ids["a"]}, jwt=cenario["jwt_b"]).corpo["message"] == "so_moderador"
    assert sb.rpc("verificar_acao", {"acao_id": ids["a"]}).status >= 400
    assert sb.rpc("fila_moderacao", {"situacao": "divulgacao"}, jwt=cenario["jwt_b"]).corpo["message"] == "so_moderador"
    sb.admin("PATCH", f"/rest/v1/pessoa?id=eq.{cenario['a']}", {"papel": "moderador"})
    fila = sb.rpc("fila_moderacao", {"situacao": "divulgacao"}, jwt=cenario["jwt_a"]).corpo
    assert sorted(m["acao"]["id"] for m in fila if m["acao"]["fonte"] == fonte) == sorted(ids.values())
    assert all(m["acao"]["verificada"] is False for m in fila)
    _verificar_todas(cenario, ids.values())
    assert pub() == {"a": True, "b": True}
    assert not [m for m in sb.rpc("fila_moderacao", {"situacao": "divulgacao"}, jwt=cenario["jwt_a"]).corpo if m["acao"]["fonte"] == fonte]
    # desverificar; de novo não pode; ação do app não se verifica
    assert sb.rpc("desverificar_acao", {"acao_id": ids["b"]}, jwt=cenario["jwt_a"]).status in (200, 204)
    assert pub()["b"] is False
    assert sb.rpc("desverificar_acao", {"acao_id": ids["b"]}, jwt=cenario["jwt_a"]).corpo["message"] == "nao_pode"
    sb.rpc("salvar_telefone", {"telefone": "11977776666"}, jwt=cenario["jwt_b"])
    novo = sb.rpc("criar_acao", {"dados": _nova()}, jwt=cenario["jwt_b"]).corpo["id"]
    assert sb.rpc("verificar_acao", {"acao_id": novo}, jwt=cenario["jwt_a"]).corpo["message"] == "nao_pode"
    # recusar uma importada tira do ar e a reimportação respeita
    assert sb.rpc("recusar_acao", {"acao_id": ids["a"], "motivo": "post de outra data"}, jwt=cenario["jwt_a"]).status in (200, 204)
    sb.rpc("importar_acoes", {"fonte": fonte, "itens": itens}, jwt=sb.SERVICE)
    assert "a" not in pub()


def test_divulgacao_publica_qualquer_mudanca_da_fonte_tira_a_verificacao_so_foto_nao(cenario):
    fonte = "teste-" + uuid.uuid4().hex[:8]
    mudancas = {"titulo": {"titulo": "Importada outro"}, "tipo": {"tipo": "ato"}, "descricao": {"descricao": "Outro texto."},
                "organizacao": {"organizacao": "Outra Org Teste"}, "lugar_nome": {"lugar_nome": "Praça Nova"}, "bairro": {"bairro": "Vila"},
                "cidade": {"cidade": "Santo André"}, "lat": {"lat": -23.7}, "online": {"online": True, "lat": None, "lon": None},
                "aprox": {"lugar_aproximado": False}, "link": {"link": "https://www.instagram.com/p/y/"}, "sem_link": {"link": ""},
                "inicio": {"inicio": "2099-02-01T10:00"}, "fim": {"fim": "2099-02-01T12:00"}, "hora_aprox": {"hora_aproximada": True}}
    chaves = list(mudancas) + ["foto", "igual"]
    itens = [_item(k) for k in chaves]
    assert sb.rpc("importar_acoes", {"fonte": fonte, "itens": itens}, jwt=sb.SERVICE).status == 200
    linhas = sb.admin("GET", f"/rest/v1/acao?fonte=eq.{fonte}&select=id,fonte_id").corpo
    ids = {l["fonte_id"]: l["id"] for l in linhas}
    sb.admin("PATCH", f"/rest/v1/pessoa?id=eq.{cenario['a']}", {"papel": "moderador"})
    _verificar_todas(cenario, ids.values())
    foto = {"url": "https://exemplo.github.io/fotos/x.jpg", "credito": "c", "pagina": None}
    novos = [_item(k, **mudancas[k]) for k in mudancas] + [_item("foto", foto=foto, organizacao_foto=foto), _item("igual")]
    assert sb.rpc("importar_acoes", {"fonte": fonte, "itens": novos}, jwt=sb.SERVICE).status == 200
    ver = {l["fonte_id"]: l["verificada_em"] is not None for l in sb.admin("GET", f"/rest/v1/acao?fonte=eq.{fonte}&select=fonte_id,verificada_em").corpo}
    assert ver == {**{k: False for k in mudancas}, "foto": True, "igual": True}


def test_divulgacao_publica_encerrada_que_volta_e_turno_a_mais_perdem_a_verificacao(cenario):
    fonte = "teste-" + uuid.uuid4().hex[:8]
    itens = [_item("a"), _item("b")]
    sb.rpc("importar_acoes", {"fonte": fonte, "itens": itens}, jwt=sb.SERVICE)
    ids = {l["fonte_id"]: l["id"] for l in sb.admin("GET", f"/rest/v1/acao?fonte=eq.{fonte}&select=id,fonte_id").corpo}
    sb.admin("PATCH", f"/rest/v1/pessoa?id=eq.{cenario['a']}", {"papel": "moderador"})
    _verificar_todas(cenario, ids.values())
    ver = lambda: {l["fonte_id"]: l["verificada_em"] is not None for l in sb.admin("GET", f"/rest/v1/acao?fonte=eq.{fonte}&select=fonte_id,verificada_em").corpo}
    # "a" sai da agenda (encerrada) e volta igual: perde a verificação
    sb.rpc("importar_acoes", {"fonte": fonte, "itens": [_item("b")]}, jwt=sb.SERVICE)
    sb.rpc("importar_acoes", {"fonte": fonte, "itens": itens}, jwt=sb.SERVICE)
    assert ver() == {"a": False, "b": True}
    # "b" ganhou um segundo turno por fora: a importação traz um só, então a verificação cai
    assert sb.admin("POST", "/rest/v1/turno", {"acao": ids["b"], "inicio": "2099-02-02T09:00", "fim": "2099-02-02T11:00"}).status in (200, 201)
    sb.rpc("importar_acoes", {"fonte": fonte, "itens": itens}, jwt=sb.SERVICE)
    assert ver()["b"] is False


def test_fila_divulgacao_mantem_hora_aproximada_ate_o_fim_do_dia(cenario):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).date().isoformat()
    fonte = "teste-" + uuid.uuid4().hex[:8]
    itens = [_item("aprox", inicio=f"{hoje}T00:00", fim=f"{hoje}T00:01", hora_aproximada=True),
             _item("exato", inicio=f"{hoje}T00:00", fim=f"{hoje}T00:01")]
    assert sb.rpc("importar_acoes", {"fonte": fonte, "itens": itens}, jwt=sb.SERVICE).status == 200
    sb.admin("PATCH", f"/rest/v1/pessoa?id=eq.{cenario['a']}", {"papel": "moderador"})
    fila = sb.rpc("fila_moderacao", {"situacao": "divulgacao"}, jwt=cenario["jwt_a"]).corpo
    assert [m["acao"]["titulo"] for m in fila if m["acao"]["fonte"] == fonte] == ["Importada aprox"]


def _acao_da_fonte(fonte, fonte_id):
    return sb.admin("GET", f"/rest/v1/acao?fonte=eq.{fonte}&fonte_id=eq.{fonte_id}&select=*").corpo[0]


def test_duvida_entra_em_analise_fora_do_ar_e_aparece_na_fila_com_o_motivo(cenario):
    fonte = "teste-" + uuid.uuid4().hex[:8]
    itens = [_item("ok"), _item("fraca", status="em análise", motivo_duvida="confiança baixa"),
             _item("sem", status="em análise", motivo_duvida="sem cidade reconhecida", cidade="Xyz - SP", lat=None, lon=None, lugar_nome=None)]
    r = sb.rpc("importar_acoes", {"fonte": fonte, "itens": itens}, jwt=sb.SERVICE)
    assert r.status == 200, r.corpo
    assert [a["titulo"] for a in sb.chamar("GET", f"/rest/v1/acao_publica?fonte=eq.{fonte}").corpo] == ["Importada ok"]
    assert _acao_da_fonte(fonte, "fraca")["status"] == "em análise"
    # publicada sem ponto no mapa continua proibida
    r = sb.rpc("importar_acoes", {"fonte": fonte, "itens": [_item("x", lat=None, lon=None)]}, jwt=sb.SERVICE)
    assert r.status >= 400 and "sem_lugar" in str(r.corpo)
    sb.admin("PATCH", f"/rest/v1/pessoa?id=eq.{cenario['a']}", {"papel": "moderador"})
    fila = [m for m in sb.rpc("fila_moderacao", {"situacao": "em análise"}, jwt=cenario["jwt_a"]).corpo if m["acao"]["fonte"] == fonte]
    assert sorted((m["acao"]["titulo"], m["duvida"], m["organizador"]) for m in fila) == [
        ("Importada fraca", "confiança baixa", None), ("Importada sem", "sem cidade reconhecida", None)]
    # aprovar: a com lugar vai ao ar já verificada; a sem lugar não dá para aprovar
    fraca, sem = _acao_da_fonte(fonte, "fraca")["id"], _acao_da_fonte(fonte, "sem")["id"]
    assert sb.rpc("aprovar_acao", {"acao_id": sem}, jwt=cenario["jwt_a"]).corpo["message"] == "sem_lugar"
    assert sb.rpc("aprovar_acao", {"acao_id": fraca}, jwt=cenario["jwt_a"]).status in (200, 204)
    pub = {a["titulo"]: a["verificada"] for a in sb.chamar("GET", f"/rest/v1/acao_publica?fonte=eq.{fonte}").corpo}
    assert pub == {"Importada ok": False, "Importada fraca": True}
    # recusar a sem lugar funciona
    assert sb.rpc("recusar_acao", {"acao_id": sem, "motivo": "sem lugar"}, jwt=cenario["jwt_a"]).status in (200, 204)


def test_reimportar_nao_mexe_na_decisao_da_moderacao_e_a_nunca_aprovada_nao_vai_ao_ar(cenario):
    fonte = "teste-" + uuid.uuid4().hex[:8]
    duv = _item("d", status="em análise", motivo_duvida="confiança baixa")
    assert sb.rpc("importar_acoes", {"fonte": fonte, "itens": [duv]}, jwt=sb.SERVICE).status == 200
    # reimportar sem status (como se a dúvida tivesse sumido) não publica: só a moderação decide
    assert sb.rpc("importar_acoes", {"fonte": fonte, "itens": [_item("d")]}, jwt=sb.SERVICE).status == 200
    assert _acao_da_fonte(fonte, "d")["status"] == "em análise"
    # sumiu da fonte: encerra; volta: vai para a análise, não para o ar (nunca esteve publicada)
    assert sb.rpc("importar_acoes", {"fonte": fonte, "itens": []}, jwt=sb.SERVICE).status == 200
    assert _acao_da_fonte(fonte, "d")["status"] == "encerrada"
    assert sb.rpc("importar_acoes", {"fonte": fonte, "itens": [duv]}, jwt=sb.SERVICE).status == 200
    assert _acao_da_fonte(fonte, "d")["status"] == "em análise"
    # já publicada que volta: volta ao ar; recusada continua recusada
    assert sb.rpc("importar_acoes", {"fonte": fonte, "itens": [duv, _item("p")]}, jwt=sb.SERVICE).status == 200
    assert sb.rpc("importar_acoes", {"fonte": fonte, "itens": [duv]}, jwt=sb.SERVICE).status == 200
    assert _acao_da_fonte(fonte, "p")["status"] == "encerrada"
    assert sb.rpc("importar_acoes", {"fonte": fonte, "itens": [duv, _item("p")]}, jwt=sb.SERVICE).status == 200
    assert _acao_da_fonte(fonte, "p")["status"] == "publicada"
    sb.admin("PATCH", f"/rest/v1/pessoa?id=eq.{cenario['a']}", {"papel": "moderador"})
    d = _acao_da_fonte(fonte, "d")["id"]
    assert sb.rpc("recusar_acao", {"acao_id": d, "motivo": "não é ação"}, jwt=cenario["jwt_a"]).status in (200, 204)
    assert sb.rpc("importar_acoes", {"fonte": fonte, "itens": [duv, _item("p")]}, jwt=sb.SERVICE).status == 200
    assert _acao_da_fonte(fonte, "d")["status"] == "recusada"


def test_publicada_que_perde_o_ponto_na_fonte_guarda_o_lugar_e_perde_a_verificacao(cenario):
    fonte = "teste-" + uuid.uuid4().hex[:8]
    assert sb.rpc("importar_acoes", {"fonte": fonte, "itens": [_item("a")]}, jwt=sb.SERVICE).status == 200
    sb.admin("PATCH", f"/rest/v1/pessoa?id=eq.{cenario['a']}", {"papel": "moderador"})
    _verificar_todas(cenario, [_acao_da_fonte(fonte, "a")["id"]])
    sem = _item("a", status="em análise", motivo_duvida="sem cidade reconhecida", cidade="Xyz", lat=None, lon=None, lugar_nome=None)
    r = sb.rpc("importar_acoes", {"fonte": fonte, "itens": [sem]}, jwt=sb.SERVICE)
    assert r.status == 200, r.corpo
    a = _acao_da_fonte(fonte, "a")
    assert (a["status"], a["cidade"], a["lat"], a["verificada_em"]) == ("publicada", "Diadema", -23.68, None)
