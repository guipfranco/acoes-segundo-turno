-- Toda ação cadastrada pelo app tem imagem (a arte da divulgação ou uma foto).
-- 1. Bucket público `fotos-acoes`: leitura pública; quem entrou envia só para a própria pasta (<id da pessoa>/...).
--    O app reduz a imagem no celular antes de enviar (JPEG de até 1600 px), por isso o limite de 2 MB.
--    A função previa-instagram (supabase/functions) grava ali a arte puxada do link do post, com a chave de serviço.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('fotos-acoes', 'fotos-acoes', true, 2097152, array['image/jpeg', 'image/webp', 'image/png'])
on conflict (id) do update set public = true, file_size_limit = excluded.file_size_limit, allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists fotos_acoes_envio_proprio on storage.objects;
create policy fotos_acoes_envio_proprio on storage.objects for insert to authenticated
  with check (bucket_id = 'fotos-acoes' and (storage.foldername(name))[1] = auth.uid()::text);

-- 2. criar_acao passa a exigir a imagem (https; vem do bucket acima).
create or replace function criar_acao(dados jsonb) returns json language plpgsql security definer set search_path = public as $$
declare p pessoa; a_id bigint; t jsonb; online boolean; grupo text; foto text; n int; verificada boolean; situacao status_acao;
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

  insert into acao (titulo, tipo, descricao, organizador, organizacao, lugar_nome, bairro, cidade, lat, lon, online,
                    detalhe, contato_tipo, contato_link, foto_url, status)
  values (left(trim(dados->>'titulo'), 140), (dados->>'tipo')::tipo_acao, left(coalesce(dados->>'descricao', ''), 4000), p.id,
          nullif(dados->>'organizacao', '')::bigint,
          case when online then null else left(dados->>'lugar_nome', 200) end,
          case when online then null else left(dados->>'bairro', 120) end,
          case when online then null else left(dados->>'cidade', 120) end,
          case when online then null else (dados->>'lat')::double precision end,
          case when online then null else (dados->>'lon')::double precision end,
          online, left(nullif(trim(coalesce(dados->>'detalhe', '')), ''), 1000),
          case when grupo is null then 'organizador_chama' else 'link_grupo' end::contato_tipo, grupo, foto, situacao)
  returning id into a_id;
  insert into turno (acao, inicio, fim, lotacao)
    select a_id, (x->>'inicio')::timestamp, (x->>'fim')::timestamp, nullif(x->>'lotacao', '')::int
    from jsonb_array_elements(dados->'turnos') x;
  return json_build_object('id', a_id, 'status', situacao);
end $$;
