-- "Eu vou!" também nas ações de divulgação (importadas, sem organizador real).
-- Nelas a inscrição só marca presença: entra no contador e em Minhas inscrições, não pede telefone e não
-- manda dado para ninguém (o organizador é a pessoa de sistema, que nunca entra).
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

-- Minhas inscrições passa a trazer a origem, o lugar aproximado e o link da divulgação, como a view pública.
create or replace function minhas_inscricoes() returns json language sql stable security definer set search_path = public as $$
  select coalesce(json_agg(json_build_object(
    'turno', json_build_object('id', t.id, 'acao', t.acao, 'inicio', t.inicio, 'fim', t.fim, 'lotacao', t.lotacao,
             'vao', (select count(*) from inscricao x where x.turno = t.id and x.cancelada_em is null)),
    'acao', json_build_object('id', a.id, 'titulo', a.titulo, 'tipo', a.tipo, 'descricao', a.descricao, 'organizador', a.organizador,
             'organizador_nome', (select nome from pessoa where id = a.organizador), 'organizacao', a.organizacao,
             'lugar_nome', a.lugar_nome, 'bairro', a.bairro, 'cidade', a.cidade, 'lat', a.lat, 'lon', a.lon, 'online', a.online,
             'foto_url', a.foto_url, 'foto_credito', a.foto_credito, 'foto_pagina', a.foto_pagina, 'prioritaria', a.prioritaria,
             'contato_tipo', a.contato_tipo, 'status', a.status, 'criada_em', a.criada_em,
             'fonte', a.fonte, 'lugar_aproximado', a.lugar_aproximado,
             'link_divulgacao', case when a.contato_tipo::text = 'divulgacao' then a.contato_link end)
  ) order by t.inicio), '[]'::json)
  from inscricao i join turno t on t.id = i.turno join acao a on a.id = t.acao
  where i.pessoa = auth.uid() and i.cancelada_em is null
$$;
