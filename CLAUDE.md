# CLAUDE.md

**Agenda Bora Lula**: site onde quem organiza ações pelo voto do Lula no 2º turno cadastra a ação e quem quer ajudar
acha uma perto de si e diz "Eu vou!". Iniciativa do Comitê Popular do Lula (não é a campanha). Mantenedor: Gui
(guipfranco), que decide produto, dá o OK de merge e é o único com acesso à produção.

- No ar: https://guipfranco.github.io/acoes-segundo-turno/ (GitHub Pages da `master`).
- Repo, URL e projeto Supabase seguem o nome antigo `acoes-segundo-turno` por decisão do Gui.
- O que o app faz, tela a tela: `docs/funcionalidades.md`. Operação da produção: `docs/operacao.md`.

## Regras que valem sempre

- Tudo em pt-BR (código, comentários, commits, docs), datas AAAA-MM-DD.
- **Nunca dado pessoal real** no repo (nome, telefone, e-mail, link de grupo de pessoa comum), nem em teste, captura
  ou issue. Ações e organizações públicas (partidos, mandatos, movimentos, comitês) podem, sempre com crédito à fonte.
  Pessoas de exemplo são inventadas; ação importada tem como organizador uma pessoa de sistema.
- **Nunca segredo**: `service_role`, senha do banco, token do Supabase, segredo do Google. A chave anon/publishable em
  `app/config.js` é pública por desenho. Segredos locais ficam em `.env` (fora do git).
- **Sem build, sem framework**: `app/` é HTML, CSS e JS puros. Scripts de CDN com versão exata e `integrity`.
- `app/tokens.css` é arquivo do guia do Comitê: não editar. Estilo vai em `app/marca.css`.
- Celular primeiro; desktop (≥ 900 px) depois.
- Comandos que gravam em produção (`publicar_acoes.py --aplicar`, `ir_ao_ar.py`, `fotos_divulgacao.py ... --aplicar`,
  `limpar_fotos.py --aplicar`, `supabase db push`/`functions deploy`) só o Gui roda. Sem o token eles não funcionam;
  com ele, não rode sem pedido explícito.

## Como trabalhar

1. Branch nova a partir da `master` atualizada para toda mudança de código (app, scripts, testes, migrações), por
   menor que seja: `git switch master && git pull && git switch -c <nome-curto>`. Nada de worktree.
2. Testes passando antes de cada commit: `python -m pytest tests -q` e `node --test "tests/js/*.test.js"`.
3. Commit em pt-BR e push logo em seguida. Cada push que toca `app/` gera prévia em
   https://guipfranco.github.io/acoes-segundo-turno/previa/<branch>/ (dados de exemplo).
4. Pull request contra `master` com o link da prévia. Merge só com OK do Gui. Depois do merge, apagar a branch no
   origin (tira a prévia).
5. Direto na `master` só o que não é código: documentação, CLAUDE.md, skills.

Skills do projeto (`.claude/skills/`), carregue a que bate com a tarefa:

| Tarefa | Skill |
| --- | --- |
| Mexer em tela, estilo, filtro, texto, camada de dados (`app/`) | `mexer-no-app` |
| Criar ou mudar tabela, view, função SQL, RLS (`supabase/`) | `mudar-banco` |
| Abrir PR, prévia, merge, conferir antes de entregar | `entregar-mudanca` |
| Importar ações da agenda Bora Lula ou das redes, fotos dos posts (só o Gui) | `importar-acoes` |
| Moderação, incidente, migração em produção, cópia do banco, cotas (só o Gui) | `operar-producao` |

## Mapa

| Pasta | O que é |
| --- | --- |
| `app/` | o site inteiro. `index.html` (telas), `api.js` escolhe `api-exemplo.js` (dados de `dados.js`) ou `api-supabase.js` |
| `supabase/migrations/` | esquema, RLS e funções SQL (as regras sensíveis moram aqui); `supabase/functions/previa-instagram` |
| `scripts/` | importação (`bora_lula.py`, `publicar_acoes.py`, `fotos_divulgacao.py`), Pages, snapshot, backup, produção |
| `tests/` | pytest (telas, scripts; `test_supabase.py` só com pilha local) e `tests/js/` (`node --test`) |
| `fotos/divulgacao/` | artes das ações importadas, servidas pelo Pages (as URLs estão gravadas no banco: não renomear) |
| `docs/` | spec em `docs/superpowers/specs/`, desenho em `docs/2026-10-08-design-mockup.md`, capturas em `docs/capturas/` |
| `.github/workflows/` | `pages.yml` (publicação + prévias + `publico.json` de hora em hora), `backup.yml` (cópia diária) |

Fora do repo: `levantamento/` (no .gitignore) é o repo PRIVADO https://github.com/guipfranco/acoes-levantamento, com a
varredura bruta (nomes e telefones). Nunca copiar nada de lá para cá nem torná-lo público.

## Decisões do Gui (não reabrir sem ele)

- Inscrição com nome e telefone desde a v1; telefones dos inscritos visíveis a quem organiza.
- Moderação humana por voluntários; automação depois. Segundo moderador fica para depois.
- Toda ação importada vai ao ar como "Divulgação pública" até a moderação verificar (não confiamos na revisão da
  agenda de origem).
- Uma vaquinha só, geral, apontando para a arrecadação oficial (`https://doelula.com.br/`).
- Busca por lugar livre (Brasil inteiro); referência visual Airbnb/Meetup.
- Rodapé fixo: "Uma iniciativa do Comitê Popular do Lula. Não é site oficial da campanha. Nenhuma divulgação paga."
- Domínio próprio + Cloudflare: o Gui faz depois.
- **Fusão com o boralula.org** (2026-10-10, combinada com a equipe de lá): a Agenda vai virar parte do boralula.org e
  depois desligar. O projeto já está em `acoes-segundo-turno/` no repo `comite-popular-tech/agregador-de-agendas`.
  O que portar e as decisões: `docs/2026-10-10-fusao-com-boralula.md`. Até a fusão, este repo segue no ar como está.
