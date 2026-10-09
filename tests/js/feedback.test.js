// "Fale com a gente" (feedback) e horário aproximado nas duas camadas de dados.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ApiExemplo = require('../../app/api-exemplo.js');
const { deTurno, deFeedback, agoraBrasilia, hojeBrasilia } = require('../../app/api-supabase.js');

function dados() {
  const src = fs.readFileSync(path.join(__dirname, '../../app/dados.js'), 'utf8');
  const window = {};
  new Function('window', src)(window);
  return window.DADOS;
}
const moderador = d => d.pessoas.find(p => p.papel === 'moderador' && !p.bloqueada);

test('exemplo: publico traz agora e o turno com horário aproximado', async () => {
  const d = dados(); const api = ApiExemplo.criar(d);
  const pub = await api.publico();
  assert.equal(pub.config.agora, d.config.agora);
  assert.ok(pub.turnos.some(t => t.horaAproximada === true));
  assert.ok(pub.turnos.every(t => typeof t.horaAproximada === 'boolean'));
  delete d.config.agora;
  assert.equal((await ApiExemplo.criar(d).publico()).config.agora, d.config.hoje + 'T00:00');
});

test('exemplo: qualquer pessoa manda feedback, logada ou não; texto curto é erro', async () => {
  const d = dados(); const api = ApiExemplo.criar(d);
  const antes = d.feedbacks.length;
  await api.sair();
  const r = await api.enviarFeedback({ texto: 'O horário da ação 3 está errado', contato: '  ', tela: '#/acao/3', acaoId: 3, navegador: 'iOS Safari' });
  assert.ok(r.id > 0);
  const f = d.feedbacks.find(x => x.id === r.id);
  assert.equal(f.pessoa, null); assert.equal(f.contato, null); assert.equal(f.acao, 3); assert.equal(f.tratadoEm, null);
  await api.entrar();
  const r2 = await api.enviarFeedback({ texto: 'Ideia: lista das online', acaoId: 99999 });
  assert.equal(d.feedbacks.find(x => x.id === r2.id).pessoa, d.config.eu);
  assert.equal(d.feedbacks.find(x => x.id === r2.id).acao, null); // ação que não existe não entra
  await assert.rejects(api.enviarFeedback({ texto: 'oi' }), e => e.codigo === 'sem_texto');
  assert.equal(d.feedbacks.length, antes + 2);
});

test('exemplo: só moderador lê e marca como tratado', async () => {
  const d = dados(); const api = ApiExemplo.criar(d);
  await assert.rejects(api.feedbacks(), e => e.codigo === 'so_moderador'); // config.eu é organizador
  await assert.rejects(api.tratarFeedback(1, true), e => e.codigo === 'so_moderador');
  d.config.eu = moderador(d).id; const mod = ApiExemplo.criar(d);
  const pend = await mod.feedbacks();
  assert.ok(pend.length >= 1 && pend.every(f => f.tratadoEm === null));
  const trat = await mod.feedbacks(false);
  assert.ok(trat.length >= 1 && trat.every(f => f.tratadoEm));
  assert.equal(trat[0].pessoa.nome, d.pessoas.find(p => p.id === 4).nome);
  assert.equal(pend[0].pessoa, null); assert.equal(pend[0].acaoTitulo, d.acoes.find(a => a.id === 3).titulo);
  await mod.tratarFeedback(pend[0].id, true);
  assert.ok(!(await mod.feedbacks()).some(f => f.id === pend[0].id));
  await mod.tratarFeedback(pend[0].id, false);
  assert.ok((await mod.feedbacks()).some(f => f.id === pend[0].id));
  await assert.rejects(mod.tratarFeedback(99999, true), e => e.codigo === 'nao_pode');
});

test('supabase: deTurno lê hora_aproximada e deFeedback converte para Brasília', () => {
  assert.equal(deTurno({ id: 1, acao: 7, inicio: '2026-10-09T19:00:00', fim: '2026-10-09T23:00:00', lotacao: null, vao: 0, hora_aproximada: true }).horaAproximada, true);
  assert.equal(deTurno({ id: 1, acao: 7, inicio: '2026-10-09T19:00:00', fim: '2026-10-09T23:00:00', lotacao: null, vao: 0 }).horaAproximada, false);
  const f = deFeedback({ id: 5, texto: 't', contato: null, tela: '#/acao/3', acao: 3, acao_titulo: 'Giro', navegador: 'iOS Safari',
    criado_em: '2026-10-09T20:14:00+00:00', tratado_em: null, pessoa: { nome: 'Ana', email: 'a@x', telefone: null } });
  assert.equal(f.criadoEm, '2026-10-09T17:14'); assert.equal(f.tratadoEm, null); assert.equal(f.acaoTitulo, 'Giro');
  assert.deepEqual(f.pessoa, { nome: 'Ana', email: 'a@x', telefone: null });
  assert.equal(deFeedback({ id: 6, texto: 't', pessoa: null, criado_em: '2026-10-09T20:14:00+00:00' }).pessoa, null);
});

test('supabase: agoraBrasilia tem o formato do turno e começa pelo dia de hoje', () => {
  const a = agoraBrasilia();
  assert.match(a, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/);
  assert.equal(a.slice(0, 10), hojeBrasilia());
});
