-- Moderação além de aprovar e recusar: suspender (tira do ar, dá para reativar), reativar e excluir.
-- E a página de uma ação que não está publicada, para quem a criou e para moderador (a view pública só tem
-- as publicadas, e por isso a fila abria uma página vazia).
-- Suspensa usa o status 'rascunho' (o app mostra "Suspensa"). Reimportar não reativa: importar_acoes só mexe
-- no status de quem estava 'encerrada'.

-- Ação em qualquer status, para quem criou ou modera; para os outros, null.
create or replace function acao_restrita(acao_id bigint) returns json language plpgsql stable security definer set search_path = public as $$
declare a acao;
begin
  select * into a from acao where id = acao_id;
  if not found or auth.uid() is null or not (a.organizador = auth.uid() or eh_moderador()) then return null; end if;
  return json_build_object('acao', acao_completa_json(a),
    'turnos', coalesce((select json_agg(json_build_object('id', t.id, 'acao', t.acao, 'inicio', t.inicio, 'fim', t.fim, 'lotacao', t.lotacao,
      'vao', (select count(*) from inscricao i where i.turno = t.id and i.cancelada_em is null)) order by t.inicio)
      from turno t where t.acao = a.id), '[]'::json));
end $$;

create or replace function suspender_acao(acao_id bigint, motivo text default null) returns void language plpgsql security definer set search_path = public as $$
begin
  if not eh_moderador() then raise exception 'so_moderador'; end if;
  update acao set status = 'rascunho', motivo_recusa = left(nullif(trim(coalesce(motivo, '')), ''), 500)
   where id = acao_id and status in ('em análise', 'publicada');
  if not found then raise exception 'nao_pode'; end if;
  insert into registro_moderacao (moderador, acao_feita, alvo_tipo, alvo_id, motivo)
  values (auth.uid(), 'suspender', 'acao', acao_id::text, nullif(trim(coalesce(motivo, '')), ''));
end $$;

create or replace function reativar_acao(acao_id bigint) returns void language plpgsql security definer set search_path = public as $$
begin
  if not eh_moderador() then raise exception 'so_moderador'; end if;
  update acao set status = 'publicada', motivo_recusa = null where id = acao_id and status = 'rascunho';
  if not found then raise exception 'nao_pode'; end if;
  insert into registro_moderacao (moderador, acao_feita, alvo_tipo, alvo_id) values (auth.uid(), 'reativar', 'acao', acao_id::text);
end $$;

-- Apaga a ação, os turnos e as inscrições. Ação importada não se exclui (a próxima importação traria de volta):
-- suspende. O registro guarda o título, já que a ação some.
create or replace function excluir_acao(acao_id bigint) returns void language plpgsql security definer set search_path = public as $$
declare a acao;
begin
  if not eh_moderador() then raise exception 'so_moderador'; end if;
  select * into a from acao where id = acao_id;
  if not found then raise exception 'nao_pode'; end if;
  if a.fonte is not null then raise exception 'importada'; end if;
  delete from acao where id = acao_id;
  insert into registro_moderacao (moderador, acao_feita, alvo_tipo, alvo_id, motivo) values (auth.uid(), 'excluir', 'acao', acao_id::text, a.titulo);
end $$;

revoke execute on function acao_restrita(bigint), suspender_acao(bigint, text), reativar_acao(bigint), excluir_acao(bigint) from public, anon;
grant execute on function acao_restrita(bigint), suspender_acao(bigint, text), reativar_acao(bigint), excluir_acao(bigint) to authenticated;
