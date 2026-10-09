-- Miniatura da foto da ação (2026-10-09). As fotos das ações importadas saem do bucket do Supabase (plano Free,
-- 5 GB/mês de saída) e passam a ser servidas pelo GitHub Pages em fotos/divulgacao/<código>.jpg (arte inteira) e
-- <código>-mini.jpg (480 px, para os cards). O app usa a mini nos cards da vitrine e do mapa e a cheia na página da
-- ação. criar_acao não muda: foto enviada pelo app continua sem mini (o card usa a foto cheia).

alter table acao add column foto_mini_url text;

-- 1. view pública: `create or replace view` só aceita coluna nova no fim da lista.
create or replace view acao_publica as
  select a.id, a.titulo, a.tipo, a.descricao, a.organizador, p.nome as organizador_nome, a.organizacao,
         a.lugar_nome, a.bairro, a.cidade, a.lat, a.lon, a.online,
         a.foto_url, a.foto_credito, a.foto_pagina, a.prioritaria, a.contato_tipo, a.status, a.criada_em,
         a.fonte, a.lugar_aproximado,
         case when a.contato_tipo::text = 'divulgacao' then a.contato_link end as link_divulgacao,
         a.foto_mini_url
  from acao a join pessoa p on p.id = a.organizador
  where a.status = 'publicada';

-- 2. ação completa (Minhas ações, Fila, link de cancelada): igual à da migração 23, com foto_mini_url.
create or replace function acao_completa_json(a acao) returns json language sql stable security definer set search_path = public as $$
  select json_build_object('id', a.id, 'titulo', a.titulo, 'tipo', a.tipo, 'descricao', a.descricao, 'organizador', a.organizador,
    'organizador_nome', (select nome from pessoa where id = a.organizador), 'organizacao', a.organizacao,
    'lugar_nome', a.lugar_nome, 'bairro', a.bairro, 'cidade', a.cidade, 'lat', a.lat, 'lon', a.lon, 'online', a.online,
    'foto_url', a.foto_url, 'foto_credito', a.foto_credito, 'foto_pagina', a.foto_pagina, 'foto_mini_url', a.foto_mini_url,
    'prioritaria', a.prioritaria,
    'contato_tipo', a.contato_tipo, 'status', a.status, 'criada_em', a.criada_em, 'fonte', a.fonte,
    'lugar_aproximado', a.lugar_aproximado, 'motivo_recusa', a.motivo_recusa, 'detalhe', a.detalhe, 'contato_link', a.contato_link,
    'link_divulgacao', case when a.contato_tipo::text = 'divulgacao' then a.contato_link end,
    'organizacao_link', a.organizacao_link,
    'organizacao_dados', (select json_build_object('nome', o.nome, 'verificada', o.verificada, 'link_oficial', o.link_oficial)
                          from organizacao o where o.id = a.organizacao))
$$;
revoke execute on function acao_completa_json(acao) from public, anon, authenticated;

-- 3. minhas inscrições: igual à da migração 40, com foto_mini_url.
create or replace function minhas_inscricoes() returns json language sql stable security definer set search_path = public as $$
  select coalesce(json_agg(json_build_object(
    'turno', json_build_object('id', t.id, 'acao', t.acao, 'inicio', t.inicio, 'fim', t.fim, 'lotacao', t.lotacao,
             'vao', (select count(*) from inscricao x where x.turno = t.id and x.cancelada_em is null)),
    'acao', json_build_object('id', a.id, 'titulo', a.titulo, 'tipo', a.tipo, 'descricao', a.descricao, 'organizador', a.organizador,
             'organizador_nome', (select nome from pessoa where id = a.organizador), 'organizacao', a.organizacao,
             'lugar_nome', a.lugar_nome, 'bairro', a.bairro, 'cidade', a.cidade, 'lat', a.lat, 'lon', a.lon, 'online', a.online,
             'foto_url', a.foto_url, 'foto_credito', a.foto_credito, 'foto_pagina', a.foto_pagina, 'foto_mini_url', a.foto_mini_url,
             'prioritaria', a.prioritaria,
             'contato_tipo', a.contato_tipo, 'status', a.status, 'criada_em', a.criada_em,
             'fonte', a.fonte, 'lugar_aproximado', a.lugar_aproximado,
             'link_divulgacao', case when a.contato_tipo::text = 'divulgacao' then a.contato_link end,
             'ultimo_inicio', (select max(x.inicio) from turno x where x.acao = a.id)),
    'desistiu', i.cancelada_em is not null
  ) order by t.inicio), '[]'::json)
  from inscricao i join turno t on t.id = i.turno join acao a on a.id = t.acao
  where i.pessoa = auth.uid()
$$;

-- 4. importar_acoes. Há duas migrações 20261009000050 que a redefinem, em branches diferentes: `seguranca`
--    (link/foto/logo só http(s)) e `feedback_e_hora_aproximada` (turno.hora_aproximada). Esta é a UNIÃO das duas,
--    mais foto.mini (mesma regra de https), e vale seja qual for a ordem do merge porque 60 roda depois das duas.
--    A coluna e a view de hora aproximada são criadas aqui se ainda não existem, para a função rodar nas duas árvores.
--    Item com foto nova sobrescreve a mini (inclusive para null, se vier sem); item sem foto não apaga nem a foto nem a mini.
alter table turno add column if not exists hora_aproximada boolean not null default false;
create or replace view turno_publico as
  select t.id, t.acao, t.inicio, t.fim, t.lotacao,
         (select count(*) from inscricao i where i.turno = t.id and i.cancelada_em is null)::int as vao,
         t.hora_aproximada
  from turno t join acao a on a.id = t.acao
  where a.status = 'publicada';

create or replace function importar_acoes(fonte text, itens jsonb, encerrar_faltantes boolean default true)
returns json language plpgsql security definer set search_path = public as $$
#variable_conflict use_column
declare
  it jsonb; org_id bigint; a_id bigint; t_id bigint; nova boolean; aprox boolean;
  link text; foto_url text; foto_mini text; logo_url text;
  n_ins int := 0; n_atu int := 0; n_enc int := 0; ids text[] := '{}';
  sistema constant uuid := '00000000-0000-0000-0000-00000000b07a';
  re_https constant text := '^(https://|http://(127\.0\.0\.1|localhost)[:/])';
begin
  if importar_acoes.fonte is null or importar_acoes.fonte = '' then raise exception 'fonte_vazia'; end if;
  for it in select * from jsonb_array_elements(itens) loop
    org_id := null;
    link := nullif(trim(coalesce(it->>'link', '')), '');
    if link !~* '^https?://' then link := null; end if;
    foto_url := nullif(trim(coalesce(it->'foto'->>'url', '')), '');
    if foto_url !~ re_https then foto_url := null; end if;
    foto_mini := nullif(trim(coalesce(it->'foto'->>'mini', '')), '');
    if foto_url is null or foto_mini !~ re_https then foto_mini := null; end if;
    logo_url := nullif(trim(coalesce(it->'organizacao_foto'->>'url', '')), '');
    if logo_url !~ re_https then logo_url := null; end if;
    if coalesce(it->>'organizacao', '') <> '' then
      insert into organizacao (nome, tipo, foto_url, foto_credito, foto_pagina)
        values (it->>'organizacao', coalesce((it->>'organizacao_tipo')::tipo_org, 'coletivo'),
                logo_url, it->'organizacao_foto'->>'credito', it->'organizacao_foto'->>'pagina')
        on conflict (nome) do update set
          foto_url = coalesce(organizacao.foto_url, excluded.foto_url),
          foto_credito = case when organizacao.foto_url is null then excluded.foto_credito else organizacao.foto_credito end,
          foto_pagina = case when organizacao.foto_url is null then excluded.foto_pagina else organizacao.foto_pagina end
        returning id into org_id;
    end if;
    insert into acao (titulo, tipo, descricao, organizador, organizacao, lugar_nome, bairro, cidade, lat, lon, online,
                      lugar_aproximado, contato_tipo, contato_link, status, fonte, fonte_id, importada_em,
                      foto_url, foto_credito, foto_pagina, foto_mini_url)
    values (it->>'titulo', (it->>'tipo')::tipo_acao, coalesce(it->>'descricao', ''), sistema, org_id,
            it->>'lugar_nome', it->>'bairro', it->>'cidade', (it->>'lat')::double precision, (it->>'lon')::double precision,
            coalesce((it->>'online')::boolean, false), coalesce((it->>'lugar_aproximado')::boolean, false),
            (case when link is not null then 'divulgacao' else 'organizador_chama' end)::contato_tipo,
            link, 'publicada', importar_acoes.fonte, it->>'fonte_id', now(),
            foto_url, it->'foto'->>'credito', it->'foto'->>'pagina', foto_mini)
    on conflict (fonte, fonte_id) where fonte is not null do update set
      titulo = excluded.titulo, tipo = excluded.tipo, descricao = excluded.descricao, organizacao = excluded.organizacao,
      lugar_nome = excluded.lugar_nome, bairro = excluded.bairro, cidade = excluded.cidade, lat = excluded.lat, lon = excluded.lon,
      online = excluded.online, lugar_aproximado = excluded.lugar_aproximado, contato_tipo = excluded.contato_tipo,
      contato_link = excluded.contato_link, importada_em = now(),
      foto_url = coalesce(excluded.foto_url, acao.foto_url),
      foto_credito = case when excluded.foto_url is not null then excluded.foto_credito else acao.foto_credito end,
      foto_pagina = case when excluded.foto_url is not null then excluded.foto_pagina else acao.foto_pagina end,
      foto_mini_url = case when excluded.foto_url is not null then excluded.foto_mini_url else acao.foto_mini_url end,
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
