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
const turnoFuturo = (d, a) => d.turnos.find(t => t.acao === a.id && t.inicio.slice(0, 10) >= d.config.hoje);
// ação de outro organizador (config.eu organizador já enxerga o combinado sem se inscrever), com contato por link e turno futuro
const publicada = d => d.acoes.find(a => a.status === 'publicada' && a.contatoTipo === 'link_grupo' && a.organizador !== d.config.eu && turnoFuturo(d, a));

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

test('ação importada no modo exemplo: lugar aproximado e link de divulgação público, contato ainda escondido', async () => {
  const d = dados();
  d.acoes.push({ id: 9901, titulo: 'Importada', tipo: 'outro', descricao: 'Fonte: teste.', organizador: d.acoes[0].organizador, organizacao: null,
    lugar: { nome: 'Praça', bairro: '', cidade: 'Recife', uf: 'PE', lat: -8, lon: -34, precisao: 'cidade' }, detalhe: '',
    contatoTipo: 'divulgacao', contatoWhatsapp: null, contatoLink: 'https://www.instagram.com/p/x/', status: 'publicada', fonte: 'bora-lula', criadaEm: d.config.hoje });
  d.turnos.push({ id: 9901, acao: 9901, inicio: d.config.hoje + 'T10:00', fim: d.config.hoje + 'T12:00', lotacao: null });
  const api = ApiExemplo.criar(d);
  const a = (await api.publico()).acoes.find(x => x.id === 9901);
  assert.equal(a.lugar.aproximado, true); assert.equal(a.fonte, 'bora-lula');
  assert.equal(a.linkDivulgacao, 'https://www.instagram.com/p/x/'); assert.equal(a.contatoLink, undefined);
  const comum = (await api.publico()).acoes.find(x => x.id !== 9901 && !x.lugar.online);
  assert.equal(comum.lugar.aproximado, false); assert.equal(comum.linkDivulgacao, null);
});

test('organização com logo no modo exemplo sai com foto; sem logo, foto null', async () => {
  const d = dados();
  d.organizacoes.push({ id: 9901, nome: 'Org com logo', tipo: 'partido', verificada: false, foto: { url: 'https://commons.wikimedia.org/x', credito: 'c, via Wikimedia Commons', pagina: 'https://commons.wikimedia.org/wiki/File:x' } });
  const orgs = (await ApiExemplo.criar(d).publico()).organizacoes;
  assert.deepEqual(orgs.find(o => o.id === 9901).foto, { url: 'https://commons.wikimedia.org/x', credito: 'c, via Wikimedia Commons', pagina: 'https://commons.wikimedia.org/wiki/File:x' });
  assert.equal(orgs.find(o => o.id !== 9901).foto, null);
});

// ação nova vinda do formulário, com turno amanhã
const novaAcao = (d, extra) => Object.assign({ titulo: 'Panfletagem teste', tipo: 'panfletagem', descricao: 'x', online: false, foto: 'https://exemplo.org/arte.jpg',
  lugar_nome: 'Praça', bairro: 'Centro', cidade: 'São Paulo', lat: -23.5, lon: -46.6,
  turnos: [{ inicio: d.config.hoje.slice(0, 10) + 'T23:00', fim: d.config.hoje.slice(0, 10) + 'T23:30' }] }, extra || {});

test('criar ação: participante vai para análise, verificado publica direto, e aparece em minhasAcoes', async () => {
  const d = dados(); const api = ApiExemplo.criar(d);
  const eu = d.pessoas.find(p => p.id === d.config.eu);
  eu.papel = 'participante'; eu.organizacao = null; eu.telefone = '(11) 98888-7777';
  const r = await api.criarAcao(novaAcao(d));
  assert.equal(r.status, 'em análise');
  const minhas = await api.minhasAcoes();
  assert.equal(minhas[0].acao.id, r.id); assert.equal(minhas[0].acao.status, 'em análise');
  assert.ok(!(await api.publico()).acoes.some(a => a.id === r.id));
  eu.papel = 'organizador';
  assert.equal((await api.criarAcao(novaAcao(d))).status, 'publicada');
});

test('criar ação: exige telefone, limita 10 por dia e valida grupo e turnos', async () => {
  const d = dados(); const api = ApiExemplo.criar(d);
  const eu = d.pessoas.find(p => p.id === d.config.eu);
  eu.papel = 'participante'; eu.organizacao = null; eu.telefone = null;
  await assert.rejects(api.criarAcao(novaAcao(d)), { codigo: 'sem_telefone' });
  eu.telefone = '(11) 98888-7777';
  await assert.rejects(api.criarAcao(novaAcao(d, { grupo: 'https://golpe.com' })), { codigo: 'grupo_invalido' });
  await assert.rejects(api.criarAcao(novaAcao(d, { turnos: [] })), { codigo: 'turno_invalido' });
  await assert.rejects(api.criarAcao(novaAcao(d, { foto: '' })), { codigo: 'sem_foto' });
  eu.papel = 'organizador'; // publica direto: não esbarra no limite de 10 em análise
  const ja = d.acoes.filter(a => a.organizador === eu.id && a.criadaEm === d.config.hoje).length;
  for (let i = ja; i < 10; i++) await api.criarAcao(novaAcao(d));
  await assert.rejects(api.criarAcao(novaAcao(d)), { codigo: 'limite_diario' });
});

test('fila: só moderador; aprovar publica e recusar exige motivo', async () => {
  const d = dados(); const api = ApiExemplo.criar(d);
  const eu = d.pessoas.find(p => p.id === d.config.eu);
  const mod = d.pessoas.find(p => p.papel === 'moderador');
  eu.papel = 'participante'; eu.organizacao = null; eu.telefone = '(11) 98888-7777';
  const { id } = await api.criarAcao(novaAcao(d));
  await assert.rejects(api.fila(), { codigo: 'so_moderador' });
  d.config.eu = mod.id; const api2 = ApiExemplo.criar(d);
  assert.ok((await api2.fila()).some(m => m.acao.id === id && m.organizador.telefone === '(11) 98888-7777'));
  await assert.rejects(api2.recusar(id, ' '), { codigo: 'sem_motivo' });
  await api2.aprovar(id);
  assert.ok((await api2.publico()).acoes.some(a => a.id === id));
});

test('moderação: suspender tira do ar, reativar volta, excluir apaga (importada não)', async () => {
  const d = dados(); const api = ApiExemplo.criar(d);
  const a = d.acoes.find(x => x.status === 'publicada' && !x.fonte && turnoFuturo(d, x));
  await assert.rejects(api.suspender(a.id), { codigo: 'so_moderador' });
  d.config.eu = d.pessoas.find(p => p.papel === 'moderador').id; const mod = ApiExemplo.criar(d);
  await mod.suspender(a.id, 'endereço errado');
  assert.ok(!(await mod.publico()).acoes.some(x => x.id === a.id));
  assert.ok((await mod.fila('rascunho')).some(m => m.acao.id === a.id && m.acao.motivoRecusa === 'endereço errado'));
  assert.equal((await mod.acao(a.id)).acao.status, 'rascunho');
  await mod.reativar(a.id);
  assert.ok((await mod.publico()).acoes.some(x => x.id === a.id));
  await mod.excluir(a.id);
  assert.equal(await mod.acao(a.id), null);
  assert.ok(!d.turnos.some(t => t.acao === a.id));
  const imp = d.acoes.find(x => x.fonte);
  if (imp) await assert.rejects(mod.excluir(imp.id), { codigo: 'importada' });
});

test('eu vou em ação de divulgação não pede telefone', async () => {
  const d = dados(); const api = ApiExemplo.criar(d);
  const a = d.acoes.find(x => x.status === 'publicada' && turnoFuturo(d, x));
  a.contatoTipo = 'divulgacao'; a.contatoLink = 'https://www.instagram.com/p/x/';
  d.pessoas.find(p => p.id === d.config.eu).telefone = null;
  const t = turnoFuturo(d, a);
  await api.inscrever(t.id);
  assert.ok((await api.minhasInscricoes()).some(m => m.turno.id === t.id));
});
