# Como contribuir

Obrigado por querer ajudar. O projeto é pequeno, feito por voluntários e com prazo curto (o 2º turno), então
preferimos mudanças pequenas e frequentes a grandes reformas.

## Por onde começar

1. Abra o site no ar e use. Achou um erro ou tem uma ideia? Abra uma
   [issue](https://github.com/guipfranco/acoes-segundo-turno/issues) antes de codar, para a gente combinar o
   que faz sentido. Issues marcadas `boa primeira tarefa` são um bom começo.
2. Rode localmente seguindo o [README](README.md). Quase tudo da interface funciona em `?modo=exemplo`, sem
   banco nem login.
3. Leia a spec em `docs/superpowers/specs/` e o desenho visual em `docs/2026-10-08-design-mockup.md` para
   entender as decisões já tomadas.

## Se você usa o Claude Code

O `CLAUDE.md` da raiz resume as regras e o mapa do projeto, e `.claude/skills/` tem um roteiro para cada tipo de
tarefa (mexer no app, mudar o banco, entregar a mudança, importar ações, operar a produção). O Claude carrega a skill
certa sozinho; vale pedir pelo nome ("use a skill mudar-banco"). As duas de produção são só para o mantenedor. Ao
mudar como algo funciona, atualize a skill e o `docs/funcionalidades.md` no mesmo PR.

## Regras da casa

- **Tudo em português do Brasil**: código, comentários, commits, issues, documentação. Datas em AAAA-MM-DD.
- **Nunca dado pessoal real** (nome, telefone, e-mail, link de grupo de pessoa comum) em código, teste,
  documentação, captura de tela ou issue. Ações e organizações públicas podem aparecer, com crédito à fonte.
- **Nunca segredo**: chave `service_role`, senha do banco, segredo do Google. A chave anon do Supabase é
  pública e pode ficar no `app/config.js`.
- **Sem build, sem framework**: o app é HTML, CSS e JS puros. Scripts de CDN levam `integrity`.
- **Celular primeiro**: a maioria das pessoas usa pelo celular; o desktop (≥ 900 px) vem depois.
- **Toda mudança passa por teste**: `python -m pytest tests -q` e `node --test "tests/js/*.test.js"` precisam
  passar. Mudança de comportamento vem com teste novo.

## Fluxo

1. Faça um fork (ou, se tiver acesso, uma branch) a partir da `master`. Nunca commite direto na `master`.
2. Uma branch por mudança, com nome curto do que faz (`filtro-quando`, `corrige-ics`).
3. Commits em pt-BR, curtos, explicando o porquê quando não for óbvio.
4. Abra o pull request contra `master` descrevendo o que muda e como testou. Se mexeu em tela, inclua uma
   captura. Cada push que toca `app/` gera uma prévia navegável em
   `https://guipfranco.github.io/acoes-segundo-turno/previa/<branch>/` (só para branches do repositório
   principal, não de forks), com dados de exemplo.
5. O merge na `master` é feito pelo mantenedor depois da revisão. Cada push na `master` republica o site.

## O que precisa de acesso especial

Você **não** precisa de nada disso para contribuir com interface, testes, scripts ou documentação:

- Banco de produção, importação de ações (`publicar_acoes.py --aplicar`), moderação e segredos ficam com o
  mantenedor e com quem ele indicar.
- Mudanças em `supabase/migrations/` são bem-vindas, mas precisam rodar na pilha local (`docs/operacao.md`)
  e só vão para produção pela mão do mantenedor.
- O levantamento bruto de fontes fica num repositório privado separado porque contém nomes e telefones.

## Conduta

Seja gentil e direto. O projeto é político por natureza, mas as discussões aqui são sobre o site. Assédio,
exposição de dados de terceiros ou uso do repositório para ataque pessoal levam a bloqueio.
