-- Duas coisas que vieram do primeiro uso real do site (WhatsApp, 2026-10-09):
-- 1. Horário aproximado: ação importada cuja divulgação só diz "à noite" / "à tarde" / "de manhã" (ex.: giro nos
--    bares "à noite") era gravada como 9h às 11h e o app mostrava esse horário como se fosse certo. Agora o turno
--    leva `hora_aproximada`, o app mostra o período ("sex 09/10, à noite") e avisa que a divulgação não deu horário.
-- 2. Feedback: qualquer pessoa, logada ou não, manda uma mensagem pelo site (erro, dado errado numa ação, ideia,
--    contato). A moderação lê e marca como tratada na Fila. Ninguém lê nem escreve na tabela direto (RLS sem
--    política): só pelas funções abaixo.

-- ---------- 1. horário aproximado ----------
alter table turno add column hora_aproximada boolean not null default false;

-- create or replace view só aceita coluna nova no fim
create or replace view turno_publico as
  select t.id, t.acao, t.inicio, t.fim, t.lotacao,
         (select count(*) from inscricao i where i.turno = t.id and i.cancelada_em is null)::int as vao,
         t.hora_aproximada
  from turno t join acao a on a.id = t.acao
  where a.status = 'publicada';

-- importar_acoes: igual à migração 03, mais `hora_aproximada` (opcional, padrão false) no turno
create or replace function importar_acoes(fonte text, itens jsonb, encerrar_faltantes boolean default true)
returns json language plpgsql security definer set search_path = public as $$
#variable_conflict use_column
declare
  it jsonb; org_id bigint; a_id bigint; t_id bigint; nova boolean; aprox boolean;
  n_ins int := 0; n_atu int := 0; n_enc int := 0; ids text[] := '{}';
  sistema constant uuid := '00000000-0000-0000-0000-00000000b07a';
begin
  if importar_acoes.fonte is null or importar_acoes.fonte = '' then raise exception 'fonte_vazia'; end if;
  for it in select * from jsonb_array_elements(itens) loop
    org_id := null;
    if coalesce(it->>'organizacao', '') <> '' then
      insert into organizacao (nome, tipo, foto_url, foto_credito, foto_pagina)
        values (it->>'organizacao', coalesce((it->>'organizacao_tipo')::tipo_org, 'coletivo'),
                nullif(it->'organizacao_foto'->>'url', ''), it->'organizacao_foto'->>'credito', it->'organizacao_foto'->>'pagina')
        on conflict (nome) do update set
          foto_url = coalesce(organizacao.foto_url, excluded.foto_url),
          foto_credito = case when organizacao.foto_url is null then excluded.foto_credito else organizacao.foto_credito end,
          foto_pagina = case when organizacao.foto_url is null then excluded.foto_pagina else organizacao.foto_pagina end
        returning id into org_id;
    end if;
    insert into acao (titulo, tipo, descricao, organizador, organizacao, lugar_nome, bairro, cidade, lat, lon, online,
                      lugar_aproximado, contato_tipo, contato_link, status, fonte, fonte_id, importada_em,
                      foto_url, foto_credito, foto_pagina)
    values (it->>'titulo', (it->>'tipo')::tipo_acao, coalesce(it->>'descricao', ''), sistema, org_id,
            it->>'lugar_nome', it->>'bairro', it->>'cidade', (it->>'lat')::double precision, (it->>'lon')::double precision,
            coalesce((it->>'online')::boolean, false), coalesce((it->>'lugar_aproximado')::boolean, false),
            (case when coalesce(it->>'link', '') <> '' then 'divulgacao' else 'organizador_chama' end)::contato_tipo,
            nullif(it->>'link', ''), 'publicada', importar_acoes.fonte, it->>'fonte_id', now(),
            nullif(it->'foto'->>'url', ''), it->'foto'->>'credito', it->'foto'->>'pagina')
    on conflict (fonte, fonte_id) where fonte is not null do update set
      titulo = excluded.titulo, tipo = excluded.tipo, descricao = excluded.descricao, organizacao = excluded.organizacao,
      lugar_nome = excluded.lugar_nome, bairro = excluded.bairro, cidade = excluded.cidade, lat = excluded.lat, lon = excluded.lon,
      online = excluded.online, lugar_aproximado = excluded.lugar_aproximado, contato_tipo = excluded.contato_tipo,
      contato_link = excluded.contato_link, importada_em = now(),
      foto_url = coalesce(excluded.foto_url, acao.foto_url),
      foto_credito = case when excluded.foto_url is not null then excluded.foto_credito else acao.foto_credito end,
      foto_pagina = case when excluded.foto_url is not null then excluded.foto_pagina else acao.foto_pagina end,
      status = case when acao.status = 'encerrada' then 'publicada' else acao.status end
    returning id, (xmax = 0) into a_id, nova;
    if nova then n_ins := n_ins + 1; else n_atu := n_atu + 1; end if;
    ids := ids || (it->>'fonte_id');
    aprox := coalesce((it->>'hora_aproximada')::boolean, false);
    select id into t_id from turno where acao = a_id order by inicio limit 1;
    if found then
      update turno set inicio = (it->>'inicio')::timestamp, fim = (it->>'fim')::timestamp, hora_aproximada = aprox where id = t_id;
    else
      insert into turno (acao, inicio, fim, hora_aproximada) values (a_id, (it->>'inicio')::timestamp, (it->>'fim')::timestamp, aprox);
    end if;
  end loop;
  if encerrar_faltantes then
    update acao set status = 'encerrada'
      where acao.fonte = importar_acoes.fonte and status = 'publicada' and not (fonte_id = any (ids));
    get diagnostics n_enc = row_count;
  end if;
  return json_build_object('inseridas', n_ins, 'atualizadas', n_atu, 'encerradas', n_enc);
end $$;

-- inscrever: igual à migração 20, mas "já passou" olha o fim do turno (exato) ou o dia (aproximado), como o app
create or replace function inscrever(turno_id bigint) returns json language plpgsql security definer set search_path = public as $$
declare p pessoa; t turno; a acao; ativa inscricao;
begin
  if auth.uid() is null then raise exception 'precisa_entrar'; end if;
  select * into p from pessoa where id = auth.uid();
  if p.bloqueada then raise exception 'bloqueada'; end if;
  select * into t from turno where id = turno_id for update;
  if not found then raise exception 'nao_publicada'; end if;
  select * into a from acao where id = t.acao;
  if a.status <> 'publicada' then raise exception 'nao_publicada'; end if;
  if a.contato_tipo::text <> 'divulgacao' and p.telefone is null then raise exception 'sem_telefone'; end if;
  if (case when t.hora_aproximada then t.fim::date < hoje_brasilia() else t.fim < (now() at time zone 'America/Sao_Paulo') end) then
    raise exception 'turno_passado';
  end if;
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

-- ---------- 2. feedback ----------
create table feedback (
  id bigint generated always as identity primary key,
  pessoa uuid references pessoa(id),            -- null: mandou sem entrar
  texto text not null check (length(texto) between 3 and 2000),
  contato text check (contato is null or length(contato) <= 120),   -- e-mail ou WhatsApp, se a pessoa quiser resposta
  tela text check (tela is null or length(tela) <= 200),            -- hash da tela de onde veio (#/acao/12)
  acao bigint references acao(id),              -- quando é sobre uma ação
  navegador text check (navegador is null or length(navegador) <= 200),
  criado_em timestamptz not null default now(),
  tratado_em timestamptz,
  tratado_por uuid references pessoa(id)
);
alter table feedback enable row level security;  -- sem política: só as funções abaixo mexem

-- Qualquer pessoa manda, logada ou não. Freio: 10 por hora por pessoa logada; 100 por hora no total das anônimas.
create or replace function enviar_feedback(texto text, contato text default null, tela text default null, acao_id bigint default null, navegador text default null)
returns json language plpgsql security definer set search_path = public as $$
declare t text := left(trim(coalesce(texto, '')), 2000); n int; f_id bigint;
begin
  if length(t) < 3 then raise exception 'sem_texto'; end if;
  if auth.uid() is not null then
    select count(*) into n from feedback where pessoa = auth.uid() and criado_em > now() - interval '1 hour';
    if n >= 10 then raise exception 'muitas_mensagens'; end if;
  else
    select count(*) into n from feedback where pessoa is null and criado_em > now() - interval '1 hour';
    if n >= 100 then raise exception 'muitas_mensagens'; end if;
  end if;
  insert into feedback (pessoa, texto, contato, tela, acao, navegador)
  values (auth.uid(), t, left(nullif(trim(coalesce(contato, '')), ''), 120), left(nullif(trim(coalesce(tela, '')), ''), 200),
          (select id from acao where id = acao_id), left(nullif(trim(coalesce(navegador, '')), ''), 200))
  returning id into f_id;
  return json_build_object('id', f_id);
end $$;
grant execute on function enviar_feedback(text, text, text, bigint, text) to anon, authenticated;

-- Só moderador lê: pendentes (padrão) ou as 200 últimas tratadas. Quem mandou logado aparece com nome, e-mail e telefone.
create or replace function feedbacks(pendentes boolean default true) returns json language plpgsql stable security definer set search_path = public as $$
begin
  if not eh_moderador() then raise exception 'so_moderador'; end if;
  return (select coalesce(json_agg(x.j), '[]'::json) from (
    select json_build_object('id', f.id, 'texto', f.texto, 'contato', f.contato, 'tela', f.tela, 'acao', f.acao, 'acao_titulo', a.titulo,
             'navegador', f.navegador, 'criado_em', f.criado_em, 'tratado_em', f.tratado_em,
             'pessoa', case when p.id is null then null else json_build_object('nome', p.nome, 'email', p.email, 'telefone', p.telefone) end) as j
    from feedback f left join pessoa p on p.id = f.pessoa left join acao a on a.id = f.acao
    where (f.tratado_em is null) = pendentes
    order by f.criado_em desc limit 200) x);
end $$;

create or replace function tratar_feedback(feedback_id bigint, tratado boolean default true) returns void language plpgsql security definer set search_path = public as $$
begin
  if not eh_moderador() then raise exception 'so_moderador'; end if;
  update feedback set tratado_em = case when tratado then now() end, tratado_por = case when tratado then auth.uid() end where id = feedback_id;
  if not found then raise exception 'nao_pode'; end if;
end $$;
revoke execute on function feedbacks(boolean), tratar_feedback(bigint, boolean) from public, anon;
grant execute on function feedbacks(boolean), tratar_feedback(bigint, boolean) to authenticated;
