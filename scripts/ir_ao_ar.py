"""Põe o projeto de produção do Supabase no ar pela Management API e pelo CLI.

Cobre os passos de Supabase de "O que falta para ir ao ar" (docs/operacao.md). O login do Google no
Google Cloud continua manual: o script só cola o ID e o segredo no Supabase.

Variáveis de ambiente (nunca vão para o repo):
  SUPABASE_ACCESS_TOKEN   token pessoal, criado em https://supabase.com/dashboard/account/tokens
  SUPABASE_DB_PASSWORD    senha do banco (escolha uma forte e guarde no gerenciador de senhas)
  GOOGLE_CLIENT_ID        ID do cliente OAuth (passo auth; opcional)
  GOOGLE_CLIENT_SECRET    segredo do cliente OAuth (passo auth; opcional)

Uso:
  python scripts/ir_ao_ar.py senha          # redefine a senha do banco e guarda em .env (fora do git)
  python scripts/ir_ao_ar.py criar          # cria o projeto em São Paulo e espera ficar pronto
  python scripts/ir_ao_ar.py migrar         # link + db push + confere que as views públicas são só leitura
  python scripts/ir_ao_ar.py auth           # desliga e-mail, liga Google, Site URL e Redirect URLs
  python scripts/ir_ao_ar.py config         # escreve URL e chave pública em app/config.js
  python scripts/ir_ao_ar.py semear --telefone "(11) 9xxxx-xxxx"   # depois de entrar uma vez pelo site
  python scripts/ir_ao_ar.py tudo           # criar, migrar, auth e config em sequência

O ref do projeto fica em supabase/.temp/project-ref (fora do git); --ref força outro.
As variáveis também podem ficar em .env na raiz (NOME=valor por linha; o arquivo está no .gitignore).
"""
import argparse
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
API = "https://api.supabase.com/v1"
NOME = "acoes-segundo-turno"
REGIAO = "sa-east-1"
SITE = "https://guipfranco.github.io/acoes-segundo-turno/"
REDIRECTS = ["https://guipfranco.github.io/acoes-segundo-turno/**", "http://localhost:8000/**"]
ARQ_REF = RAIZ / "supabase" / ".temp" / "project-ref"
CONFIG_JS = RAIZ / "app" / "config.js"
EMAIL_DONO = "guilhermepereirafranco@gmail.com"
ARQ_ENV = RAIZ / ".env"


def ler_env():
    """NOME=valor por linha de .env; não sobrescreve o que já está no ambiente."""
    if not ARQ_ENV.exists():
        return
    for linha in ARQ_ENV.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        k, v = linha.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip("'\""))


def gravar_env(nome, valor):
    linhas = ARQ_ENV.read_text(encoding="utf-8").splitlines() if ARQ_ENV.exists() else []
    linhas = [l for l in linhas if not l.startswith(nome + "=")] + [f"{nome}={valor}"]
    ARQ_ENV.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    os.environ[nome] = valor


class Falha(Exception):
    pass


def env(nome, obrigatoria=True):
    v = os.environ.get(nome, "").strip()
    if obrigatoria and not v:
        raise Falha(f"falta a variável de ambiente {nome} (veja o topo de scripts/ir_ao_ar.py)")
    return v


def chamar(metodo, caminho, corpo=None, base=API, cabecalhos=None):
    """Faz a requisição HTTP. Devolve (status, json ou texto)."""
    h = {"User-Agent": "acoes-segundo-turno/ir_ao_ar", "Accept": "application/json"}
    if base == API:
        h["Authorization"] = "Bearer " + env("SUPABASE_ACCESS_TOKEN")
    h.update(cabecalhos or {})
    dados = None
    if corpo is not None:
        dados = json.dumps(corpo).encode()
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(base + caminho, data=dados, headers=h, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            status, bruto = r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        status, bruto = e.code, e.read().decode(errors="replace")
    try:
        return status, json.loads(bruto) if bruto else None
    except json.JSONDecodeError:
        return status, bruto


def ok(status, resp, oque):
    if not 200 <= status < 300:
        raise Falha(f"{oque}: HTTP {status} {resp}")
    return resp


def ler_ref(args):
    if args.ref:
        return args.ref
    if ARQ_REF.exists():
        return ARQ_REF.read_text().strip()
    raise Falha("não sei o ref do projeto: rode o passo criar ou passe --ref")


def guardar_ref(ref):
    ARQ_REF.parent.mkdir(parents=True, exist_ok=True)
    ARQ_REF.write_text(ref)


def npx(*args):
    exe = shutil.which("npx") or shutil.which("npx.cmd")
    if not exe:
        raise Falha("npx não encontrado (instale o Node)")
    senha = env("SUPABASE_DB_PASSWORD")
    print("  $ npx supabase " + " ".join("***" if a == senha else a for a in args))
    r = subprocess.run([exe, "--yes", "supabase", *args], cwd=RAIZ, env={**os.environ, "SUPABASE_DB_PASSWORD": senha})
    if r.returncode:
        raise Falha(f"npx supabase {args[0]} saiu com código {r.returncode}")


# ---- passos ----

def senha(args):
    """Redefine a senha do banco pela Management API e guarda em .env."""
    ref = ler_ref(args)
    nova = secrets.token_urlsafe(27)
    ok(*chamar("PATCH", f"/projects/{ref}/database/password", {"password": nova}), "redefinir a senha do banco")
    gravar_env("SUPABASE_DB_PASSWORD", nova)
    print(f"senha do banco redefinida e guardada em {ARQ_ENV} (fora do git)")


def criar(args):
    senha = env("SUPABASE_DB_PASSWORD")
    projetos = ok(*chamar("GET", "/projects"), "listar projetos")
    existente = next((p for p in projetos if p.get("name") == NOME), None)
    if existente:
        ref = existente["id"]
        print(f"projeto {NOME} já existe: {ref}")
    else:
        orgs = ok(*chamar("GET", "/organizations"), "listar organizações")
        if not orgs:
            raise Falha("a conta não tem organização: crie uma no painel do Supabase")
        org = next((o for o in orgs if o.get("id") == args.org), None) if args.org else None
        if not org:
            if len(orgs) > 1:
                nomes = ", ".join(f"{o['name']} ({o['id']})" for o in orgs)
                raise Falha(f"há mais de uma organização, escolha com --org: {nomes}")
            org = orgs[0]
        print(f"criando {NOME} em {REGIAO} na organização {org['name']}...")
        p = ok(*chamar("POST", "/projects", {"name": NOME, "organization_id": org["id"],
                                              "region": REGIAO, "db_pass": senha}), "criar projeto")
        ref = p["id"]
    guardar_ref(ref)
    for _ in range(60):
        st = ok(*chamar("GET", f"/projects/{ref}"), "ver projeto").get("status")
        if st == "ACTIVE_HEALTHY":
            print(f"projeto pronto: https://{ref}.supabase.co")
            return ref
        print(f"  status {st}, esperando...")
        time.sleep(10)
    raise Falha("o projeto não ficou pronto em 10 minutos; rode de novo daqui a pouco")


def chave_publica(chaves):
    """Prefere a anon legada (JWT); cai na publishable se for a única. Nunca devolve chave secreta."""
    for k in chaves:
        if k.get("name") == "anon" and k.get("api_key"):
            return k["api_key"]
    for k in chaves:
        if k.get("type") == "publishable" and k.get("api_key"):
            return k["api_key"]
    raise Falha("não achei a chave anon nem a publishable do projeto")


def pegar_chave(ref):
    return chave_publica(ok(*chamar("GET", f"/projects/{ref}/api-keys"), "listar chaves"))


def conferir_so_leitura(ref, anon):
    st, resp = chamar("PATCH", "/rest/v1/configuracao_publica?chave=eq.vaquinha", {"valor": "x"},
                      base=f"https://{ref}.supabase.co",
                      cabecalhos={"apikey": anon, "Authorization": "Bearer " + anon})
    if st in (401, 403, 405):
        print(f"views públicas só leitura: PATCH com a chave anon deu {st}")
    else:
        raise Falha(f"PATCH em configuracao_publica com a chave anon deu {st} {resp}: revise as migrações")


def migrar(args):
    ref = ler_ref(args)
    npx("link", "--project-ref", ref, "--password", env("SUPABASE_DB_PASSWORD"))
    npx("db", "push", "--password", env("SUPABASE_DB_PASSWORD"))
    conferir_so_leitura(ref, pegar_chave(ref))


def corpo_auth(client_id, segredo):
    corpo = {"site_url": SITE, "uri_allow_list": ",".join(REDIRECTS), "external_email_enabled": False}
    if client_id and segredo:
        corpo.update(external_google_enabled=True, external_google_client_id=client_id,
                     external_google_secret=segredo)
    return corpo


def auth(args):
    ref = ler_ref(args)
    cid, seg = env("GOOGLE_CLIENT_ID", False), env("GOOGLE_CLIENT_SECRET", False)
    ok(*chamar("PATCH", f"/projects/{ref}/config/auth", corpo_auth(cid, seg)), "configurar auth")
    print(f"auth: Site URL {SITE}, redirects {', '.join(REDIRECTS)}, login por e-mail desligado")
    if cid and seg:
        print("auth: Google ligado")
    else:
        print("auth: Google NÃO ligado (faltam GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET); rode auth de novo depois")
    print(f"  URI de redirecionamento para o Google Cloud: https://{ref}.supabase.co/auth/v1/callback")


def texto_config(url, chave):
    return ("// Configuração pública do app. Sem `supabase`, o app roda no modo exemplo (dados fictícios em memória).\n"
            "// A chave anon do Supabase é pública por desenho: o que protege os dados é o RLS no banco.\n"
            f"window.CONFIG = {{ supabase: {{ url: '{url}', anonKey: '{chave}' }} }};\n")


def config(args):
    ref = ler_ref(args)
    chave = pegar_chave(ref)
    CONFIG_JS.write_text(texto_config(f"https://{ref}.supabase.co", chave), encoding="utf-8")
    print("app/config.js preenchido. Para publicar:\n"
          "  git add app/config.js && git commit -m 'Ligar Supabase de produção' && git push")


def sql_semear(telefone, email=EMAIL_DONO):
    if not re.fullmatch(r"[0-9()+\- ]{8,20}", telefone):
        raise Falha("telefone com caracteres estranhos")
    return f"""
update pessoa set papel = 'organizador', telefone = '{telefone}' where email = '{email}';
insert into acao (titulo, tipo, descricao, organizador, lugar_nome, bairro, cidade, lat, lon, detalhe, contato_tipo, status)
select 'Ação de teste', 'panfletagem', 'Só para testar o site.', id, 'Praça da Sé', 'Sé', 'São Paulo', -23.5505, -46.6333,
       'Perto da catedral.', 'organizador_chama', 'publicada'
from pessoa where email = '{email}' and not exists (select 1 from acao where titulo = 'Ação de teste');
insert into turno (acao, inicio, fim)
select a.id, (hoje_brasilia() + 2)::timestamp + time '10:00', (hoje_brasilia() + 2)::timestamp + time '12:00'
from acao a where a.titulo = 'Ação de teste' and not exists (select 1 from turno t where t.acao = a.id);
"""


def semear(args):
    ref = ler_ref(args)

    def q(s):
        return ok(*chamar("POST", f"/projects/{ref}/database/query", {"query": s}), "rodar SQL")

    if not q(f"select 1 from pessoa where email = '{EMAIL_DONO}'"):
        raise Falha(f"{EMAIL_DONO} ainda não entrou pelo site: entre uma vez com o Google e rode de novo")
    q(sql_semear(args.telefone))
    print("organizador promovido e 'Ação de teste' semeada (daqui a 2 dias, 10h às 12h)")


def tudo(args):
    criar(args)
    migrar(args)
    auth(args)
    config(args)


PASSOS = {"senha": senha, "criar": criar, "migrar": migrar, "auth": auth, "config": config, "semear": semear, "tudo": tudo}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("passo", choices=list(PASSOS))
    ap.add_argument("--ref", help="ref do projeto (padrão: supabase/.temp/project-ref)")
    ap.add_argument("--org", help="id da organização, se a conta tiver mais de uma")
    ap.add_argument("--telefone", help="seu telefone, para o passo semear")
    args = ap.parse_args(argv)
    ler_env()
    if args.passo == "semear" and not args.telefone:
        ap.error("semear precisa de --telefone")
    try:
        PASSOS[args.passo](args)
    except Falha as e:
        print("ERRO: " + str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
