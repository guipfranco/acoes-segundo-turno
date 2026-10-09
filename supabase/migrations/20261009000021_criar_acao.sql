-- Qualquer pessoa que entrou pode criar ação. A ação nasce "em análise" e só aparece depois que um moderador
-- aprova, a não ser que quem cria seja verificado: papel organizador ou moderador (dado por um moderador) ou
-- membro de organização verificada (pessoa.organizacao). Escolher uma organização verificada na tela não basta.
-- Contra abuso: no máximo 10 ações por dia por pessoa e 10 esperando análise ao mesmo tempo.
-- Quem criou acompanha o status (e o motivo da recusa) no Perfil.

-- Cria a ação e os turnos. `dados`:
--   {titulo, tipo, descricao, foto, online, lugar_nome, bairro, cidade, lat, lon, detalhe, grupo, organizacao,
--    turnos: [{inicio, fim, lotacao}]}
-- Exige telefone (quem organiza recebe a lista de quem vai e precisa ser achado pelo moderador).
create or replace function criar_acao(dados jsonb) returns json language plpgsql security definer set search_path = public as $$
declare p pessoa; a_id bigint; t jsonb; online boolean; grupo text; foto text; n int; verificada boolean; situacao status_acao;
begin
  if auth.uid() is null then raise exception 'precisa_entrar'; end if;
  select * into p from pessoa where id = auth.uid();
  if p.bloqueada then raise exception 'bloqueada'; end if;
  if p.telefone is null then raise exception 'sem_telefone'; end if;
  if (select count(*) from acao where organizador = p.id and (criada_em at time zone 'America/Sao_Paulo')::date = hoje_brasilia()) >= 10 then
    raise exception 'limite_diario';
  end if;
  if (select count(*) from acao where organizador = p.id and status = 'em análise') >= 10 then raise exception 'limite_em_analise'; end if;
  verificada := p.papel in ('organizador', 'moderador')
    or exists (select 1 from organizacao o where o.id = p.organizacao and o.verificada);
  situacao := case when verificada then 'publicada' else 'em análise' end;
  if coalesce(trim(dados->>'titulo'), '') = '' then raise exception 'sem_titulo'; end if;
  online := coalesce((dados->>'online')::boolean, false);
  if not online and (coalesce(trim(dados->>'lugar_nome'), '') = '' or dados->>'lat' is null or dados->>'lon' is null) then
    raise exception 'sem_lugar';
  end if;
  n := coalesce(jsonb_array_length(dados->'turnos'), 0);
  if n = 0 or n > 20 then raise exception 'turno_invalido'; end if;
  for t in select * from jsonb_array_elements(dados->'turnos') loop
    if t->>'inicio' is null or t->>'fim' is null or (t->>'fim')::timestamp <= (t->>'inicio')::timestamp
       or (t->>'inicio')::date < hoje_brasilia() then
      raise exception 'turno_invalido';
    end if;
  end loop;
  grupo := nullif(trim(coalesce(dados->>'grupo', '')), '');
  if grupo is not null and grupo !~ '^https://chat\.whatsapp\.com/' then raise exception 'grupo_invalido'; end if;
  foto := nullif(trim(coalesce(dados->>'foto', '')), '');
  if foto is not null and foto !~ '^https://' then foto := null; end if;

  insert into acao (titulo, tipo, descricao, organizador, organizacao, lugar_nome, bairro, cidade, lat, lon, online,
                    detalhe, contato_tipo, contato_link, foto_url, status)
  values (left(trim(dados->>'titulo'), 140), (dados->>'tipo')::tipo_acao, left(coalesce(dados->>'descricao', ''), 4000), p.id,
          nullif(dados->>'organizacao', '')::bigint,
          case when online then null else left(dados->>'lugar_nome', 200) end,
          case when online then null else left(dados->>'bairro', 120) end,
          case when online then null else left(dados->>'cidade', 120) end,
          case when online then null else (dados->>'lat')::double precision end,
          case when online then null else (dados->>'lon')::double precision end,
          online, left(nullif(trim(coalesce(dados->>'detalhe', '')), ''), 1000),
          case when grupo is null then 'organizador_chama' else 'link_grupo' end::contato_tipo, grupo, foto, situacao)
  returning id into a_id;
  insert into turno (acao, inicio, fim, lotacao)
    select a_id, (x->>'inicio')::timestamp, (x->>'fim')::timestamp, nullif(x->>'lotacao', '')::int
    from jsonb_array_elements(dados->'turnos') x;
  return json_build_object('id', a_id, 'status', situacao);
end $$;

-- Ação no formato da view pública, mais o que só quem organiza (ou modera) vê.
create or replace function acao_completa_json(a acao) returns json language sql stable security definer set search_path = public as $$
  select json_build_object('id', a.id, 'titulo', a.titulo, 'tipo', a.tipo, 'descricao', a.descricao, 'organizador', a.organizador,
    'organizador_nome', (select nome from pessoa where id = a.organizador), 'organizacao', a.organizacao,
    'lugar_nome', a.lugar_nome, 'bairro', a.bairro, 'cidade', a.cidade, 'lat', a.lat, 'lon', a.lon, 'online', a.online,
    'foto_url', a.foto_url, 'foto_credito', a.foto_credito, 'foto_pagina', a.foto_pagina, 'prioritaria', a.prioritaria,
    'contato_tipo', a.contato_tipo, 'status', a.status, 'criada_em', a.criada_em, 'fonte', a.fonte,
    'lugar_aproximado', a.lugar_aproximado, 'motivo_recusa', a.motivo_recusa, 'detalhe', a.detalhe, 'contato_link', a.contato_link,
    'link_divulgacao', case when a.contato_tipo::text = 'divulgacao' then a.contato_link end)
$$;

-- Turnos com a lista de quem vai (nome e telefone: vão para quem organiza, como diz a tela de inscrição).
create or replace function turnos_com_inscritos_json(acao_id bigint) returns json language sql stable security definer set search_path = public as $$
  select coalesce(json_agg(json_build_object('id', t.id, 'acao', t.acao, 'inicio', t.inicio, 'fim', t.fim, 'lotacao', t.lotacao,
    'vao', (select count(*) from inscricao x where x.turno = t.id and x.cancelada_em is null),
    'inscritos', coalesce((select json_agg(json_build_object('nome', q.nome, 'telefone', q.telefone) order by i.criada_em)
                           from inscricao i join pessoa q on q.id = i.pessoa
                           where i.turno = t.id and i.cancelada_em is null), '[]'::json)) order by t.inicio), '[]'::json)
  from turno t where t.acao = acao_id
$$;

-- As ações que eu criei, em qualquer status.
create or replace function minhas_acoes() returns json language sql stable security definer set search_path = public as $$
  select coalesce(json_agg(json_build_object('acao', acao_completa_json(a), 'turnos', turnos_com_inscritos_json(a.id))
                           order by a.criada_em desc), '[]'::json)
  from acao a where a.organizador = auth.uid()
$$;

-- Quem criou (ou um moderador) encerra a ação.
create or replace function encerrar_acao(acao_id bigint) returns void language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then raise exception 'precisa_entrar'; end if;
  update acao set status = 'encerrada'
   where id = acao_id and (organizador = auth.uid() or eh_moderador()) and status in ('em análise', 'publicada');
  if not found then raise exception 'nao_pode'; end if;
end $$;

-- Fila de moderação: ações em análise (ou publicadas criadas pelo app), com quem criou e o histórico dela.
create or replace function fila_moderacao(situacao text default 'em análise') returns json language plpgsql stable security definer set search_path = public as $$
begin
  if not eh_moderador() then raise exception 'so_moderador'; end if;
  return (select coalesce(json_agg(json_build_object(
      'acao', acao_completa_json(a), 'turnos', turnos_com_inscritos_json(a.id),
      'organizador', json_build_object('id', p.id, 'nome', p.nome, 'email', p.email, 'telefone', p.telefone, 'bloqueada', p.bloqueada,
        'criadas', (select count(*) from acao x where x.organizador = p.id),
        'aprovadas', (select count(*) from acao x where x.organizador = p.id and x.status in ('publicada', 'encerrada')),
        'recusadas', (select count(*) from acao x where x.organizador = p.id and x.status = 'recusada')))
    order by a.criada_em desc), '[]'::json)
    from acao a join pessoa p on p.id = a.organizador
    where a.status::text = situacao and a.fonte is null);
end $$;

create or replace function aprovar_acao(acao_id bigint) returns void language plpgsql security definer set search_path = public as $$
begin
  if not eh_moderador() then raise exception 'so_moderador'; end if;
  update acao set status = 'publicada', motivo_recusa = null where id = acao_id and status = 'em análise';
  if not found then raise exception 'nao_pode'; end if;
  insert into registro_moderacao (moderador, acao_feita, alvo_tipo, alvo_id) values (auth.uid(), 'aprovar', 'acao', acao_id::text);
end $$;

create or replace function recusar_acao(acao_id bigint, motivo text) returns void language plpgsql security definer set search_path = public as $$
begin
  if not eh_moderador() then raise exception 'so_moderador'; end if;
  if coalesce(trim(motivo), '') = '' then raise exception 'sem_motivo'; end if;
  update acao set status = 'recusada', motivo_recusa = left(trim(motivo), 500) where id = acao_id and status in ('em análise', 'publicada');
  if not found then raise exception 'nao_pode'; end if;
  insert into registro_moderacao (moderador, acao_feita, alvo_tipo, alvo_id, motivo) values (auth.uid(), 'recusar', 'acao', acao_id::text, trim(motivo));
end $$;

-- Só quem entrou chama; os auxiliares não são API.
revoke execute on function acao_completa_json(acao), turnos_com_inscritos_json(bigint) from public, anon, authenticated;
revoke execute on function criar_acao(jsonb), minhas_acoes(), encerrar_acao(bigint), fila_moderacao(text),
  aprovar_acao(bigint), recusar_acao(bigint, text) from public, anon;
grant execute on function criar_acao(jsonb), minhas_acoes(), encerrar_acao(bigint), fila_moderacao(text),
  aprovar_acao(bigint), recusar_acao(bigint, text) to authenticated;

-- A sessão passa a trazer a organização da pessoa (o app usa para saber se ela é verificada).
create or replace function pessoa_json(p pessoa) returns json language sql immutable as $$
  select json_build_object('id', p.id, 'nome', p.nome, 'email', p.email, 'telefone', p.telefone, 'papel', p.papel,
                           'bloqueada', p.bloqueada, 'organizacao', p.organizacao)
$$;
