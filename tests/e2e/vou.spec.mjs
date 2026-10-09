// Roteiro de ponta a ponta do "Eu vou!", no modo exemplo (sem Google, sem Supabase).
// Roda: node tests/e2e/vou.spec.mjs
// Precisa de `python -m http.server 8000 -d app` no ar e do pacote `playwright` resolvível pelo Node
// (não está no package.json de propósito: instale fora do repo ou rode `npm i --no-save playwright`).
// Ação 3 (Adesivaço na Sé): contatoTipo 'organizador_chama'; a pessoa 2 (config.eu) só está inscrita
// no horário 7, de outra ação, então o formulário de inscrição abre nos horários da ação 3.
import { chromium } from 'playwright';
const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 390, height: 800 } });
try {
  await p.goto('http://localhost:8000/?modo=exemplo#/inicio');
  await p.waitForSelector('.evento');
  await p.click('#conta'); // o exemplo começa logado: a conta leva ao Perfil, onde fica o Sair
  await p.click('text=Sair da conta');
  await p.waitForFunction(() => document.getElementById('conta-rotulo').textContent === 'Entrar');
  await p.goto('http://localhost:8000/?modo=exemplo#/acao/3');
  await p.click('.acao-lado >> text=Eu vou!'); // o do topo (celular) só rola até os horários
  await p.waitForSelector('#vtel'); // volta do "login" com o formulário aberto
  await p.fill('#vtel', '11988887777'); await p.click('text=Confirmar');
  await p.waitForSelector('text=vai entrar em contato');
  await p.goto('http://localhost:8000/?modo=exemplo#/inscricoes'); // abre o Perfil na seção "Onde eu vou"
  await p.waitForSelector('#inscricoes .insc');
  console.log('ok');
} finally { await b.close(); }
