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
