---
name: mudar-banco
description: Use quando a tarefa da Agenda Bora Lula pede tabela, coluna, view, função SQL, regra de acesso (RLS), gatilho, bucket ou edge function nova ou mudada (pasta supabase/), ou quando um teste de tests/test_supabase.py falha, ou quando o app precisa de um dado ou permissão que o banco ainda não dá.
---

# Mudar o banco

O banco (Supabase/Postgres) é onde moram as regras sensíveis: quem pode ver telefone, quem modera, limites por dia.
O navegador usa a chave pública; o que protege os dados é RLS + funções `security definer` que conferem a permissão
a cada chamada. Toda mudança é uma migração nova, testada na pilha local. Quem aplica em produção é o Gui.

## Fazer a migração

1. Arquivo novo em `supabase/migrations/AAAAMMDDNNNNNN_nome_curto.sql` (data de hoje + sequência, maior que a última).
   Nunca editar migração antiga: ela já rodou em produção. Antes de abrir o PR, `git fetch` e confira se a `master`
   ganhou migração com número igual ou maior que o seu; se sim, renomeie a sua para depois dela.
2. Padrões da casa (copie de `20261010000010_verificacao_divulgacao.sql`):
   - Função exposta: `language plpgsql security definer set search_path = public`, confere `auth.uid()` e o papel
     logo no começo (`if not eh_moderador() then raise exception 'so_moderador'; end if;`). O código curto do erro
     ganha texto para a pessoa nos mapas de mensagens de `app/index.html` (procure `so_moderador:`).
   - Depois de cada função: `revoke execute ... from public, anon` e `grant execute ... to authenticated` (ou deixe
     para `anon` só se for de leitura pública de verdade).
   - Views públicas (`acao_publica`, `turno_publico`, `organizacao_publica`, `configuracao_publica`) nunca expõem
     telefone, e-mail, detalhe ou contato. `create or replace view` só aceita coluna nova NO FIM da lista.
   - Coluna nova em `acao` (ou `turno`, `organizacao`) quase nunca para na view: funções como `acao_completa_json`,
     `minhas_inscricoes`, `criar_acao`, `fila_moderacao` e `importar_acoes` repetem a lista de campos. Ache a versão
     MAIS NOVA de cada uma (`grep -n "create or replace function <nome>" supabase/migrations/*.sql`, a última vence) e
     recrie a partir dela, nunca da primeira.
   - Comentário no topo dizendo o que a migração faz e por quê.
3. Espelhar no app: `app/api-supabase.js` chama a função/view; `app/api-exemplo.js` imita a mesma regra com os mesmos
   códigos de erro (skill `mexer-no-app`). Se a view ganhou coluna, `scripts/snapshot_publico.py` e o `publico.json`
   passam a trazê-la sozinhos.

## Pilha local e testes

Precisa de Docker. A pilha local é uma só por máquina: não rode duas sessões de teste de banco ao mesmo tempo.

```sh
npx supabase start -x studio,postgres-meta,realtime,edge-runtime,logflare,vector   # o start completo falha no health check do studio
npx supabase db reset            # aplica todas as migrações + supabase/seed.sql; "Error status 502" no fim costuma ser só reinício
export SUPABASE_URL=http://127.0.0.1:54321 SUPABASE_ANON_KEY=<anon key do start> SUPABASE_SERVICE_KEY=<service_role key do start>
python -m pytest tests/test_supabase.py -q
```

- As chaves saem no fim do `start` (o `supabase status` falha sem o studio).
- Se `/auth/v1` der 502 depois do reset: `docker restart supabase_kong_acoes-segundo-turno`.
- Volume corrompido ("could not find the database system"): `npx supabase stop --no-backup` e `start` de novo.
- **Nunca** aponte essas variáveis para a produção.

Teste novo em `tests/test_supabase.py` para cada regra: o caminho permitido E o proibido (anônimo, pessoa comum,
moderador). Use o fixture `cenario` e o cliente `tests/supabase_cliente.py`.

## Ir para produção (só o Gui)

A ordem importa: **migração em produção ANTES do merge na `master`**. O merge republica o app; se o app novo chegar
antes das funções, as telas que dependem delas dão erro para todo mundo. No PR, escreva em destaque:
"precisa aplicar a migração `<arquivo>` antes do merge" e, se for o caso, "e reimportar com `publicar_acoes.py`". Como
o Gui aplica: skill `operar-producao`.

Edge function (`supabase/functions/previa-instagram`): mudança também só vale depois de
`npx supabase functions deploy previa-instagram`, feito pelo Gui.

## Erros comuns

| Sintoma | Causa |
| --- | --- |
| `cannot change name of view column` | coluna nova no meio da view; mova para o fim |
| Função funciona no SQL e dá 404/permissão no app | faltou `grant execute ... to authenticated` |
| Teste passa sozinho e falha em conjunto | dado de outro teste; use nomes/ids únicos por teste |
| App em produção quebrado logo depois do merge | merge antes da migração; aplicar a migração já resolve |
