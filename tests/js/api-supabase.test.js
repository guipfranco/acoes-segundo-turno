const test = require('node:test');
const assert = require('node:assert/strict');
const { deAcao, deTurno, dePessoa, deOrg, hojeBrasilia } = require('../../app/api-supabase.js');

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
  assert.deepEqual(on.foto, { url: 'https://x/y.jpg', credito: 'c', pagina: null });
  const imp = deAcao({ online: false, lugar_nome: 'Praça', bairro: null, cidade: 'Recife', lat: -8, lon: -34, lugar_aproximado: true,
    fonte: 'bora-lula', contato_tipo: 'divulgacao', link_divulgacao: 'https://www.instagram.com/p/x/' });
  assert.equal(imp.lugar.aproximado, true); assert.equal(imp.fonte, 'bora-lula');
  assert.equal(imp.contatoTipo, 'divulgacao'); assert.equal(imp.linkDivulgacao, 'https://www.instagram.com/p/x/');
});

test('deTurno corta os segundos e dePessoa mantém o contrato', () => {
  const t = deTurno({ id: 1, acao: 7, inicio: '2026-10-10T08:00:00', fim: '2026-10-10T10:00:00', lotacao: null, vao: 3 });
  assert.equal(t.inicio, '2026-10-10T08:00'); assert.equal(t.fim, '2026-10-10T10:00'); assert.equal(t.vao, 3);
  assert.deepEqual(dePessoa({ id: 'u', nome: 'N', email: 'e', telefone: null, papel: 'participante', bloqueada: false }),
    { id: 'u', nome: 'N', email: 'e', telefone: null, papel: 'participante', bloqueada: false, organizacao: null });
  assert.match(hojeBrasilia(), /^\d{4}-\d{2}-\d{2}$/);
});
