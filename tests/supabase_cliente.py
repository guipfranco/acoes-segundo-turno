"""Cliente mínimo do Supabase para os testes de regras: REST do PostgREST e Auth, só urllib."""
import json
import os
import urllib.error
import urllib.request

URL = os.environ.get("SUPABASE_URL", "http://127.0.0.1:54321")
ANON = os.environ.get("SUPABASE_ANON_KEY", "")
SERVICE = os.environ.get("SUPABASE_SERVICE_KEY", "")


class Resposta:
    def __init__(self, status, corpo):
        self.status, self.corpo = status, corpo


def chamar(metodo, caminho, corpo=None, jwt=None, chave=None, extra=None):
    chave = chave or ANON
    cab = {"apikey": chave, "Authorization": f"Bearer {jwt or chave}", "Content-Type": "application/json", "Prefer": "return=representation"}
    cab.update(extra or {})
    dados = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(URL + caminho, data=dados, method=metodo, headers=cab)
    try:
        with urllib.request.urlopen(req) as r:
            texto = r.read().decode()
            return Resposta(r.status, json.loads(texto) if texto else None)
    except urllib.error.HTTPError as e:
        texto = e.read().decode()
        try:
            return Resposta(e.code, json.loads(texto))
        except ValueError:
            return Resposta(e.code, texto)


def criar_usuario(email, nome):
    r = chamar("POST", "/auth/v1/admin/users", {"email": email, "password": "senha123", "email_confirm": True, "user_metadata": {"full_name": nome}}, chave=SERVICE)
    assert r.status in (200, 201), r.corpo
    return r.corpo["id"]


def entrar(email):
    r = chamar("POST", "/auth/v1/token?grant_type=password", {"email": email, "password": "senha123"})
    assert r.status == 200, r.corpo
    return r.corpo["access_token"]


def rpc(nome, args, jwt=None):
    return chamar("POST", f"/rest/v1/rpc/{nome}", args, jwt=jwt)


def admin(metodo, caminho, corpo=None):
    return chamar(metodo, caminho, corpo, chave=SERVICE)
