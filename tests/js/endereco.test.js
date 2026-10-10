// Endereço no cadastro: separar o número da casa (o Photon recebe a rua sem ele) e ler a sugestão do Photon.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

// as funções moram no index.html (sem build); pega os trechos de UF_DE a sugestaoDe e juntarTrechos e avalia isolado
const html = fs.readFileSync(path.join(__dirname, '../../app/index.html'), 'utf8');
const trecho = html.slice(html.indexOf('const UF_DE='), html.indexOf('let sugEnd=')) + html.slice(html.indexOf('function juntarTrechos'), html.indexOf('function mostrarSugEnd'));
const { numeroDe, semNumero, sugestaoDe, juntarTrechos } = new Function(trecho + '; return { numeroDe, semNumero, sugestaoDe, juntarTrechos };')();

test('número da casa: o último número solto; "25 de Março" é nome de rua', () => {
  const casos = [
    ['Rua da Consolação, 1000, São Paulo', 'Rua da Consolação São Paulo', '1000'],
    ['Av. Paulista 900', 'Av. Paulista', '900'],
    ['Praça da Sé s/n', 'Praça da Sé', 's/n'],
    ['Rua 25 de Março, 300', 'Rua 25 de Março', '300'],
    ['Av. 9 de Julho 50, São Paulo', 'Av. 9 de Julho São Paulo', '50'],
    ['Rua 7 de Setembro', 'Rua 7 de Setembro', ''],
  ];
  for (const [texto, rua, numero] of casos) {
    assert.equal(semNumero(texto), rua, texto);
    assert.equal(numeroDe(texto), numero, texto);
  }
});

test('sugestão do Photon: nome, bairro, cidade, UF e se é rua; sem cidade não serve', () => {
  const f = (props, coords = [-46.65, -23.55]) => ({ properties: props, geometry: { coordinates: coords } });
  assert.deepEqual(sugestaoDe(f({ name: 'Rua da Consolação', district: 'Vila Buarque', city: 'São Paulo', state: 'São Paulo', osm_key: 'highway' })),
    { nome: 'Rua da Consolação', bairro: 'Vila Buarque', cidade: 'São Paulo', uf: 'SP', rua: true, lat: -23.55, lon: -46.65 });
  const praca = sugestaoDe(f({ name: 'Largo da Batata', locality: 'Pinheiros', city: 'São Paulo', state: 'São Paulo', osm_key: 'leisure' }));
  assert.equal(praca.rua, false); assert.equal(praca.bairro, 'Pinheiros');
  assert.equal(sugestaoDe(f({ name: 'Sem cidade', state: 'Bahia' })), null);
  assert.equal(sugestaoDe(f({ street: 'Avenida Boa Viagem', city: 'Recife', state: 'Pernambuco' })).nome, 'Avenida Boa Viagem');
});

test('a mesma rua em vários trechos vira uma sugestão só por cidade, sem bairro', () => {
  const s = (nome, bairro, cidade, uf) => ({ nome, bairro, cidade, uf, rua: true, lat: 0, lon: 0 });
  const l = juntarTrechos([s('Rua da Consolação', 'Jardim Paulista', 'São Paulo', 'SP'), s('Rua da Consolação', 'Vila Buarque', 'São Paulo', 'SP'),
    s('Rua da Consolação', 'Conjunto Palmeiras', 'Fortaleza', 'CE'), s('Largo da Batata', 'Pinheiros', 'São Paulo', 'SP')]);
  assert.deepEqual(l.map(x => [x.nome, x.bairro, x.cidade]), [['Rua da Consolação', '', 'São Paulo'],
    ['Rua da Consolação', 'Conjunto Palmeiras', 'Fortaleza'], ['Largo da Batata', 'Pinheiros', 'São Paulo']]);
});
