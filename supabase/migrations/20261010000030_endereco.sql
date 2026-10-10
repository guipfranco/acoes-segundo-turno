-- Endereço da ação (decisão do Gui, 2026-10-10): quem cadastra pode escrever o endereço (rua e número) e o app acha o
-- ponto no mapa por ele; quem vai vê o endereço e um link "Como chegar". O endereço é PÚBLICO, como o pino já era: o
-- formulário avisa para usar lugar público e nunca endereço de casa, e a moderação confere antes de publicar. A
-- importação passa a guardar o endereço que vem da fonte (antes só servia para achar o ponto). Aditiva: o app de
-- antes segue funcionando (coluna vazia).

alter table acao add column if not exists endereco text;
alter table acao add constraint acao_endereco_tamanho check (endereco is null or length(endereco) <= 200);

-- 1. view pública: `endereco` no fim (create or replace view só aceita coluna nova no fim).
create or replace view acao_publica as
  select a.id, a.titulo, a.tipo, a.descricao, a.organizador, p.nome as organizador_nome, a.organizacao,
         a.lugar_nome, a.bairro, a.cidade, a.lat, a.lon, a.online,
         a.foto_url, a.foto_credito, a.foto_pagina, a.prioritaria, a.contato_tipo, a.status, a.criada_em,
         a.fonte, a.lugar_aproximado,
         case when a.contato_tipo::text = 'divulgacao' then a.contato_link end as link_divulgacao,
         a.foto_mini_url,
         (a.fonte is null or a.verificada_em is not null) as verificada,
         a.endereco
  from acao a join pessoa p on p.id = a.organizador
  where a.status = 'publicada';

-- 2. ação completa (Fila, Minhas ações, link de cancelada): igual à da migração 20261010000010, com `endereco`.
create or replace function acao_completa_json(a acao) returns json language sql stable security definer set search_path = public as $$
  select json_build_object('id', a.id, 'titulo', a.titulo, 'tipo', a.tipo, 'descricao', a.descricao, 'organizador', a.organizador,
    'organizador_nome', (select nome from pessoa where id = a.organizador), 'organizacao', a.organizacao,
    'lugar_nome', a.lugar_nome, 'endereco', a.endereco, 'bairro', a.bairro, 'cidade', a.cidade, 'lat', a.lat, 'lon', a.lon, 'online', a.online,
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

-- 3. minhas inscrições: igual à da migração 20261010000010, com `endereco`.
create or replace function minhas_inscricoes() returns json language sql stable security definer set search_path = public as $$
  select coalesce(json_agg(json_build_object(
    'turno', json_build_object('id', t.id, 'acao', t.acao, 'inicio', t.inicio, 'fim', t.fim, 'lotacao', t.lotacao,
             'vao', (select count(*) from inscricao x where x.turno = t.id and x.cancelada_em is null)),
    'acao', json_build_object('id', a.id, 'titulo', a.titulo, 'tipo', a.tipo, 'descricao', a.descricao, 'organizador', a.organizador,
             'organizador_nome', (select nome from pessoa where id = a.organizador), 'organizacao', a.organizacao,
             'lugar_nome', a.lugar_nome, 'endereco', a.endereco, 'bairro', a.bairro, 'cidade', a.cidade, 'lat', a.lat, 'lon', a.lon, 'online', a.online,
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

-- 4. criar_acao: igual à da migração 51, mais `endereco` (opcional, até 200 caracteres; ação online não tem).
create or replace function criar_acao(dados jsonb) returns json language plpgsql security definer set search_path = public as $$
declare p pessoa; a_id bigint; t jsonb; online boolean; grupo text; foto text; n int; verificada boolean; situacao status_acao;
        org_id bigint; org_nome text; org_link text; achada organizacao;
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
  foto := nullif(trim(coalesce(dados->>'foto', '')), '');
  -- só imagem do próprio Storage (bucket fotos-acoes; a pilha local passa para os testes)
  if not url_de_imagem_valida(foto) then raise exception 'sem_foto'; end if;
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
  -- quem organiza
  org_nome := nullif(trim(coalesce(dados->>'organizacao_nome', '')), '');
  org_link := nullif(trim(coalesce(dados->>'organizacao_link', '')), '');
  if nullif(dados->>'organizacao', '')::bigint is not null and nullif(dados->>'organizacao', '')::bigint = p.organizacao then
    org_id := p.organizacao;
    -- em nome da minha organização: precisa do post dela anunciando a ação (com ou sem selo)
    if not link_oficial_valido(org_link) then raise exception 'link_post'; end if;
  elsif org_nome is not null then
    if length(org_nome) < 3 or length(org_nome) > 80 then raise exception 'nome_organizacao'; end if;
    if not link_oficial_valido(org_link) then raise exception 'link_post'; end if;
    achada := organizacao_por_nome(org_nome);
    if achada.id is null then
      insert into organizacao (nome, tipo, criada_por) values (org_nome, 'coletivo', p.id) returning id into org_id;
    else
      org_id := achada.id;
    end if;
  end if;
  if org_id is null then org_link := null; end if;

  insert into acao (titulo, tipo, descricao, organizador, organizacao, lugar_nome, endereco, bairro, cidade, lat, lon, online,
                    detalhe, contato_tipo, contato_link, foto_url, status, organizacao_link)
  values (left(trim(dados->>'titulo'), 140), (dados->>'tipo')::tipo_acao, left(coalesce(dados->>'descricao', ''), 4000), p.id,
          org_id,
          case when online then null else left(dados->>'lugar_nome', 200) end,
          case when online then null else left(nullif(trim(coalesce(dados->>'endereco', '')), ''), 200) end,
          case when online then null else left(dados->>'bairro', 120) end,
          case when online then null else left(dados->>'cidade', 120) end,
          case when online then null else (dados->>'lat')::double precision end,
          case when online then null else (dados->>'lon')::double precision end,
          online, left(nullif(trim(coalesce(dados->>'detalhe', '')), ''), 1000),
          case when grupo is null then 'organizador_chama' else 'link_grupo' end::contato_tipo, grupo, foto, situacao, org_link)
  returning id into a_id;
  insert into turno (acao, inicio, fim, lotacao)
    select a_id, (x->>'inicio')::timestamp, (x->>'fim')::timestamp, nullif(x->>'lotacao', '')::int
    from jsonb_array_elements(dados->'turnos') x;
  return json_build_object('id', a_id, 'status', situacao);
end $$;

-- 5. importar_acoes: igual à da migração 20261010000020, mais `endereco`. A verificação cai se o endereço mudou, mas
--    só quando já havia um: na primeira reimportação depois desta migração as ações ganham o endereço sem perder a
--    verificação. Lugar sem ponto que não apaga o da ação no ar também guarda o endereço que ela tinha.
create or replace function importar_acoes(fonte text, itens jsonb, encerrar_faltantes boolean default true)
returns json language plpgsql security definer set search_path = public as $$
#variable_conflict use_column
declare
  st status_acao; sem_ponto boolean;
  it jsonb; org_id bigint; a_id bigint; t_id bigint; nova boolean; aprox boolean; mudou boolean;
  antes acao; t_antes turno; n_turnos int; novo_ini timestamp; novo_fim timestamp;
  link text; foto_url text; foto_mini text; logo_url text; ender text;
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
    ender := left(nullif(trim(coalesce(it->>'endereco', '')), ''), 200);
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
        or (antes.endereco is not null and antes.endereco is distinct from ender)
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
    insert into acao (titulo, tipo, descricao, organizador, organizacao, lugar_nome, endereco, bairro, cidade, lat, lon, online,
                      lugar_aproximado, contato_tipo, contato_link, status, fonte, fonte_id, importada_em,
                      foto_url, foto_credito, foto_pagina, foto_mini_url, motivo_duvida)
    values (it->>'titulo', (it->>'tipo')::tipo_acao, coalesce(it->>'descricao', ''), sistema, org_id,
            it->>'lugar_nome', ender, it->>'bairro', it->>'cidade', (it->>'lat')::double precision, (it->>'lon')::double precision,
            coalesce((it->>'online')::boolean, false), coalesce((it->>'lugar_aproximado')::boolean, false),
            (case when link is not null then 'divulgacao' else 'organizador_chama' end)::contato_tipo,
            link, st, importar_acoes.fonte, it->>'fonte_id', now(),
            foto_url, it->'foto'->>'credito', it->'foto'->>'pagina', foto_mini, nullif(trim(coalesce(it->>'motivo_duvida', '')), ''))
    on conflict (fonte, fonte_id) where fonte is not null do update set
      titulo = excluded.titulo, tipo = excluded.tipo, descricao = excluded.descricao, organizacao = excluded.organizacao,
      -- sem ponto no mapa na fonte: a ação que já está no ar guarda o lugar que tinha (a verificação cai, porque mudou)
      lugar_nome = case when sem_ponto and acao.status <> 'em análise' then acao.lugar_nome else excluded.lugar_nome end,
      endereco = case when sem_ponto and acao.status <> 'em análise' then acao.endereco else excluded.endereco end,
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
