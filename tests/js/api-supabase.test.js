const test = require('node:test');
const assert = require('node:assert/strict');
const { criar, deAcao, deTurno, dePessoa, deOrg, hojeBrasilia } = require('../../app/api-supabase.js');

// Supabase de mentira: cada from(view) devolve uma consulta encadeável que resolve com dados[view]
function supabaseFalso(dados, sessao) {
  const views = [];
  const sb = { auth: { getSession: async () => ({ data: { session: sessao || null } }) }, rpc: async () => ({ data: null, error: null }), from(v) {
    views.push(v);
    const q = { then: (ok, erro) => Promise.resolve({ data: dados[v] || [], error: null }).then(ok, erro) };
    for (const m of ['select', 'gte', 'eq', 'order', 'range', 'maybeSingle']) q[m] = () => q;
    return q;
  } };
  return { sb, views };
}
function comAmbiente(dados, fetchFalso, sessao) {
  const { sb, views } = supabaseFalso(dados, sessao);
  global.window = { supabase: { createClient: () => sb } };
  global.fetch = fetchFalso;
  return { api: criar({ url: 'https://x.supabase.co', anonKey: 'anon' }), views };
}
const resposta = (status, corpo) => async (url, opts) => {
  assert.equal(url, 'publico.json'); assert.equal(opts.cache, 'no-cache');
  return { ok: status === 200, status, json: async () => { if (typeof corpo === 'string') throw new SyntaxError(corpo); return corpo; } };
};
const amanha = () => { const d = new Date(); d.setDate(d.getDate() + 1); return d.toISOString().slice(0, 10) + 'T09:00:00'; };
const bancoFalso = { configuracao_publica: [{ chave: 'frase', valor: 'do banco' }], organizacao_publica: [{ id: 1, nome: 'PT', tipo: 'partido', verificada: true }],
  acao_publica: [{ id: 2, titulo: 'Do banco', online: true }], turno_publico: [{ id: 20, acao: 2, inicio: amanha(), fim: amanha() }] };

test('publico() usa o publico.json fresco e mapeia as linhas cruas', async () => {
  const snap = { geradoEm: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
    configuracao: [{ chave: 'frase', valor: 'do arquivo' }, { chave: 'vaquinha', valor: 'https://v' }],
    organizacoes: [{ id: 5, nome: 'MST', tipo: 'movimento', verificada: false, foto_url: null }],
    acoes: [{ id: 7, titulo: 'Do arquivo', online: false, lugar_nome: 'Praça', bairro: 'Centro', cidade: 'SP', lat: -23.5, lon: -46.6,
      foto_url: 'https://s/f.jpg', foto_mini_url: 'https://s/f-mini.jpg', foto_credito: 'c', foto_pagina: null }],
    turnos: [{ id: 70, acao: 7, inicio: amanha(), fim: amanha() }, { id: 71, acao: 7, inicio: '2020-01-01T08:00:00', fim: '2020-01-01T10:00:00' }] };
  const { api, views } = comAmbiente(bancoFalso, resposta(200, snap));
  const p = await api.publico();
  assert.equal(api.origemPublico, 'snapshot'); assert.deepEqual(views, []);
  assert.equal(p.config.frase, 'do arquivo'); assert.equal(p.config.vaquinha, 'https://v'); assert.equal(p.config.hoje, hojeBrasilia());
  assert.deepEqual(p.organizacoes, [{ id: 5, nome: 'MST', tipo: 'movimento', verificada: false, foto: null }]);
  assert.equal(p.acoes[0].titulo, 'Do arquivo'); assert.equal(p.acoes[0].lugar.cidade, 'SP');
  assert.deepEqual(p.acoes[0].foto, { url: 'https://s/f.jpg', mini: 'https://s/f-mini.jpg', credito: 'c', pagina: null });
  assert.deepEqual(p.turnos.map(t => t.id), [70]); // o turno passado sai, como no Supabase
  assert.equal(p.turnos[0].inicio.length, 16);
});

test('publico() cai no Supabase com snapshot velho, 404, JSON inválido ou incompleto', async () => {
  const velho = { geradoEm: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(), configuracao: [], organizacoes: [], acoes: [], turnos: [] };
  const casos = [resposta(200, velho), resposta(404, null), resposta(200, 'Unexpected token <'), resposta(200, { geradoEm: new Date().toISOString(), acoes: [] }),
    resposta(200, { configuracao: [], organizacoes: [], acoes: [], turnos: [] }), async () => { throw new TypeError('Failed to fetch'); }];
  for (const f of casos) {
    const { api, views } = comAmbiente(bancoFalso, f);
    const p = await api.publico();
    assert.equal(api.origemPublico, 'supabase');
    assert.deepEqual(views.sort(), ['acao_publica', 'configuracao_publica', 'organizacao_publica', 'turno_publico']);
    assert.equal(p.config.frase, 'do banco'); assert.equal(p.acoes[0].titulo, 'Do banco'); assert.equal(p.organizacoes[0].nome, 'PT');
    assert.deepEqual(p.turnos.map(t => t.id), [20]);
  }
});

const snapFresco = () => ({ geradoEm: new Date().toISOString(), configuracao: [{ chave: 'frase', valor: 'do arquivo' }], organizacoes: [], acoes: [], turnos: [] });

test('publico() com sessão vai direto ao Supabase, sem ler o snapshot', async () => {
  let fetches = 0;
  const f = async (...a) => { fetches++; return resposta(200, snapFresco())(...a); };
  const { api, views } = comAmbiente(bancoFalso, f, { user: { id: 'u1' } });
  const p = await api.publico();
  assert.equal(api.origemPublico, 'supabase'); assert.equal(fetches, 0);
  assert.deepEqual(views.sort(), ['acao_publica', 'configuracao_publica', 'organizacao_publica', 'turno_publico']);
  assert.equal(p.config.frase, 'do banco');
  // sem sessão, quem só olha segue no snapshot
  const semSessao = comAmbiente(bancoFalso, resposta(200, snapFresco()));
  assert.equal((await semSessao.api.publico()).config.frase, 'do arquivo');
  assert.equal(semSessao.api.origemPublico, 'snapshot'); assert.deepEqual(semSessao.views, []);
});

test('publico() deixa o snapshot depois que a página escreveu algo', async () => {
  for (const escrever of [a => a.inscrever(1), a => a.desistir(1), a => a.criarAcao({}), a => a.encerrarAcao(1), a => a.aprovar(1),
    a => a.recusar(1, 'm'), a => a.suspender(1), a => a.reativar(1), a => a.excluir(1), a => a.bloquear('p'), a => a.desbloquear('p')]) {
    const { api, views } = comAmbiente(bancoFalso, resposta(200, snapFresco()));
    assert.equal((await api.publico()).config.frase, 'do arquivo'); assert.deepEqual(views, []);
    await escrever(api);
    assert.equal((await api.publico()).config.frase, 'do banco');
    assert.equal(api.origemPublico, 'supabase'); assert.ok(views.includes('acao_publica'));
  }
});

test('deOrg leva o logo da organização (ou null)', () => {
  assert.deepEqual(deOrg({ id: 3, nome: 'PT de Diadema', tipo: 'partido', verificada: false, foto_url: 'https://commons.wikimedia.org/x', foto_credito: 'PT, domínio público, via Wikimedia Commons', foto_pagina: 'https://commons.wikimedia.org/wiki/File:x' }),
    { id: 3, nome: 'PT de Diadema', tipo: 'partido', verificada: false, foto: { url: 'https://commons.wikimedia.org/x', credito: 'PT, domínio público, via Wikimedia Commons', pagina: 'https://commons.wikimedia.org/wiki/File:x' } });
  assert.deepEqual(deOrg({ id: 4, nome: 'Org', tipo: 'coletivo', verificada: true, foto_url: null, foto_credito: null, foto_pagina: null }), { id: 4, nome: 'Org', tipo: 'coletivo', verificada: true, foto: null });
});

test('deAcao converte linha da view no formato AcaoPublica', () => {
  const a = deAcao({ id: 7, titulo: 'T', tipo: 'panfletagem', descricao: 'd', organizador: 'u1', organizador_nome: 'Carlos', organizacao: null,
    lugar_nome: 'Praça', bairro: 'Centro', cidade: 'São Paulo', lat: -23.5, lon: -46.6, online: false,
    foto_url: null, foto_credito: null, foto_pagina: null, prioritaria: true, contato_tipo: 'whatsapp', status: 'publicada', criada_em: '2026-10-08T12:00:00+00:00' });
  assert.deepEqual(a.lugar, { nome: 'Praça', bairro: 'Centro', cidade: 'São Paulo', lat: -23.5, lon: -46.6, online: false, aproximado: false });
  assert.equal(a.fonte, null); assert.equal(a.linkDivulgacao, null);
  assert.equal(a.foto, null); assert.equal(a.organizadorNome, 'Carlos'); assert.equal(a.contatoTipo, 'whatsapp');
  assert.equal(a.criadaEm, '2026-10-08'); assert.equal(a.detalhe, undefined);
  const on = deAcao({ online: true, lugar_nome: null, bairro: null, cidade: null, lat: null, lon: null, foto_url: 'https://x/y.jpg', foto_credito: 'c', foto_pagina: null });
  assert.deepEqual(on.lugar, { nome: 'Online', bairro: 'Online', cidade: 'Online', lat: null, lon: null, online: true });
  assert.deepEqual(on.foto, { url: 'https://x/y.jpg', mini: null, credito: 'c', pagina: null });
  assert.equal(deAcao({ foto_url: 'https://x/y.jpg', foto_mini_url: 'https://x/y-mini.jpg' }).foto.mini, 'https://x/y-mini.jpg');
  const imp = deAcao({ online: false, lugar_nome: 'Praça', bairro: null, cidade: 'Recife', lat: -8, lon: -34, lugar_aproximado: true,
    fonte: 'bora-lula', contato_tipo: 'divulgacao', link_divulgacao: 'https://www.instagram.com/p/x/' });
  assert.equal(imp.lugar.aproximado, true); assert.equal(imp.fonte, 'bora-lula');
  assert.equal(imp.contatoTipo, 'divulgacao'); assert.equal(imp.linkDivulgacao, 'https://www.instagram.com/p/x/');
  // divulgação pública: importada sem verificação (ou sem a coluna, snapshot antigo) tem a etiqueta; verificada e do app, não
  assert.equal(imp.divulgacaoPublica, true);
  assert.equal(deAcao({ fonte: 'redes', verificada: false }).divulgacaoPublica, true);
  assert.equal(deAcao({ fonte: 'redes', verificada: true }).divulgacaoPublica, false);
  assert.equal(a.divulgacaoPublica, false);
});

test('deTurno corta os segundos e dePessoa mantém o contrato', () => {
  const t = deTurno({ id: 1, acao: 7, inicio: '2026-10-10T08:00:00', fim: '2026-10-10T10:00:00', lotacao: null, vao: 3 });
  assert.equal(t.inicio, '2026-10-10T08:00'); assert.equal(t.fim, '2026-10-10T10:00'); assert.equal(t.vao, 3);
  assert.deepEqual(dePessoa({ id: 'u', nome: 'N', email: 'e', telefone: null, papel: 'participante', bloqueada: false }),
    { id: 'u', nome: 'N', email: 'e', telefone: null, papel: 'participante', bloqueada: false, organizacao: null });
  assert.match(hojeBrasilia(), /^\d{4}-\d{2}-\d{2}$/);
});

// ---- página da ação pelo snapshot e paginação do caminho ao vivo (2026-10-09) ----

// Supabase de mentira que honra range(a, b), eq(col, val) e maybeSingle(), e registra as chamadas de rpc
function supabasePaginado(dados, sessao) {
  const views = [], rpcs = [];
  const sb = { auth: { getSession: async () => ({ data: { session: sessao || null } }) },
    rpc: async (nome) => { rpcs.push(nome); return { data: null, error: null }; },
    from(v) {
      views.push(v);
      let a = 0, b = Infinity, so = null, single = false;
      const q = { then: (ok, erro) => {
        let linhas = dados[v] || [];
        if (so) linhas = linhas.filter(r => r[so.col] === so.val);
        linhas = linhas.slice(a, Math.min(b + 1, a + 1000)); // como o PostgREST: no máximo max_rows (1000) por resposta
        return Promise.resolve({ data: single ? (linhas[0] || null) : linhas, error: null }).then(ok, erro);
      } };
      for (const m of ['select', 'gte', 'order']) q[m] = () => q;
      q.eq = (col, val) => { so = { col, val }; return q; };
      q.range = (x, y) => { a = x; b = y; return q; };
      q.maybeSingle = () => { single = true; return q; };
      return q;
    } };
  return { sb, views, rpcs };
}
function ambientePaginado(dados, fetchFalso, sessao) {
  const { sb, views, rpcs } = supabasePaginado(dados, sessao);
  global.window = { supabase: { createClient: () => sb } };
  global.fetch = fetchFalso;
  return { api: criar({ url: 'https://x.supabase.co', anonKey: 'anon' }), views, rpcs };
}
const snapComAcoes = () => ({ geradoEm: new Date().toISOString(), configuracao: [], organizacoes: [],
  acoes: [{ id: 7, titulo: 'Do arquivo', online: true }, { id: 8, titulo: 'Outra', online: true }],
  turnos: [{ id: 70, acao: 7, inicio: amanha(), fim: amanha() }, { id: 80, acao: 8, inicio: amanha(), fim: amanha() }, { id: 71, acao: 7, inicio: amanha(), fim: amanha() }] });

test('acao(id) sem sessão vem do snapshot: só os turnos daquela ação, sem tocar no Supabase', async () => {
  const { api, views, rpcs } = ambientePaginado(bancoFalso, resposta(200, snapComAcoes()));
  const r = await api.acao(7);
  assert.equal(r.acao.titulo, 'Do arquivo'); assert.deepEqual(r.turnos.map(t => t.id), [70, 71]);
  assert.deepEqual(r.inscrita, []); assert.equal(r.combinado, null);
  assert.deepEqual(views, []); assert.deepEqual(rpcs, []);
});

test('acao(id) cai no Supabase quando a ação não está no snapshot, com sessão ou depois de escrever', async () => {
  const banco = Object.assign({}, bancoFalso, { acao_publica: [{ id: 2, titulo: 'Do banco', online: true }], turno_publico: [{ id: 20, acao: 2, inicio: amanha(), fim: amanha() }] });
  // fora do snapshot (aprovada há menos de 1 h, ou cancelada)
  let amb = ambientePaginado(banco, resposta(200, snapComAcoes()));
  let r = await amb.api.acao(2);
  assert.equal(r.acao.titulo, 'Do banco'); assert.deepEqual(r.turnos.map(t => t.id), [20]);
  assert.ok(amb.views.includes('acao_publica')); assert.deepEqual(amb.rpcs, ['acao_para_mim']);
  // com sessão: nem lê o arquivo
  let fetches = 0;
  amb = ambientePaginado(banco, async (...a) => { fetches++; return resposta(200, snapComAcoes())(...a); }, { user: { id: 'u1' } });
  await amb.api.acao(2);
  assert.equal(fetches, 0); assert.ok(amb.views.includes('acao_publica'));
  // depois de escrever nesta página
  amb = ambientePaginado(banco, resposta(200, snapComAcoes()));
  await amb.api.inscrever(20);
  await amb.api.acao(2);
  assert.ok(amb.views.includes('acao_publica'));
});

test('a mesma página baixa o publico.json uma vez: inicial e ação em seguida compartilham a leitura', async () => {
  let fetches = 0;
  const { api, views } = ambientePaginado(bancoFalso, async (...a) => { fetches++; return resposta(200, snapComAcoes())(...a); });
  await api.publico(); await api.acao(7); await api.acao(8);
  assert.equal(fetches, 1); assert.deepEqual(views, []);
});

test('publico() ao vivo pagina de 1000 em 1000 e não para na página curta', async () => {
  const muitas = Array.from({ length: 2300 }, (_, i) => ({ id: i + 1, titulo: 'A' + i, online: true }));
  const turnos = Array.from({ length: 1200 }, (_, i) => ({ id: i + 1, acao: i + 1, inicio: amanha(), fim: amanha() }));
  const banco = Object.assign({}, bancoFalso, { acao_publica: muitas, turno_publico: turnos });
  const { api } = ambientePaginado(banco, resposta(404, null));
  const p = await api.publico();
  assert.equal(api.origemPublico, 'supabase');
  assert.equal(p.acoes.length, 2300); assert.equal(p.acoes[2299].id, 2300);
  assert.equal(p.turnos.length, 1200);
});

// ---------- entrar ----------
function ambienteLogin(cfgExtra, google) {
  const chamadas = { oauth: [], idToken: [], init: null, botao: null };
  const sb = { auth: { getSession: async () => ({ data: { session: null } }),
    signInWithOAuth: async a => { chamadas.oauth.push(a); return { error: null }; },
    signInWithIdToken: async a => { chamadas.idToken.push(a); return { error: null }; } } };
  // DOM mínimo: a janela de login só precisa de createElement, querySelector, showModal/close e listeners
  const els = {};
  const elemento = () => ({ hidden: false, textContent: '', onclick: null, ouvintes: {},
    set innerHTML(_) { for (const c of ['.login-google-botao', '.login-google-erro', '.login-google-fechar']) els[c] = elemento(); },
    querySelector: c => els[c], addEventListener(t, f) { this.ouvintes[t] = f; }, showModal() { this.aberta = true; }, close() { this.aberta = false; }, remove() {} });
  global.document = { createElement: () => (els.caixa = elemento()), body: { appendChild() {} }, documentElement: { clientWidth: 390 } };
  global.location = { origin: 'https://site', pathname: '/app/', hash: '#/acao/3' };
  global.window = { supabase: { createClient: () => sb }, google };
  return { api: criar(Object.assign({ url: 'https://x.supabase.co', anonKey: 'anon' }, cfgExtra)), chamadas, els };
}

// espera a janela abrir (o nonce passa pelo crypto.subtle, assíncrono)
async function abriu(els) { for (let i = 0; i < 200 && !(els.caixa && els.caixa.aberta); i++) await new Promise(r => setTimeout(r, 5)); }

test('entrar() sem googleClientId segue no redirecionamento pelo Supabase', async () => {
  const { api, chamadas } = ambienteLogin({}, undefined);
  await api.entrar();
  assert.deepEqual(chamadas.oauth, [{ provider: 'google', options: { redirectTo: 'https://site/app/#/acao/3' } }]);
});

test('entrar() com googleClientId usa o botão do Google e manda o nonce cru ao Supabase', async () => {
  const crypto = require('node:crypto');
  let cb = null, init = null, botao = null;
  const google = { accounts: { id: { initialize: o => { init = o; cb = o.callback; }, renderButton: (el, o) => { botao = o; } } } };
  const { api, chamadas, els } = ambienteLogin({ googleClientId: 'cid' }, google);
  const p = api.entrar();
  await abriu(els);
  assert.equal(init.client_id, 'cid'); assert.equal(botao.locale, 'pt-BR'); assert.equal(els.caixa.aberta, true);
  assert.deepEqual(chamadas.oauth, []);
  await cb({ credential: 'tok' });
  assert.equal(await p, true); assert.equal(els.caixa.aberta, false);
  const [{ provider, token, nonce }] = chamadas.idToken;
  assert.equal(provider, 'google'); assert.equal(token, 'tok');
  assert.equal(init.nonce, crypto.createHash('sha256').update(nonce).digest('hex'));
});

test('entrar() pelo botão: fechar a janela resolve false sem entrar', async () => {
  const google = { accounts: { id: { initialize() {}, renderButton() {} } } };
  const { api, chamadas, els } = ambienteLogin({ googleClientId: 'cid' }, google);
  const p = api.entrar();
  await abriu(els);
  els['.login-google-fechar'].onclick();
  assert.equal(await p, false); assert.deepEqual(chamadas.idToken, []);
});
