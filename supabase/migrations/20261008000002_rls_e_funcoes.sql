-- Correções da revisão da Task 6: formato do telefone no pedido e nome de reserva com e-mail vazio.
alter table pedido_organizador add constraint pedido_telefone_formato check (telefone ~ '^\(\d{2}\) 9\d{4}-\d{4}$');

create or replace function nova_pessoa() returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into pessoa (id, nome, email) values (
    new.id,
    coalesce(nullif(new.raw_user_meta_data->>'full_name',''), nullif(new.raw_user_meta_data->>'name',''),
             nullif(split_part(coalesce(new.email,''),'@',1),''), 'Sem nome'),
    new.email);
  return new;
end $$;

-- RLS em todas as tabelas. Views públicas (Task 6) continuam legíveis por todos.
alter table organizacao enable row level security;
alter table pessoa enable row level security;
alter table acao enable row level security;
alter table turno enable row level security;
alter table inscricao enable row level security;
alter table pedido_organizador enable row level security;
alter table configuracao enable row level security;
alter table registro_moderacao enable row level security;

-- pessoa: cada um lê o seu; moderador lê todos. Escrita só por função.
create policy pessoa_propria on pessoa for select using (id = auth.uid() or eh_moderador());
revoke insert, update, delete on pessoa from anon, authenticated;

-- acao e turno: organizador vê as suas em qualquer status; moderador vê todas. Sem insert/update neste plano.
create policy acao_do_organizador on acao for select using (organizador = auth.uid() or eh_moderador());
create policy turno_do_organizador on turno for select using (
  exists (select 1 from acao a where a.id = turno.acao and (a.organizador = auth.uid() or eh_moderador())));
revoke insert, update, delete on acao, turno from anon, authenticated;

-- inscricao: cada um lê as suas; escrita só por função.
create policy inscricao_propria on inscricao for select using (pessoa = auth.uid());
revoke insert, update, delete on inscricao from anon, authenticated;

-- o resto: nada direto nesta etapa
revoke all on organizacao, pedido_organizador, configuracao, registro_moderacao from anon, authenticated;

-- formata e valida telefone: 11 dígitos nacionais, celular com 9
create function formatar_telefone(t text) returns text language plpgsql immutable as $$
declare d text := regexp_replace(coalesce(t,''), '\D', '', 'g');
begin
  if d !~ '^\d{2}9\d{8}$' then raise exception 'telefone_invalido'; end if;
  return '(' || substr(d,1,2) || ') ' || substr(d,3,5) || '-' || substr(d,8,4);
end $$;

create function pessoa_json(p pessoa) returns json language sql immutable as $$
  select json_build_object('id', p.id, 'nome', p.nome, 'email', p.email, 'telefone', p.telefone, 'papel', p.papel, 'bloqueada', p.bloqueada)
$$;

create function salvar_telefone(telefone text) returns json language plpgsql security definer set search_path = public as $$
declare p pessoa;
begin
  if auth.uid() is null then raise exception 'precisa_entrar'; end if;
  update pessoa set telefone = formatar_telefone(salvar_telefone.telefone) where id = auth.uid() returning * into p;
  return pessoa_json(p);
end $$;

create function combinado_json(a acao) returns json language sql immutable as $$
  select json_build_object('detalhe', a.detalhe, 'contato', json_build_object('tipo', a.contato_tipo, 'whatsapp', a.contato_whatsapp, 'link', a.contato_link))
$$;

-- quem pode ver detalhe e contato: organizador, moderador, ou inscrito ativo numa ação publicada
create function pode_ver_combinado(a acao) returns boolean language sql stable security definer set search_path = public as $$
  select a.organizador = auth.uid() or eh_moderador() or (a.status = 'publicada' and exists (
    select 1 from inscricao i join turno t on t.id = i.turno
    where t.acao = a.id and i.pessoa = auth.uid() and i.cancelada_em is null))
$$;

create function acao_para_mim(acao_id bigint) returns json language plpgsql stable security definer set search_path = public as $$
declare a acao;
begin
  select * into a from acao where id = acao_id;
  if not found then return null; end if;
  return json_build_object(
    'inscrita', coalesce((select json_agg(t.id order by t.inicio) from turno t join inscricao i on i.turno = t.id
                          where t.acao = a.id and i.pessoa = auth.uid() and i.cancelada_em is null), '[]'::json),
    'combinado', case when pode_ver_combinado(a) then combinado_json(a) else null end);
end $$;

create function inscrever(turno_id bigint) returns json language plpgsql security definer set search_path = public as $$
declare p pessoa; t turno; a acao; ativa inscricao;
begin
  if auth.uid() is null then raise exception 'precisa_entrar'; end if;
  select * into p from pessoa where id = auth.uid();
  if p.bloqueada then raise exception 'bloqueada'; end if;
  if p.telefone is null then raise exception 'sem_telefone'; end if;
  select * into t from turno where id = turno_id;
  if not found then raise exception 'nao_publicada'; end if;
  select * into a from acao where id = t.acao;
  if a.status <> 'publicada' then raise exception 'nao_publicada'; end if;
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

create function desistir(turno_id bigint) returns void language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then raise exception 'precisa_entrar'; end if;
  update inscricao set cancelada_em = now() where pessoa = auth.uid() and turno = turno_id and cancelada_em is null;
end $$;

create function minhas_inscricoes() returns json language sql stable security definer set search_path = public as $$
  select coalesce(json_agg(json_build_object(
    'turno', json_build_object('id', t.id, 'acao', t.acao, 'inicio', t.inicio, 'fim', t.fim, 'lotacao', t.lotacao,
             'vao', (select count(*) from inscricao x where x.turno = t.id and x.cancelada_em is null)),
    'acao', json_build_object('id', a.id, 'titulo', a.titulo, 'tipo', a.tipo, 'descricao', a.descricao, 'organizador', a.organizador,
             'organizador_nome', (select nome from pessoa where id = a.organizador), 'organizacao', a.organizacao,
             'lugar_nome', a.lugar_nome, 'bairro', a.bairro, 'cidade', a.cidade, 'lat', a.lat, 'lon', a.lon, 'online', a.online,
             'foto_url', a.foto_url, 'foto_credito', a.foto_credito, 'foto_pagina', a.foto_pagina, 'prioritaria', a.prioritaria,
             'contato_tipo', a.contato_tipo, 'status', a.status, 'criada_em', a.criada_em)
  ) order by t.inicio), '[]'::json)
  from inscricao i join turno t on t.id = i.turno join acao a on a.id = t.acao
  where i.pessoa = auth.uid() and i.cancelada_em is null
$$;

-- anon não chama o que exige sessão (a função também checa). `inscrever` e `acao_para_mim` ficam
-- executáveis por anon de propósito: a primeira devolve 'precisa_entrar', a segunda devolve inscrita vazia.
-- O revoke inclui public porque o Postgres dá execute a public por padrão; authenticated tem grant próprio.
revoke execute on function salvar_telefone(text), desistir(bigint), minhas_inscricoes() from public, anon;
