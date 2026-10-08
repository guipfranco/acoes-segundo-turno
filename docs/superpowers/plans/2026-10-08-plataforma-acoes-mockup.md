# Plataforma de ações do 2º turno: mockup navegável. Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Um protótipo navegável, em HTML estático, das cinco telas da plataforma (Início, Ação, Criar ação, Minhas ações, Fila), com dados de exemplo da RMSP, publicado como artifact privado para a equipe clicar e corrigir textos e fluxos antes de qualquer código de produção.

**Architecture:** Repo novo `acoes-segundo-turno` ao lado deste. Um único `mockup/index.html` com CSS e JS inline, roteamento por hash (`#/inicio`, `#/acao/3`, `#/criar`, `#/minhas`, `#/fila`), estado em memória (inscrições, ações criadas e decisões da fila vivem só enquanto a aba está aberta). Dados de exemplo em `mockup/dados.js` (um `window.DADOS` com organizações, pessoas, ações, turnos e inscrições), separado do HTML para a equipe poder trocar. Mapa da segunda aba do Início usa Leaflet do cdnjs com tiles do OpenStreetMap (no mockup pode carregar tiles de fora; no artifact privado isso funciona porque é só um iframe de página comum). Testes com Python (pytest) lendo o HTML e o JS como texto e, para o fluxo, Playwright via `mcp__playwright` manual no final.

**Tech Stack:** HTML, CSS, JavaScript puro (sem build), Leaflet 1.9 do cdnjs, Python 3 + pytest para checagens estáticas, artifact privado do claude.ai para publicação.

**Spec:** `C:\Users\guilh\source\repos\mapa-segundo-turno\docs\superpowers\specs\2026-10-08-plataforma-acoes-design.md`

## Global Constraints

- Tudo em pt-BR, datas no texto no formato "sáb 11/10, 10h"; nos dados, ISO `AAAA-MM-DDTHH:MM`.
- Feito para celular: largura de referência 390 px; no desktop a página centraliza uma coluna de até 480 px.
- Página pública nunca mostra telefone. Detalhe do encontro e link do grupo só aparecem após inscrição confirmada.
- Botão **Doar** fixo no rodapé de toda tela, apontando para `DADOS.config.vaquinha`.
- Sete tipos de ação, nesta ordem e com estes rótulos: panfletagem, adesivaço, roda de conversa, ligatona, porta a porta, bandeiraço, outro.
- Status de ação: rascunho, em análise, publicada, recusada, encerrada.
- Nada de framework nem build; abrir o `index.html` no navegador tem que funcionar.
- Sem dado pessoal real: nomes e telefones de exemplo inventados, telefones no padrão `(11) 9xxxx-xxxx` com x.

## Review Focus

1. Ação sem nenhum turno futuro (todos passados): não deve aparecer no Início; na tela da ação, botão "Vou" desabilitado com "turno encerrado". Teste no Task 3.
2. Turno com lotação atingida: "Vou" vira "lotado"; teste no Task 4.
3. Pessoa já inscrita no mesmo turno clica "Vou" de novo: não duplica, mostra o estado de inscrita. Teste no Task 4.
4. Criar ação com campos obrigatórios vazios (título, lugar, pelo menos um turno, telefone): avança não; mensagem ao lado do campo. Teste no Task 5.
5. Organizador de organização verificada cria ação: status nasce "publicada" e aparece no Início sem passar pela Fila; sem selo nasce "em análise". Teste no Task 5.

---

### Task 1: Repo novo e esqueleto do mockup

**Files:**
- Create: `C:\Users\guilh\source\repos\acoes-segundo-turno\README.md`
- Create: `C:\Users\guilh\source\repos\acoes-segundo-turno\CLAUDE.md`
- Create: `C:\Users\guilh\source\repos\acoes-segundo-turno\.gitignore`
- Create: `C:\Users\guilh\source\repos\acoes-segundo-turno\mockup\index.html`
- Create: `C:\Users\guilh\source\repos\acoes-segundo-turno\tests\test_mockup.py`
- Copy: a spec deste repo para `docs/superpowers/specs/2026-10-08-plataforma-acoes-design.md` no repo novo.

**Interfaces:**
- Produces: `mockup/index.html` com um `<main id="app">` e uma função global `render()` que lê `location.hash` e chama `telaInicio()`, `telaAcao(id)`, `telaCriar()`, `telaMinhas()`, `telaFila()`. Cada `telaX` devolve uma string HTML. Um `<nav>` fixo no rodapé com Início, Criar, Minhas, Fila e o botão Doar.

- [ ] **Step 1: Criar o repo**

```bash
mkdir -p /c/Users/guilh/source/repos/acoes-segundo-turno/{mockup,tests,docs/superpowers/specs,docs/superpowers/plans}
cd /c/Users/guilh/source/repos/acoes-segundo-turno && git init -q
cp /c/Users/guilh/source/repos/mapa-segundo-turno/docs/superpowers/specs/2026-10-08-plataforma-acoes-design.md docs/superpowers/specs/
cp /c/Users/guilh/source/repos/mapa-segundo-turno/docs/superpowers/plans/2026-10-08-plataforma-acoes-mockup.md docs/superpowers/plans/
printf '__pycache__/\n.pytest_cache/\n' > .gitignore
```

- [ ] **Step 2: README e CLAUDE.md**

`README.md`:
```markdown
# Ações do 2º turno

Plataforma onde quem organiza ações para eleger o Lula no 2º turno (panfletagem, adesivaço, roda de
conversa, ligatona...) cadastra a ação, e quem quer ajudar acha uma perto de si e se inscreve.
Desenho em `docs/superpowers/specs/2026-10-08-plataforma-acoes-design.md`.

Estado: **mockup navegável** em `mockup/index.html` (abrir no navegador). Dados de exemplo em
`mockup/dados.js`. Testes: `python -m pytest tests`.
```

`CLAUDE.md`:
```markdown
# CLAUDE.md

Repo da plataforma de ações do 2º turno (voto do Lula). Nasceu do `mapa-segundo-turno` em 2026-10-08.

- Tudo em pt-BR, datas AAAA-MM-DD. Push logo depois de cada commit.
- `mockup/` é protótipo estático, sem build. Publicação só como artifact privado do claude.ai
  (id gravado aqui quando existir). Nunca URL pública enquanto tiver dados de exemplo com nomes.
- Sem dado pessoal real no repo.
```

- [ ] **Step 3: Teste que falha (esqueleto)**

`tests/test_mockup.py`:
```python
from pathlib import Path
import re

RAIZ = Path(__file__).resolve().parents[1]
HTML = (RAIZ / "mockup" / "index.html").read_text(encoding="utf-8")


def test_tem_as_cinco_telas():
    for nome in ["telaInicio", "telaAcao", "telaCriar", "telaMinhas", "telaFila"]:
        assert f"function {nome}" in HTML, nome


def test_nav_e_doar():
    assert 'id="app"' in HTML
    assert "<nav" in HTML
    assert "Doar" in HTML
```

- [ ] **Step 4: Rodar e ver falhar**

Run: `cd /c/Users/guilh/source/repos/acoes-segundo-turno && python -m pytest tests -q`
Expected: FAIL (arquivo `mockup/index.html` não existe).

- [ ] **Step 5: Esqueleto do index.html**

```html
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ações do 2º turno</title>
<style>
:root{--vermelho:#c8102e;--fundo:#fff;--texto:#1a1a1a;--cinza:#666;--borda:#e3e3e3;--ok:#1b7f3b;--aviso:#b36b00}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,sans-serif;background:#f3f3f3;color:var(--texto)}
#app{max-width:480px;margin:0 auto;background:var(--fundo);min-height:100vh;padding:16px 16px 96px}
nav{position:fixed;bottom:0;left:0;right:0;background:#fff;border-top:1px solid var(--borda)}
nav .barra{max-width:480px;margin:0 auto;display:flex}
nav a{flex:1;text-align:center;padding:10px 4px;font-size:12px;color:var(--cinza);text-decoration:none}
nav a.ativo{color:var(--vermelho);font-weight:600}
nav a.doar{background:var(--vermelho);color:#fff;font-weight:700}
h1{font-size:22px;margin:0 0 4px}h2{font-size:18px;margin:16px 0 8px}
.card{border:1px solid var(--borda);border-radius:12px;padding:12px;margin:8px 0;display:block;color:inherit;text-decoration:none}
.btn{display:inline-block;background:var(--vermelho);color:#fff;border:0;border-radius:8px;padding:12px 16px;font-size:16px;font-weight:600;cursor:pointer}
.btn[disabled]{background:#bbb;cursor:default}.btn.sec{background:#fff;color:var(--vermelho);border:1px solid var(--vermelho)}
.chip{display:inline-block;border:1px solid var(--borda);border-radius:999px;padding:4px 10px;font-size:13px;margin:2px 4px 2px 0;cursor:pointer}
.chip.ativo{background:var(--vermelho);color:#fff;border-color:var(--vermelho)}
.selo{font-size:12px;color:var(--ok)}.prior{font-size:12px;color:var(--aviso);font-weight:600}
.muted{color:var(--cinza);font-size:14px}.erro{color:var(--vermelho);font-size:13px}
label{display:block;margin:12px 0 4px;font-weight:600}input,textarea,select{width:100%;padding:10px;border:1px solid var(--borda);border-radius:8px;font-size:16px}
</style>
</head>
<body>
<main id="app"></main>
<nav><div class="barra">
  <a href="#/inicio" data-rota="inicio">Início</a>
  <a href="#/criar" data-rota="criar">Criar ação</a>
  <a href="#/minhas" data-rota="minhas">Minhas ações</a>
  <a href="#/fila" data-rota="fila">Fila</a>
  <a class="doar" id="doar" href="#" target="_blank">Doar</a>
</div></nav>
<script src="dados.js"></script>
<script>
function telaInicio(){return '<h1>Início</h1>'}
function telaAcao(id){return '<h1>Ação '+id+'</h1>'}
function telaCriar(){return '<h1>Criar ação</h1>'}
function telaMinhas(){return '<h1>Minhas ações</h1>'}
function telaFila(){return '<h1>Fila</h1>'}
function render(){
  const h=location.hash||'#/inicio';
  const [,rota,arg]=h.split('/');
  const app=document.getElementById('app');
  app.innerHTML = rota==='acao'?telaAcao(Number(arg)) : rota==='criar'?telaCriar() : rota==='minhas'?telaMinhas() : rota==='fila'?telaFila() : telaInicio();
  document.querySelectorAll('nav a[data-rota]').forEach(a=>a.classList.toggle('ativo',a.dataset.rota===(rota||'inicio')));
  document.getElementById('doar').href=(window.DADOS&&DADOS.config.vaquinha)||'#';
  window.scrollTo(0,0);
}
window.addEventListener('hashchange',render);
window.addEventListener('DOMContentLoaded',render);
</script>
</body>
</html>
```

- [ ] **Step 6: Rodar e ver passar**

Run: `python -m pytest tests -q`
Expected: 2 passed.

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "Mockup: esqueleto com roteamento por hash e barra fixa com Doar" -q
```
(Sem remoto ainda; criar no GitHub como privado quando o Gui pedir: `gh repo create acoes-segundo-turno --private --source=. --push`.)

---

### Task 2: Dados de exemplo

**Files:**
- Create: `mockup/dados.js`
- Modify: `tests/test_mockup.py`

**Interfaces:**
- Produces: `window.DADOS = {config, organizacoes, pessoas, acoes, turnos, inscricoes, areasPrioritarias}`.
  - `config`: `{vaquinha: string, frase: string, eu: number}` (`eu` é o id da pessoa logada no mockup).
  - `organizacoes[]`: `{id, nome, tipo, verificada: bool}`.
  - `pessoas[]`: `{id, nome, telefone, papel: 'participante'|'organizador'|'moderador', organizacao: number|null, bloqueada: bool}`.
  - `acoes[]`: `{id, titulo, tipo, descricao, organizador: number, organizacao: number|null, lugar: {nome, bairro, cidade, lat, lon}, detalhe, grupo, status, motivoRecusa: string|null, prioritaria: bool, criadaEm}`.
  - `turnos[]`: `{id, acao, inicio, fim, lotacao: number|null}`.
  - `inscricoes[]`: `{id, pessoa, turno, criadaEm, canceladaEm: null|string, presenca: null|bool}`.
  - `areasPrioritarias`: lista de nomes de bairros/distritos (ex.: do `candidatos-prioritarios.csv` deste repo: Grajaú, Jardim Ângela, Parelheiros, Cidade Dutra, Pedreira, Diadema, São Bernardo do Campo, Guaianases, Cidade Tiradentes, Brasilândia).
- Datas: hoje do mockup é fixo em `config.hoje = '2026-10-09'` para a lista não esvaziar com o tempo.

- [ ] **Step 1: Teste que falha**

Acrescentar em `tests/test_mockup.py`:
```python
import json, subprocess, sys

DADOS_JS = (RAIZ / "mockup" / "dados.js").read_text(encoding="utf-8")


def carregar_dados():
    # dados.js é "window.DADOS = {...};" com JSON puro dentro
    corpo = DADOS_JS.split("=", 1)[1].strip().rstrip(";")
    return json.loads(corpo)


def test_dados_tem_pelo_menos_12_acoes_e_todas_com_turno():
    d = carregar_dados()
    assert len(d["acoes"]) >= 12
    acoes_com_turno = {t["acao"] for t in d["turnos"]}
    for a in d["acoes"]:
        assert a["id"] in acoes_com_turno, a["titulo"]


def test_dados_cobrem_os_tipos_e_os_status():
    d = carregar_dados()
    tipos = {a["tipo"] for a in d["acoes"]}
    assert tipos >= {"panfletagem", "adesivaço", "roda de conversa", "ligatona", "porta a porta", "bandeiraço"}
    status = {a["status"] for a in d["acoes"]}
    assert status >= {"publicada", "em análise", "recusada", "encerrada"}


def test_dados_sem_telefone_real():
    for p in carregar_dados()["pessoas"]:
        assert re.fullmatch(r"\(11\) 9x{4}-x{4}", p["telefone"]), p


def test_dados_tem_verificada_e_nao_verificada_e_eu_sou_organizador():
    d = carregar_dados()
    assert {o["verificada"] for o in d["organizacoes"]} == {True, False}
    eu = next(p for p in d["pessoas"] if p["id"] == d["config"]["eu"])
    assert eu["papel"] == "organizador"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests -q`
Expected: FAIL (dados.js não existe).

- [ ] **Step 3: Escrever dados.js**

Regras do conteúdo (JSON puro depois de `window.DADOS =`):
- `config`: `{"vaquinha": "https://exemplo.vaquinha.oficial/lula", "frase": "O que você pode fazer hoje para eleger o Lula", "hoje": "2026-10-09", "eu": 2}`.
- 5 organizações: Mandato Barba (mandato, verificada), Mandato Alfredinho (mandato, verificada), PT Diadema (partido, verificada), Coletivo Periferia Viva (coletivo, não verificada), MTST Grajaú (movimento, verificada).
- 8 pessoas: id 1 Ana Souza (moderador), id 2 Carlos Lima (organizador, organização null), id 3 Beatriz Ramos (organizador, org 1), id 4 Diego Alves (organizador, org 4), ids 5 a 8 participantes. Telefones `(11) 9xxxx-xxxx`.
- 14 ações, ids 1 a 14, com lugares reais e públicos da RMSP (estação Grajaú, terminal Parelheiros, praça da Sé, estação Jardim Ângela, Largo 13 em Santo Amaro, terminal Diadema, praça da Matriz de São Bernardo, estação Brasilândia, estação Guaianases, feira de Cidade Tiradentes, Largo da Batata, terminal Pedreira, estação Itaquera, Capão Redondo). Coordenadas aproximadas (lat negativa −23.x, lon −46.x). Distribuição: 9 publicadas, 2 em análise (ids 12 e 13, organizador 4 e organizador 2), 1 recusada (id 14, motivo "pede dinheiro para o material"), 1 encerrada (id 11, turnos em 2026-10-05), e uma publicada (id 10) cujo turno já passou (2026-10-07), para o Review Focus 1. `prioritaria: true` quando `lugar.bairro` está em `areasPrioritarias`. Ações 1, 2 e 12 têm `organizador: 2` (eu). Cada ação com `detalhe` (ex.: "Saída 2 da estação, perto do ponto de ônibus. Camisa vermelha.") e `grupo` ("https://chat.whatsapp.com/exemploXXXX").
- Turnos: pelo menos 1 por ação; ações 1 e 3 com 2 turnos; turno 5 (da ação 3) com `lotacao: 2` e 2 inscrições (Review Focus 2). Datas entre 2026-10-09 e 2026-10-18, exceto as citadas.
- Inscrições: ~12, incluindo a pessoa 2 inscrita no turno 7 (Review Focus 3), e na ação 11 (encerrada) três inscrições com `presenca` true/true/false.
- `areasPrioritarias`: `["Grajaú","Jardim Ângela","Parelheiros","Cidade Dutra","Pedreira","Diadema","São Bernardo do Campo","Guaianases","Cidade Tiradentes","Brasilândia","Capão Redondo"]`.

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests -q`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "Mockup: dados de exemplo da RMSP (organizações, pessoas, ações, turnos, inscrições)" -q
```

---

### Task 3: Tela Início (lista, filtros, mapa)

**Files:**
- Modify: `mockup/index.html` (substituir `telaInicio`, acrescentar helpers)
- Modify: `tests/test_mockup.py`

**Interfaces:**
- Produces helpers globais usados pelas outras telas:
  - `fmtData(iso)` → `"sáb 11/10, 10h"` (dias `dom seg ter qua qui sex sáb`; minutos só se ≠ 00, ex. `"10h30"`).
  - `turnosDa(acaoId)` → turnos ordenados por início.
  - `turnosFuturos(acaoId)` → só os com `inicio >= DADOS.config.hoje`.
  - `inscritosNo(turnoId)` → inscrições não canceladas do turno.
  - `vaoNa(acaoId)` → soma de inscritos em todos os turnos da ação.
  - `org(id)`, `pessoa(id)`, `acao(id)` → lookups.
  - `distanciaKm(a, b)` → haversine entre `{lat, lon}`.
  - `estado` global: `{onde: {lat, lon, rotulo} | null, quando: 'qualquer'|'hoje'|'amanha'|'fds', tipo: string|null, aba: 'lista'|'mapa'}`.
  - `ICONES`: mapa tipo → emoji (panfletagem 📄, adesivaço 🏷️, roda de conversa 🗣️, ligatona 📞, porta a porta 🚪, bandeiraço 🚩, outro ✨).
- Lista: só ações `status === 'publicada'` com ao menos um turno futuro; filtro Quando compara a data do primeiro turno futuro com `hoje` (`hoje`, `hoje+1`, `fds` = sáb ou dom nos próximos 7 dias); ordenação por data do primeiro turno futuro e depois distância (se `estado.onde`).
- Campo "onde": chips com três locais prontos (Sé, Grajaú, Diadema) que setam `estado.onde`, mais botão "usar minha localização" (`navigator.geolocation`, com fallback silencioso). Sem localização, não mostra distância.
- Aba mapa: `div#mapa` de 420 px, Leaflet do cdnjs (`https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js` e `.css`), tiles `https://tile.openstreetmap.org/{z}/{x}/{y}.png`, um marcador por ação com popup que linka para `#/acao/{id}`. Instanciar o mapa depois de inserir o HTML (função `montarMapa()` chamada ao final de `render()` quando `estado.aba === 'mapa'`).
- Card: link para `#/acao/{id}`; mostra ícone, título, organizador (nome da organização com "✓ verificada" ou nome da pessoa), `fmtData` do primeiro turno futuro, bairro e cidade, distância se houver, "N vão", e "Área prioritária" se `prioritaria`.
- Vazio: texto "Ainda não tem ação perto de você. Crie a primeira." e botão para `#/criar`.

- [ ] **Step 1: Teste que falha**

Acrescentar:
```python
def test_inicio_tem_filtros_abas_e_helpers():
    for s in ["function fmtData", "function turnosFuturos", "function vaoNa", "function distanciaKm",
              "data-quando=\"hoje\"", "data-quando=\"fds\"", "data-aba=\"mapa\"",
              "Ainda não tem ação perto de você", "Área prioritária", "leaflet"]:
        assert s in HTML, s
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests -q -k inicio`
Expected: FAIL.

- [ ] **Step 3: Implementar**

Substituir a `telaInicio` do esqueleto e acrescentar os helpers no mesmo `<script>` (antes de `render`):
```js
const ICONES={'panfletagem':'📄','adesivaço':'🏷️','roda de conversa':'🗣️','ligatona':'📞','porta a porta':'🚪','bandeiraço':'🚩','outro':'✨'};
const TIPOS=Object.keys(ICONES);
const estado={onde:null,quando:'qualquer',tipo:null,aba:'lista',filaAba:'analise'};
const org=id=>DADOS.organizacoes.find(o=>o.id===id);
const pessoa=id=>DADOS.pessoas.find(p=>p.id===id);
const acao=id=>DADOS.acoes.find(a=>a.id===id);
const turnosDa=id=>DADOS.turnos.filter(t=>t.acao===id).sort((a,b)=>a.inicio.localeCompare(b.inicio));
const turnosFuturos=id=>turnosDa(id).filter(t=>t.inicio.slice(0,10)>=DADOS.config.hoje);
const inscritosNo=tid=>DADOS.inscricoes.filter(i=>i.turno===tid&&!i.canceladaEm);
const vaoNa=id=>turnosDa(id).reduce((n,t)=>n+inscritosNo(t.id).length,0);
function fmtData(iso){const d=new Date(iso);const dias=['dom','seg','ter','qua','qui','sex','sáb'];
  const dd=String(d.getDate()).padStart(2,'0'),mm=String(d.getMonth()+1).padStart(2,'0');
  const h=d.getHours()+'h'+(d.getMinutes()?String(d.getMinutes()).padStart(2,'0'):'');
  return `${dias[d.getDay()]} ${dd}/${mm}, ${h}`}
function distanciaKm(a,b){const r=6371,x=(b.lat-a.lat)*Math.PI/180,y=(b.lon-a.lon)*Math.PI/180;
  const s=Math.sin(x/2)**2+Math.cos(a.lat*Math.PI/180)*Math.cos(b.lat*Math.PI/180)*Math.sin(y/2)**2;
  return 2*r*Math.asin(Math.sqrt(s))}
function nomeOrganizador(a){if(a.organizacao){const o=org(a.organizacao);return o.nome+(o.verificada?' <span class="selo">✓ verificada</span>':'')}return pessoa(a.organizador).nome}
function somaDias(iso,n){const d=new Date(iso+'T00:00');d.setDate(d.getDate()+n);return d.toISOString().slice(0,10)}
function acoesVisiveis(){
  const hoje=DADOS.config.hoje;
  let lista=DADOS.acoes.filter(a=>a.status==='publicada'&&turnosFuturos(a.id).length)
    .map(a=>({a,t:turnosFuturos(a.id)[0]}));
  if(estado.tipo)lista=lista.filter(x=>x.a.tipo===estado.tipo);
  if(estado.quando==='hoje')lista=lista.filter(x=>x.t.inicio.slice(0,10)===hoje);
  if(estado.quando==='amanha')lista=lista.filter(x=>x.t.inicio.slice(0,10)===somaDias(hoje,1));
  if(estado.quando==='fds')lista=lista.filter(x=>{const d=x.t.inicio.slice(0,10);const w=new Date(d+'T00:00').getDay();return d<=somaDias(hoje,7)&&(w===0||w===6)});
  lista.forEach(x=>x.km=estado.onde?distanciaKm(estado.onde,x.a.lugar):null);
  return lista.sort((p,q)=>p.t.inicio.localeCompare(q.t.inicio)||((p.km??0)-(q.km??0)));
}
function cardAcao(x){const a=x.a;return `<a class="card" href="#/acao/${a.id}">
  <div>${ICONES[a.tipo]} <strong>${a.titulo}</strong></div>
  <div class="muted">${nomeOrganizador(a)}</div>
  <div>${fmtData(x.t.inicio)} · ${a.lugar.bairro}, ${a.lugar.cidade}${x.km!=null?` · ${x.km.toFixed(1)} km`:''}</div>
  <div class="muted">${vaoNa(a.id)} vão${a.prioritaria?' · <span class="prior">Área prioritária</span>':''}</div></a>`}
function telaInicio(){
  const lista=acoesVisiveis();
  const locais=[{rotulo:'Sé',lat:-23.5505,lon:-46.6333},{rotulo:'Grajaú',lat:-23.7746,lon:-46.6978},{rotulo:'Diadema',lat:-23.6861,lon:-46.6228}];
  return `<h1>Ações do 2º turno</h1><p class="muted">${DADOS.config.frase}</p>
  <div><span class="muted">Onde você está:</span> ${locais.map(l=>`<span class="chip ${estado.onde&&estado.onde.rotulo===l.rotulo?'ativo':''}" onclick="estado.onde=${JSON.stringify(l).replace(/"/g,'&quot;')};render()">${l.rotulo}</span>`).join('')}
    <span class="chip" onclick="usarLocalizacao()">📍 usar minha localização</span></div>
  <div style="margin-top:8px">${[['qualquer','Qualquer dia'],['hoje','Hoje'],['amanha','Amanhã'],['fds','Fim de semana']].map(([k,v])=>`<span class="chip ${estado.quando===k?'ativo':''}" data-quando="${k}" onclick="estado.quando='${k}';render()">${v}</span>`).join('')}</div>
  <div style="margin-top:8px">${TIPOS.map(t=>`<span class="chip ${estado.tipo===t?'ativo':''}" onclick="estado.tipo=estado.tipo==='${t}'?null:'${t}';render()">${ICONES[t]} ${t}</span>`).join('')}</div>
  <div style="margin-top:12px"><span class="chip ${estado.aba==='lista'?'ativo':''}" data-aba="lista" onclick="estado.aba='lista';render()">Lista</span><span class="chip ${estado.aba==='mapa'?'ativo':''}" data-aba="mapa" onclick="estado.aba='mapa';render()">Mapa</span></div>
  ${estado.aba==='mapa'?'<div id="mapa" style="height:420px;border-radius:12px;margin-top:8px"></div>':
    lista.length?lista.map(cardAcao).join(''):`<p>Ainda não tem ação perto de você. Crie a primeira.</p><a class="btn" href="#/criar">Criar ação</a>`}`}
function usarLocalizacao(){if(!navigator.geolocation)return;navigator.geolocation.getCurrentPosition(p=>{estado.onde={rotulo:'aqui',lat:p.coords.latitude,lon:p.coords.longitude};render()},()=>{})}
function montarMapa(){const el=document.getElementById('mapa');if(!el||!window.L)return;
  const m=L.map(el).setView([-23.6,-46.6],10);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap'}).addTo(m);
  acoesVisiveis().forEach(x=>L.marker([x.a.lugar.lat,x.a.lugar.lon]).addTo(m).bindPopup(`${ICONES[x.a.tipo]} <a href="#/acao/${x.a.id}">${x.a.titulo}</a><br>${fmtData(x.t.inicio)}`))}
```
No `<head>`, acrescentar:
```html
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js"></script>
```
Em `render()`, depois de setar `innerHTML`: `if(rota!=='acao'&&estado.aba==='mapa'&&(rota||'inicio')==='inicio')montarMapa();`.

- [ ] **Step 4: Rodar e ver passar; abrir no navegador**

Run: `python -m pytest tests -q` → todos passam. Abrir `mockup/index.html` no navegador: lista com 8 ações (a de id 10, turno passado, fora), chips funcionam, aba Mapa mostra os pinos.

- [ ] **Step 5: Teste do Review Focus 1 (ação só com turno passado não aparece)**

```python
def test_acao_com_turno_passado_fica_fora_da_lista():
    d = carregar_dados()
    hoje = d["config"]["hoje"]
    futuros = {t["acao"] for t in d["turnos"] if t["inicio"][:10] >= hoje}
    a10 = next(a for a in d["acoes"] if a["id"] == 10)
    assert a10["status"] == "publicada" and 10 not in futuros
    assert "turnosFuturos(a.id).length" in HTML  # filtro da lista exige turno futuro
```
Run: `python -m pytest tests -q` → passa.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "Mockup: tela Início com lista, filtros de quando e tipo, onde estou e aba mapa" -q
```

---

### Task 4: Tela Ação e inscrição

**Files:**
- Modify: `mockup/index.html` (substituir `telaAcao`, acrescentar `fluxoVou`)
- Modify: `tests/test_mockup.py`

**Interfaces:**
- Consumes: helpers do Task 3.
- Produces: `estado.inscrevendo = {turno: id, passo: 'dados'|'codigo'|null, nome, telefone}`; função `inscrever(turnoId)` que cria uma inscrição para `DADOS.config.eu` (no mockup, a pessoa logada; "nome e telefone" digitados são só visuais); `desistir(turnoId)` seta `canceladaEm`.
- Regras: botão **Vou** por turno. Se `inscritosNo(t.id)` já tem `pessoa === eu` → mostra "Você vai ✓" e botão "desistir". Se `t.lotacao && inscritosNo(t.id).length >= t.lotacao` → botão desabilitado "lotado". Se `t.inicio < hoje` → desabilitado "turno encerrado". Se não há nenhum turno futuro → aviso no topo "Esta ação já aconteceu".
- Fluxo Vou (dentro da mesma tela, sem modal): passo `dados` mostra campos nome e telefone e o aviso "Seu nome e telefone vão para quem organiza esta ação." com botão "Receber código"; passo `codigo` mostra campo de 4 dígitos (qualquer valor aceito no mockup) e "Confirmar"; ao confirmar, `inscrever` e volta a `passo: null`.
- Só quando a pessoa logada está inscrita em algum turno da ação: bloco "Combinado" com `detalhe`, botão "Entrar no grupo do WhatsApp" (`a.grupo`), e botão "Compartilhar" (`navigator.share` se existir; senão copia a URL).
- Mini-mapa: `div#minimapa` 180 px, Leaflet, um marcador, `montarMiniMapa(a)` chamado em `render()` quando `rota === 'acao'`.

- [ ] **Step 1: Teste que falha**

```python
def test_tela_acao_regras_de_inscricao():
    for s in ["function telaAcao", "function inscrever", "function desistir", "lotado", "turno encerrado",
              "Esta ação já aconteceu", "Você vai", "Seu nome e telefone vão para quem organiza esta ação",
              "Receber código", "Entrar no grupo do WhatsApp", "minimapa"]:
        assert s in HTML, s


def test_detalhe_e_grupo_so_para_inscritos():
    # o bloco "Combinado" só é montado dentro do ramo que checa inscrição
    i = HTML.index("Combinado")
    assert "estouInscrito" in HTML[i-400:i]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests -q -k "acao or inscritos"` → FAIL.

- [ ] **Step 3: Implementar**

```js
estado.inscrevendo=null;
const eu=()=>DADOS.config.eu;
const estouInscrito=tid=>inscritosNo(tid).some(i=>i.pessoa===eu());
function inscrever(tid){if(estouInscrito(tid))return;DADOS.inscricoes.push({id:Date.now(),pessoa:eu(),turno:tid,criadaEm:DADOS.config.hoje,canceladaEm:null,presenca:null});estado.inscrevendo=null;render()}
function desistir(tid){const i=DADOS.inscricoes.find(i=>i.turno===tid&&i.pessoa===eu()&&!i.canceladaEm);if(i)i.canceladaEm=DADOS.config.hoje;render()}
function iniciarVou(tid){estado.inscrevendo={turno:tid,passo:'dados'};render()}
function pedirCodigo(){estado.inscrevendo.passo='codigo';render()}
function compartilhar(){const u=location.href;if(navigator.share)navigator.share({url:u});else{navigator.clipboard&&navigator.clipboard.writeText(u);alert('Link copiado')}}
function botaoTurno(t){
  const n=inscritosNo(t.id).length;
  if(estouInscrito(t.id))return `<span class="selo">Você vai ✓</span> <button class="btn sec" onclick="desistir(${t.id})">desistir</button>`;
  if(t.inicio.slice(0,10)<DADOS.config.hoje)return `<button class="btn" disabled>turno encerrado</button>`;
  if(t.lotacao&&n>=t.lotacao)return `<button class="btn" disabled>lotado</button>`;
  return `<button class="btn" onclick="iniciarVou(${t.id})">Vou</button>`}
function telaAcao(id){const a=acao(id);if(!a)return '<p>Ação não encontrada.</p>';
  const ts=turnosDa(id),futuros=turnosFuturos(id);const ins=estado.inscrevendo;
  const inscritoEmAlgum=ts.some(t=>estouInscrito(t.id));
  return `<a href="#/inicio" class="muted">← voltar</a>
  <h1>${ICONES[a.tipo]} ${a.titulo}</h1>
  <div class="muted">${nomeOrganizador(a)}${a.prioritaria?' · <span class="prior">Área prioritária</span>':''}</div>
  ${futuros.length?'':'<p class="erro">Esta ação já aconteceu.</p>'}
  <p>${a.descricao}</p>
  <h2>Onde</h2><div>${a.lugar.nome}</div><div class="muted">${a.lugar.bairro}, ${a.lugar.cidade}</div>
  <div id="minimapa" style="height:180px;border-radius:12px;margin:8px 0"></div>
  <h2>Quando</h2>
  ${ts.map(t=>`<div class="card"><div>${fmtData(t.inicio)} até ${fmtData(t.fim).split(', ')[1]} · ${inscritosNo(t.id).length} vão${t.lotacao?` de ${t.lotacao}`:''}</div><div style="margin-top:8px">${botaoTurno(t)}</div>
    ${ins&&ins.turno===t.id&&ins.passo==='dados'?`<label>Seu nome</label><input id="vnome"><label>Seu WhatsApp</label><input id="vtel" placeholder="(11) 9xxxx-xxxx"><p class="muted">Seu nome e telefone vão para quem organiza esta ação.</p><button class="btn" onclick="pedirCodigo()">Receber código</button>`:''}
    ${ins&&ins.turno===t.id&&ins.passo==='codigo'?`<label>Código que chegou no WhatsApp</label><input id="vcod" maxlength="4" placeholder="0000"><button class="btn" onclick="inscrever(${t.id})">Confirmar</button>`:''}</div>`).join('')}
  ${inscritoEmAlgum?`<h2>Combinado</h2><div class="card"><p>${a.detalhe}</p><a class="btn" href="${a.grupo}" target="_blank">Entrar no grupo do WhatsApp</a> <button class="btn sec" onclick="compartilhar()">Compartilhar</button></div>`:''}
  <h2>Quem organiza</h2><div class="muted">${nomeOrganizador(a)}</div>`}
function montarMiniMapa(a){const el=document.getElementById('minimapa');if(!el||!window.L)return;const m=L.map(el,{zoomControl:false}).setView([a.lugar.lat,a.lugar.lon],15);L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(m);L.marker([a.lugar.lat,a.lugar.lon]).addTo(m)}
```
Em `render()`: `if(rota==='acao'&&acao(Number(arg)))montarMiniMapa(acao(Number(arg)));`.

- [ ] **Step 4: Rodar, abrir no navegador**

`python -m pytest tests -q` → passa. No navegador: ação 3, turno 5 mostra "lotado"; ação 7 (turno 7) mostra "Você vai ✓" e o bloco Combinado; ação 10 mostra "Esta ação já aconteceu"; fluxo Vou em outra ação conclui e libera o Combinado.

- [ ] **Step 5: Testes dos Review Focus 2 e 3**

```python
def test_turno_lotado_e_inscricao_duplicada_nos_dados_e_no_codigo():
    d = carregar_dados()
    t5 = next(t for t in d["turnos"] if t["id"] == 5)
    n5 = len([i for i in d["inscricoes"] if i["turno"] == 5 and not i["canceladaEm"]])
    assert t5["lotacao"] == n5 == 2
    assert any(i["turno"] == 7 and i["pessoa"] == d["config"]["eu"] for i in d["inscricoes"])
    assert "if(estouInscrito(tid))return" in HTML  # não duplica
    assert "n>=t.lotacao" in HTML
```
Run → passa.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "Mockup: tela Ação com turnos, fluxo Vou com código, lotação, desistir e bloco Combinado só para inscritos" -q
```

---

### Task 5: Criar ação (3 passos)

**Files:**
- Modify: `mockup/index.html` (substituir `telaCriar`)
- Modify: `tests/test_mockup.py`

**Interfaces:**
- Consumes: helpers, `eu()`, `TIPOS`, `ICONES`.
- Produces: `estado.criar = {passo: 1|2|3, tipo, titulo, descricao, lugar: {nome,bairro,cidade,lat,lon}|null, turnos: [{inicio,fim,lotacao}], detalhe, grupo, nome, telefone, organizacao: id|null, erros: {}}`; função `publicarAcao()` que cria a ação com `status` = `'publicada'` se `organizacao && org(organizacao).verificada`, senão `'em análise'`, `organizador: eu()`, `prioritaria: DADOS.areasPrioritarias.includes(lugar.bairro)`, e os turnos; depois redireciona para `#/minhas` com uma mensagem no topo.
- `MODELOS`: por tipo, `{titulo, descricao, dica}`. Ex.: panfletagem → título "Panfletagem na estação", descrição "Vamos distribuir material do Lula na saída da estação. Traga disposição; o material a gente leva.", dica "Leve 2 pessoas por saída e combine um ponto de encontro fácil de achar."; adesivaço → "Adesivaço no semáforo"...; roda de conversa → "Roda de conversa no bairro"; ligatona → "Ligatona para indecisos" com dica "Cada pessoa traz a lista dos próprios contatos; a gente passa o roteiro."; porta a porta → "Porta a porta na vila"; bandeiraço → "Bandeiraço na avenida"; outro → título vazio.
- Lugares prontos para busca (passo 2): lista `LUGARES` de 12 lugares públicos (os mesmos dos dados mais alguns), filtrada por texto digitado; ao escolher, mostra mini-mapa com o pino (`montarMiniMapaLugar`).
- Validação (botão "Continuar"/"Publicar"): passo 1 exige tipo; passo 2 exige título, lugar, ≥1 turno com início e fim e `fim > inicio`; passo 3 exige nome e telefone no formato `(11) 9xxxx-xxxx` ou 11 dígitos. Erro ao lado do campo, em `.erro`.
- Organização no passo 3: `<select>` com "Sou eu mesmo(a)" e as organizações; texto ao lado "✓ verificada: publica na hora" ou "sem selo: passa pela fila".

- [ ] **Step 1: Teste que falha**

```python
def test_criar_tem_tres_passos_modelos_e_validacao():
    for s in ["function telaCriar", "function publicarAcao", "const MODELOS", "const LUGARES",
              "Continuar", "Publicar", "sua ação está em análise", "publica na hora", "passa pela fila",
              "Detalhe do encontro, só para inscritos", "Link do grupo de WhatsApp"]:
        assert s in HTML, s


def test_status_nasce_publicada_so_com_organizacao_verificada():
    assert "o&&o.verificada?'publicada':'em análise'" in HTML
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests -q -k criar` → FAIL.

- [ ] **Step 3: Implementar**

```js
const MODELOS={
 'panfletagem':{titulo:'Panfletagem na estação',descricao:'Vamos distribuir material do Lula na saída da estação. Traga disposição; o material a gente leva.',dica:'Leve 2 pessoas por saída e combine um ponto de encontro fácil de achar.'},
 'adesivaço':{titulo:'Adesivaço no semáforo',descricao:'Adesivos do Lula para carros, motos e quem passar. Material garantido.',dica:'Escolha um cruzamento com semáforo longo e calçada larga.'},
 'roda de conversa':{titulo:'Roda de conversa no bairro',descricao:'Conversa aberta sobre por que votar no Lula e como responder às dúvidas de vizinhos e família.',dica:'Lugar com sombra e lugar para sentar. Uma hora basta.'},
 'ligatona':{titulo:'Ligatona para indecisos',descricao:'Cada pessoa liga para os próprios contatos com um roteiro simples. Pode ser de casa.',dica:'Cada pessoa traz a lista dos próprios contatos; a gente passa o roteiro.'},
 'porta a porta':{titulo:'Porta a porta na vila',descricao:'Em duplas, conversa na porta com quem mora na região. Roteiro e material no ponto de encontro.',dica:'Sempre em dupla. Combine horário de voltar ao ponto.'},
 'bandeiraço':{titulo:'Bandeiraço na avenida',descricao:'Bandeiras e faixas do Lula na hora do rush. Traga bandeira se tiver.',dica:'Hora do rush, calçada larga, longe da faixa de pedestres.'},
 'outro':{titulo:'',descricao:'',dica:'Descreva o que vai acontecer e o que a pessoa precisa levar.'}};
const LUGARES=[{nome:'Estação Grajaú',bairro:'Grajaú',cidade:'São Paulo',lat:-23.7746,lon:-46.6978},{nome:'Terminal Parelheiros',bairro:'Parelheiros',cidade:'São Paulo',lat:-23.8273,lon:-46.7271},{nome:'Praça da Sé',bairro:'Sé',cidade:'São Paulo',lat:-23.5505,lon:-46.6333},{nome:'Estação Jardim Ângela',bairro:'Jardim Ângela',cidade:'São Paulo',lat:-23.7138,lon:-46.7609},{nome:'Largo 13 de Maio',bairro:'Santo Amaro',cidade:'São Paulo',lat:-23.6510,lon:-46.7087},{nome:'Terminal Diadema',bairro:'Centro',cidade:'Diadema',lat:-23.6861,lon:-46.6228},{nome:'Praça da Matriz',bairro:'Centro',cidade:'São Bernardo do Campo',lat:-23.6944,lon:-46.5654},{nome:'Estação Brasilândia',bairro:'Brasilândia',cidade:'São Paulo',lat:-23.4616,lon:-46.6895},{nome:'Estação Guaianases',bairro:'Guaianases',cidade:'São Paulo',lat:-23.5410,lon:-46.4103},{nome:'Feira de Cidade Tiradentes',bairro:'Cidade Tiradentes',cidade:'São Paulo',lat:-23.5853,lon:-46.4035},{nome:'Largo da Batata',bairro:'Pinheiros',cidade:'São Paulo',lat:-23.5668,lon:-46.6931},{nome:'Terminal Capão Redondo',bairro:'Capão Redondo',cidade:'São Paulo',lat:-23.6666,lon:-46.7680}];
function novoCriar(){return {passo:1,tipo:null,titulo:'',descricao:'',lugar:null,buscaLugar:'',turnos:[{inicio:'',fim:'',lotacao:''}],detalhe:'',grupo:'',nome:'',telefone:'',organizacao:null,erros:{}}}
estado.criar=novoCriar();estado.aviso=null;
function cv(campo,valor){estado.criar[campo]=valor}
function escolherTipo(t){const c=estado.criar;c.tipo=t;c.titulo=MODELOS[t].titulo;c.descricao=MODELOS[t].descricao;c.erros={};c.passo=2;render()}
function escolherLugar(i){estado.criar.lugar=LUGARES[i];render()}
function addTurno(){estado.criar.turnos.push({inicio:'',fim:'',lotacao:''});render()}
function telValido(t){return /^\(\d{2}\) 9[\dx]{4}-[\dx]{4}$/.test(t)||/^\d{11}$/.test(t.replace(/\D/g,''))}
function validarPasso2(){const c=estado.criar,e={};if(!c.titulo.trim())e.titulo='Dê um título.';if(!c.lugar)e.lugar='Escolha um lugar público.';
  const ts=c.turnos.filter(t=>t.inicio||t.fim);if(!ts.length)e.turnos='Informe pelo menos um turno.';else if(ts.some(t=>!t.inicio||!t.fim||t.fim<=t.inicio))e.turnos='Cada turno precisa de início e fim, e o fim depois do início.';
  c.erros=e;if(!Object.keys(e).length)c.passo=3;render()}
function publicarAcao(){const c=estado.criar,e={};if(!c.nome.trim())e.nome='Seu nome.';if(!telValido(c.telefone))e.telefone='Telefone no formato (11) 9xxxx-xxxx.';c.erros=e;if(Object.keys(e).length){render();return}
  const o=c.organizacao?org(c.organizacao):null;const status=o&&o.verificada?'publicada':'em análise';
  const id=Math.max(...DADOS.acoes.map(a=>a.id))+1;
  DADOS.acoes.push({id,titulo:c.titulo,tipo:c.tipo,descricao:c.descricao,organizador:eu(),organizacao:c.organizacao,lugar:c.lugar,detalhe:c.detalhe,grupo:c.grupo,status,motivoRecusa:null,prioritaria:DADOS.areasPrioritarias.includes(c.lugar.bairro),criadaEm:DADOS.config.hoje});
  c.turnos.filter(t=>t.inicio&&t.fim).forEach((t,i)=>DADOS.turnos.push({id:Date.now()+i,acao:id,inicio:t.inicio,fim:t.fim,lotacao:t.lotacao?Number(t.lotacao):null}));
  estado.aviso=status==='publicada'?'Ação publicada! Já aparece no Início.':'Recebemos: sua ação está em análise, avisamos pelo WhatsApp.';
  estado.criar=novoCriar();location.hash='#/minhas'}
function telaCriar(){const c=estado.criar,E=k=>c.erros[k]?`<div class="erro">${c.erros[k]}</div>`:'';
  if(c.passo===1)return `<h1>Criar ação</h1><p class="muted">Passo 1 de 3: que tipo de ação?</p>${TIPOS.map(t=>`<a class="card" href="#" onclick="escolherTipo('${t}');return false"><strong>${ICONES[t]} ${t}</strong><div class="muted">${MODELOS[t].dica}</div></a>`).join('')}`;
  if(c.passo===2)return `<h1>Criar ação</h1><p class="muted">Passo 2 de 3: onde e quando · ${ICONES[c.tipo]} ${c.tipo}</p>
   <label>Título</label><input value="${c.titulo}" oninput="cv('titulo',this.value)">${E('titulo')}
   <label>Descrição</label><textarea rows="3" oninput="cv('descricao',this.value)">${c.descricao}</textarea>
   <label>Lugar público do encontro</label><input placeholder="estação, praça, terminal, feira..." value="${c.buscaLugar}" oninput="cv('buscaLugar',this.value);render();document.querySelector('input[placeholder^=estação]').focus()">
   ${c.lugar?`<div class="card"><strong>${c.lugar.nome}</strong><div class="muted">${c.lugar.bairro}, ${c.lugar.cidade}</div><div id="minimapa" style="height:160px;margin-top:8px"></div></div>`:
     LUGARES.map((l,i)=>({l,i})).filter(x=>x.l.nome.toLowerCase().includes(c.buscaLugar.toLowerCase())).slice(0,5).map(x=>`<a class="card" href="#" onclick="escolherLugar(${x.i});return false">${x.l.nome} <span class="muted">· ${x.l.bairro}, ${x.l.cidade}</span></a>`).join('')}${E('lugar')}
   <label>Turnos</label>${c.turnos.map((t,i)=>`<div class="card"><input type="datetime-local" value="${t.inicio}" onchange="estado.criar.turnos[${i}].inicio=this.value"> até <input type="datetime-local" value="${t.fim}" onchange="estado.criar.turnos[${i}].fim=this.value"><input type="number" placeholder="lotação (opcional)" value="${t.lotacao}" oninput="estado.criar.turnos[${i}].lotacao=this.value"></div>`).join('')}
   <button class="btn sec" onclick="addTurno()">+ outro turno</button>${E('turnos')}
   <label>Detalhe do encontro, só para inscritos</label><input placeholder="ex.: saída 2, camisa vermelha" value="${c.detalhe}" oninput="cv('detalhe',this.value)">
   <label>Link do grupo de WhatsApp</label><input placeholder="https://chat.whatsapp.com/..." value="${c.grupo}" oninput="cv('grupo',this.value)">
   <p><button class="btn sec" onclick="estado.criar.passo=1;render()">Voltar</button> <button class="btn" onclick="validarPasso2()">Continuar</button></p>`;
  const o=c.organizacao?org(c.organizacao):null;
  return `<h1>Criar ação</h1><p class="muted">Passo 3 de 3: quem organiza</p>
   <label>Seu nome</label><input value="${c.nome}" oninput="cv('nome',this.value)">${E('nome')}
   <label>Seu WhatsApp</label><input placeholder="(11) 9xxxx-xxxx" value="${c.telefone}" oninput="cv('telefone',this.value)">${E('telefone')}
   <label>Em nome de uma organização?</label><select onchange="estado.criar.organizacao=this.value?Number(this.value):null;render()"><option value="">Sou eu mesmo(a)</option>${DADOS.organizacoes.map(x=>`<option value="${x.id}" ${c.organizacao===x.id?'selected':''}>${x.nome}</option>`).join('')}</select>
   <div class="muted">${o&&o.verificada?'✓ verificada: publica na hora':'sem selo: passa pela fila (sua ação está em análise até um moderador aprovar)'}</div>
   <p><button class="btn sec" onclick="estado.criar.passo=2;render()">Voltar</button> <button class="btn" onclick="publicarAcao()">Publicar</button></p>`}
```
Em `render()`: `if(rota==='criar'&&estado.criar.passo===2&&estado.criar.lugar){const l=estado.criar.lugar;montarMiniMapa({lugar:l})}`.

- [ ] **Step 4: Rodar, abrir no navegador**

`python -m pytest tests -q` → passa. No navegador: criar com organização verificada vai para "publicada" e aparece no Início; sem organização vai para "em análise" e aparece na Fila. Campos vazios mostram erro sem avançar.

- [ ] **Step 5: Teste do Review Focus 4 (validação)**

```python
def test_validacao_dos_campos_obrigatorios():
    for s in ["Dê um título.", "Escolha um lugar público.", "Informe pelo menos um turno.",
              "Telefone no formato", "t.fim<=t.inicio"]:
        assert s in HTML, s
```
Run → passa.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "Mockup: Criar ação em 3 passos com modelos por tipo, busca de lugar público, turnos e organização" -q
```

---

### Task 6: Minhas ações (organizador) e Fila (moderador)

**Files:**
- Modify: `mockup/index.html` (substituir `telaMinhas`, `telaFila`)
- Modify: `tests/test_mockup.py`

**Interfaces:**
- Consumes: tudo acima; `estado.aviso` (mostrado uma vez no topo de Minhas e zerado).
- Minhas: ações com `organizador === eu()`, ordenadas por status (em análise, publicada, encerrada, recusada) e data. Card expansível (`estado.minhasAberta = id`) com: status e motivo da recusa; por turno, lista de inscritos (nome e telefone), botões **Copiar números** (`navigator.clipboard`), **Mandar aviso** (abre `textarea` com texto pronto: "Oi! Amanhã tem {titulo} às {hora} em {lugar}. {detalhe}. Até lá!" e botão "copiar"), **Marcar presença** (só se `t.inicio < hoje`: checkbox por inscrito que seta `presenca`), **Encerrar** (status → encerrada), **Editar** (leva para `#/criar` com `estado.criar` preenchido a partir da ação, passo 2; ao publicar de novo, substitui a ação em vez de criar: `estado.criar.editando = id`).
- Fila: `estado.filaAba` = `'analise'` | `'publicadas'`. Em análise: ações `status === 'em análise'`, mais nova primeiro, mostrando o que o participante veria (reuso de `cardAcao` com o primeiro turno) mais telefone do organizador, "já criou N ações (M aprovadas, K recusadas)", botões **Aprovar** (→ publicada), **Recusar** (abre campo motivo, obrigatório, → recusada), **Dar selo à organização** (se `organizacao` e não verificada → `verificada = true`). Publicadas: botões **Despublicar** (→ rascunho) e **Bloquear organizador** (`pessoa.bloqueada = true` e despublica todas as ações dessa pessoa).
- Regras de recusa escritas acima da lista, como lembrete ao moderador: "Recuse se: não é ação de campanha; o lugar não é público; convoca para confronto; pede dinheiro; tem dado pessoal no texto."

- [ ] **Step 1: Teste que falha**

```python
def test_minhas_e_fila():
    for s in ["function telaMinhas", "function telaFila", "Copiar números", "Mandar aviso", "Marcar presença",
              "Encerrar", "Editar", "Aprovar", "Recusar", "Dar selo à organização", "Despublicar",
              "Bloquear organizador", "Recuse se:", "já criou"]:
        assert s in HTML, s


def test_recusa_exige_motivo_e_bloqueio_despublica_tudo():
    assert "Escreva o motivo" in HTML
    assert "bloqueada=true" in HTML.replace(" ", "")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests -q -k "minhas or recusa"` → FAIL.

- [ ] **Step 3: Implementar**

```js
estado.minhasAberta=null;estado.avisoTexto=null;estado.recusando=null;
const ORDEM={'em análise':0,'publicada':1,'encerrada':2,'recusada':3,'rascunho':4};
function textoAviso(a,t){return `Oi! ${fmtData(t.inicio)} tem ${a.titulo} em ${a.lugar.nome}, ${a.lugar.bairro}. ${a.detalhe} Até lá!`}
function copiar(txt){navigator.clipboard&&navigator.clipboard.writeText(txt);alert('Copiado')}
function marcarPresenca(insId,v){const i=DADOS.inscricoes.find(i=>i.id===insId);if(i)i.presenca=v}
function encerrar(id){acao(id).status='encerrada';render()}
function editar(id){const a=acao(id);const c=novoCriar();Object.assign(c,{passo:2,editando:id,tipo:a.tipo,titulo:a.titulo,descricao:a.descricao,lugar:a.lugar,detalhe:a.detalhe,grupo:a.grupo,organizacao:a.organizacao,nome:pessoa(a.organizador).nome,telefone:pessoa(a.organizador).telefone,turnos:turnosDa(id).map(t=>({inicio:t.inicio,fim:t.fim,lotacao:t.lotacao||''}))});estado.criar=c;location.hash='#/criar'}
function telaMinhas(){const minhas=DADOS.acoes.filter(a=>a.organizador===eu()).sort((p,q)=>ORDEM[p.status]-ORDEM[q.status]);
  const aviso=estado.aviso?`<div class="card" style="background:#eaf7ee">${estado.aviso}</div>`:'';estado.aviso=null;
  return `<h1>Minhas ações</h1>${aviso}${minhas.length?'':'<p class="muted">Você ainda não criou nenhuma ação.</p>'}
  ${minhas.map(a=>`<div class="card"><div onclick="estado.minhasAberta=estado.minhasAberta===${a.id}?null:${a.id};render()" style="cursor:pointer"><strong>${ICONES[a.tipo]} ${a.titulo}</strong> <span class="muted">· ${a.status}</span>${a.motivoRecusa?`<div class="erro">Motivo: ${a.motivoRecusa}</div>`:''}<div class="muted">${vaoNa(a.id)} inscritos</div></div>
   ${estado.minhasAberta===a.id?turnosDa(a.id).map(t=>{const ins=inscritosNo(t.id);const passado=t.inicio.slice(0,10)<DADOS.config.hoje;return `<div style="margin-top:8px;border-top:1px solid var(--borda);padding-top:8px"><strong>${fmtData(t.inicio)}</strong> · ${ins.length} inscritos
     ${ins.map(i=>`<div>${pessoa(i.pessoa).nome} <span class="muted">${pessoa(i.pessoa).telefone}</span>${passado?` <label style="display:inline;font-weight:400"><input type="checkbox" style="width:auto" ${i.presenca?'checked':''} onchange="marcarPresenca(${i.id},this.checked)"> presente</label>`:''}</div>`).join('')}
     <div style="margin-top:6px"><button class="btn sec" onclick="copiar('${ins.map(i=>pessoa(i.pessoa).telefone).join(', ')}')">Copiar números</button> <button class="btn sec" onclick="estado.avisoTexto=${t.id};render()">Mandar aviso</button>${passado?' <span class="muted">Marcar presença: marque quem foi</span>':''}</div>
     ${estado.avisoTexto===t.id?`<textarea rows="3" id="aviso${t.id}">${textoAviso(a,t)}</textarea><button class="btn sec" onclick="copiar(document.getElementById('aviso${t.id}').value)">copiar</button>`:''}</div>`}).join('')+`<div style="margin-top:8px"><button class="btn sec" onclick="editar(${a.id})">Editar</button> ${a.status!=='encerrada'?`<button class="btn sec" onclick="encerrar(${a.id})">Encerrar</button>`:''}</div>`:''}</div>`).join('')}`}
function historicoOrganizador(pid){const as=DADOS.acoes.filter(a=>a.organizador===pid);return `já criou ${as.length} ações (${as.filter(a=>a.status==='publicada'||a.status==='encerrada').length} aprovadas, ${as.filter(a=>a.status==='recusada').length} recusadas)`}
function aprovar(id){acao(id).status='publicada';render()}
function recusar(id){const m=(document.getElementById('motivo'+id)||{}).value||'';if(!m.trim()){estado.recusando=id;estado.erroRecusa='Escreva o motivo.';render();return}const a=acao(id);a.status='recusada';a.motivoRecusa=m;estado.recusando=null;render()}
function darSelo(oid){org(oid).verificada=true;render()}
function despublicar(id){acao(id).status='rascunho';render()}
function bloquear(pid){pessoa(pid).bloqueada=true;DADOS.acoes.filter(a=>a.organizador===pid&&a.status==='publicada').forEach(a=>a.status='rascunho');render()}
function telaFila(){const aba=estado.filaAba;
  const lista=aba==='analise'?DADOS.acoes.filter(a=>a.status==='em análise').sort((p,q)=>q.criadaEm.localeCompare(p.criadaEm)):DADOS.acoes.filter(a=>a.status==='publicada');
  return `<h1>Fila de moderação</h1>
  <span class="chip ${aba==='analise'?'ativo':''}" onclick="estado.filaAba='analise';render()">Em análise (${DADOS.acoes.filter(a=>a.status==='em análise').length})</span><span class="chip ${aba==='publicadas'?'ativo':''}" onclick="estado.filaAba='publicadas';render()">Publicadas</span>
  <p class="muted">Recuse se: não é ação de campanha; o lugar não é público; convoca para confronto; pede dinheiro; tem dado pessoal no texto.</p>
  ${lista.length?'':'<p class="muted">Nada por aqui.</p>'}
  ${lista.map(a=>{const t=turnosDa(a.id)[0]||{inicio:a.criadaEm+'T00:00'};const p=pessoa(a.organizador);const o=a.organizacao?org(a.organizacao):null;return `<div class="card">${cardAcao({a,t,km:null})}
   <div class="muted">Organizador: ${p.nome} · ${p.telefone} · ${historicoOrganizador(p.id)}</div>
   <div style="margin-top:8px">${aba==='analise'?`<button class="btn" onclick="aprovar(${a.id})">Aprovar</button> <button class="btn sec" onclick="estado.recusando=${a.id};render()">Recusar</button>${o&&!o.verificada?` <button class="btn sec" onclick="darSelo(${o.id})">Dar selo à organização</button>`:''}`:
     `<button class="btn sec" onclick="despublicar(${a.id})">Despublicar</button> <button class="btn sec" onclick="bloquear(${p.id})">Bloquear organizador</button>`}</div>
   ${estado.recusando===a.id?`<label>Motivo da recusa</label><input id="motivo${a.id}" placeholder="ex.: pede dinheiro para o material">${estado.erroRecusa?`<div class="erro">${estado.erroRecusa}</div>`:''}<button class="btn" onclick="recusar(${a.id})">Confirmar recusa</button>`:''}</div>`}).join('')}`}
```
Em `publicarAcao()`, antes de `DADOS.acoes.push`, tratar edição: `if(c.editando){const a=acao(c.editando);Object.assign(a,{titulo:c.titulo,descricao:c.descricao,lugar:c.lugar,detalhe:c.detalhe,grupo:c.grupo,organizacao:c.organizacao,prioritaria:DADOS.areasPrioritarias.includes(c.lugar.bairro)});DADOS.turnos=DADOS.turnos.filter(t=>t.acao!==a.id);c.turnos.filter(t=>t.inicio&&t.fim).forEach((t,i)=>DADOS.turnos.push({id:Date.now()+i,acao:a.id,inicio:t.inicio,fim:t.fim,lotacao:t.lotacao?Number(t.lotacao):null}));estado.aviso='Ação atualizada.';estado.criar=novoCriar();location.hash='#/minhas';return}`.

- [ ] **Step 4: Rodar, abrir no navegador**

`python -m pytest tests -q` → passa. No navegador: Minhas mostra as ações 1, 2 e 12 do Carlos (eu); abrir a 11 encerrada não aparece (é de outra pessoa) mas a 2 com turno passado permite marcar presença; Fila mostra 12 e 13; aprovar a 13 faz ela aparecer no Início; recusar sem motivo mostra erro.

- [ ] **Step 5: Teste do Review Focus 5 (verificada nasce publicada, sem selo em análise)**

```python
def test_fluxo_de_status_nos_dados_e_no_codigo():
    d = carregar_dados()
    a12 = next(a for a in d["acoes"] if a["id"] == 12)
    assert a12["status"] == "em análise" and a12["organizacao"] in (None, 4)
    assert ".status='publicada'" in HTML  # aprovar
    assert "a.status='recusada'" in HTML  # recusar
```
Run → passa.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "Mockup: Minhas ações (inscritos, aviso, presença, editar, encerrar) e Fila (aprovar, recusar com motivo, selo, despublicar, bloquear)" -q
```

---

### Task 7: Verificação no navegador e publicação como artifact privado

**Files:**
- Modify: `CLAUDE.md` (id do artifact)
- Modify: `README.md` (link)

- [ ] **Step 1: Percorrer os cinco fluxos com o Playwright**

Com `mcp__playwright__browser_navigate` em `file:///C:/Users/guilh/source/repos/acoes-segundo-turno/mockup/index.html`, viewport 390×844, e `browser_snapshot` em cada tela: Início (lista e mapa), Ação 3 (lotado), Ação 5 (fluxo Vou até o Combinado), Criar (três passos até publicar com organização verificada e sem), Minhas (presença na ação 2), Fila (aprovar 13, recusar 12 com motivo). Tirar um screenshot de cada tela em `docs/capturas/` (criar a pasta) para o Gui ver sem abrir.

- [ ] **Step 2: Corrigir o que quebrar**

Qualquer erro de console (`browser_console_messages`) ou texto cortado no celular é corrigido no `index.html` e coberto por teste quando for regra de negócio. Commit por correção.

- [ ] **Step 3: Publicar como artifact privado**

Como o artifact não carrega `dados.js` externo por padrão, publicar com `files: {"dados.js": "mockup/dados.js"}` junto com `file_path: mockup/index.html`, `icon: "map"`, descrição "Mockup navegável da plataforma de ações do 2º turno". Não compartilhar publicamente. Gravar a URL devolvida no `CLAUDE.md` e no `README.md`.

- [ ] **Step 4: Commit e criar o remoto**

```bash
git add -A && git commit -m "Mockup: capturas e artifact privado" -q
gh repo create acoes-segundo-turno --private --source=. --push
```

- [ ] **Step 5: Relatar ao Gui**

Mensagem final com a URL do artifact, o que validar primeiro (textos dos modelos por tipo, ordem dos passos de criação, o que aparece antes e depois de inscrever) e as três decisões técnicas que vêm a seguir na v1 real: verificação de telefone (WhatsApp Business API vs SMS), hospedagem sem servidor (Supabase ou Firebase, no plano gratuito) e como ler as áreas prioritárias do `mapa-segundo-turno`.
