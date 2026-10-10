---
name: operar-producao
description: Use quando a tarefa da Agenda Bora Lula toca a produção - aplicar migração no Supabase de produção, publicar a edge function, dar papel de moderador ou organizador, tirar ação ou pessoa do ar, pedido de remoção de foto, limpar fotos órfãs, cópia do banco (backup e restauração), cota do plano grátis, ou o site no ar está com erro.
---

# Operar a produção

Produção = Supabase `acoes-segundo-turno` (ref `ommitzndniqnmsjsjghb`, São Paulo, plano Free) + GitHub Pages da
`master`. **Só o Gui opera.** Se você não é o Gui: escreva o passo no PR ou na issue e pare. Se é o Gui pedindo: rode
sempre o ensaio (quando houver) antes do comando que grava, e diga o efeito prático antes de executar.

Referência completa, com histórico do que já foi aplicado: `docs/operacao.md`. Segredos (`SUPABASE_ACCESS_TOKEN`,
`SUPABASE_DB_PASSWORD`) ficam no `.env` da raiz, fora do git; os scripts leem de lá.

## Tarefas

| Tarefa | Como |
| --- | --- |
| Aplicar migração nova | `python scripts/ir_ao_ar.py migrar` (link + db push + confere que as views públicas são só leitura); conferir com `npx supabase migration list --linked`. Sempre ANTES do merge do app que depende dela |
| Publicar edge function | `npx supabase functions deploy previa-instagram --project-ref ommitzndniqnmsjsjghb` |
| Dar papel | SQL Editor: `update pessoa set papel='moderador' where email='...'` (ou `organizador`; tirar: `apoiador`). A pessoa precisa ter entrado uma vez pelo site |
| Tirar ação do ar | Fila (`#/fila`): Suspender (volta com Reativar) ou Excluir |
| Bloquear pessoa | Fila, "Bloquear organizador"; reserva: `select bloquear_pessoa('<uuid>', 'motivo')` / `desbloquear_pessoa` |
| Verificar importadas | Fila, aba Divulgação: conferir no post original, Verificar ou Recusar com motivo |
| Pedido de remoção de arte | excluir a ação na Fila e apagar a imagem no mesmo dia (bucket `fotos-acoes`, ou o arquivo em `fotos/divulgacao/` por commit); responder a quem pediu |
| Fotos órfãs no bucket | `python scripts/limpar_fotos.py` (ensaio) e `--aplicar`; uma vez por dia |
| Adiantar a vitrine | Actions > "Publicar app no GitHub Pages" > Run workflow (senão atualiza de hora em hora) |
| Senha do banco perdida | `python scripts/ir_ao_ar.py senha` (redefine e grava no `.env`) |

## Cópia do banco

`.github/workflows/backup.yml` roda todo dia às 00:17 de Brasília e guarda `banco-<data>.tar.gz.enc` (cifrado com
`BACKUP_SENHA`) como artefato por 90 dias. Restaurar: seção "Cópia do banco" de `docs/operacao.md` (openssl, depois
`esquema.sql` e `dados.sql` com `session_replication_role = replica`). Nunca restaurar em produção sem o Gui decidir.

## Cotas do plano Free

Painel: https://supabase.com/dashboard/project/ommitzndniqnmsjsjghb/settings/billing/usage. O que mais cresce é egress
(5 GB/mês). Banco acima de 500 MB vira só leitura na hora. Pausa após 7 dias sem uso. Saída: Pro, US$ 25/mês.

## Lei eleitoral

Nunca pagar impulsionamento (anúncio, post patrocinado) para o site nem para ação dele. Ação importada sempre mostra
a fonte e o link da divulgação original.

## Ao relatar para o Gui

Linguagem leiga, pelo efeito prático ("quem não está logado vai ver a ação nova em até 1 h"), com o termo técnico
entre parênteses só se ajudar. Diga o que foi feito, o que foi conferido e o que ficou pendente.
