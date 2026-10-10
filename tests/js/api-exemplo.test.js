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
    assert.equal(typeof a.organizadorNome, 'string'); assert.ok(['organizador_chama', 'whatsapp', 'link_grupo', 'divulgacao'].includes(a.contatoTipo));
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
  const naoPub = d.acoes.find(x => !['publicada', 'encerrada'].includes(x.status)); const tn = d.turnos.find(x => x.acao === naoPub.id);
  await assert.rejects(api.inscrever(tn.id), e => e.codigo === 'nao_publicada');
  await api.sair();
  assert.equal(await api.acao(naoPub.id), null); // deslogado não vê ação fora de publicada
  const cancelada = d.acoes.find(x => x.status === 'encerrada');
  const ab = await api.acao(cancelada.id); // cancelada continua abrindo pelo link, sem o combinado
  assert.equal(ab.acao.status, 'encerrada'); assert.equal(ab.combinado, null);
});

test('cancelada ainda em análise não abre pelo link nem conta como aprovada', async () => {
  const d = dados(); const api = ApiExemplo.criar(d);
  const a = d.acoes.find(x => x.status === 'em análise'); const dono = a.organizador;
  d.config.eu = dono; await api.entrar(); await api.encerrarAcao(a.id);
  assert.equal((await api.acao(a.id)).acao.status, 'encerrada'); // quem criou vê
  await api.sair();
  assert.equal(await api.acao(a.id), null); // os outros não
  const mod = d.pessoas.find(p => p.papel === 'moderador'); d.config.eu = mod.id; await api.entrar();
  const fila = await api.fila('em análise'); const dele = fila.find(m => m.organizador.id === dono);
  if (dele) assert.equal(dele.organizador.aprovadas, d.acoes.filter(x => x.organizador === dono && x.publicadaEm && ['publicada', 'encerrada'].includes(x.status)).length);
});

test('salvarTelefone valida 11 dígitos e minhasInscricoes guarda a desistência', async () => {
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
  const depois = (await api.minhasInscricoes()).find(m => m.turno.id === t.id);
  assert.ok(depois && depois.desistiu); // desistir não some: fica no histórico
  const minhas2 = await api.minhasAcoes(); assert.ok(minhas2.every(m => m.turnos.every(x => Array.isArray(x.desistiram))));
  // quem organiza vê quem desistiu, só pelo nome (o telefone não segue depois da desistência)
  const minha = minhas2.find(m => m.acao.status === 'publicada' && m.turnos.some(x => x.inicio.slice(0, 10) >= d.config.hoje)); const tm = minha.turnos.find(x => x.inicio.slice(0, 10) >= d.config.hoje);
  await api.inscrever(tm.id); await api.desistir(tm.id);
  const des = (await api.minhasAcoes()).find(m => m.acao.id === minha.acao.id).turnos.find(x => x.id === tm.id).desistiram;
  assert.ok(des.length >= 1 && des.every(x => x.nome && !('telefone' in x)));
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

test('moderação: suspender tira do ar, reativar volta, excluir marca excluída', async () => {
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
  assert.equal((await mod.acao(a.id)).acao.status, 'excluída');
  assert.ok(!(await mod.publico()).acoes.some(x => x.id === a.id) && d.turnos.some(t => t.acao === a.id));
  await assert.rejects(mod.excluir(a.id), { codigo: 'nao_pode' });
  // importada suspensa aparece em Suspensas
  const imp = d.acoes.find(x => x.status === 'publicada' && x.id !== a.id); imp.fonte = 'bora-lula';
  await mod.suspender(imp.id);
  assert.ok((await mod.fila('rascunho')).some(m => m.acao.id === imp.id));
  // em análise não se suspende (recusa); pessoa bloqueada não volta ao ar
  const pend = d.acoes.find(x => x.status === 'em análise');
  if (pend) await assert.rejects(mod.suspender(pend.id), { codigo: 'nao_pode' });
  d.pessoas.find(p => p.id === imp.organizador).bloqueada = true;
  await assert.rejects(mod.reativar(imp.id), { codigo: 'organizador_bloqueado' });
});

test('moderação: bloquear pessoa suspende as publicadas dela; desbloquear só desmarca', async () => {
  const d = dados(); const api = ApiExemplo.criar(d);
  const a = d.acoes.find(x => x.status === 'publicada' && !x.fonte && turnoFuturo(d, x));
  const alvo = a.organizador;
  await assert.rejects(api.bloquear(alvo), { codigo: 'so_moderador' });
  const modP = d.pessoas.find(p => p.papel === 'moderador'); d.config.eu = modP.id; const mod = ApiExemplo.criar(d);
  await assert.rejects(mod.bloquear(modP.id), { codigo: 'nao_pode' });
  await mod.bloquear(alvo, 'spam');
  assert.equal(d.pessoas.find(p => p.id === alvo).bloqueada, true);
  assert.ok(!(await mod.publico()).acoes.some(x => x.organizador === alvo));
  assert.ok((await mod.fila('rascunho')).some(m => m.acao.id === a.id && m.acao.motivoRecusa === 'spam'));
  await assert.rejects(mod.reativar(a.id), { codigo: 'organizador_bloqueado' });
  await mod.desbloquear(alvo);
  assert.equal(d.pessoas.find(p => p.id === alvo).bloqueada, false);
  assert.equal(d.acoes.find(x => x.id === a.id).status, 'rascunho');
  await assert.rejects(mod.desbloquear(alvo), { codigo: 'nao_pode' });
  await mod.reativar(a.id);
  assert.ok((await mod.publico()).acoes.some(x => x.id === a.id));
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

test('organização: nome novo liga na hora, nome existente vira pedido; ação só usa a própria organização', async () => {
  const d = dados(); const api = ApiExemplo.criar(d);
  const eu = d.pessoas.find(p => p.id === d.config.eu);
  eu.papel = 'participante'; eu.organizacao = null; eu.telefone = '(11) 98888-7777';
  await assert.rejects(api.salvarOrganizacao('Comitê Teste da Vila', 'coletivo'), { codigo: 'link_oficial' });
  const nova = await api.salvarOrganizacao('Comitê Teste da Vila', 'coletivo', 'https://exemplo.org/logo.png', 'https://instagram.com/comite');
  assert.equal(nova.situacao, 'ligada');
  const mo = await api.minhaOrganizacao();
  assert.equal(mo.organizacao.nome, 'Comitê Teste da Vila'); assert.equal(mo.organizacao.verificada, false); assert.equal(mo.organizacao.minha, true);
  const verificada = d.organizacoes.find(o => o.verificada);
  const ped = await api.salvarOrganizacao(verificada.nome.toUpperCase(), 'mandato', null, 'https://instagram.com/x');
  assert.equal(ped.situacao, 'pedido');
  assert.equal(eu.organizacao, nova.id); // não entrou na verificada sem aprovação
  // ação: organização de outra pessoa pelo id é ignorada; nome escrito à mão liga (ou cria sem selo)
  const r1 = await api.criarAcao(novaAcao(d, { organizacao: verificada.id }));
  assert.equal(d.acoes.find(a => a.id === r1.id).organizacao, null);
  await assert.rejects(api.criarAcao(novaAcao(d, { organizacao_nome: 'Coletivo Escrito à Mão' })), { codigo: 'link_post' });
  const r2 = await api.criarAcao(novaAcao(d, { organizacao_nome: 'Coletivo Escrito à Mão', organizacao_link: 'https://www.instagram.com/p/abc/' }));
  const o2 = d.organizacoes.find(o => o.id === d.acoes.find(a => a.id === r2.id).organizacao);
  assert.equal(o2.nome, 'Coletivo Escrito à Mão'); assert.equal(o2.verificada, false);
  assert.equal(r2.status, 'em análise');
  // moderação aprova o pedido: passa a ser da verificada e publica direto
  const mod = d.pessoas.find(p => p.papel === 'moderador'); d.config.eu = mod.id; const apiMod = ApiExemplo.criar(d);
  const fila = await apiMod.filaOrganizacoes();
  const p = fila.pedidos.find(x => x.organizacao === verificada.nome);
  await apiMod.decidirPedido(p.id, true);
  assert.equal(eu.organizacao, verificada.id);
  d.config.eu = eu.id; const api2 = ApiExemplo.criar(d);
  await assert.rejects(api2.criarAcao(novaAcao(d, { organizacao: verificada.id })), { codigo: 'link_post' }); // com selo também
  assert.equal((await api2.criarAcao(novaAcao(d, { organizacao: verificada.id, organizacao_link: 'https://www.instagram.com/p/x/' }))).status, 'publicada');
});

test('divulgação pública: importada sem verificação tem a etiqueta; cadastrada no app e verificada não', async () => {
  const d = dados(); const api = ApiExemplo.criar(d);
  const pub = await api.publico();
  const importadas = pub.acoes.filter(a => a.fonte);
  assert.ok(importadas.some(a => a.divulgacaoPublica) && importadas.some(a => !a.divulgacaoPublica));
  assert.ok(pub.acoes.filter(a => !a.fonte).every(a => a.divulgacaoPublica === false));
});

test('divulgação pública: só moderador verifica; a fila lista as não verificadas e verificar tira da fila', async () => {
  const d = dados(); const api = ApiExemplo.criar(d);
  const alvo = d.acoes.find(a => a.fonte && !a.verificadaEm && a.status === 'publicada');
  await assert.rejects(api.verificar(alvo.id), { codigo: 'so_moderador' });
  await assert.rejects(api.fila('divulgacao'), { codigo: 'so_moderador' });
  d.config.eu = d.pessoas.find(p => p.papel === 'moderador').id; await api.entrar();
  const fila = await api.fila('divulgacao');
  assert.ok(fila.some(m => m.acao.id === alvo.id));
  assert.ok(fila.every(m => m.acao.fonte && m.acao.divulgacaoPublica && m.organizador === null));
  await api.verificar(alvo.id);
  assert.ok(!(await api.fila('divulgacao')).some(m => m.acao.id === alvo.id));
  assert.equal((await api.publico()).acoes.find(a => a.id === alvo.id).divulgacaoPublica, false);
  await api.desverificar(alvo.id);
  assert.equal((await api.publico()).acoes.find(a => a.id === alvo.id).divulgacaoPublica, true);
  const doApp = d.acoes.find(a => !a.fonte && a.status === 'publicada');
  await assert.rejects(api.verificar(doApp.id), { codigo: 'nao_pode' });
  // recusar uma importada tira do ar
  await api.recusar(alvo.id, 'post de outra data');
  assert.ok(!(await api.publico()).acoes.some(a => a.id === alvo.id));
});

test('fila divulgação: turno de hora aproximada fica até o fim do dia; o exato sai quando termina', async () => {
  const d = dados(); const api = ApiExemplo.criar(d);
  const aprox = d.turnos.find(t => t.horaAproximada && d.acoes.find(a => a.id === t.acao).fonte);
  const exato = d.turnos.find(t => !t.horaAproximada && (d.acoes.find(a => a.id === t.acao) || {}).fonte && !d.acoes.find(a => a.id === t.acao).verificadaEm);
  aprox.inicio = '2026-10-11T18:00'; aprox.fim = '2026-10-11T20:00';
  exato.inicio = '2026-10-11T18:00'; exato.fim = '2026-10-11T20:00';
  d.config.agora = '2026-10-11T22:00'; d.config.hoje = '2026-10-11';
  d.config.eu = d.pessoas.find(p => p.papel === 'moderador').id; await api.entrar();
  const ids = (await api.fila('divulgacao')).map(m => m.acao.id);
  assert.ok(ids.includes(aprox.acao)); assert.ok(!ids.includes(exato.acao));
});
