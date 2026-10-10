# Mudança para o repo agregador-de-agendas (plano, 2026-10-10)

**Substituído no mesmo dia:** o Carlos trouxe o repo inteiro para `acoes-segundo-turno/` no agregador (`git subtree`),
e o Gui decidiu fundir a Agenda com o boralula.org. Plano em vigor: `docs/2026-10-10-fusao-com-boralula.md`. O resto
deste arquivo fica como registro da análise.

Decisão do Gui (2026-10-10): o projeto passa a morar numa pasta do repo PRIVADO
`comite-popular-tech/agregador-de-agendas` (projeto boralula, branch `main`), e a equipe trabalha lá. Ainda não foi
feito. Este arquivo lista o que quebra e a ordem para mudar sem derrubar o site.

## O que existe lá (lido em 2026-10-10)

- O site do boralula vai ao ar por um Worker do Cloudflare, publicado à mão da máquina de alguém do núcleo
  (`tools/empacotar.py` + `tools/publicar.py`), que só empacota a pasta `site/`. Uma pasta nossa não seria publicada
  sem querer, mas também não há nada pronto para publicar um segundo site.
- GitHub Pages: **não dá**. A organização está no plano gratuito e o GitHub não serve Pages de repo privado nesse
  plano. Proteção de branch e rulesets também não (403).
- Único workflow: `testes.yml` (unittest e `node --test` só da pasta `tests/` da raiz). Nossos testes não rodariam lá,
  mas também não quebram a CI deles. Actions de repo privado no plano gratuito: ~2.000 minutos/mês para a organização
  toda.
- Fluxo combinado no CONTRIBUTING: PR revisado por outra pessoa, só "Squash and merge" (achata nosso histórico),
  ramo `<frente>/<número>-<descrição>`, commits com prefixo `boralula:`. Na prática os commits vão direto no `main`
  por um script de envio "só de ida" a partir de uma cópia local de um dos mantenedores (kaducovas): **precisa
  combinar com ele antes**, senão um envio pode apagar a nossa pasta.
- Não há CLAUDE.md, AGENTS.md nem `.claude/` lá. O nosso CLAUDE.md e as skills funcionam numa subpasta quando a sessão
  do Claude Code é aberta dentro dela.
- `.gitignore` da raiz não cobre `levantamento/`, `backups/` nem `.env` em subpasta: o nosso `.gitignore` vai junto.
- Tamanho: o repo tem ~9 MB; nós somamos ~66 MB, dos quais 58 MB são as 582 fotos de `fotos/divulgacao/`.
- Eles usam `SUPABASE_ACCESS_TOKEN` para outro projeto Supabase: nomear os nossos segredos com prefixo (ex.:
  `BORALULA_GUI_SUPABASE_TOKEN`) para não confundir.

## O que quebra se só copiarmos a pasta

| Hoje | Por que quebra |
| --- | --- |
| Site em `guipfranco.github.io/acoes-segundo-turno` | publicado pelo Pages deste repo público; lá não há Pages |
| Fotos das importadas | as URLs gravadas no banco apontam para o Pages deste repo |
| `publico.json` de hora em hora | gerado pelo workflow do Pages deste repo |
| Prévia por branch | idem |
| `publicar_acoes.py --aplicar` | confere se o Pages deste repo já serve a foto antes de gravar |
| Cópia diária do banco | workflow e segredos deste repo; workflow em subpasta não roda |
| Login Google | origem autorizada é `guipfranco.github.io`; endereço novo precisa entrar no Google Cloud e no Supabase |

## Caminhos

**A. Código lá, publicação continua aqui (menor risco).** A equipe trabalha na pasta do agregador; este repo público
vira só o "alvo de publicação": um script (ou workflow lá, com token) copia `app/` e `fotos/` para cá a cada merge, e o
Pages, o `publico.json`, a cópia do banco e as URLs das fotos seguem como estão. Contra: duas cópias para manter em
sincronia, prévias por branch deixam de existir (ou passam a ser publicadas daqui).

**B. Mudar a publicação para o Cloudflare Pages (combina com o domínio próprio que o Gui já queria).** Cloudflare
Pages ligado ao repo privado, pasta raiz `bora-lula-gui/app`, com prévia por branch nativa. Exige: trocar no banco as
URLs das fotos (um `update ... replace(...)`), mover as fotos para o Cloudflare (Pages ou R2) e talvez tirá-las do git,
gerar `publico.json` por cron (Worker com cron ou GitHub Actions), adaptar `publicar_acoes.py` (conferência HEAD no
endereço novo), mover a cópia do banco para `.github/workflows/` da raiz do agregador com `paths:` e segredos com
prefixo, autorizar a origem nova no Google e no Supabase, e redirecionar o endereço antigo.

**C. Não mudar o código; levar só a documentação.** Pasta no agregador com README e as skills apontando para este
repo público. Zero risco, mas a equipe trabalha em dois lugares.

Recomendação: **A agora** (dá para fazer numa tarde sem tocar na produção) e **B junto com o domínio próprio**.

## Passo a passo (caminho A)

1. Combinar com o kaducovas: a pasta e como o envio "só de ida" dele não a sobrescreve.
2. Nome da pasta **sem espaço** (ex.: `bora-lula-gui/`): espaço atrapalha terminal, `paths:` de Actions e URLs. Se o
   nome visível precisa ser "Bora Lula - Gui", ele vai no título do README da pasta.
3. Copiar o repo sem `.git`, sem `levantamento/`, `.env`, `backups/`, `node_modules/`, `.claude/settings.local.json`
   (o `git archive master` já faz isso). Decidir se `fotos/` vai (58 MB para cada voluntário clonar).
4. Ajustar o CLAUDE.md e as skills: onde se trabalha, como uma mudança chega ao site (passa pela cópia para este repo),
   regras do CONTRIBUTING de lá (prefixo, squash).
5. Script de publicação: do agregador para este repo (`app/`, `fotos/`), rodado pelo Gui depois de cada merge, ou
   workflow lá com um token de escrita só neste repo.
6. Avisar no README deste repo que o desenvolvimento mudou de lugar; manter o MIT ou não (o código passa a viver num
   repo privado).
