# Implementação v1, etapas 1 e 2: camada de dados, Supabase, login Google, vitrine e Vou

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tirar o mockup do papel: o site publicado no GitHub Pages passa a ler ações de um banco Supabase, a entrar com Google e a gravar inscrições de verdade (Vou, desistir, Minhas inscrições), sem mudar o visual.

**Architecture:** O `mockup/` vira `app/` e ganha uma camada de dados (`API`) com dois miolos intercambiáveis: `api-exemplo.js` (dados fictícios em memória, para desenvolver e para o protótipo seguir navegável) e `api-supabase.js` (Postgres + Auth do Supabase, via `supabase-js` de CDN). As telas só falam com `API`. O que é sensível (quem vê detalhe e contato, inscrever, desistir) é função SQL no banco com `security definer`; o telefone nunca é legível pela chave pública. Criar ação, Minhas ações e Fila continuam funcionando só no modo exemplo neste plano; no modo Supabase ficam escondidos com "em breve" até o plano das etapas 3 e 4.

**Tech Stack:** HTML/CSS/JS sem build (como hoje), Leaflet 1.9.4, `@supabase/supabase-js@2.45.4` (UMD via jsDelivr), Supabase (Postgres 15, RLS, Auth com Google), Supabase CLI via `npx supabase` com Docker para o banco local, Python 3.10 + pytest (testes de telas e de regras do banco via REST), Node 24 `node --test` (testes da camada de exemplo), GitHub Pages.

**Spec:** `docs/superpowers/specs/2026-10-08-implementacao-v1-design.md` (e a spec do produto `docs/superpowers/specs/2026-10-08-plataforma-acoes-design.md`).

## Global Constraints

- Tudo em pt-BR, datas AAAA-MM-DD, horários `AAAA-MM-DDTHH:MM` (hora de Brasília, sem fuso) entre front e API. Commits em pt-BR; push logo depois de cada commit (CLAUDE.md).
- Sem build. Bibliotecas só por CDN (cdnjs ou jsDelivr) com versão exata.
- Sem dado pessoal real no repo. Pessoas e organizações de exemplo são inventadas; telefones de exemplo no formato `(11) 9xxxx-xxxx`.
- Só a chave pública (anon) do Supabase vai para o repo. `service_role` e segredos do Google nunca entram no git.
- Login só por conta social (Google agora; Facebook depois). Sem e-mail e senha, sem código por SMS.
- Telefone nunca aparece em página pública nem é legível por quem não deve: garantido por RLS e views, não por JS.
- Organizador é status concedido; neste plano ninguém cria ação no modo Supabase (sem política de insert em `acao`).
- Formas de contato: `organizador_chama` (padrão), `whatsapp`, `link_grupo`. Link de grupo nunca é obrigatório.
- Pages publica em cada push em `master` que toque `app/`.
- Testes: `python -m pytest tests` precisa passar ao fim de cada task; `node --test tests/js` idem a partir da Task 2.

## Review Focus

1. Horário na virada do dia: um horário com início hoje às 23:30 e fim 00:30 de amanhã deve ser aceito (fim > início) e continuar visível até o fim do dia de hoje. Teste na Task 6 (`check (fim > inicio)`) e Task 2 (`turno_passado` compara só a data).
2. Volta do login do Google no meio do Vou: a pessoa toca em Vou, vai para o Google, volta com `?code=` na URL e precisa cair na mesma ação com o formulário de telefone aberto, sem `#/acao/N` ser perdido. Teste na Task 9 (roteiro Playwright).
3. Telefone mal formatado ou com DDD de outro país: o banco aceita só 11 dígitos nacionais (`^\d{11}$` depois de tirar não dígitos); o front formata. Teste na Task 7 (`salvar_telefone` recusa `123`).
4. Inscrição repetida e reinscrição depois de desistir: `inscrever` duas vezes não duplica nem erra; desistir e inscrever de novo reativa a mesma linha e o `vao` volta a contar. Teste na Task 7.
5. Ação despublicada depois da inscrição: quem estava inscrito não vê mais detalhe e contato de uma ação que saiu de `publicada`, salvo organizador e moderador. Teste na Task 7 (`combinado` exige `status = 'publicada'` para inscritos).

---

### Task 1: Renomear `mockup/` para `app/`

**Files:**
- Rename: `mockup/` → `app/` (git mv)
- Modify: `.github/workflows/pages.yml`, `tests/test_mockup.py`, `scripts/bora_lula.py`, `README.md`, `CLAUDE.md`

**Interfaces:**
- Produces: a pasta `app/` com `index.html`, `dados.js`, `lugares.js`, `fundo.js`, `leaflet.css`. Toda task seguinte fala em `app/`.

- [ ] **Step 1: Mover a pasta e trocar as referências**

```bash
git mv mockup app
sed -i 's#"mockup"#"app"#g; s#path: mockup#path: app#g' tests/test_mockup.py
sed -i 's#path: mockup#path: app#; s#"mockup/\*\*"#"app/**"#; s#Publicar mockup#Publicar app#' .github/workflows/pages.yml
sed -i 's#RAIZ / "mockup"#RAIZ / "app"#g' scripts/bora_lula.py
sed -i 's#`mockup/#`app/#g; s#mockup/index.html#app/index.html#g' README.md CLAUDE.md
grep -rn "mockup" tests scripts .github README.md CLAUDE.md
```

O `grep` final só pode devolver menções em prosa ("o mockup validou...") e o nome do arquivo de teste. Troque à mão o que sobrar de caminho. Em `tests/test_mockup.py`, a função `test_workflow_do_pages_publica_so_a_pasta_mockup` passa a checar `"path: app"` (o sed já cuidou).

- [ ] **Step 2: Rodar os testes**

Run: `python -m pytest tests -q`
Expected: todos passam (os mesmos de antes).

- [ ] **Step 3: Commit e push**

```bash
git add -A
git commit -m "Renomear mockup/ para app/: a pasta vira o app de verdade"
git push
```

Confira em https://github.com/guipfranco/acoes-segundo-turno/actions que o workflow do Pages rodou e o site continua no ar.

---

### Task 2: Contrato da camada de dados e miolo de exemplo (`app/api-exemplo.js`)

**Files:**
- Create: `app/api-exemplo.js`
- Create: `tests/js/api-exemplo.test.js`
- Modify: `app/dados.js` (campos de contato), `scripts/bora_lula.py:153`

**Interfaces:**
- Produces: `ApiExemplo.criar(dados)` devolve um objeto `API` com o contrato abaixo. No browser fica em `window.ApiExemplo`; no Node, `require('../../app/api-exemplo.js')`.

Contrato de `API` (vale para os dois miolos; todo método devolve Promise):

```
API.modo                      'exemplo' | 'supabase'
API.sessao()                  -> Pessoa | null
API.entrar()                  -> void   (exemplo: entra como dados.config.eu; supabase: redireciona ao Google)
API.sair()                    -> void
API.publico()                 -> { config:{vaquinha, frase, hoje}, organizacoes:[Organizacao], acoes:[AcaoPublica], turnos:[Turno] }
API.acao(id)                  -> { acao:AcaoPublica, turnos:[Turno], inscrita:[turnoId], combinado:Combinado|null } | null
API.salvarTelefone(telefone)  -> Pessoa
API.inscrever(turnoId)        -> { combinado:Combinado }   rejeita com Error e.codigo em
                                 precisa_entrar | sem_telefone | bloqueada | lotado | turno_passado | nao_publicada
API.desistir(turnoId)         -> void
API.minhasInscricoes()        -> [ { acao:AcaoPublica, turno:Turno } ]

Pessoa       = { id, nome, email, telefone|null, papel:'participante'|'organizador'|'moderador', bloqueada }
Organizacao  = { id, nome, tipo, verificada }
AcaoPublica  = { id, titulo, tipo, descricao, organizador, organizadorNome, organizacao|null,
                 lugar:{nome,bairro,cidade,lat,lon,online}, foto:{url,credito,pagina}|null,
                 prioritaria, status, contatoTipo, criadaEm }
Turno        = { id, acao, inicio:'AAAA-MM-DDTHH:MM', fim, lotacao|null, vao:n }
Combinado    = { detalhe:string|null, contato:{ tipo, whatsapp|null, link|null } }
```

`AcaoPublica` nunca carrega `detalhe`, `contatoWhatsapp` nem `contatoLink`: isso só sai em `Combinado`.

- [ ] **Step 1: Trocar `grupo` por forma de contato nos dados de exemplo**

```bash
python - <<'EOF'
import json
p='app/dados.js'; s=open(p,encoding='utf-8').read()
d=json.loads(s.split('=',1)[1].strip().rstrip(';'))
for a in d['acoes']:
    g=a.pop('grupo',None)
    a['contatoTipo']='link_grupo' if g else 'organizador_chama'
    a['contatoWhatsapp']=None; a['contatoLink']=g or None
# variedade para as telas: ação 2 pede para chamarem no WhatsApp, ação 3 é "eu entro em contato"
a2=next(a for a in d['acoes'] if a['id']==2); a2.update(contatoTipo='whatsapp',contatoWhatsapp='(11) 9xxxx-xxxx',contatoLink=None)
a3=next(a for a in d['acoes'] if a['id']==3); a3.update(contatoTipo='organizador_chama',contatoWhatsapp=None,contatoLink=None)
for p_ in d['pessoas']: p_.setdefault('email', None)
open(p,'w',encoding='utf-8',newline='\n').write('window.DADOS = '+json.dumps(d,ensure_ascii=False,indent=1)+';\n')
EOF
sed -i 's#"detalhe": "", "grupo": None,#"detalhe": "", "contatoTipo": "organizador_chama", "contatoWhatsapp": None, "contatoLink": None,#' scripts/bora_lula.py
grep -c '"grupo"' app/dados.js scripts/bora_lula.py
```

Expected: `0` nos dois arquivos.

- [ ] **Step 2: Escrever os testes do miolo de exemplo**

Create `tests/js/api-exemplo.test.js`:

```js
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ApiExemplo = require('../../app/api-exemplo.js');

function dados() {
  const src = fs.readFileSync(path.join(__dirname, '../../app/dados.js'), 'utf8');
  const window = {};
  new Function('window', src)(window);
  return window.DADOS;
}
const publicada = d => d.acoes.find(a => a.status === 'publicada' && a.contatoTipo === 'link_grupo');
const turnoFuturo = (d, a) => d.turnos.find(t => t.acao === a.id && t.inicio.slice(0, 10) >= d.config.hoje);

test('publico só traz publicadas e nunca detalhe nem contato', async () => {
  const d = dados(); const api = ApiExemplo.criar(d);
  const pub = await api.publico();
  assert.equal(pub.config.hoje, d.config.hoje);
  assert.ok(pub.acoes.length > 0);
  assert.ok(pub.acoes.every(a => a.status === 'publicada'));
  for (const a of pub.acoes) {
    assert.equal(a.detalhe, undefined); assert.equal(a.contatoLink, undefined); assert.equal(a.contatoWhatsapp, undefined);
    assert.equal(typeof a.organizadorNome, 'string'); assert.ok(['organizador_chama', 'whatsapp', 'link_grupo'].includes(a.contatoTipo));
  }
  const t = pub.turnos[0];
  assert.equal(typeof t.vao, 'number');
});

test('sessão começa como config.eu; sair e entrar', async () => {
  const d = dados(); const api = ApiExemplo.criar(d);
  assert.equal((await api.sessao()).id, d.config.eu);
  await api.sair(); assert.equal(await api.sessao(), null);
  await api.entrar(); assert.equal((await api.sessao()).id, d.config.eu);
});

test('acao: combinado só para inscrito; inscrever e desistir mexem em vao e inscrita', async () => {
  const d = dados(); const api = ApiExemplo.criar(d);
  const a = publicada(d); const t = turnoFuturo(d, a);
  // garante que config.eu não está inscrito nesse turno
  d.inscricoes = d.inscricoes.filter(i => !(i.turno === t.id && i.pessoa === d.config.eu));
  let r = await api.acao(a.id);
  assert.equal(r.combinado, null); assert.deepEqual(r.inscrita, []);
  const antes = r.turnos.find(x => x.id === t.id).vao;
  const ins = await api.inscrever(t.id);
  assert.equal(ins.combinado.contato.tipo, 'link_grupo'); assert.equal(ins.combinado.contato.link, a.contatoLink);
  r = await api.acao(a.id);
  assert.deepEqual(r.inscrita, [t.id]); assert.equal(r.turnos.find(x => x.id === t.id).vao, antes + 1);
  await api.inscrever(t.id); // repetir não duplica
  assert.equal((await api.acao(a.id)).turnos.find(x => x.id === t.id).vao, antes + 1);
  await api.desistir(t.id);
  r = await api.acao(a.id);
  assert.equal(r.combinado, null); assert.equal(r.turnos.find(x => x.id === t.id).vao, antes);
  await api.inscrever(t.id); // reinscrever depois de desistir
  assert.equal((await api.acao(a.id)).turnos.find(x => x.id === t.id).vao, antes + 1);
});

test('erros: precisa_entrar, sem_telefone, bloqueada, lotado, turno_passado, nao_publicada', async () => {
  const d = dados(); const api = ApiExemplo.criar(d);
  const a = publicada(d); const t = turnoFuturo(d, a);
  d.inscricoes = d.inscricoes.filter(i => !(i.turno === t.id && i.pessoa === d.config.eu));
  await api.sair();
  await assert.rejects(api.inscrever(t.id), e => e.codigo === 'precisa_entrar');
  await api.entrar();
  const eu = d.pessoas.find(p => p.id === d.config.eu);
  eu.telefone = null;
  await assert.rejects(api.inscrever(t.id), e => e.codigo === 'sem_telefone');
  await api.salvarTelefone('(11) 9xxxx-xxxx');
  eu.bloqueada = true;
  await assert.rejects(api.inscrever(t.id), e => e.codigo === 'bloqueada');
  eu.bloqueada = false;
  d.inscricoes.push({ id: 99902, pessoa: 99, turno: t.id, criadaEm: d.config.hoje, canceladaEm: null, presenca: null });
  t.lotacao = d.inscricoes.filter(i => i.turno === t.id && !i.canceladaEm).length; // >= 1
  await assert.rejects(api.inscrever(t.id), e => e.codigo === 'lotado');
  t.lotacao = null;
  const passado = { id: 99901, acao: a.id, inicio: '2020-01-01T10:00', fim: '2020-01-01T12:00', lotacao: null };
  d.turnos.push(passado);
  await assert.rejects(api.inscrever(passado.id), e => e.codigo === 'turno_passado');
  const naoPub = d.acoes.find(x => x.status !== 'publicada'); const tn = d.turnos.find(x => x.acao === naoPub.id);
  await assert.rejects(api.inscrever(tn.id), e => e.codigo === 'nao_publicada');
  await api.sair();
  assert.equal(await api.acao(naoPub.id), null); // deslogado não vê ação fora de publicada
});

test('salvarTelefone valida 11 dígitos e minhasInscricoes lista só as ativas', async () => {
  const d = dados(); const api = ApiExemplo.criar(d);
  await assert.rejects(api.salvarTelefone('123'), e => e.codigo === 'telefone_invalido');
  const p = await api.salvarTelefone('11988887777');
  assert.equal(p.telefone, '(11) 98888-7777');
  const a = publicada(d); const t = turnoFuturo(d, a);
  await api.inscrever(t.id);
  const minhas = await api.minhasInscricoes();
  assert.ok(minhas.some(m => m.turno.id === t.id && m.acao.id === a.id));
  assert.ok(minhas.every(m => m.acao.detalhe === undefined));
  await api.desistir(t.id);
  assert.ok(!(await api.minhasInscricoes()).some(m => m.turno.id === t.id));
});
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `node --test tests/js`
Expected: falha com `Cannot find module '../../app/api-exemplo.js'`.

- [ ] **Step 4: Escrever `app/api-exemplo.js`**

```js
// Miolo de exemplo da camada de dados: opera sobre window.DADOS em memória.
// Mesmo contrato de api-supabase.js. Serve para desenvolver e para o protótipo seguir navegável.
(function (raiz, fabrica) {
  if (typeof module !== 'undefined' && module.exports) module.exports = fabrica();
  else raiz.ApiExemplo = fabrica();
})(typeof window !== 'undefined' ? window : this, function () {
  function erro(codigo) { const e = new Error(codigo); e.codigo = codigo; return e; }
  function formatarTelefone(t) {
    const d = String(t || '').replace(/[^\dx]/gi, '');
    if (!/^\d{2}9[\dx]{8}$/i.test(d)) throw erro('telefone_invalido');
    return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
  }
  function criar(dados) {
    let sessao = dados.config.eu;
    const pessoa = id => dados.pessoas.find(p => p.id === id);
    const org = id => dados.organizacoes.find(o => o.id === id);
    const ativas = tid => dados.inscricoes.filter(i => i.turno === tid && !i.canceladaEm);
    const publica = a => ({
      id: a.id, titulo: a.titulo, tipo: a.tipo, descricao: a.descricao, organizador: a.organizador,
      organizadorNome: (pessoa(a.organizador) || { nome: '' }).nome, organizacao: a.organizacao,
      lugar: Object.assign({}, a.lugar), foto: a.foto ? Object.assign({}, a.foto) : null,
      prioritaria: !!a.prioritaria, status: a.status, contatoTipo: a.contatoTipo || 'organizador_chama', criadaEm: a.criadaEm,
    });
    const turno = t => ({ id: t.id, acao: t.acao, inicio: t.inicio, fim: t.fim, lotacao: t.lotacao || null, vao: ativas(t.id).length });
    const turnosDa = aid => dados.turnos.filter(t => t.acao === aid).sort((a, b) => a.inicio.localeCompare(b.inicio)).map(turno);
    const combinadoDe = a => ({ detalhe: a.detalhe || null, contato: { tipo: a.contatoTipo || 'organizador_chama', whatsapp: a.contatoWhatsapp || null, link: a.contatoLink || null } });
    const inscritaEm = aid => dados.turnos.filter(t => t.acao === aid && sessao != null && ativas(t.id).some(i => i.pessoa === sessao)).map(t => t.id);
    const podeVer = a => sessao != null && (a.organizador === sessao || (pessoa(sessao) || {}).papel === 'moderador' || (a.status === 'publicada' && inscritaEm(a.id).length > 0));
    const sessaoObj = () => { if (sessao == null) return null; const p = pessoa(sessao); return { id: p.id, nome: p.nome, email: p.email || null, telefone: p.telefone || null, papel: p.papel, bloqueada: !!p.bloqueada }; };
    return {
      modo: 'exemplo',
      async sessao() { return sessaoObj(); },
      async entrar() { sessao = dados.config.eu; },
      async sair() { sessao = null; },
      async publico() {
        return {
          config: { vaquinha: dados.config.vaquinha, frase: dados.config.frase, hoje: dados.config.hoje },
          organizacoes: dados.organizacoes.map(o => ({ id: o.id, nome: o.nome, tipo: o.tipo, verificada: !!o.verificada })),
          acoes: dados.acoes.filter(a => a.status === 'publicada').map(publica),
          turnos: dados.turnos.filter(t => (dados.acoes.find(a => a.id === t.acao) || {}).status === 'publicada').map(turno),
        };
      },
      async acao(id) {
        const a = dados.acoes.find(x => x.id === id);
        if (!a || (a.status !== 'publicada' && !(sessao != null && (a.organizador === sessao || (pessoa(sessao) || {}).papel === 'moderador')))) return null;
        return { acao: publica(a), turnos: turnosDa(a.id), inscrita: inscritaEm(a.id), combinado: podeVer(a) ? combinadoDe(a) : null };
      },
      async salvarTelefone(telefone) {
        if (sessao == null) throw erro('precisa_entrar');
        pessoa(sessao).telefone = formatarTelefone(telefone);
        return sessaoObj();
      },
      async inscrever(tid) {
        if (sessao == null) throw erro('precisa_entrar');
        const p = pessoa(sessao);
        if (p.bloqueada) throw erro('bloqueada');
        if (!p.telefone) throw erro('sem_telefone');
        const t = dados.turnos.find(x => x.id === tid); const a = t && dados.acoes.find(x => x.id === t.acao);
        if (!a || a.status !== 'publicada') throw erro('nao_publicada');
        if (t.inicio.slice(0, 10) < dados.config.hoje) throw erro('turno_passado');
        const ja = dados.inscricoes.find(i => i.turno === tid && i.pessoa === sessao);
        if (!(ja && !ja.canceladaEm)) {
          if (t.lotacao && ativas(tid).length >= t.lotacao) throw erro('lotado');
          if (ja) { ja.canceladaEm = null; ja.criadaEm = dados.config.hoje; }
          else dados.inscricoes.push({ id: Date.now() + Math.floor(Math.random() * 1000), pessoa: sessao, turno: tid, criadaEm: dados.config.hoje, canceladaEm: null, presenca: null });
        }
        return { combinado: combinadoDe(a) };
      },
      async desistir(tid) {
        if (sessao == null) throw erro('precisa_entrar');
        const i = dados.inscricoes.find(i => i.turno === tid && i.pessoa === sessao && !i.canceladaEm);
        if (i) i.canceladaEm = dados.config.hoje;
      },
      async minhasInscricoes() {
        if (sessao == null) return [];
        return dados.inscricoes.filter(i => i.pessoa === sessao && !i.canceladaEm).map(i => {
          const t = dados.turnos.find(x => x.id === i.turno); const a = t && dados.acoes.find(x => x.id === t.acao);
          return a ? { acao: publica(a), turno: turno(t) } : null;
        }).filter(Boolean).sort((p, q) => p.turno.inicio.localeCompare(q.turno.inicio));
      },
    };
  }
  return { criar, formatarTelefone };
});
```

- [ ] **Step 5: Rodar os testes**

Run: `node --test tests/js && python -m pytest tests -q`
Expected: os 5 testes Node passam; pytest passa (o teste `test_dados_sem_telefone_real` continua valendo).

- [ ] **Step 6: Commit e push**

```bash
git add app/api-exemplo.js app/dados.js scripts/bora_lula.py tests/js/api-exemplo.test.js
git commit -m "Camada de dados: contrato da API e miolo de exemplo em memória; forma de contato nos dados"
git push
```

---

### Task 3: `index.html` passa a ler pela API (modo exemplo, sem mudança visível)

**Files:**
- Create: `app/api.js` (escolhe o miolo), `app/config.js`
- Modify: `app/index.html` (scripts, helpers, `render`), `tests/test_mockup.py`

**Interfaces:**
- Consumes: `window.ApiExemplo.criar(window.DADOS)` (Task 2).
- Produces: `window.API` (contrato da Task 2); cache público `PUB` (`{config, organizacoes, acoes, turnos}`) e `estado.sessao` (`Pessoa|null`), `estado.acaoAberta` (retorno de `API.acao`), usados por todas as telas de participante. `recarregar()` recarrega `PUB` e `estado.sessao`. `render()` vira `async`.

- [ ] **Step 1: Criar `app/config.js` e `app/api.js`**

`app/config.js` (por enquanto sem Supabase; a Task 9 preenche):

```js
// Configuração pública do app. Sem `supabase`, o app roda no modo exemplo (dados fictícios em memória).
// A chave anon do Supabase é pública por desenho: o que protege os dados é o RLS no banco.
window.CONFIG = { supabase: null };
```

`app/api.js`:

```js
// Escolhe o miolo da camada de dados: Supabase quando configurado, senão o exemplo em memória.
// Forçar o exemplo mesmo com Supabase configurado: abrir com ?modo=exemplo
(function () {
  const forcaExemplo = new URLSearchParams(location.search).get('modo') === 'exemplo';
  const cfg = window.CONFIG && window.CONFIG.supabase;
  if (cfg && !forcaExemplo && window.ApiSupabase) window.API = window.ApiSupabase.criar(cfg);
  else window.API = window.ApiExemplo.criar(window.DADOS);
})();
```

- [ ] **Step 2: Trocar os scripts e os helpers no `index.html`**

Na tag `<script src="dados.js">`, substitua o bloco de scripts por:

```html
<script src="dados.js"></script>
<script src="lugares.js"></script>
<script src="fundo.js"></script>
<script src="config.js"></script>
<script src="api-exemplo.js"></script>
<script src="api.js"></script>
```

No bloco `// ---------- dados e helpers ----------`, troque as linhas de `const org=` até `function vaoNa` por:

```js
let PUB={config:{hoje:'',frase:'',vaquinha:'#'},organizacoes:[],acoes:[],turnos:[]};
const org=id=>PUB.organizacoes.find(o=>o.id===id);
const pessoa=id=>DADOS.pessoas.find(p=>p.id===id); // só telas de organizador e moderador (modo exemplo)
const acao=id=>PUB.acoes.find(a=>a.id===id);
const eu=()=>estado.sessao?estado.sessao.id:null;
const turnosDa=id=>PUB.turnos.filter(t=>t.acao===id).sort((a,b)=>a.inicio.localeCompare(b.inicio));
function turnosFuturos(id){return turnosDa(id).filter(t=>t.inicio.slice(0,10)>=PUB.config.hoje)}
```

e, mais abaixo, estas três:

```js
const vaoNo=t=>t.vao||0;
const estouInscrito=tid=>!!(estado.acaoAberta&&estado.acaoAberta.inscrita.includes(tid));
// helpers só do modo exemplo, para Criar, Minhas e Fila (que ainda leem DADOS até o próximo plano)
const acaoExemplo=id=>DADOS.acoes.find(a=>a.id===id);
const turnosDaExemplo=id=>DADOS.turnos.filter(t=>t.acao===id).sort((a,b)=>a.inicio.localeCompare(b.inicio));
const inscritosNo=tid=>DADOS.inscricoes.filter(i=>i.turno===tid&&!i.canceladaEm);
const vaoNaExemplo=id=>turnosDaExemplo(id).reduce((n,t)=>n+inscritosNo(t.id).length,0);
function vaoNa(id){const ts=turnosDa(id);return ts.length?ts.reduce((n,t)=>n+vaoNo(t),0):(API.modo==='exemplo'?vaoNaExemplo(id):0)}
```

Em `editar`, `encerrar`, `aprovar`, `recusar`, `despublicar` e no ramo `c.editando` de `publicarAcao`, troque `acao(` por `acaoExemplo(`: essas funções mexem em ações fora de `publicada`, que não estão em `PUB`. Em `telaMinhas`, `telaFila`, `editar` e `atualizarTurnos`, troque `turnosDa(` por `turnosDaExemplo(`.

Acrescente ao objeto `estado` as chaves `sessao:null,acaoAberta:null`. Troque `nomeOrganizador` para usar `a.organizadorNome`:

```js
function nomeOrganizador(a){if(a.organizacao){const o=org(a.organizacao)||DADOS.organizacoes.find(x=>x.id===a.organizacao);return esc(o.nome)+(o.verificada?' <span class="selo">✓ verificada</span>':'')}return esc(a.organizadorNome!=null?a.organizadorNome:(pessoa(a.organizador)||{}).nome)}
```

(o fallback para `pessoa(...)` e `DADOS.organizacoes` serve à Fila e a Minhas ações no modo exemplo, que passam ações cruas do `DADOS` para `cardAcao`.)

Substitua toda ocorrência de `DADOS.config.hoje` por `PUB.config.hoje` e `DADOS.config.frase` por `PUB.config.frase`. Em `botaoTurno` e `telaAcao` (telas de participante), `inscritosNo(t.id).length` vira `vaoNo(t)`; em `telaMinhas` fica `inscritosNo` (lista de nomes do exemplo). As telas Minhas, Fila e Criar continuam lendo `DADOS.*` (modo exemplo); nelas, `eu()` já funciona porque a sessão de exemplo começa como `config.eu`.

```bash
sed -i 's/DADOS\.config\.hoje/PUB.config.hoje/g; s/DADOS\.config\.frase/PUB.config.frase/g' app/index.html
grep -n "inscritosNo\|DADOS\.config\.eu\|DADOS\.turnos\|DADOS\.acoes\|DADOS\.inscricoes" app/index.html
```

O que o `grep` listar dentro de `telaMinhas`, `telaFila`, `telaCriar`, `publicarAcao`, `atualizarTurnos`, `editar`, `historicoOrganizador`, `bloquear`, `marcarPresenca` pode ficar. O que estiver em `telaAcao`, `telaInicio`, `telaMapa`, `acoesVisiveis`, `cardAcao`, `cardEvento`, `botaoTurno` precisa virar `PUB`/`vaoNo`/`estouInscrito`.

- [ ] **Step 3: `render` assíncrono e `recarregar`**

Substitua `function render(){` ... até o fim da função por:

```js
async function recarregar(){PUB=await API.publico();estado.sessao=await API.sessao()}
let renderN=0;
async function render(){
  const n=++renderN;
  const h=location.hash||'#/inicio';const [,rota,arg]=h.split('/');
  if(rota!=='acao')estado.inscrevendo=null;if(rota!=='fila'){estado.recusando=null;estado.erroRecusa=null}
  if(rota==='acao'){estado.acaoAberta=await API.acao(Number(arg));if(n!==renderN)return}
  if(mapa){mapa.remove();mapa=null;marcadores=[]}
  const app=document.getElementById('app');
  const soExemplo=['criar','minhas','fila'].includes(rota)&&API.modo!=='exemplo';
  app.innerHTML=soExemplo?'<div class="pagina"><h1>Em breve</h1><p>Criar ação, Minhas ações e a Fila chegam na próxima etapa.</p></div>':
    rota==='acao'?telaAcao(Number(arg)):rota==='criar'?telaCriar():rota==='minhas'?telaMinhas():rota==='fila'?telaFila():rota==='mapa'?telaMapa():telaInicio();
  document.querySelectorAll('nav a[data-rota]').forEach(a=>a.classList.toggle('ativo',a.dataset.rota===(rota||'inicio')));
  document.querySelectorAll('nav a[data-so-exemplo]').forEach(a=>a.style.display=API.modo==='exemplo'?'':'none');
  document.getElementById('doar').href=PUB.config.vaquinha||'#';
  if(rota==='mapa')montarMapa();
  if((rota||'inicio')==='inicio')chutarCidade();
  const ab=estado.acaoAberta;
  if(rota==='acao'&&ab&&!ehOnline(ab.acao))montarMiniMapa(ab.acao.lugar,false);
  if(rota==='criar'&&estado.criar.passo===2&&!estado.criar.online&&estado.criar.lugar.lat!=null){const r=montarMiniMapa(estado.criar.lugar,true);if(r)r.mk.on('dragend',()=>{const p=r.mk.getLatLng();estado.criar.lugar.lat=p.lat;estado.criar.lugar.lon=p.lng})}
  if(rota!=='mapa')window.scrollTo(0,0);
}
async function sincronizar(){await recarregar();await render()}
document.addEventListener('click',e=>{if(!e.target.closest('#topo,.caixa')){const s=document.getElementById('sugestoes');if(s)s.style.display='none'}});
window.addEventListener('hashchange',render);
window.addEventListener('DOMContentLoaded',sincronizar);
```

Na `<nav>`, marque os três links de organizador/moderador com `data-so-exemplo`:

```html
<a href="#/criar" data-rota="criar" data-so-exemplo onclick="novaCriacao()"><span>＋</span><span>Criar ação</span></a>
<a href="#/minhas" data-rota="minhas" data-so-exemplo><span>👤</span><span>Minhas</span></a>
<a href="#/fila" data-rota="fila" data-so-exemplo><span>✅</span><span>Fila</span></a>
```

Em `telaAcao(id)`, a primeira linha vira:

```js
function telaAcao(id){const ab=estado.acaoAberta;if(!ab)return '<div class="pagina"><p>Ação não encontrada.</p></div>';const a=ab.acao,fechada=a.status!=='publicada';
  const ts=ab.turnos,futuros=ts.filter(t=>t.inicio.slice(0,10)>=PUB.config.hoje),ins=estado.inscrevendo;const inscritoEmAlgum=ab.inscrita.length>0;
```

e o bloco `Combinado` passa a ler `ab.combinado` (a Task 4 troca o conteúdo; aqui só precisa não quebrar):

```js
${ab.combinado?`<h2>Combinado</h2><div class="aviso"><p>${esc(ab.combinado.detalhe||'')}</p>${ab.combinado.contato.link?`<a class="btn" href="${esc(ab.combinado.contato.link)}" target="_blank" rel="noopener">Entrar no grupo do WhatsApp</a> `:''}<button class="btn sec" onclick="compartilhar()">Compartilhar</button></div>`:''}
```

As funções do mockup que mutam `DADOS` (`publicarAcao`, `encerrar`, `aprovar`, `recusar`, `darSelo`, `despublicar`, `bloquear`, `atualizarTurnos`) continuam iguais, mas onde chamam `render()` ou mudam `location.hash` passam a chamar `sincronizar()` antes, para `PUB` refletir a mutação. Regra prática: troque `render()` por `sincronizar()` nessas oito funções.

- [ ] **Step 4: Inscrever e desistir pela API (versão mínima; a Task 4 refaz o fluxo)**

```js
async function inscrever(tid){try{await API.inscrever(tid)}catch(e){alert('Não deu: '+e.codigo);return}estado.inscrevendo=null;await sincronizar()}
async function desistir(tid){await API.desistir(tid);await sincronizar()}
```

- [ ] **Step 5: Ajustar os testes de tela**

Em `tests/test_mockup.py`, troque as asserções de implementação que mudaram de propósito:

```python
# em test_formato_presencial_ou_online_em_toda_a_cadeia:
    assert "!ehOnline(ab.acao)" in HTML  # ação online não monta minimapa
# em test_mapa_virou_rota_propria: mantém "rota==='mapa'?telaMapa()" (continua existindo)
```

Acrescente:

```python
def test_telas_de_participante_leem_pela_api():
    for s in ['src="api.js"', 'src="api-exemplo.js"', 'src="config.js"', "async function render", "await API.acao(",
              "API.publico()", "const vaoNo=", "estado.acaoAberta", "data-so-exemplo"]:
        assert s in HTML, s
    inicio = HTML[HTML.index("function acoesVisiveis"):HTML.index("function telaCriar")]
    assert "DADOS.acoes" not in inicio and "DADOS.inscricoes" not in inicio and "DADOS.config" not in inicio
```

- [ ] **Step 6: Rodar os testes e abrir o app**

Run: `python -m pytest tests -q && node --test tests/js`
Expected: passam.

Run: `python -m http.server 8000 -d app` e abra http://localhost:8000/#/inicio, `#/mapa`, uma ação, `#/minhas`, `#/fila`. Conferir: vitrine igual à de antes, Vou e desistir funcionam, `N vão` muda, Minhas e Fila seguem iguais. Pare o servidor.

- [ ] **Step 7: Commit e push**

```bash
git add app/index.html app/api.js app/config.js tests/test_mockup.py
git commit -m "Telas de participante leem pela camada de dados; render assíncrono; modo exemplo escolhido em api.js"
git push
```

---

### Task 4: Fluxo do Vou com telefone e forma de contato

**Files:**
- Modify: `app/index.html` (`telaAcao`, `botaoTurno`, `iniciarVou`, `inscrever`), `tests/test_mockup.py`

**Interfaces:**
- Consumes: `API.sessao`, `API.entrar`, `API.salvarTelefone`, `API.inscrever`, `estado.acaoAberta.combinado`.
- Produces: `continuarVouPendente()` (usado na Task 5 e na volta do Google na Task 8), chave `localStorage.vouPendente`.

- [ ] **Step 1: Teste de tela**

Acrescente em `tests/test_mockup.py`:

```python
def test_vou_pede_telefone_uma_vez_e_mostra_a_forma_de_contato():
    acao = HTML[HTML.index("function telaAcao"):HTML.index("function montarMiniMapa")]
    assert "Receber código" not in HTML and "Código que chegou" not in HTML
    for s in ["Seu nome e telefone vão para quem organiza esta ação", "vai entrar em contato", "Chamar no WhatsApp",
              "Entrar no grupo do WhatsApp", "wa.me/55", "organizador_chama", "'whatsapp'", "link_grupo"]:
        assert s in acao, s
    assert "function continuarVouPendente" in HTML and "vouPendente" in HTML
```

Run: `python -m pytest tests -q -k vou_pede` → FAIL.

- [ ] **Step 2: Implementar**

Troque `inscrever`, `iniciarVou`, `pedirCodigo` e `botaoTurno` por:

```js
async function iniciarVou(tid){
  if(!estado.sessao){localStorage.setItem('vouPendente',String(tid));await API.entrar();await continuarVouPendente();return}
  estado.inscrevendo={turno:tid,telefone:estado.sessao.telefone||'',erro:null};render()}
async function continuarVouPendente(){const tid=Number(localStorage.getItem('vouPendente'));if(!tid)return;
  estado.sessao=await API.sessao();if(!estado.sessao)return;localStorage.removeItem('vouPendente');
  estado.inscrevendo={turno:tid,telefone:estado.sessao.telefone||'',erro:null};await render()}
const MENSAGEM={precisa_entrar:'Entre para se inscrever.',sem_telefone:'Informe seu WhatsApp.',telefone_invalido:'Telefone no formato (11) 9xxxx-xxxx.',bloqueada:'Sua conta está bloqueada.',lotado:'Esse horário lotou.',turno_passado:'Esse horário já passou.',nao_publicada:'Esta ação não está aberta a inscrições.'};
async function confirmarVou(tid){const ins=estado.inscrevendo;const tel=(document.getElementById('vtel')||{}).value||'';
  try{if(tel!==(estado.sessao.telefone||''))estado.sessao=await API.salvarTelefone(tel);await API.inscrever(tid)}
  catch(e){ins.erro=MENSAGEM[e.codigo]||'Não deu. Tente de novo.';ins.telefone=tel;render();return}
  estado.inscrevendo=null;await sincronizar()}
async function inscrever(tid){return confirmarVou(tid)}
function botaoTurno(t){const n=vaoNo(t);
  if(t.inicio.slice(0,10)<PUB.config.hoje)return `<button class="btn" disabled>horário encerrado</button>${estouInscrito(t.id)?' <span class="selo">você estava inscrito</span>':''}`;
  if(estouInscrito(t.id))return `<span class="selo">Você vai ✓</span> <button class="btn sec mini" onclick="desistir(${t.id})">desistir</button>`;
  if(t.lotacao&&n>=t.lotacao)return `<button class="btn" disabled>lotado</button>`;
  return `<button class="btn" onclick="iniciarVou(${t.id})">Vou</button>`}
```

Em `telaAcao`, o formulário dentro de cada horário vira:

```js
${ins&&ins.turno===t.id?`<div class="sec" style="margin-top:8px">Você: <strong>${esc(estado.sessao.nome)}</strong></div><label>Seu WhatsApp</label><input id="vtel" value="${esc(ins.telefone)}" placeholder="(11) 9xxxx-xxxx" inputmode="tel"><p class="sec" style="margin-top:8px">Seu nome e telefone vão para quem organiza esta ação.</p>${ins.erro?`<div class="erro">${esc(ins.erro)}</div>`:''}<div style="margin-top:8px"><button class="btn" onclick="confirmarVou(${t.id})">Confirmar</button> <button class="btn sec mini" onclick="estado.inscrevendo=null;render()">Cancelar</button></div>`:''}
```

E o bloco Combinado:

```js
function blocoCombinado(a,c){const ct=c.contato;const tel=ct.whatsapp?ct.whatsapp.replace(/\D/g,''):'';
  const como=ct.tipo==='organizador_chama'?`<p><strong>${nomeOrganizador(a)}</strong> vai entrar em contato pelo seu WhatsApp.</p>`:
    ct.tipo==='whatsapp'?`<p>Chame quem organiza para combinar:</p><a class="btn" href="https://wa.me/55${tel}" target="_blank" rel="noopener">Chamar no WhatsApp</a> `:
    ct.tipo==='link_grupo'&&ct.link?`<a class="btn" href="${esc(ct.link)}" target="_blank" rel="noopener">Entrar no grupo do WhatsApp</a> `:'';
  return `<h2>Combinado</h2><div class="aviso">${c.detalhe?`<p>${esc(c.detalhe)}</p>`:''}${como}<button class="btn sec" onclick="compartilhar()">Compartilhar</button></div>`}
```

e em `telaAcao`: `${ab.combinado?blocoCombinado(a,ab.combinado):''}`. Troque "turno encerrado" por "horário encerrado" no teste `test_turno_encerrado_vence_inscrito`.

- [ ] **Step 3: Rodar testes e conferir no browser**

Run: `python -m pytest tests -q && node --test tests/js`
Expected: passam. No browser (`python -m http.server 8000 -d app`): abrir ação 1, Vou, confirmar telefone, ver "Entrar no grupo"; ação 2 mostra "Chamar no WhatsApp"; ação 3 mostra "vai entrar em contato".

- [ ] **Step 4: Commit e push**

```bash
git add app/index.html tests/test_mockup.py
git commit -m "Vou: telefone pedido uma vez, confirmação e bloco Combinado conforme a forma de contato"
git push
```

---

### Task 5: Entrar, Sair e Minhas inscrições

**Files:**
- Modify: `app/index.html` (nav, rota `#/inscricoes`, `telaInscricoes`), `tests/test_mockup.py`

**Interfaces:**
- Consumes: `API.sessao`, `API.entrar`, `API.sair`, `API.minhasInscricoes`, `cardEvento`.

- [ ] **Step 1: Teste de tela**

```python
def test_entrar_sair_e_minhas_inscricoes():
    for s in ["function telaInscricoes", "rota==='inscricoes'", 'data-rota="inscricoes"', "API.minhasInscricoes()",
              "Entrar com Google", "function entrar", "function sair", "Você ainda não se inscreveu"]:
        assert s in HTML, s
```

Run: `python -m pytest tests -q -k entrar_sair` → FAIL.

- [ ] **Step 2: Implementar**

Na `<nav>`, antes do link Doar:

```html
<a href="#/inscricoes" data-rota="inscricoes"><span>🙋</span><span>Inscrições</span></a>
<a href="#" id="conta" onclick="return contaClique()"><span>👋</span><span id="conta-rotulo">Entrar</span></a>
```

No script:

```js
async function entrar(){await API.entrar();await sincronizar()}
async function sair(){await API.sair();localStorage.removeItem('vouPendente');await sincronizar()}
function contaClique(){if(estado.sessao)sair();else entrar();return false}
function telaInscricoes(){
  if(!estado.sessao)return `<div class="pagina estreita"><h1>Minhas inscrições</h1><p>Entre para ver em que ações você disse que vai.</p><button class="btn" onclick="entrar()">Entrar com Google</button></div>`;
  const lista=estado.minhasInscricoes||[];
  return `<div class="pagina"><h1>Minhas inscrições</h1><p class="sec" style="font-size:15px">${esc(estado.sessao.nome)}${estado.sessao.telefone?`, ${esc(estado.sessao.telefone)}`:''}</p>
  ${lista.length?`<div class="trilho">${lista.map(m=>cardEvento({a:m.acao,t:m.turno})).join('')}</div>`:'<div class="vazio"><p>Você ainda não se inscreveu em nenhuma ação.</p><a class="btn" href="#/inicio">Ver ações</a></div>'}</div>`}
```

Em `render`, logo depois do `if(rota==='acao'){...}`: `if(rota==='inscricoes'){estado.minhasInscricoes=await API.minhasInscricoes();if(n!==renderN)return}` e na cadeia de telas `rota==='inscricoes'?telaInscricoes():`. Ainda em `render`, depois de ajustar os links da nav:

```js
document.getElementById('conta-rotulo').textContent=estado.sessao?'Sair':'Entrar';
```

No modo exemplo, `API.entrar()` resolve na hora; o rótulo "Entrar com Google" fica igual nos dois modos.

- [ ] **Step 3: Rodar testes, conferir e commitar**

Run: `python -m pytest tests -q && node --test tests/js` → passam. No browser: Sair, abrir ação, Vou leva a entrar e reabre o formulário de telefone (via `vouPendente`); `#/inscricoes` lista a inscrição.

```bash
git add app/index.html tests/test_mockup.py
git commit -m "Entrar e sair na barra; tela Minhas inscrições"
git push
```

---

### Task 6: Supabase local, esquema e views públicas

**Files:**
- Create: `supabase/config.toml` (gerado por `npx supabase init`), `supabase/migrations/20261008000001_esquema.sql`, `supabase/seed.sql`
- Modify: `.gitignore`, `package.json` (novo, só para fixar a versão da CLI)

**Interfaces:**
- Produces: tabelas `pessoa`, `organizacao`, `acao`, `turno`, `inscricao`, `pedido_organizador`, `configuracao`, `registro_moderacao`; views `acao_publica`, `turno_publico`, `organizacao_publica`, `configuracao_publica`; funções `eh_moderador()`, `hoje_brasilia()`; trigger que cria `pessoa` ao criar usuário. A Task 7 adiciona RLS e as RPCs.

- [ ] **Step 1: Iniciar a CLI e o banco local**

```bash
npm init -y >/dev/null && npm install --save-dev supabase@1.200.3
npx supabase init
npx supabase start
```

Anote o que `supabase start` imprime: `API URL` (http://127.0.0.1:54321), `anon key` e `service_role key`. Acrescente ao `.gitignore`:

```
node_modules/
supabase/.branches/
supabase/.temp/
.env
```

- [ ] **Step 2: Escrever a migração do esquema**

`supabase/migrations/20261008000001_esquema.sql`:

```sql
-- Esquema da v1. Horários em timestamp sem fuso, sempre hora de Brasília.
create type papel as enum ('participante','organizador','moderador');
create type tipo_org as enum ('mandato','partido','movimento','coletivo');
create type tipo_acao as enum ('panfletagem','adesivaço','roda de conversa','ligatona','porta a porta','bandeiraço','outro');
create type status_acao as enum ('rascunho','em análise','publicada','recusada','encerrada');
create type contato_tipo as enum ('organizador_chama','whatsapp','link_grupo');
create type status_pedido as enum ('em análise','aprovado','recusado');

create table organizacao (
  id bigint generated always as identity primary key,
  nome text not null unique,
  tipo tipo_org not null,
  verificada boolean not null default false,
  criada_em timestamptz not null default now()
);

create table pessoa (
  id uuid primary key references auth.users(id) on delete cascade,
  nome text not null,
  email text,
  telefone text check (telefone is null or telefone ~ '^\(\d{2}\) 9\d{4}-\d{4}$'),
  papel papel not null default 'participante',
  organizacao bigint references organizacao(id),
  bloqueada boolean not null default false,
  criada_em timestamptz not null default now()
);

create table acao (
  id bigint generated always as identity primary key,
  titulo text not null,
  tipo tipo_acao not null,
  descricao text not null default '',
  organizador uuid not null references pessoa(id),
  organizacao bigint references organizacao(id),
  lugar_nome text, bairro text, cidade text,
  lat double precision, lon double precision,
  online boolean not null default false,
  detalhe text,
  contato_tipo contato_tipo not null default 'organizador_chama',
  contato_whatsapp text,
  contato_link text,
  foto_url text, foto_credito text, foto_pagina text,
  prioritaria boolean not null default false,
  status status_acao not null default 'em análise',
  motivo_recusa text,
  criada_em timestamptz not null default now(),
  check (online or (lat is not null and lon is not null and lugar_nome is not null))
);

create table turno (
  id bigint generated always as identity primary key,
  acao bigint not null references acao(id) on delete cascade,
  inicio timestamp not null,
  fim timestamp not null,
  lotacao int check (lotacao is null or lotacao > 0),
  check (fim > inicio)
);
create index turno_acao on turno(acao);

create table inscricao (
  id bigint generated always as identity primary key,
  pessoa uuid not null references pessoa(id) on delete cascade,
  turno bigint not null references turno(id) on delete cascade,
  criada_em timestamptz not null default now(),
  cancelada_em timestamptz,
  presenca boolean,
  unique (pessoa, turno)
);
create index inscricao_turno on inscricao(turno);

create table pedido_organizador (
  id bigint generated always as identity primary key,
  pessoa uuid not null references pessoa(id) on delete cascade,
  organizacao bigint references organizacao(id),
  organizacao_proposta text,
  telefone text not null,
  como_confirmar text not null,
  status status_pedido not null default 'em análise',
  motivo_recusa text,
  decidido_por uuid references pessoa(id),
  decidido_em timestamptz,
  criado_em timestamptz not null default now()
);

create table configuracao (chave text primary key, valor text not null);
insert into configuracao values
  ('vaquinha','https://exemplo.vaquinha.oficial/lula'),
  ('frase','O que você pode fazer hoje para eleger o Lula');

create table registro_moderacao (
  id bigint generated always as identity primary key,
  moderador uuid not null references pessoa(id),
  acao_feita text not null,
  alvo_tipo text not null,
  alvo_id text not null,
  motivo text,
  criado_em timestamptz not null default now()
);

-- helpers (security definer: não disparam RLS, evitam recursão nas políticas de pessoa)
create function hoje_brasilia() returns date language sql stable as
  $$ select (now() at time zone 'America/Sao_Paulo')::date $$;
create function eh_moderador() returns boolean language sql stable security definer set search_path = public as
  $$ select exists (select 1 from pessoa where id = auth.uid() and papel = 'moderador' and not bloqueada) $$;

-- cria a pessoa no primeiro login
create function nova_pessoa() returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into pessoa (id, nome, email) values (
    new.id,
    coalesce(new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'name', split_part(coalesce(new.email,''),'@',1), 'Sem nome'),
    new.email);
  return new;
end $$;
create trigger ao_criar_usuario after insert on auth.users for each row execute function nova_pessoa();

-- views públicas: pertencem ao postgres e por isso ignoram RLS de propósito; só expõem colunas públicas
create view acao_publica as
  select a.id, a.titulo, a.tipo, a.descricao, a.organizador, p.nome as organizador_nome, a.organizacao,
         a.lugar_nome, a.bairro, a.cidade, a.lat, a.lon, a.online,
         a.foto_url, a.foto_credito, a.foto_pagina, a.prioritaria, a.contato_tipo, a.status, a.criada_em
  from acao a join pessoa p on p.id = a.organizador
  where a.status = 'publicada';
create view turno_publico as
  select t.id, t.acao, t.inicio, t.fim, t.lotacao,
         (select count(*) from inscricao i where i.turno = t.id and i.cancelada_em is null)::int as vao
  from turno t join acao a on a.id = t.acao
  where a.status = 'publicada';
create view organizacao_publica as select id, nome, tipo, verificada from organizacao;
create view configuracao_publica as select chave, valor from configuracao;
```

- [ ] **Step 3: Semente para desenvolvimento**

`supabase/seed.sql` (só roda no banco local; produção começa vazia):

```sql
-- Usuários de exemplo (senha 'senha123' só no banco local). O trigger cria as pessoas.
insert into auth.users (id, instance_id, aud, role, email, encrypted_password, email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
                        confirmation_token, recovery_token, email_change_token_new, email_change, created_at, updated_at)
values
 ('00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000000','authenticated','authenticated','ana@exemplo.local', extensions.crypt('senha123', extensions.gen_salt('bf')), now(), '{"provider":"email","providers":["email"]}', '{"full_name":"Ana Souza"}', '', '', '', '', now(), now()),
 ('00000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000000','authenticated','authenticated','carlos@exemplo.local', extensions.crypt('senha123', extensions.gen_salt('bf')), now(), '{"provider":"email","providers":["email"]}', '{"full_name":"Carlos Lima"}', '', '', '', '', now(), now());
update pessoa set papel='moderador' where id='00000000-0000-0000-0000-000000000001';
update pessoa set papel='organizador', telefone='(11) 91111-1111' where id='00000000-0000-0000-0000-000000000002';
insert into organizacao (nome, tipo, verificada) values ('Mandato Vereadora Rosa','mandato',true), ('Coletivo Periferia Viva','coletivo',false);
insert into acao (titulo, tipo, descricao, organizador, organizacao, lugar_nome, bairro, cidade, lat, lon, detalhe, contato_tipo, contato_link, status)
values ('Panfletagem na estação Grajaú','panfletagem','Vamos distribuir material do Lula na saída da estação.','00000000-0000-0000-0000-000000000002',1,'Estação Grajaú','Grajaú','São Paulo',-23.7746,-46.6978,'Saída principal, perto do ponto de ônibus.','link_grupo','https://chat.whatsapp.com/exemplo','publicada');
insert into turno (acao, inicio, fim, lotacao) values (1, (hoje_brasilia() + 1)::timestamp + time '09:00', (hoje_brasilia() + 1)::timestamp + time '12:00', null);
```

- [ ] **Step 4: Aplicar e conferir**

```bash
npx supabase db reset
curl -s "http://127.0.0.1:54321/rest/v1/acao_publica?select=id,titulo,organizador_nome,contato_tipo" -H "apikey: ANON"
curl -s "http://127.0.0.1:54321/rest/v1/turno_publico?select=*" -H "apikey: ANON"
```

(troque `ANON` pela anon key local). Expected: a ação Grajaú com `organizador_nome` "Carlos Lima" e `contato_tipo` "link_grupo"; o turno com `vao: 0`. `curl .../rest/v1/acao -H "apikey: ANON"` ainda devolve a linha inteira: a RLS entra na Task 7.

- [ ] **Step 5: Commit e push**

```bash
git add supabase/config.toml supabase/migrations supabase/seed.sql .gitignore package.json package-lock.json
git commit -m "Supabase: esquema da v1, views públicas, trigger de pessoa e semente local"
git push
```

---

### Task 7: RLS, funções de inscrição e testes de regras do banco

**Files:**
- Create: `supabase/migrations/20261008000002_rls_e_funcoes.sql`, `tests/test_supabase.py`, `tests/supabase_cliente.py`

**Interfaces:**
- Produces: RPCs `acao_para_mim(acao_id)`, `inscrever(turno_id)`, `desistir(turno_id)`, `salvar_telefone(telefone)`, `minhas_inscricoes()`. Erros saem como `raise exception` com a mensagem igual ao código do contrato (`precisa_entrar`, `sem_telefone`, `bloqueada`, `lotado`, `turno_passado`, `nao_publicada`, `telefone_invalido`).

- [ ] **Step 1: Cliente de teste em Python (REST puro, sem dependências)**

`tests/supabase_cliente.py`:

```python
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
```

- [ ] **Step 2: Escrever os testes de regras**

`tests/test_supabase.py`:

```python
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
```

- [ ] **Step 3: Rodar e ver falhar**

```bash
export SUPABASE_URL=http://127.0.0.1:54321 SUPABASE_ANON_KEY=<anon> SUPABASE_SERVICE_KEY=<service_role>
python -m pytest tests/test_supabase.py -q
```

Expected: falham (`acao` visível para anon; RPCs inexistentes, 404).

- [ ] **Step 4: Escrever a migração de RLS e funções**

`supabase/migrations/20261008000002_rls_e_funcoes.sql`:

```sql
-- RLS em todas as tabelas. Views públicas (Task 6) continuam legíveis por todos.
alter table organizacao enable row level security;
alter table pessoa enable row level security;
alter table acao enable row level security;
alter table turno enable row level security;
alter table inscricao enable row level security;
alter table pedido_organizador enable row level security;
alter table configuracao enable row level security;
alter table registro_moderacao enable row level security;

-- pessoa: cada um lê o seu; moderador lê todos. Escrita só por função.
create policy pessoa_propria on pessoa for select using (id = auth.uid() or eh_moderador());
revoke insert, update, delete on pessoa from anon, authenticated;

-- acao e turno: organizador vê as suas em qualquer status; moderador vê todas. Sem insert/update neste plano.
create policy acao_do_organizador on acao for select using (organizador = auth.uid() or eh_moderador());
create policy turno_do_organizador on turno for select using (
  exists (select 1 from acao a where a.id = turno.acao and (a.organizador = auth.uid() or eh_moderador())));
revoke insert, update, delete on acao, turno from anon, authenticated;

-- inscricao: cada um lê as suas; escrita só por função.
create policy inscricao_propria on inscricao for select using (pessoa = auth.uid());
revoke insert, update, delete on inscricao from anon, authenticated;

-- o resto: nada direto nesta etapa
revoke all on organizacao, pedido_organizador, configuracao, registro_moderacao from anon, authenticated;

-- formata e valida telefone: 11 dígitos nacionais, celular com 9
create function formatar_telefone(t text) returns text language plpgsql immutable as $$
declare d text := regexp_replace(coalesce(t,''), '\D', '', 'g');
begin
  if d !~ '^\d{2}9\d{8}$' then raise exception 'telefone_invalido'; end if;
  return '(' || substr(d,1,2) || ') ' || substr(d,3,5) || '-' || substr(d,8,4);
end $$;

create function pessoa_json(p pessoa) returns json language sql immutable as $$
  select json_build_object('id', p.id, 'nome', p.nome, 'email', p.email, 'telefone', p.telefone, 'papel', p.papel, 'bloqueada', p.bloqueada)
$$;

create function salvar_telefone(telefone text) returns json language plpgsql security definer set search_path = public as $$
declare p pessoa;
begin
  if auth.uid() is null then raise exception 'precisa_entrar'; end if;
  update pessoa set telefone = formatar_telefone(salvar_telefone.telefone) where id = auth.uid() returning * into p;
  return pessoa_json(p);
end $$;

create function combinado_json(a acao) returns json language sql immutable as $$
  select json_build_object('detalhe', a.detalhe, 'contato', json_build_object('tipo', a.contato_tipo, 'whatsapp', a.contato_whatsapp, 'link', a.contato_link))
$$;

-- quem pode ver detalhe e contato: organizador, moderador, ou inscrito ativo numa ação publicada
create function pode_ver_combinado(a acao) returns boolean language sql stable security definer set search_path = public as $$
  select a.organizador = auth.uid() or eh_moderador() or (a.status = 'publicada' and exists (
    select 1 from inscricao i join turno t on t.id = i.turno
    where t.acao = a.id and i.pessoa = auth.uid() and i.cancelada_em is null))
$$;

create function acao_para_mim(acao_id bigint) returns json language plpgsql stable security definer set search_path = public as $$
declare a acao;
begin
  select * into a from acao where id = acao_id;
  if not found then return null; end if;
  return json_build_object(
    'inscrita', coalesce((select json_agg(t.id order by t.inicio) from turno t join inscricao i on i.turno = t.id
                          where t.acao = a.id and i.pessoa = auth.uid() and i.cancelada_em is null), '[]'::json),
    'combinado', case when pode_ver_combinado(a) then combinado_json(a) else null end);
end $$;

create function inscrever(turno_id bigint) returns json language plpgsql security definer set search_path = public as $$
declare p pessoa; t turno; a acao; ativa inscricao;
begin
  if auth.uid() is null then raise exception 'precisa_entrar'; end if;
  select * into p from pessoa where id = auth.uid();
  if p.bloqueada then raise exception 'bloqueada'; end if;
  if p.telefone is null then raise exception 'sem_telefone'; end if;
  select * into t from turno where id = turno_id;
  if not found then raise exception 'nao_publicada'; end if;
  select * into a from acao where id = t.acao;
  if a.status <> 'publicada' then raise exception 'nao_publicada'; end if;
  if t.inicio::date < hoje_brasilia() then raise exception 'turno_passado'; end if;
  select * into ativa from inscricao where pessoa = p.id and turno = t.id and cancelada_em is null;
  if not found then
    if t.lotacao is not null and (select count(*) from inscricao where turno = t.id and cancelada_em is null) >= t.lotacao then
      raise exception 'lotado';
    end if;
    insert into inscricao (pessoa, turno) values (p.id, t.id)
      on conflict (pessoa, turno) do update set cancelada_em = null, criada_em = now();
  end if;
  return json_build_object('combinado', combinado_json(a));
end $$;

create function desistir(turno_id bigint) returns void language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then raise exception 'precisa_entrar'; end if;
  update inscricao set cancelada_em = now() where pessoa = auth.uid() and turno = turno_id and cancelada_em is null;
end $$;

create function minhas_inscricoes() returns json language sql stable security definer set search_path = public as $$
  select coalesce(json_agg(json_build_object(
    'turno', json_build_object('id', t.id, 'acao', t.acao, 'inicio', t.inicio, 'fim', t.fim, 'lotacao', t.lotacao,
             'vao', (select count(*) from inscricao x where x.turno = t.id and x.cancelada_em is null)),
    'acao', json_build_object('id', a.id, 'titulo', a.titulo, 'tipo', a.tipo, 'descricao', a.descricao, 'organizador', a.organizador,
             'organizador_nome', (select nome from pessoa where id = a.organizador), 'organizacao', a.organizacao,
             'lugar_nome', a.lugar_nome, 'bairro', a.bairro, 'cidade', a.cidade, 'lat', a.lat, 'lon', a.lon, 'online', a.online,
             'foto_url', a.foto_url, 'foto_credito', a.foto_credito, 'foto_pagina', a.foto_pagina, 'prioritaria', a.prioritaria,
             'contato_tipo', a.contato_tipo, 'status', a.status, 'criada_em', a.criada_em)
  ) order by t.inicio), '[]'::json)
  from inscricao i join turno t on t.id = i.turno join acao a on a.id = t.acao
  where i.pessoa = auth.uid() and i.cancelada_em is null
$$;

-- anon não chama o que exige sessão (a função também checa). `inscrever` e `acao_para_mim` ficam
-- executáveis por anon de propósito: a primeira devolve 'precisa_entrar', a segunda devolve inscrita vazia.
revoke execute on function salvar_telefone(text), desistir(bigint), minhas_inscricoes() from anon;
```

- [ ] **Step 5: Aplicar e rodar os testes**

```bash
npx supabase db reset
python -m pytest tests/test_supabase.py -q
```

Expected: 5 testes passam. Se `test_pessoa_ve_so_a_si_e_nao_muda_papel` falhar no PATCH com status 200 e `[]`, é porque o `revoke update` não pegou: confira com `npx supabase db diff` que a migração foi aplicada e que não há política de update.

- [ ] **Step 6: Commit e push**

```bash
git add supabase/migrations/20261008000002_rls_e_funcoes.sql tests/test_supabase.py tests/supabase_cliente.py
git commit -m "Supabase: RLS, funções de inscrição e testes de regras do banco"
git push
```

---

### Task 8: `app/api-supabase.js`

**Files:**
- Create: `app/api-supabase.js`
- Create: `tests/js/api-supabase.test.js` (só os mapeadores puros)
- Modify: `app/index.html` (scripts), `app/api.js` (sem mudança; já escolhe `ApiSupabase` quando existe)

**Interfaces:**
- Consumes: `supabase-js` UMD em `window.supabase`; RPCs da Task 7; views da Task 6.
- Produces: `window.ApiSupabase.criar({url, anonKey})` com o contrato da Task 2; mapeadores `ApiSupabase.deAcao(linha)`, `ApiSupabase.deTurno(linha)`, `ApiSupabase.dePessoa(json)` exportados para teste.

- [ ] **Step 1: Teste dos mapeadores**

`tests/js/api-supabase.test.js`:

```js
const test = require('node:test');
const assert = require('node:assert/strict');
const { deAcao, deTurno, dePessoa, hojeBrasilia } = require('../../app/api-supabase.js');

test('deAcao converte linha da view no formato AcaoPublica', () => {
  const a = deAcao({ id: 7, titulo: 'T', tipo: 'panfletagem', descricao: 'd', organizador: 'u1', organizador_nome: 'Carlos', organizacao: null,
    lugar_nome: 'Praça', bairro: 'Centro', cidade: 'São Paulo', lat: -23.5, lon: -46.6, online: false,
    foto_url: null, foto_credito: null, foto_pagina: null, prioritaria: true, contato_tipo: 'whatsapp', status: 'publicada', criada_em: '2026-10-08T12:00:00+00:00' });
  assert.deepEqual(a.lugar, { nome: 'Praça', bairro: 'Centro', cidade: 'São Paulo', lat: -23.5, lon: -46.6, online: false });
  assert.equal(a.foto, null); assert.equal(a.organizadorNome, 'Carlos'); assert.equal(a.contatoTipo, 'whatsapp');
  assert.equal(a.criadaEm, '2026-10-08'); assert.equal(a.detalhe, undefined);
  const on = deAcao({ online: true, lugar_nome: null, bairro: null, cidade: null, lat: null, lon: null, foto_url: 'https://x/y.jpg', foto_credito: 'c', foto_pagina: null });
  assert.deepEqual(on.lugar, { nome: 'Online', bairro: 'Online', cidade: 'Online', lat: null, lon: null, online: true });
  assert.deepEqual(on.foto, { url: 'https://x/y.jpg', credito: 'c', pagina: null });
});

test('deTurno corta os segundos e dePessoa mantém o contrato', () => {
  const t = deTurno({ id: 1, acao: 7, inicio: '2026-10-10T08:00:00', fim: '2026-10-10T10:00:00', lotacao: null, vao: 3 });
  assert.equal(t.inicio, '2026-10-10T08:00'); assert.equal(t.fim, '2026-10-10T10:00'); assert.equal(t.vao, 3);
  assert.deepEqual(dePessoa({ id: 'u', nome: 'N', email: 'e', telefone: null, papel: 'participante', bloqueada: false }),
    { id: 'u', nome: 'N', email: 'e', telefone: null, papel: 'participante', bloqueada: false });
  assert.match(hojeBrasilia(), /^\d{4}-\d{2}-\d{2}$/);
});
```

Run: `node --test tests/js` → FAIL (módulo não existe).

- [ ] **Step 2: Escrever `app/api-supabase.js`**

```js
// Miolo Supabase da camada de dados. Mesmo contrato de api-exemplo.js.
// Lê as views públicas pela REST e chama as funções SQL para tudo que exige sessão.
(function (raiz, fabrica) {
  if (typeof module !== 'undefined' && module.exports) module.exports = fabrica();
  else raiz.ApiSupabase = fabrica();
})(typeof window !== 'undefined' ? window : this, function () {
  const semSeg = s => (s ? String(s).slice(0, 16) : s);
  function hojeBrasilia() {
    return new Intl.DateTimeFormat('sv-SE', { timeZone: 'America/Sao_Paulo', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
  }
  function deAcao(r) {
    return {
      id: r.id, titulo: r.titulo, tipo: r.tipo, descricao: r.descricao || '', organizador: r.organizador,
      organizadorNome: r.organizador_nome || '', organizacao: r.organizacao == null ? null : r.organizacao,
      lugar: r.online ? { nome: 'Online', bairro: 'Online', cidade: 'Online', lat: null, lon: null, online: true }
        : { nome: r.lugar_nome, bairro: r.bairro, cidade: r.cidade, lat: r.lat, lon: r.lon, online: false },
      foto: r.foto_url ? { url: r.foto_url, credito: r.foto_credito || '', pagina: r.foto_pagina || null } : null,
      prioritaria: !!r.prioritaria, status: r.status, contatoTipo: r.contato_tipo || 'organizador_chama',
      criadaEm: r.criada_em ? String(r.criada_em).slice(0, 10) : null,
    };
  }
  const deTurno = r => ({ id: r.id, acao: r.acao, inicio: semSeg(r.inicio), fim: semSeg(r.fim), lotacao: r.lotacao == null ? null : r.lotacao, vao: r.vao || 0 });
  const dePessoa = p => ({ id: p.id, nome: p.nome, email: p.email || null, telefone: p.telefone || null, papel: p.papel, bloqueada: !!p.bloqueada });
  function erroDe(e) { const x = new Error(e.message || 'erro'); x.codigo = (e.message || '').trim(); x.original = e; return x; }

  function criar(cfg) {
    const sb = window.supabase.createClient(cfg.url, cfg.anonKey, { auth: { flowType: 'pkce', detectSessionInUrl: true, persistSession: true } });
    async function uid() { const { data } = await sb.auth.getSession(); return data.session ? data.session.user.id : null; }
    async function rpc(nome, args) { const { data, error } = await sb.rpc(nome, args || {}); if (error) throw erroDe(error); return data; }
    return {
      modo: 'supabase',
      async sessao() {
        const id = await uid(); if (!id) return null;
        const { data, error } = await sb.from('pessoa').select('id,nome,email,telefone,papel,bloqueada').eq('id', id).maybeSingle();
        if (error) throw erroDe(error); return data ? dePessoa(data) : null;
      },
      async entrar() {
        const volta = location.origin + location.pathname + location.hash;
        const { error } = await sb.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: volta } });
        if (error) throw erroDe(error);
      },
      async sair() { await sb.auth.signOut(); },
      async publico() {
        const [cfgR, orgR, acR, tR] = await Promise.all([
          sb.from('configuracao_publica').select('chave,valor'),
          sb.from('organizacao_publica').select('id,nome,tipo,verificada'),
          sb.from('acao_publica').select('*'),
          sb.from('turno_publico').select('*').gte('inicio', hojeBrasilia() + 'T00:00:00'),
        ]);
        for (const r of [cfgR, orgR, acR, tR]) if (r.error) throw erroDe(r.error);
        const config = { hoje: hojeBrasilia(), frase: '', vaquinha: '#' };
        for (const c of cfgR.data) config[c.chave] = c.valor;
        return { config, organizacoes: orgR.data, acoes: acR.data.map(deAcao), turnos: tR.data.map(deTurno) };
      },
      async acao(id) {
        const [aR, tR, mim] = await Promise.all([
          sb.from('acao_publica').select('*').eq('id', id).maybeSingle(),
          sb.from('turno_publico').select('*').eq('acao', id).order('inicio'),
          rpc('acao_para_mim', { acao_id: id }),
        ]);
        if (aR.error) throw erroDe(aR.error); if (tR.error) throw erroDe(tR.error);
        if (!aR.data) return null;
        return { acao: deAcao(aR.data), turnos: tR.data.map(deTurno), inscrita: (mim && mim.inscrita) || [], combinado: (mim && mim.combinado) || null };
      },
      async salvarTelefone(telefone) { return dePessoa(await rpc('salvar_telefone', { telefone })); },
      async inscrever(turnoId) { return rpc('inscrever', { turno_id: turnoId }); },
      async desistir(turnoId) { await rpc('desistir', { turno_id: turnoId }); },
      async minhasInscricoes() { return (await rpc('minhas_inscricoes')).map(m => ({ acao: deAcao(m.acao), turno: deTurno(m.turno) })); },
    };
  }
  return { criar, deAcao, deTurno, dePessoa, hojeBrasilia };
});
```

Observação sobre `acao(id)` para ação não publicada: a view devolve nada, então organizador e moderador também veem "Ação não encontrada" na página pública. É o esperado neste plano; Minhas ações (plano seguinte) lê a tabela.

- [ ] **Step 3: Ligar no `index.html` e tratar a volta do Google**

Scripts (antes de `api.js`):

```html
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/dist/umd/supabase.js"></script>
<script src="api-supabase.js"></script>
```

Em `sincronizar` (Task 3), trate a volta do OAuth: o Supabase devolve `?code=...` na URL; depois de `recarregar()`, limpe a query e retome o Vou pendente:

```js
async function sincronizar(){await recarregar();
  if(location.search.includes('code=')){history.replaceState(null,'',location.pathname+location.hash)}
  if(estado.sessao&&localStorage.getItem('vouPendente')){await continuarVouPendente();return}
  await render()}
```

No modo exemplo nada muda. Acrescente ao teste `test_telas_de_participante_leem_pela_api` as strings `'src="api-supabase.js"'`, `"supabase-js@2.45.4"` e `"replaceState"`.

- [ ] **Step 4: Rodar os testes e conferir contra o banco local**

Run: `node --test tests/js && python -m pytest tests -q` → passam.

Conferência manual contra o banco local: em `app/config.js` ponha temporariamente `{supabase:{url:'http://127.0.0.1:54321',anonKey:'<anon local>'}}`, suba `python -m http.server 8000 -d app` e abra http://localhost:8000. A vitrine deve mostrar a ação Grajaú da semente com "0 vão". O botão Entrar vai falhar (Google não está configurado no local): esperado. Volte `config.js` para `{supabase:null}` antes de commitar.

- [ ] **Step 5: Commit e push**

```bash
git add app/api-supabase.js app/index.html tests/js/api-supabase.test.js tests/test_mockup.py
git commit -m "Miolo Supabase da camada de dados e volta do login do Google"
git push
```

---

### Task 9: Projeto de produção, Google OAuth, configuração e roteiro de ponta a ponta

**Files:**
- Modify: `app/config.js`, `README.md`, `CLAUDE.md`
- Create: `docs/operacao.md`, `tests/e2e/vou.spec.mjs`

**Interfaces:**
- Consumes: tudo acima.
- Produces: o site em https://guipfranco.github.io/acoes-segundo-turno/ lendo do Supabase de produção com login Google.

- [ ] **Step 1: Criar o projeto no Supabase e aplicar as migrações**

No painel https://supabase.com/dashboard: New project, nome `acoes-segundo-turno`, região `South America (São Paulo)`, plano Free. Guarde a senha do banco fora do repo. Depois:

```bash
npx supabase login
npx supabase link --project-ref <ref do projeto>
npx supabase db push
```

Em Settings > API copie `Project URL` e `anon public`. Em Authentication > Providers > Email, desligue "Enable Email provider" (só social).

- [ ] **Step 2: Google OAuth**

No Google Cloud Console (https://console.cloud.google.com): crie um projeto, em "APIs e serviços > Tela de permissão OAuth" escolha Externo, nome "Ações do 2º turno", e-mail de suporte, domínio autorizado `supabase.co`; escopos só `email`, `profile`, `openid`; publique o app (modo Produção; escopos básicos não exigem verificação). Em "Credenciais > Criar credenciais > ID do cliente OAuth", tipo Aplicativo da Web, origens JavaScript `https://guipfranco.github.io`, URI de redirecionamento `https://<ref>.supabase.co/auth/v1/callback`. Copie ID e segredo.

No Supabase, Authentication > Providers > Google: ative, cole ID e segredo. Em Authentication > URL Configuration: Site URL `https://guipfranco.github.io/acoes-segundo-turno/`; Redirect URLs: `https://guipfranco.github.io/acoes-segundo-turno/**` e `http://localhost:8000/**`.

- [ ] **Step 3: Configurar o app e publicar**

`app/config.js`:

```js
// Configuração pública do app. A chave anon do Supabase é pública por desenho: o que protege os dados é o RLS.
// Abrir com ?modo=exemplo para navegar com os dados fictícios.
window.CONFIG = { supabase: { url: 'https://<ref>.supabase.co', anonKey: '<anon public>' } };
```

Semeie uma primeira ação de verdade pelo SQL Editor do painel (sem dado real de terceiros: use você mesmo como organizador depois de entrar uma vez pelo site, pegando seu `id` em `pessoa`):

```sql
update pessoa set papel = 'organizador', telefone = '(11) 9xxxx-xxxx' where email = 'guilhermepereirafranco@gmail.com';
insert into acao (titulo, tipo, descricao, organizador, lugar_nome, bairro, cidade, lat, lon, detalhe, contato_tipo, status)
select 'Ação de teste', 'panfletagem', 'Só para testar o site.', id, 'Praça da Sé', 'Sé', 'São Paulo', -23.5505, -46.6333, 'Perto da catedral.', 'organizador_chama', 'publicada' from pessoa where email = 'guilhermepereirafranco@gmail.com';
insert into turno (acao, inicio, fim) select id, (hoje_brasilia() + 2)::timestamp + time '10:00', (hoje_brasilia() + 2)::timestamp + time '12:00' from acao where titulo = 'Ação de teste';
```

```bash
git add app/config.js
git commit -m "Configuração do Supabase de produção (chave pública)"
git push
```

Espere o Pages publicar e abra o site: a ação de teste aparece; Entrar leva ao Google e volta; Vou pede telefone e mostra "vai entrar em contato"; Minhas inscrições lista; desistir some. Teste também `?modo=exemplo`.

- [ ] **Step 4: Roteiro de ponta a ponta com Playwright (modo exemplo, sem Google)**

`tests/e2e/vou.spec.mjs` (roda com `npx playwright@1.47.2 test`? Não: sem dependência nova. Use o script abaixo com o Playwright que já está na máquina pelo MCP, ou pule se não houver):

```js
// Roda: node tests/e2e/vou.spec.mjs  (precisa de `python -m http.server 8000 -d app` no ar e do pacote playwright no PATH do node)
import { chromium } from 'playwright';
const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 390, height: 800 } });
await p.goto('http://localhost:8000/?modo=exemplo#/inicio');
await p.waitForSelector('.evento');
await p.click('#conta'); // sair (exemplo começa logado)
await p.waitForFunction(() => document.getElementById('conta-rotulo').textContent === 'Entrar');
await p.goto('http://localhost:8000/?modo=exemplo#/acao/3'); // ação 3: 'organizador_chama'; se o Carlos já estiver inscrito nela, escolha outra
await p.click('text=Vou');
await p.waitForSelector('#vtel'); // volta do "login" com o formulário aberto
await p.fill('#vtel', '11988887777'); await p.click('text=Confirmar');
await p.waitForSelector('text=vai entrar em contato');
await p.goto('http://localhost:8000/?modo=exemplo#/inscricoes');
await p.waitForSelector('.evento');
console.log('ok'); await b.close();
```

Se o pacote `playwright` não estiver disponível para o Node, registre no commit que o roteiro foi conferido à mão (passos do Step 3) e deixe o arquivo para a próxima etapa.

- [ ] **Step 5: Documentar operação e atualizar README e CLAUDE.md**

`docs/operacao.md`:

```markdown
# Operação (v1)

- Produção: Supabase projeto `acoes-segundo-turno` (região São Paulo, plano grátis). Front no GitHub Pages.
- Migrações: `supabase/migrations/`. Aplicar com `npx supabase db push` depois de `npx supabase link`.
- Banco local: `npx supabase start` (Docker), `npx supabase db reset` aplica migrações e `seed.sql`.
- Testes: `python -m pytest tests` (telas; regras do banco se `SUPABASE_URL`, `SUPABASE_ANON_KEY`,
  `SUPABASE_SERVICE_KEY` apontarem para o local) e `node --test tests/js`.
- Moderador: por enquanto, `update pessoa set papel='moderador' where email='...'` no SQL Editor.
- Organizador parceiro: `update pessoa set papel='organizador' where email='...'`.
- Plano grátis pausa após 7 dias sem uso: o ping diário entra na etapa 5.
- Segredos (service_role, senha do banco, segredo do Google) ficam fora do repo.
```

No `README.md`, troque o parágrafo "Estado" por: app em `app/` lendo do Supabase (login Google, Vou e Minhas inscrições de verdade; Criar, Minhas ações e Fila só no modo exemplo até a próxima etapa), `?modo=exemplo` para os dados fictícios, operação em `docs/operacao.md`. No `CLAUDE.md`, atualize a linha de `mockup/` para `app/` e acrescente: "Camada de dados em `app/api.js` (escolhe `api-exemplo.js` ou `api-supabase.js`); regras sensíveis são funções SQL em `supabase/migrations/`; nunca commitar service_role."

- [ ] **Step 6: Commit e push**

```bash
git add docs/operacao.md README.md CLAUDE.md tests/e2e
git commit -m "Site no ar com Supabase e login Google; operação documentada"
git push
```

---

## Self-review

**Spec coverage (etapas 1 e 2):** camada de dados (Task 2, 3), Supabase com tabelas e RLS (6, 7), login Google (8, 9), vitrine e Vou de verdade (3, 4, 8), forma de contato com as três opções na tela do participante (4), aviso de dados no primeiro login: **não coberto**; a tela de confirmação do Vou já traz o aviso de telefone, e o aviso geral no primeiro login entra junto com "Quero organizar" no próximo plano. Orientação para fechar o grupo e caixa de confirmação: pertence a Criar ação (próximo plano). Facebook, ping e backup: etapa 5, fora deste plano. Vocabulário "horário": o front usa "horário encerrado" (Task 4); os nomes internos continuam `turno`.

**Placeholders:** `<ref>`, `<anon>` e `<service_role>` são valores que só existem depois de criar o projeto; estão marcados como tais nos passos manuais.

**Consistência de nomes:** `vaoNo(t)`, `estouInscrito(tid)`, `estado.acaoAberta.{acao,turnos,inscrita,combinado}`, `continuarVouPendente`, `sincronizar`, códigos de erro iguais em `api-exemplo.js`, nas funções SQL e em `MENSAGEM`. `minhas_inscricoes` devolve `acao` em snake_case e `api-supabase.js` passa por `deAcao`, igual à view.

**Review Focus:** itens 1, 3, 4 e 5 têm teste na Task 7 e no Node da Task 2; o item 2 (volta do Google) depende de ambiente real e fica no Step 3 da Task 9 e no roteiro de exemplo (`vouPendente`).
