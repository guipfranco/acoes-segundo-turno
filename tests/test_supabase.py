"""Regras do banco: só rodam com SUPABASE_URL, SUPABASE_ANON_KEY e SUPABASE_SERVICE_KEY no ambiente
(banco local do `npx supabase start`). Cada teste cria seus próprios usuários e ação."""
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
