-- Esquema da v1. Horários em timestamp sem fuso, sempre hora de Brasília.
create type papel as enum ('participante','organizador','moderador');
create type tipo_org as enum ('mandato','partido','movimento','coletivo');
create type tipo_acao as enum ('panfletagem','adesivaço','roda de conversa','ligatona','porta a porta','bandeiraço','outro');
create type status_acao as enum ('rascunho','em análise','publicada','recusada','encerrada');
create type contato_tipo as enum ('organizador_chama','whatsapp','link_grupo');
create type status_pedido as enum ('em análise','aprovado','recusado');

create table organizacao (
  id bigint generated always as identity primary key,
  nome text not null unique,
  tipo tipo_org not null,
  verificada boolean not null default false,
  criada_em timestamptz not null default now()
);

create table pessoa (
  id uuid primary key references auth.users(id) on delete cascade,
  nome text not null,
  email text,
  telefone text check (telefone is null or telefone ~ '^\(\d{2}\) 9\d{4}-\d{4}$'),
  papel papel not null default 'participante',
  organizacao bigint references organizacao(id),
  bloqueada boolean not null default false,
  criada_em timestamptz not null default now()
);

create table acao (
  id bigint generated always as identity primary key,
  titulo text not null,
  tipo tipo_acao not null,
  descricao text not null default '',
  organizador uuid not null references pessoa(id),
  organizacao bigint references organizacao(id),
  lugar_nome text, bairro text, cidade text,
  lat double precision, lon double precision,
  online boolean not null default false,
  detalhe text,
  contato_tipo contato_tipo not null default 'organizador_chama',
  contato_whatsapp text,
  contato_link text,
  foto_url text, foto_credito text, foto_pagina text,
  prioritaria boolean not null default false,
  status status_acao not null default 'em análise',
  motivo_recusa text,
  criada_em timestamptz not null default now(),
  check (online or (lat is not null and lon is not null and lugar_nome is not null))
);

create table turno (
  id bigint generated always as identity primary key,
  acao bigint not null references acao(id) on delete cascade,
  inicio timestamp not null,
  fim timestamp not null,
  lotacao int check (lotacao is null or lotacao > 0),
  check (fim > inicio)
);
create index turno_acao on turno(acao);

create table inscricao (
  id bigint generated always as identity primary key,
  pessoa uuid not null references pessoa(id) on delete cascade,
  turno bigint not null references turno(id) on delete cascade,
  criada_em timestamptz not null default now(),
  cancelada_em timestamptz,
  presenca boolean,
  unique (pessoa, turno)
);
create index inscricao_turno on inscricao(turno);

create table pedido_organizador (
  id bigint generated always as identity primary key,
  pessoa uuid not null references pessoa(id) on delete cascade,
  organizacao bigint references organizacao(id),
  organizacao_proposta text,
  telefone text not null,
  como_confirmar text not null,
  status status_pedido not null default 'em análise',
  motivo_recusa text,
  decidido_por uuid references pessoa(id),
  decidido_em timestamptz,
  criado_em timestamptz not null default now()
);

create table configuracao (chave text primary key, valor text not null);
insert into configuracao values
  ('vaquinha','https://exemplo.vaquinha.oficial/lula'),
  ('frase','O que você pode fazer hoje para eleger o Lula');

create table registro_moderacao (
  id bigint generated always as identity primary key,
  moderador uuid not null references pessoa(id),
  acao_feita text not null,
  alvo_tipo text not null,
  alvo_id text not null,
  motivo text,
  criado_em timestamptz not null default now()
);

-- helpers (security definer: não disparam RLS, evitam recursão nas políticas de pessoa)
create function hoje_brasilia() returns date language sql stable as
  $$ select (now() at time zone 'America/Sao_Paulo')::date $$;
create function eh_moderador() returns boolean language sql stable security definer set search_path = public as
  $$ select exists (select 1 from pessoa where id = auth.uid() and papel = 'moderador' and not bloqueada) $$;

-- cria a pessoa no primeiro login
create function nova_pessoa() returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into pessoa (id, nome, email) values (
    new.id,
    coalesce(new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'name', split_part(coalesce(new.email,''),'@',1), 'Sem nome'),
    new.email);
  return new;
end $$;
create trigger ao_criar_usuario after insert on auth.users for each row execute function nova_pessoa();

-- views públicas: pertencem ao postgres e por isso ignoram RLS de propósito; só expõem colunas públicas
create view acao_publica as
  select a.id, a.titulo, a.tipo, a.descricao, a.organizador, p.nome as organizador_nome, a.organizacao,
         a.lugar_nome, a.bairro, a.cidade, a.lat, a.lon, a.online,
         a.foto_url, a.foto_credito, a.foto_pagina, a.prioritaria, a.contato_tipo, a.status, a.criada_em
  from acao a join pessoa p on p.id = a.organizador
  where a.status = 'publicada';
create view turno_publico as
  select t.id, t.acao, t.inicio, t.fim, t.lotacao,
         (select count(*) from inscricao i where i.turno = t.id and i.cancelada_em is null)::int as vao
  from turno t join acao a on a.id = t.acao
  where a.status = 'publicada';
create view organizacao_publica as select id, nome, tipo, verificada from organizacao;
create view configuracao_publica as select chave, valor from configuracao;
