// Link do mapa: o enquadramento (centro e zoom) vai no endereço para dar para copiar e mandar.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

// as funções moram no index.html (sem build); pega o trecho de vistaDoHash a montarMapa e avalia isolado
const html = fs.readFileSync(path.join(__dirname, '../../app/index.html'), 'utf8');
const trecho = html.slice(html.indexOf('function vistaDoHash'), html.indexOf('function montarMapa'));
const { vistaDoHash, hashDaVista } = new Function(trecho + '; return { vistaDoHash, hashDaVista };')();

test('endereço do mapa guarda centro e zoom e volta igual', () => {
  const h = hashDaVista({ lat: -23.550519, lon: -46.633309, zoom: 12 });
  assert.equal(h, '#/mapa?lat=-23.55052&lon=-46.63331&z=12');
  assert.deepEqual(vistaDoHash(h), { lat: -23.55052, lon: -46.63331, zoom: 12 });
});

test('sem lat/lon ou com valor inválido não muda o mapa', () => {
  for (const h of ['#/mapa', '#/mapa?', '#/mapa?lat=1', '#/mapa?lat=abc&lon=2', '#/mapa?lat=95&lon=0', '#/mapa?lat=0&lon=200', '#/mapa?lat=0&lon=0&z=x', ''])
    assert.equal(vistaDoHash(h), null, h);
});

test('zoom fica entre 3 e 18 e, se faltar, é 11 (cidade)', () => {
  assert.equal(vistaDoHash('#/mapa?lat=0&lon=0&z=40').zoom, 18);
  assert.equal(vistaDoHash('#/mapa?lat=0&lon=0&z=0').zoom, 3);
  assert.equal(vistaDoHash('#/mapa?lat=-8.05&lon=-34.9').zoom, 11);
});
