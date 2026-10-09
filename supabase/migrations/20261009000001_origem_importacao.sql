-- Ações importadas de fontes públicas (agenda Bora Lula do Comitê Popular, varredura das redes).
-- Checklist "Publicar" de docs/2026-10-08-plano-expansao-varredura.md.

-- 1. Pessoa de sistema que assina toda ação importada (acao.organizador é not null e aponta para pessoa,
--    que aponta para auth.users). Sem senha, sem provedor, banida: nunca entra. O trigger cria a pessoa.
insert into auth.users (id, instance_id, aud, role, email, encrypted_password, email_confirmed_at,
                        raw_app_meta_data, raw_user_meta_data, confirmation_token, recovery_token,
                        email_change_token_new, email_change, created_at, updated_at, banned_until)
values ('00000000-0000-0000-0000-00000000b07a', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated',
        'importacao@sistema.invalid', '', now(), '{"provider":"sistema","providers":[]}', '{"full_name":"Agenda Bora Lula"}',
        '', '', '', '', now(), now(), '2999-12-31')
on conflict (id) do nothing;
update pessoa set papel = 'organizador', nome = 'Agenda Bora Lula' where id = '00000000-0000-0000-0000-00000000b07a';

-- 3. Contato "divulgacao": a ação não tem inscrição; quem quiser ir segue o link público da divulgação original.
--    (o valor novo só pode ser usado em outra transação; abaixo as comparações são por texto)
alter type contato_tipo add value if not exists 'divulgacao';

-- 2 e 4. Origem (fonte + id na fonte, únicos) e marca de coordenada aproximada (centro do município).
alter table acao
  add column fonte text,
  add column fonte_id text,
  add column lugar_aproximado boolean not null default false,
  add column importada_em timestamptz,
  add constraint acao_fonte_par check ((fonte is null) = (fonte_id is null));
create unique index acao_fonte_unica on acao (fonte, fonte_id) where fonte is not null;

-- A view pública ganha a origem, a marca de lugar aproximado e o link de divulgação (só quando é público).
create or replace view acao_publica as
  select a.id, a.titulo, a.tipo, a.descricao, a.organizador, p.nome as organizador_nome, a.organizacao,
         a.lugar_nome, a.bairro, a.cidade, a.lat, a.lon, a.online,
         a.foto_url, a.foto_credito, a.foto_pagina, a.prioritaria, a.contato_tipo, a.status, a.criada_em,
         a.fonte, a.lugar_aproximado,
         case when a.contato_tipo::text = 'divulgacao' then a.contato_link end as link_divulgacao
  from acao a join pessoa p on p.id = a.organizador
  where a.status = 'publicada';

-- Inscrição não existe em ação de divulgação (a tela esconde o botão; a função garante).
create or replace function inscrever(turno_id bigint) returns json language plpgsql security definer set search_path = public as $$
declare p pessoa; t turno; a acao; ativa inscricao;
begin
  if auth.uid() is null then raise exception 'precisa_entrar'; end if;
  select * into p from pessoa where id = auth.uid();
  if p.bloqueada then raise exception 'bloqueada'; end if;
  if p.telefone is null then raise exception 'sem_telefone'; end if;
  select * into t from turno where id = turno_id for update;
  if not found then raise exception 'nao_publicada'; end if;
  select * into a from acao where id = t.acao;
  if a.status <> 'publicada' then raise exception 'nao_publicada'; end if;
  if a.contato_tipo::text = 'divulgacao' then raise exception 'sem_inscricao'; end if;
  if t.inicio::date < hoje_brasilia() then raise exception 'turno_passado'; end if;
  select * into ativa from inscricao where pessoa = p.id and turno = t.id and cancelada_em is null;
  if not found then
    if t.lotacao is not null and (select count(*) from inscricao where turno = t.id and cancelada_em is null) >= t.lotacao then
      raise exception 'lotado';
    end if;
    insert into inscricao (pessoa, turno) values (p.id, t.id)
      on conflict (pessoa, turno) do update set cancelada_em = null, criada_em = now();
  end if;
  return json_build_object('combinado', combinado_json(a));
end $$;

-- 4. Importação idempotente, numa transação só. `itens` é um array JSON; cada item:
--    {fonte_id, titulo, tipo, descricao, organizacao, organizacao_tipo, online, lugar_nome, bairro, cidade,
--     lat, lon, lugar_aproximado, link, inicio, fim}
--    Reimportar atualiza pelo par (fonte, fonte_id); o que sumiu da fonte vira 'encerrada'; o que voltou,
--    'publicada'. Recusa de moderador ('recusada') é respeitada. Um turno por ação, atualizado no lugar.
--    Só a chave service_role chama (revogada de anon e authenticated abaixo).
create or replace function importar_acoes(fonte text, itens jsonb, encerrar_faltantes boolean default true)
returns json language plpgsql security definer set search_path = public as $$
#variable_conflict use_column
declare
  it jsonb; org_id bigint; a_id bigint; t_id bigint; nova boolean;
  n_ins int := 0; n_atu int := 0; n_enc int := 0; ids text[] := '{}';
  sistema constant uuid := '00000000-0000-0000-0000-00000000b07a';
begin
  if importar_acoes.fonte is null or importar_acoes.fonte = '' then raise exception 'fonte_vazia'; end if;
  for it in select * from jsonb_array_elements(itens) loop
    org_id := null;
    if coalesce(it->>'organizacao', '') <> '' then
      insert into organizacao (nome, tipo) values (it->>'organizacao', coalesce((it->>'organizacao_tipo')::tipo_org, 'coletivo'))
        on conflict (nome) do update set nome = excluded.nome
        returning id into org_id;
    end if;
    insert into acao (titulo, tipo, descricao, organizador, organizacao, lugar_nome, bairro, cidade, lat, lon, online,
                      lugar_aproximado, contato_tipo, contato_link, status, fonte, fonte_id, importada_em)
    values (it->>'titulo', (it->>'tipo')::tipo_acao, coalesce(it->>'descricao', ''), sistema, org_id,
            it->>'lugar_nome', it->>'bairro', it->>'cidade', (it->>'lat')::double precision, (it->>'lon')::double precision,
            coalesce((it->>'online')::boolean, false), coalesce((it->>'lugar_aproximado')::boolean, false),
            (case when coalesce(it->>'link', '') <> '' then 'divulgacao' else 'organizador_chama' end)::contato_tipo,
            nullif(it->>'link', ''), 'publicada', importar_acoes.fonte, it->>'fonte_id', now())
    on conflict (fonte, fonte_id) where fonte is not null do update set
      titulo = excluded.titulo, tipo = excluded.tipo, descricao = excluded.descricao, organizacao = excluded.organizacao,
      lugar_nome = excluded.lugar_nome, bairro = excluded.bairro, cidade = excluded.cidade, lat = excluded.lat, lon = excluded.lon,
      online = excluded.online, lugar_aproximado = excluded.lugar_aproximado, contato_tipo = excluded.contato_tipo,
      contato_link = excluded.contato_link, importada_em = now(),
      status = case when acao.status = 'encerrada' then 'publicada' else acao.status end
    returning id, (xmax = 0) into a_id, nova;
    if nova then n_ins := n_ins + 1; else n_atu := n_atu + 1; end if;
    ids := ids || (it->>'fonte_id');
    select id into t_id from turno where acao = a_id order by inicio limit 1;
    if found then
      update turno set inicio = (it->>'inicio')::timestamp, fim = (it->>'fim')::timestamp where id = t_id;
    else
      insert into turno (acao, inicio, fim) values (a_id, (it->>'inicio')::timestamp, (it->>'fim')::timestamp);
    end if;
  end loop;
  if encerrar_faltantes then
    update acao set status = 'encerrada'
      where acao.fonte = importar_acoes.fonte and status = 'publicada' and not (fonte_id = any (ids));
    get diagnostics n_enc = row_count;
  end if;
  return json_build_object('inseridas', n_ins, 'atualizadas', n_atu, 'encerradas', n_enc);
end $$;
revoke execute on function importar_acoes(text, jsonb, boolean) from public, anon, authenticated;
grant execute on function importar_acoes(text, jsonb, boolean) to service_role;
