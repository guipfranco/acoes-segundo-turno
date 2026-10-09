-- O que foi cancelado não some (pedido do Gui, 2026-10-09).
-- 1. Ação cancelada (status 'encerrada': quem criou cancelou, ou a importada saiu da agenda de origem) continua
--    abrindo pelo link, para qualquer pessoa, com o aviso de cancelada. Fora da vitrine e do mapa, como antes.
--    Quem não criou nem modera recebe só os campos da view pública (sem detalhe, link do grupo, post oficial
--    nem motivo de recusa).
-- 2. Minhas inscrições traz também as que a pessoa desistiu (marcadas 'desistiu'), para o histórico.
-- 3. Quem organiza vê, em cada horário, quem desistiu.

create or replace function acao_restrita(acao_id bigint) returns json language plpgsql stable security definer set search_path = public as $$
declare a acao; j json;
begin
  select * into a from acao where id = acao_id;
  if not found then return null; end if;
  if auth.uid() is not null and (a.organizador = auth.uid() or eh_moderador()) then
    j := acao_completa_json(a);
  elsif a.status = 'encerrada' then
    j := (acao_completa_json(a)::jsonb - 'detalhe' - 'contato_link' - 'organizacao_link' - 'organizacao_dados' - 'motivo_recusa')::json;
  else
    return null;
  end if;
  return json_build_object('acao', j,
    'turnos', coalesce((select json_agg(json_build_object('id', t.id, 'acao', t.acao, 'inicio', t.inicio, 'fim', t.fim, 'lotacao', t.lotacao,
      'vao', (select count(*) from inscricao i where i.turno = t.id and i.cancelada_em is null)) order by t.inicio)
      from turno t where t.acao = a.id), '[]'::json));
end $$;

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
             'link_divulgacao', case when a.contato_tipo::text = 'divulgacao' then a.contato_link end),
    'desistiu', i.cancelada_em is not null
  ) order by t.inicio), '[]'::json)
  from inscricao i join turno t on t.id = i.turno join acao a on a.id = t.acao
  where i.pessoa = auth.uid()
$$;

create or replace function turnos_com_inscritos_json(acao_id bigint) returns json language sql stable security definer set search_path = public as $$
  select coalesce(json_agg(json_build_object('id', t.id, 'acao', t.acao, 'inicio', t.inicio, 'fim', t.fim, 'lotacao', t.lotacao,
    'vao', (select count(*) from inscricao x where x.turno = t.id and x.cancelada_em is null),
    'inscritos', coalesce((select json_agg(json_build_object('nome', q.nome, 'telefone', q.telefone) order by i.criada_em)
                           from inscricao i join pessoa q on q.id = i.pessoa
                           where i.turno = t.id and i.cancelada_em is null), '[]'::json),
    'desistiram', coalesce((select json_agg(json_build_object('nome', q.nome, 'telefone', q.telefone) order by i.cancelada_em)
                            from inscricao i join pessoa q on q.id = i.pessoa
                            where i.turno = t.id and i.cancelada_em is not null), '[]'::json)) order by t.inicio), '[]'::json)
  from turno t where t.acao = acao_id
$$;

-- A página da ação cancelada abre também para quem não entrou.
grant execute on function acao_restrita(bigint) to anon;
