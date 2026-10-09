-- Organização de quem usa o app (coletivo, comitê, mandato, partido, movimento).
-- No Perfil, a pessoa cadastra a sua: nome, tipo e logo. Nome novo cria a organização (sem selo) e já liga a
-- pessoa a ela; nome que já existe vira pedido para a moderação (senão qualquer um entraria numa organização
-- verificada e publicaria sem análise). O selo da organização (verificada) é dado por moderador; quem é de
-- organização verificada publica direto (regra de criar_acao, migração 20261009000021).
-- No cadastro da ação, "Quem organiza?": eu mesmo(a), a minha organização ou outra, escrita à mão.
-- Verificação: toda organização cadastrada (ou escrita à mão numa ação) vem com o link de um perfil oficial
-- (Instagram, Facebook, site). A moderação confere por ele antes de dar o selo ou aprovar a ação.

alter table organizacao add column if not exists criada_por uuid references pessoa(id);
alter table organizacao add column if not exists link_oficial text;
alter table acao add column if not exists organizacao_link text;  -- link oficial informado junto com a ação

-- link de perfil oficial: http(s), com domínio
create or replace function link_oficial_valido(l text) returns boolean language sql immutable as $$
  select coalesce(l, '') ~* '^https?://[a-z0-9.-]+\.[a-z]{2,}(/\S*)?$' and length(l) <= 300
$$;
create unique index if not exists organizacao_nome_sem_caixa on organizacao (lower(trim(nome)));

-- Acha a organização pelo nome (sem diferença de maiúsculas e espaços nas pontas).
create or replace function organizacao_por_nome(nome text) returns organizacao language sql stable security definer set search_path = public as $$
  select * from organizacao o where lower(trim(o.nome)) = lower(trim(organizacao_por_nome.nome)) limit 1
$$;

-- Minha organização e o pedido em análise, se houver.
create or replace function minha_organizacao() returns json language sql stable security definer set search_path = public as $$
  select json_build_object(
    'organizacao', (select json_build_object('id', o.id, 'nome', o.nome, 'tipo', o.tipo, 'verificada', o.verificada,
                     'foto_url', o.foto_url, 'link_oficial', o.link_oficial, 'minha', o.criada_por = p.id)
                    from organizacao o where o.id = p.organizacao),
    'pedido', (select json_build_object('id', d.id, 'nome', coalesce(o.nome, d.organizacao_proposta), 'status', d.status, 'motivo', d.motivo_recusa)
               from pedido_organizador d left join organizacao o on o.id = d.organizacao
               where d.pessoa = p.id order by d.criado_em desc limit 1))
  from pessoa p where p.id = auth.uid()
$$;

-- Cadastra (ou pede para entrar em) uma organização. Devolve {situacao: 'ligada' | 'pedido'}.
create or replace function salvar_organizacao(nome text, tipo text, logo text default null, link text default null) returns json language plpgsql security definer set search_path = public as $$
declare p pessoa; o organizacao; n text := trim(coalesce(nome, '')); l text := nullif(trim(coalesce(logo, '')), ''); lk text := trim(coalesce(link, ''));
begin
  if auth.uid() is null then raise exception 'precisa_entrar'; end if;
  select * into p from pessoa where id = auth.uid();
  if p.bloqueada then raise exception 'bloqueada'; end if;
  if length(n) < 3 or length(n) > 80 then raise exception 'nome_organizacao'; end if;
  if l is not null and l !~ '^(https://|http://(127\.0\.0\.1|localhost)[:/])' then l := null; end if;
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

-- Sair da organização (desfaz o vínculo; a organização continua).
create or replace function sair_da_organizacao() returns void language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then raise exception 'precisa_entrar'; end if;
  update pessoa set organizacao = null where id = auth.uid();
  delete from pedido_organizador where pessoa = auth.uid() and status = 'em análise';
end $$;

-- Moderação: pedidos de entrada em organização já existente e organizações sem selo.
create or replace function fila_organizacoes() returns json language plpgsql stable security definer set search_path = public as $$
begin
  if not eh_moderador() then raise exception 'so_moderador'; end if;
  return json_build_object(
    'pedidos', (select coalesce(json_agg(json_build_object('id', d.id, 'organizacao', o.nome, 'verificada', o.verificada,
                  'pessoa', q.nome, 'email', q.email, 'telefone', d.telefone, 'link', d.como_confirmar,
                  'link_oficial', o.link_oficial, 'criado_em', d.criado_em) order by d.criado_em), '[]'::json)
                from pedido_organizador d join organizacao o on o.id = d.organizacao join pessoa q on q.id = d.pessoa
                where d.status = 'em análise'),
    'sem_selo', (select coalesce(json_agg(json_build_object('id', o.id, 'nome', o.nome, 'tipo', o.tipo, 'foto_url', o.foto_url, 'link_oficial', o.link_oficial,
                  'criada_por', q.nome, 'email', q.email, 'telefone', q.telefone,
                  'membros', (select count(*) from pessoa m where m.organizacao = o.id),
                  'acoes', (select count(*) from acao a where a.organizacao = o.id)) order by o.criada_em desc), '[]'::json)
                 from organizacao o left join pessoa q on q.id = o.criada_por
                 where not o.verificada and o.criada_por is not null));
end $$;

create or replace function decidir_pedido_organizacao(pedido_id bigint, aprovar boolean, motivo text default null) returns void language plpgsql security definer set search_path = public as $$
declare d pedido_organizador;
begin
  if not eh_moderador() then raise exception 'so_moderador'; end if;
  select * into d from pedido_organizador where id = pedido_id and status = 'em análise' for update;
  if not found then raise exception 'nao_pode'; end if;
  if not aprovar and coalesce(trim(motivo), '') = '' then raise exception 'sem_motivo'; end if;
  update pedido_organizador set status = case when aprovar then 'aprovado' else 'recusado' end::status_pedido,
    motivo_recusa = case when aprovar then null else trim(motivo) end, decidido_por = auth.uid(), decidido_em = now()
   where id = pedido_id;
  if aprovar then update pessoa set organizacao = d.organizacao where id = d.pessoa; end if;
  insert into registro_moderacao (moderador, acao_feita, alvo_tipo, alvo_id, motivo)
    values (auth.uid(), case when aprovar then 'aprovar_pedido' else 'recusar_pedido' end, 'pedido_organizador', pedido_id::text, motivo);
end $$;

create or replace function dar_selo_organizacao(organizacao_id bigint) returns void language plpgsql security definer set search_path = public as $$
begin
  if not eh_moderador() then raise exception 'so_moderador'; end if;
  update organizacao set verificada = true where id = organizacao_id;
  if not found then raise exception 'nao_pode'; end if;
  insert into registro_moderacao (moderador, acao_feita, alvo_tipo, alvo_id) values (auth.uid(), 'dar_selo', 'organizacao', organizacao_id::text);
end $$;

-- criar_acao: "Quem organiza?" passa a valer assim:
--   organizacao (id) só é aceita se for a organização da própria pessoa;
--   organizacao_nome (texto) liga a ação a uma organização com esse nome, criada sem selo se ainda não existe.
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
  -- https em produção; o http da pilha local (127.0.0.1) passa para os testes
  if foto is null or foto !~ '^(https://|http://(127\.0\.0\.1|localhost)[:/])' then raise exception 'sem_foto'; end if;
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
  if nullif(dados->>'organizacao', '')::bigint is not null and nullif(dados->>'organizacao', '')::bigint = p.organizacao then
    org_id := p.organizacao;
  elsif org_nome is not null then
    if length(org_nome) < 3 or length(org_nome) > 80 then raise exception 'nome_organizacao'; end if;
    org_link := trim(coalesce(dados->>'organizacao_link', ''));
    if not link_oficial_valido(org_link) then raise exception 'link_oficial'; end if;
    achada := organizacao_por_nome(org_nome);
    if achada.id is null then
      insert into organizacao (nome, tipo, criada_por, link_oficial) values (org_nome, 'coletivo', p.id, org_link) returning id into org_id;
    else
      org_id := achada.id;
    end if;
  end if;

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

-- ação completa (Minhas ações e Fila) passa a trazer a organização: nome, selo e os links para conferir
create or replace function acao_completa_json(a acao) returns json language sql stable security definer set search_path = public as $$
  select json_build_object('id', a.id, 'titulo', a.titulo, 'tipo', a.tipo, 'descricao', a.descricao, 'organizador', a.organizador,
    'organizador_nome', (select nome from pessoa where id = a.organizador), 'organizacao', a.organizacao,
    'lugar_nome', a.lugar_nome, 'bairro', a.bairro, 'cidade', a.cidade, 'lat', a.lat, 'lon', a.lon, 'online', a.online,
    'foto_url', a.foto_url, 'foto_credito', a.foto_credito, 'foto_pagina', a.foto_pagina, 'prioritaria', a.prioritaria,
    'contato_tipo', a.contato_tipo, 'status', a.status, 'criada_em', a.criada_em, 'fonte', a.fonte,
    'lugar_aproximado', a.lugar_aproximado, 'motivo_recusa', a.motivo_recusa, 'detalhe', a.detalhe, 'contato_link', a.contato_link,
    'link_divulgacao', case when a.contato_tipo::text = 'divulgacao' then a.contato_link end,
    'organizacao_link', a.organizacao_link,
    'organizacao_dados', (select json_build_object('nome', o.nome, 'verificada', o.verificada, 'link_oficial', o.link_oficial)
                          from organizacao o where o.id = a.organizacao))
$$;
revoke execute on function acao_completa_json(acao) from public, anon, authenticated;

revoke execute on function organizacao_por_nome(text) from public, anon, authenticated;
revoke execute on function minha_organizacao(), salvar_organizacao(text, text, text, text), sair_da_organizacao(), fila_organizacoes(),
  decidir_pedido_organizacao(bigint, boolean, text), dar_selo_organizacao(bigint) from public, anon;
grant execute on function minha_organizacao(), salvar_organizacao(text, text, text, text), sair_da_organizacao(), fila_organizacoes(),
  decidir_pedido_organizacao(bigint, boolean, text), dar_selo_organizacao(bigint) to authenticated;
