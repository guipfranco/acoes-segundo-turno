-- Dúvida vai para aprovação (decisão do Gui, 2026-10-10): a importação não descarta mais ação por dúvida. A dúvida
-- (confiança baixa na varredura das redes, cidade que a gente não reconhece) entra com status 'em análise', fora do
-- ar, com o motivo em `acao.motivo_duvida`, e aparece na aba Em análise da Fila. O resto vai ao ar com a etiqueta
-- "Divulgação pública" (migração 20261010000010). Aditiva: o app de antes segue funcionando.

alter table acao add column if not exists motivo_duvida text;

-- 1. Ação sem ponto no mapa (cidade não reconhecida) só pode existir fora do ar; publicada continua precisando do lugar.
alter table acao drop constraint acao_check;
alter table acao add constraint acao_check check (online or status <> 'publicada' or (lat is not null and lon is not null and lugar_nome is not null));

-- 2. Aprovar: importada aprovada fica verificada (o moderador conferiu); sem lugar no mapa não dá para aprovar.
create or replace function aprovar_acao(acao_id bigint) returns void language plpgsql security definer set search_path = public as $$
declare a acao;
begin
  if not eh_moderador() then raise exception 'so_moderador'; end if;
  select * into a from acao where id = acao_id and status = 'em análise';
  if not found then raise exception 'nao_pode'; end if;
  if not a.online and (a.lat is null or a.lon is null or a.lugar_nome is null) then raise exception 'sem_lugar'; end if;
  update acao set status = 'publicada', motivo_recusa = null,
    verificada_em = case when fonte is not null then now() else verificada_em end,
    verificada_por = case when fonte is not null then auth.uid() else verificada_por end
    where id = acao_id;
  insert into registro_moderacao (moderador, acao_feita, alvo_tipo, alvo_id) values (auth.uid(), 'aprovar', 'acao', acao_id::text);
end $$;

-- 3. Fila: a aba Em análise passa a mostrar também as importadas em dúvida (sem pessoa organizadora, com o motivo).
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
      'acao', acao_completa_json(a), 'turnos', turnos_com_inscritos_json(a.id), 'duvida', a.motivo_duvida,
      'organizador', case when a.fonte is not null then null else json_build_object('id', p.id, 'nome', p.nome, 'email', p.email, 'telefone', p.telefone, 'bloqueada', p.bloqueada,
        'criadas', (select count(*) from acao x where x.organizador = p.id),
        'aprovadas', (select count(*) from acao x where x.organizador = p.id and x.status in ('publicada', 'encerrada') and x.publicada_em is not null),
        'recusadas', (select count(*) from acao x where x.organizador = p.id and x.status = 'recusada')) end)
    order by a.criada_em desc), '[]'::json)
    from acao a join pessoa p on p.id = a.organizador
    where a.status::text = situacao and (a.fonte is null or situacao in ('rascunho', 'em análise')));
end $$;

-- 4. importar_acoes: igual à da migração 20261010000010, mais `status` por item ('publicada' ou 'em análise', só na
--    inserção; a reimportação não mexe na decisão da moderação), `motivo_duvida`, lugar sem ponto que não apaga o da ação
--    no ar, encerrada que nunca esteve no ar volta para a análise e não para o ar, e a em análise que sumiu da fonte encerra.
create or replace function importar_acoes(fonte text, itens jsonb, encerrar_faltantes boolean default true)
returns json language plpgsql security definer set search_path = public as $$
#variable_conflict use_column
declare
  st status_acao; sem_ponto boolean;
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
    st := case when it->>'status' = 'em análise' then 'em análise' else 'publicada' end;
    sem_ponto := not coalesce((it->>'online')::boolean, false) and ((it->>'lat') is null or (it->>'lon') is null);
    if sem_ponto and st = 'publicada' then raise exception 'sem_lugar: % precisa de ponto no mapa ou status em análise', it->>'fonte_id'; end if;
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
                      foto_url, foto_credito, foto_pagina, foto_mini_url, motivo_duvida)
    values (it->>'titulo', (it->>'tipo')::tipo_acao, coalesce(it->>'descricao', ''), sistema, org_id,
            it->>'lugar_nome', it->>'bairro', it->>'cidade', (it->>'lat')::double precision, (it->>'lon')::double precision,
            coalesce((it->>'online')::boolean, false), coalesce((it->>'lugar_aproximado')::boolean, false),
            (case when link is not null then 'divulgacao' else 'organizador_chama' end)::contato_tipo,
            link, st, importar_acoes.fonte, it->>'fonte_id', now(),
            foto_url, it->'foto'->>'credito', it->'foto'->>'pagina', foto_mini, nullif(trim(coalesce(it->>'motivo_duvida', '')), ''))
    on conflict (fonte, fonte_id) where fonte is not null do update set
      titulo = excluded.titulo, tipo = excluded.tipo, descricao = excluded.descricao, organizacao = excluded.organizacao,
      -- sem ponto no mapa na fonte: a ação que já está no ar guarda o lugar que tinha (a verificação cai, porque mudou)
      lugar_nome = case when sem_ponto and acao.status <> 'em análise' then acao.lugar_nome else excluded.lugar_nome end,
      bairro = case when sem_ponto and acao.status <> 'em análise' then acao.bairro else excluded.bairro end,
      cidade = case when sem_ponto and acao.status <> 'em análise' then acao.cidade else excluded.cidade end,
      lat = case when sem_ponto and acao.status <> 'em análise' then acao.lat else excluded.lat end,
      lon = case when sem_ponto and acao.status <> 'em análise' then acao.lon else excluded.lon end,
      motivo_duvida = excluded.motivo_duvida,
      online = excluded.online, lugar_aproximado = excluded.lugar_aproximado, contato_tipo = excluded.contato_tipo,
      contato_link = excluded.contato_link, importada_em = now(),
      foto_url = coalesce(excluded.foto_url, acao.foto_url),
      foto_credito = case when excluded.foto_url is not null then excluded.foto_credito else acao.foto_credito end,
      foto_pagina = case when excluded.foto_url is not null then excluded.foto_pagina else acao.foto_pagina end,
      foto_mini_url = case when excluded.foto_url is not null then excluded.foto_mini_url else acao.foto_mini_url end,
      -- volta da fonte: só reabre no ar a que já esteve publicada; a que nunca foi aprovada volta para a análise
      status = case when acao.status = 'encerrada' and acao.publicada_em is not null then 'publicada'
                    when acao.status = 'encerrada' then 'em análise' else acao.status end
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
      where acao.fonte = importar_acoes.fonte and status in ('publicada', 'em análise') and not (fonte_id = any (ids));
    get diagnostics n_enc = row_count;
  end if;
  return json_build_object('inseridas', n_ins, 'atualizadas', n_atu, 'encerradas', n_enc);
end $$;
