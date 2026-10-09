-- Usuários de exemplo (senha 'senha123' só no banco local). O trigger cria as pessoas.
insert into auth.users (id, instance_id, aud, role, email, encrypted_password, email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
                        confirmation_token, recovery_token, email_change_token_new, email_change, created_at, updated_at)
values
 ('00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000000','authenticated','authenticated','ana@exemplo.local', extensions.crypt('senha123', extensions.gen_salt('bf')), now(), '{"provider":"email","providers":["email"]}', '{"full_name":"Ana Souza"}', '', '', '', '', now(), now()),
 ('00000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000000','authenticated','authenticated','carlos@exemplo.local', extensions.crypt('senha123', extensions.gen_salt('bf')), now(), '{"provider":"email","providers":["email"]}', '{"full_name":"Carlos Lima"}', '', '', '', '', now(), now());
update pessoa set papel='moderador' where id='00000000-0000-0000-0000-000000000001';
update pessoa set papel='organizador', telefone='(11) 91111-1111' where id='00000000-0000-0000-0000-000000000002';
insert into organizacao (nome, tipo, verificada) values ('Mandato Vereadora Rosa','mandato',true), ('Coletivo Periferia Viva','coletivo',false);
insert into acao (titulo, tipo, descricao, organizador, organizacao, lugar_nome, bairro, cidade, lat, lon, detalhe, contato_tipo, contato_link, status)
values ('Panfletagem na estação Grajaú','panfletagem','Vamos distribuir material do Lula na saída da estação.','00000000-0000-0000-0000-000000000002',1,'Estação Grajaú','Grajaú','São Paulo',-23.7746,-46.6978,'Saída principal, perto do ponto de ônibus.','link_grupo','https://chat.whatsapp.com/exemplo','publicada');
insert into turno (acao, inicio, fim, lotacao) values (1, (hoje_brasilia() + 1)::timestamp + time '09:00', (hoje_brasilia() + 1)::timestamp + time '12:00', null);
