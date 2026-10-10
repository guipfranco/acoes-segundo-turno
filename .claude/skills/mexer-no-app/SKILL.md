---
name: mexer-no-app
description: Use quando a tarefa mexe no site da Agenda Bora Lula (pasta app/) - tela, filtro, card, texto, estilo, mapa, formulário de cadastro, "Eu vou!", Perfil, Fila, ou a camada de dados (api.js, api-exemplo.js, api-supabase.js, dados.js), ou quando precisa rodar o app localmente e conferir uma mudança.
---

# Mexer no app

`app/` é o site inteiro: HTML, CSS e JS puros, sem build, sem npm, sem framework. Tudo o que muda ali precisa
funcionar nos dois modos de dados e passar nos testes.

## Rodar e olhar

```sh
python -m http.server 8000 -d app      # na raiz do projeto
# abrir http://localhost:8000/?modo=exemplo
```

`?modo=exemplo` usa dados fictícios em memória (`app/dados.js`): cadastro, moderação, "Eu vou!" e Fila funcionam sem
banco nem login (a sessão de exemplo é `dados.config.eu`). Sem o parâmetro o app lê a PRODUÇÃO (`app/config.js`):
não teste gravação assim. Para conferir no celular, use a prévia da branch (skill `entregar-mudanca`).

## Onde fica cada coisa

| Arquivo | Papel |
| --- | --- |
| `index.html` | todas as telas: `telaInicio`, `telaMapa`, `telaAcao`, `telaCriar`, `telaPerfil`, `telaContato`, `telaFila`; rota por hash (`#/mapa`, `#/acao/<id>`...) em `render()` |
| `api.js` | escolhe `ApiExemplo` ou `ApiSupabase` e expõe `window.API` |
| `api-exemplo.js` | implementação em memória sobre `dados.js`; imita as regras do banco (permissões, limites, erros) |
| `api-supabase.js` | mesma interface, falando com views e funções SQL (`rpc`); `publico()` lê `publico.json` com plano B |
| `dados.js` | `window.DADOS = {...}` com JSON puro; pessoas inventadas, ações e organizações públicas com crédito |
| `marca.css` / `tokens.css` | estilo; `tokens.css` é do guia do Comitê e NÃO se edita |
| `config.js` | URL e chave pública do Supabase (produção) |

## Regras

- **As duas APIs andam juntas.** Método novo ou mudado em `api-supabase.js` tem o espelho em `api-exemplo.js`, com o
  mesmo formato de retorno e os mesmos códigos de erro (`erro('precisa_entrar')`, `erro('so_moderador')`...). Se a regra
  é de permissão, ela mora no banco (skill `mudar-banco`); o exemplo só imita.
- **Re-render preservando o estado**: o app guarda tudo em `estado` e redesenha com `render()`. Em campo de formulário
  use `rerender()` (mantém a rolagem) ou atualize só o trecho; recarregar a tela inteira fecha o seletor de data no
  iPhone e rola ao topo.
- **Sempre escapar** texto vindo de dado com `esc()` antes de pôr em HTML.
- **Hora é de Brasília**: use `agora()` e `PUB.config.hoje`, não `new Date()` cru, para decidir o que já passou.
- **Celular primeiro** (≤ 900 px é o caso principal); botões em pílula de 44 px, foco visível.
- **Biblioteca de CDN**: versão exata, `integrity` e `crossorigin="anonymous"`; só cdnjs ou jsdelivr.
- **Dado novo em `dados.js`**: nunca pessoa real; ação/organização pública só com crédito à fonte.
- **Texto do rodapé é fixo** (ver CLAUDE.md); não pôr nome de pessoa nem link do código.

## Testes

```sh
python -m pytest tests -q              # tests/test_mockup.py confere telas e dados.js por texto
node --test "tests/js/*.test.js"       # api-exemplo e api-supabase (Supabase falso em memória)
```

Comportamento novo vem com teste novo: em `tests/js/` quando é regra da camada de dados, em `tests/test_*.py` quando é
presença de tela ou texto. Fluxo de ponta a ponta do "Eu vou!" em `tests/e2e/vou.spec.mjs` (precisa de `playwright`
instalado à parte e do servidor local no ar).

## Erros comuns

| Sintoma | Causa |
| --- | --- |
| Funciona em `?modo=exemplo`, quebra na prévia com `?modo=real` | método só existe em `api-exemplo.js`, ou a migração ainda não está em produção |
| Lista mostra ação velha por até 1 h | quem não está logado lê `publico.json` (snapshot de hora em hora); é esperado |
| Lista corta em 1000 itens | leitura ao vivo sem `tudo()` em `api-supabase.js` (a API corta em `max_rows` calada) |
| Foto da ação importada some | URL aponta para `fotos/divulgacao/`, que só existe no site da `master` (prévias não recebem fotos) |
