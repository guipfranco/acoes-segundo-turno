-- Endurecimento: views e tabelas só leitura pela API; escrita só por função.
revoke all on acao_publica, turno_publico, organizacao_publica, configuracao_publica from anon, authenticated;
grant select on acao_publica, turno_publico, organizacao_publica, configuracao_publica to anon, authenticated;
revoke all on pessoa, acao, turno, inscricao from anon, authenticated;
grant select on pessoa, acao, turno, inscricao to anon, authenticated;
-- novas tabelas e views não nascem escrevíveis pela API
alter default privileges in schema public revoke insert, update, delete, truncate, references, trigger on tables from anon, authenticated;
-- funções auxiliares não são API
revoke execute on function combinado_json(acao), pode_ver_combinado(acao), pessoa_json(pessoa), formatar_telefone(text), eh_moderador(), hoje_brasilia() from public, anon, authenticated;
-- eh_moderador() fica executável: as políticas de pessoa, acao e turno rodam com o papel de quem consulta
-- (anon/authenticated) e falham com "permission denied for function eh_moderador" sem este grant.
-- Ela só responde se o próprio usuário é moderador, nada vaza.
grant execute on function eh_moderador() to anon, authenticated;

-- trava o turno durante a inscrição: duas pessoas não passam juntas pela checagem de lotação
create or replace function inscrever(turno_id bigint) returns json language plpgsql security definer set search_path = public as $$
declare p pessoa; t turno; a acao; ativa inscricao;
begin
  if auth.uid() is null then raise exception 'precisa_entrar'; end if;
  select * into p from pessoa where id = auth.uid();
  if p.bloqueada then raise exception 'bloqueada'; end if;
  if p.telefone is null then raise exception 'sem_telefone'; end if;
  select * into t from turno where id = turno_id for update;  -- serializa inscrições concorrentes no mesmo turno
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
