-- Revisão de segurança antes de o site se espalhar (2026-10-09).
-- 1. Imagem de ação e logo de organização só do próprio Storage (buckets fotos-acoes e divulgacao). Antes
--    qualquer https passava: dava para trocar a imagem depois de aprovada e rastrear o IP de quem visita.
-- 2. importar_acoes descarta link e url de foto que não sejam http(s): o link vai para href no app.
-- 3. Bloqueio de pessoa pela moderação (bloquear_pessoa / desbloquear_pessoa), com registro.
-- 4. Limite de 40 objetos por pessoa no bucket fotos-acoes.

-- 1. URL de imagem servida pelo próprio Storage (produção) ou pela pilha local (testes).
create or replace function url_de_imagem_valida(url text) returns boolean language sql immutable as $$
  select coalesce(url, '') ~ '^https://ommitzndniqnmsjsjghb\.supabase\.co/storage/v1/object/public/(fotos-acoes|divulgacao)/'
      or coalesce(url, '') ~ '^http://(127\.0\.0\.1|localhost):\d+/storage/v1/object/public/(fotos-acoes|divulgacao)/'
$$;
revoke execute on function url_de_imagem_valida(text) from public, anon, authenticated;

-- criar_acao: igual à da migração 23, com a foto conferida por url_de_imagem_valida.
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

  insert into acao (titulo, tipo, descricao, organizador, organizacao, lugar_nome, bairro, cidade, lat, lon, online,
                    detalhe, contato_tipo, contato_link, foto_url, status, organizacao_link)
  values (left(trim(dados->>'titulo'), 140), (dados->>'tipo')::tipo_acao, left(coalesce(dados->>'descricao', ''), 4000), p.id,
          org_id,
          case when online then null else left(dados->>'lugar_nome', 200) end,
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

-- salvar_organizacao: igual à da migração 23; logo fora do Storage é descartado (vira null, sem erro).
create or replace function salvar_organizacao(nome text, tipo text, logo text default null, link text default null) returns json language plpgsql security definer set search_path = public as $$
declare p pessoa; o organizacao; n text := trim(coalesce(nome, '')); l text := nullif(trim(coalesce(logo, '')), ''); lk text := trim(coalesce(link, ''));
begin
  if auth.uid() is null then raise exception 'precisa_entrar'; end if;
  select * into p from pessoa where id = auth.uid();
  if p.bloqueada then raise exception 'bloqueada'; end if;
  if length(n) < 3 or length(n) > 80 then raise exception 'nome_organizacao'; end if;
  if not url_de_imagem_valida(l) then l := null; end if;
  if not link_oficial_valido(lk) then raise exception 'link_oficial'; end if;
  o := organizacao_por_nome(n);
  if o.id is null then
    insert into organizacao (nome, tipo, foto_url, criada_por, link_oficial) values (n, coalesce(tipo, 'coletivo')::tipo_org, l, p.id, lk) returning * into o;
    update pessoa set organizacao = o.id where id = p.id;
    return json_build_object('situacao', 'ligada', 'id', o.id);
  end if;
  if p.organizacao = o.id then
    -- já é minha: quem criou troca o logo e o link enquanto não tem selo
    if o.criada_por = p.id and not o.verificada then
      update organizacao set foto_url = coalesce(l, foto_url), link_oficial = lk where id = o.id;
    end if;
    return json_build_object('situacao', 'ligada', 'id', o.id);
  end if;
  if p.telefone is null then raise exception 'sem_telefone'; end if;
  delete from pedido_organizador where pessoa = p.id and status = 'em análise';
  insert into pedido_organizador (pessoa, organizacao, telefone, como_confirmar)
    values (p.id, o.id, p.telefone, lk);  -- como_confirmar guarda o link oficial informado
  return json_build_object('situacao', 'pedido', 'id', o.id);
end $$;

-- 2. importar_acoes: igual à da migração 03, mas link que não é http(s) vira null (e o contato, organizador_chama),
--    e url de foto ou de logo que não é https vira null (o http da pilha local passa para os testes).
create or replace function importar_acoes(fonte text, itens jsonb, encerrar_faltantes boolean default true)
returns json language plpgsql security definer set search_path = public as $$
#variable_conflict use_column
declare
  it jsonb; org_id bigint; a_id bigint; t_id bigint; nova boolean; link text; foto_url text; logo_url text; aprox boolean;
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
                      foto_url, foto_credito, foto_pagina)
    values (it->>'titulo', (it->>'tipo')::tipo_acao, coalesce(it->>'descricao', ''), sistema, org_id,
            it->>'lugar_nome', it->>'bairro', it->>'cidade', (it->>'lat')::double precision, (it->>'lon')::double precision,
            coalesce((it->>'online')::boolean, false), coalesce((it->>'lugar_aproximado')::boolean, false),
            (case when link is not null then 'divulgacao' else 'organizador_chama' end)::contato_tipo,
            link, 'publicada', importar_acoes.fonte, it->>'fonte_id', now(),
            foto_url, it->'foto'->>'credito', it->'foto'->>'pagina')
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

-- 3. Bloqueio de pessoa pela moderação. Bloquear tira do ar as ações publicadas dela (status 'rascunho', como
--    suspender_acao) e registra. Desbloquear só desmarca a flag: as ações continuam suspensas e o moderador
--    reativa uma a uma (reativar_acao). Ninguém bloqueia a si mesmo nem outro moderador.
create or replace function bloquear_pessoa(pessoa_id uuid, motivo text default null) returns void language plpgsql security definer set search_path = public as $$
declare alvo pessoa; m text := left(nullif(trim(coalesce(motivo, '')), ''), 500);
begin
  if not eh_moderador() then raise exception 'so_moderador'; end if;
  select * into alvo from pessoa where id = pessoa_id for update;
  if not found or alvo.id = auth.uid() or alvo.papel = 'moderador' then raise exception 'nao_pode'; end if;
  update pessoa set bloqueada = true where id = alvo.id;
  update acao set status = 'rascunho', motivo_recusa = m where organizador = alvo.id and status = 'publicada';
  insert into registro_moderacao (moderador, acao_feita, alvo_tipo, alvo_id, motivo)
    values (auth.uid(), 'bloquear', 'pessoa', alvo.id::text, m);
end $$;

create or replace function desbloquear_pessoa(pessoa_id uuid) returns void language plpgsql security definer set search_path = public as $$
begin
  if not eh_moderador() then raise exception 'so_moderador'; end if;
  update pessoa set bloqueada = false where id = pessoa_id and bloqueada;
  if not found then raise exception 'nao_pode'; end if;
  insert into registro_moderacao (moderador, acao_feita, alvo_tipo, alvo_id)
    values (auth.uid(), 'desbloquear', 'pessoa', pessoa_id::text);
end $$;

revoke execute on function bloquear_pessoa(uuid, text), desbloquear_pessoa(uuid) from public, anon;
grant execute on function bloquear_pessoa(uuid, text), desbloquear_pessoa(uuid) to authenticated;

-- 4. Bucket fotos-acoes: no máximo 40 objetos na pasta de cada pessoa. A pessoa passa a enxergar a própria pasta
--    (política de select), senão o subselect da checagem roda sob o RLS de storage.objects e conta zero.
drop policy if exists fotos_acoes_ver_proprio on storage.objects;
create policy fotos_acoes_ver_proprio on storage.objects for select to authenticated
  using (bucket_id = 'fotos-acoes' and (storage.foldername(name))[1] = auth.uid()::text);

drop policy if exists fotos_acoes_envio_proprio on storage.objects;
create policy fotos_acoes_envio_proprio on storage.objects for insert to authenticated
  with check (bucket_id = 'fotos-acoes' and (storage.foldername(name))[1] = auth.uid()::text
    and (select count(*) from storage.objects o
         where o.bucket_id = 'fotos-acoes' and (storage.foldername(o.name))[1] = auth.uid()::text) < 40);
