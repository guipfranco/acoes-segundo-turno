-- Verificação das ações de divulgação pública (2026-10-10). Decisão do Gui: não confiar na revisão de quem publica a
-- agenda de origem (nem do feed Bora Lula do Comitê, que tem formulário aberto, nem da varredura das redes). Toda ação
-- importada (acao.fonte não nulo) continua indo ao ar, mas o app mostra a etiqueta "Divulgação pública" até alguém da
-- moderação conferir pelo post original e marcar como verificada. Reimportar com data, hora, lugar ou link diferentes
-- tira a verificação: o que a moderação conferiu já não é o que está no ar.

alter table acao add column verificada_em timestamptz, add column verificada_por uuid references pessoa(id);

-- 1. view pública: `verificada` no fim (create or replace view só aceita coluna nova no fim). Ação cadastrada no app
--    passou pela regra de publicação de lá (análise ou organizador verificado) e conta como verificada.
create or replace view acao_publica as
  select a.id, a.titulo, a.tipo, a.descricao, a.organizador, p.nome as organizador_nome, a.organizacao,
         a.lugar_nome, a.bairro, a.cidade, a.lat, a.lon, a.online,
         a.foto_url, a.foto_credito, a.foto_pagina, a.prioritaria, a.contato_tipo, a.status, a.criada_em,
         a.fonte, a.lugar_aproximado,
         case when a.contato_tipo::text = 'divulgacao' then a.contato_link end as link_divulgacao,
         a.foto_mini_url,
         (a.fonte is null or a.verificada_em is not null) as verificada
  from acao a join pessoa p on p.id = a.organizador
  where a.status = 'publicada';

-- 2. ação completa (Fila, Minhas ações, link de cancelada): igual à da migração 60, com `verificada`.
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
                          from organizacao o where o.id = a.organizacao),
    'verificada', (a.fonte is null or a.verificada_em is not null))
$$;
revoke execute on function acao_completa_json(acao) from public, anon, authenticated;

-- 2b. minhas inscrições: igual à da migração 60, com `verificada` (a lista "Onde eu vou" mostra a etiqueta).
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
             'verificada', (a.fonte is null or a.verificada_em is not null),
             'ultimo_inicio', (select max(x.inicio) from turno x where x.acao = a.id)),
    'desistiu', i.cancelada_em is not null
  ) order by t.inicio), '[]'::json)
  from inscricao i join turno t on t.id = i.turno join acao a on a.id = t.acao
  where i.pessoa = auth.uid()
$$;

-- 3. moderação marca e desmarca. Só ação importada e no ar; fica no registro de moderação.
create or replace function verificar_acao(acao_id bigint) returns void language plpgsql security definer set search_path = public as $$
begin
  if not eh_moderador() then raise exception 'so_moderador'; end if;
  update acao set verificada_em = now(), verificada_por = auth.uid()
    where id = acao_id and fonte is not null and status = 'publicada';
  if not found then raise exception 'nao_pode'; end if;
  insert into registro_moderacao (moderador, acao_feita, alvo_tipo, alvo_id) values (auth.uid(), 'verificar', 'acao', acao_id::text);
end $$;

create or replace function desverificar_acao(acao_id bigint) returns void language plpgsql security definer set search_path = public as $$
begin
  if not eh_moderador() then raise exception 'so_moderador'; end if;
  update acao set verificada_em = null, verificada_por = null where id = acao_id and fonte is not null and verificada_em is not null;
  if not found then raise exception 'nao_pode'; end if;
  insert into registro_moderacao (moderador, acao_feita, alvo_tipo, alvo_id) values (auth.uid(), 'desverificar', 'acao', acao_id::text);
end $$;

revoke execute on function verificar_acao(bigint), desverificar_acao(bigint) from public, anon;
grant execute on function verificar_acao(bigint), desverificar_acao(bigint) to authenticated;

-- 4. Fila: igual à da migração 40, mais a situação 'divulgacao': importadas no ar, sem verificação, com horário que
--    ainda vale (como turnoVale no app: o exato até terminar, o de hora aproximada até o fim do dia), da mais próxima para a mais distante (a de amanhã é a que mais precisa ser conferida).
create or replace function fila_moderacao(situacao text default 'em análise') returns json language plpgsql stable security definer set search_path = public as $$
declare agora timestamp := now() at time zone 'America/Sao_Paulo';
begin
  if not eh_moderador() then raise exception 'so_moderador'; end if;
  if situacao = 'divulgacao' then
    return (select coalesce(json_agg(json_build_object(
        'acao', acao_completa_json(a), 'turnos', turnos_com_inscritos_json(a.id), 'organizador', null)
      order by n.prox), '[]'::json)
      from acao a cross join lateral (select min(t.inicio) as prox from turno t where t.acao = a.id
                                        and (case when t.hora_aproximada then t.fim::date >= agora::date else t.fim >= agora end)) n
      where a.fonte is not null and a.status = 'publicada' and a.verificada_em is null and n.prox is not null);
  end if;
  return (select coalesce(json_agg(json_build_object(
      'acao', acao_completa_json(a), 'turnos', turnos_com_inscritos_json(a.id),
      'organizador', json_build_object('id', p.id, 'nome', p.nome, 'email', p.email, 'telefone', p.telefone, 'bloqueada', p.bloqueada,
        'criadas', (select count(*) from acao x where x.organizador = p.id),
        'aprovadas', (select count(*) from acao x where x.organizador = p.id and x.status in ('publicada', 'encerrada') and x.publicada_em is not null),
        'recusadas', (select count(*) from acao x where x.organizador = p.id and x.status = 'recusada')))
    order by a.criada_em desc), '[]'::json)
    from acao a join pessoa p on p.id = a.organizador
    where a.status::text = situacao and (a.fonte is null or situacao = 'rascunho'));
end $$;

-- 5. importar_acoes: igual à da migração 60, mais a regra de verificação. Ação nova nasce sem verificação. Na
--    reimportação, a verificação cai se mudou QUALQUER coisa que vem da fonte (título, tipo, descrição, organização,
--    lugar, ponto, online, lugar aproximado, contato/link, horários, hora aproximada) ou se a ação estava encerrada e
--    volta ao ar. Só foto da ação e logo da organização não contam: não mudam o que a moderação conferiu.
--    Horários: a importação traz um turno; se a ação tem outro número de turnos, ou o primeiro mudou, cai.
--    A linha antiga é lida antes do upsert, o "mudou" é um booleano só e a verificação cai num UPDATE só.
create or replace function importar_acoes(fonte text, itens jsonb, encerrar_faltantes boolean default true)
returns json language plpgsql security definer set search_path = public as $$
#variable_conflict use_column
declare
  it jsonb; org_id bigint; a_id bigint; t_id bigint; nova boolean; aprox boolean; mudou boolean;
  antes acao; t_antes turno; n_turnos int; novo_ini timestamp; novo_fim timestamp;
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
    aprox := coalesce((it->>'hora_aproximada')::boolean, false);
    novo_ini := (it->>'inicio')::timestamp; novo_fim := (it->>'fim')::timestamp;
    -- linha antiga (se existe) e o que mudou nela em relação ao que veio da fonte
    select * into antes from acao where acao.fonte = importar_acoes.fonte and acao.fonte_id = it->>'fonte_id';
    if found then
      select count(*) into n_turnos from turno where turno.acao = antes.id;
      select * into t_antes from turno where turno.acao = antes.id order by inicio limit 1;
      mudou := antes.status = 'encerrada'
        or antes.titulo is distinct from (it->>'titulo') or antes.tipo is distinct from (it->>'tipo')::tipo_acao
        or antes.descricao is distinct from coalesce(it->>'descricao', '') or antes.organizacao is distinct from org_id
        or antes.lugar_nome is distinct from (it->>'lugar_nome') or antes.bairro is distinct from (it->>'bairro')
        or antes.cidade is distinct from (it->>'cidade')
        or antes.lat is distinct from (it->>'lat')::double precision or antes.lon is distinct from (it->>'lon')::double precision
        or antes.online is distinct from coalesce((it->>'online')::boolean, false)
        or antes.lugar_aproximado is distinct from coalesce((it->>'lugar_aproximado')::boolean, false)
        or antes.contato_link is distinct from link
        or antes.contato_tipo is distinct from (case when link is not null then 'divulgacao' else 'organizador_chama' end)::contato_tipo
        or n_turnos <> 1 or t_antes.inicio is distinct from novo_ini or t_antes.fim is distinct from novo_fim
        or t_antes.hora_aproximada is distinct from aprox;
    else
      mudou := false;
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
    if mudou then update acao set verificada_em = null, verificada_por = null where id = a_id and verificada_em is not null; end if;
    if nova then n_ins := n_ins + 1; else n_atu := n_atu + 1; end if;
    ids := ids || (it->>'fonte_id');
    select id into t_id from turno where acao = a_id order by inicio limit 1;
    if found then
      update turno set inicio = novo_ini, fim = novo_fim, hora_aproximada = aprox where id = t_id;
    else
      insert into turno (acao, inicio, fim, hora_aproximada) values (a_id, novo_ini, novo_fim, aprox);
    end if;
  end loop;
  if encerrar_faltantes then
    update acao set status = 'encerrada'
      where acao.fonte = importar_acoes.fonte and status = 'publicada' and not (fonte_id = any (ids));
    get diagnostics n_enc = row_count;
  end if;
  return json_build_object('inseridas', n_ins, 'atualizadas', n_atu, 'encerradas', n_enc);
end $$;
