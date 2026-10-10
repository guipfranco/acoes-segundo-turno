---
name: entregar-mudanca
description: Use quando uma mudança de código da Agenda Bora Lula está pronta ou quase - antes de commitar, ao abrir pull request, mandar link de prévia, pedir revisão, fazer merge na master ou limpar a branch depois do merge.
---

# Entregar uma mudança

Toda mudança de código vai por branch + pull request, e o merge na `master` só acontece com OK do Gui: cada push na
`master` republica o site para todo mundo. Sem worktrees: uma branch por mudança, trocada com `git switch`.

## Antes de commitar

```sh
git switch master && git pull                 # se ainda não está numa branch da tarefa
git switch -c <nome-curto>                    # ex.: filtro-quando, corrige-ics
python -m pytest tests -q
node --test "tests/js/*.test.js"
git status                                    # conferir que nada de .env, levantamento/, backups/ ou fonte comercial entrou
```

Conferir no diff: nenhum dado pessoal real, nenhum segredo, nenhuma edição em `app/tokens.css`, `dados.js` só com
gente inventada. Se a mudança altera o que o app faz ou como se opera, atualize no mesmo PR `docs/funcionalidades.md`,
`docs/operacao.md` e a skill afetada em `.claude/skills/`. Commit em pt-BR, curto, com o porquê quando não for óbvio. Push logo depois de cada commit.

## Prévia

Cada push de branch que toque `app/` publica em
`https://guipfranco.github.io/acoes-segundo-turno/previa/<branch>/` (lista em `/previa/`) em 2 a 4 minutos: dados de
exemplo, etiqueta amarela com o nome da branch, sem contador de visitas. `?modo=real` liga a produção: cuidado se a
branch depende de migração ainda não aplicada, e não grave dados de teste lá. A prévia não tem fotos das importadas
nem `publico.json`. Branch de fork não ganha prévia.

## Pull request

```sh
gh pr create --base master --title "<o que muda>" --body "<corpo>"
```

O corpo responde, nesta ordem:
1. O que muda para quem usa o site (em linguagem leiga).
2. Link da prévia e, se mexeu em tela, uma captura (sem dado pessoal).
3. Como testou (comandos e o que conferiu à mão).
4. **Passos de produção**, se houver, em negrito: migração a aplicar ANTES do merge, função a publicar, reimportação.

Mande ao Gui o link do PR e o da prévia. Não suba servidor local para ele ver: a prévia é o caminho.

## Depois do OK

Quem faz o merge é o Gui (ou com o OK explícito dele, na mesma conversa). Se há migração, ela vai primeiro (skill
`mudar-banco`). Depois do merge:

```sh
git push origin --delete <branch>             # tira a prévia
git switch master && git pull && git branch -d <branch>
```

## Erros comuns

| Situação | O que fazer |
| --- | --- |
| Prévia não apareceu | o push não tocou `app/`, ou o workflow ainda roda (aba Actions) |
| Duas pessoas na mesma área | combine no PR/issue; branches curtas e merge frequente evitam conflito em `index.html` |
| Conflito em `app/index.html` | `git pull --rebase origin master` na branch, resolver, rodar os testes de novo |
| Tentação de commitar direto na `master` "porque é pequeno" | não: só documentação vai direto; código sempre por PR |
