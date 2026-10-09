# Operação (v1)

- Produção: Supabase projeto `acoes-segundo-turno` (região São Paulo, plano grátis). Front no GitHub Pages
  (`https://guipfranco.github.io/acoes-segundo-turno/`, só a pasta `app/`).
- Migrações: `supabase/migrations/`. Aplicar com `npx supabase db push` depois de `npx supabase link`.
- Moderador: por enquanto, `update pessoa set papel='moderador' where email='...'` no SQL Editor.
- Organizador parceiro: `update pessoa set papel='organizador' where email='...'`.
- Plano grátis pausa após 7 dias sem uso: o ping diário entra na etapa 5.
- Segredos (service_role, senha do banco, segredo do Google) ficam fora do repo. A chave `anon` em
  `app/config.js` é pública por desenho; o que protege os dados é o RLS.

## Modo exemplo

`app/config.js` com `supabase: null`, ou `?modo=exemplo` na URL, usa os dados fictícios em memória
(`app/dados.js` via `app/api-exemplo.js`). Sem `supabase` configurado o app já abre assim. Criar ação,
Minhas ações e Fila de moderação só existem neste modo até a próxima etapa.

## Banco local

Precisa de Docker. Na raiz do repo:

```bash
npx supabase start      # sobe a pilha local (mostra URL e as chaves anon e service_role)
npx supabase db reset   # aplica as migrações e o supabase/seed.sql
```

Particularidades no Windows:

- `[analytics]` está desligado em `supabase/config.toml`: o contêiner `vector` falha no Docker do Windows.
- `npx supabase db reset` aplica migrações e seed, mas pode terminar com código diferente de zero e a
  mensagem `Error status 502`. Se o banco está certo, é só o reinício dos serviços.
- Depois de um reset, se `/auth/v1` responder 502, rode `docker restart supabase_kong_acoes-segundo-turno`.

## Testes

```bash
python -m pytest tests -q            # telas (modo exemplo) e, se as variáveis abaixo existirem, regras do banco
node --test "tests/js/*.test.js"     # camada de dados (api-exemplo e api-supabase)
```

As regras do banco (`tests/test_supabase.py`) só rodam com `SUPABASE_URL`, `SUPABASE_ANON_KEY` e
`SUPABASE_SERVICE_KEY` apontando para a pilha **local** (`npx supabase start`); sem elas são puladas.
Nunca aponte para produção. Exemplo:

```bash
export SUPABASE_URL=http://127.0.0.1:54321 SUPABASE_ANON_KEY=<anon local> SUPABASE_SERVICE_KEY=<service_role local>
python -m pytest tests -q
```

Roteiro de ponta a ponta do "Inscreva-se" (modo exemplo, sem Google): `tests/e2e/vou.spec.mjs`. Precisa do
pacote `playwright` resolvível pelo Node (não está no `package.json`) e de
`python -m http.server 8000 -d app` no ar; rode `node tests/e2e/vou.spec.mjs`.

## Semear a primeira ação e promover pessoas

Depois de entrar uma vez pelo site (isso cria a linha em `pessoa`), no SQL Editor do painel:

```sql
update pessoa set papel = 'organizador', telefone = '(11) 9xxxx-xxxx' where email = 'guilhermepereirafranco@gmail.com';
insert into acao (titulo, tipo, descricao, organizador, lugar_nome, bairro, cidade, lat, lon, detalhe, contato_tipo, status)
select 'Ação de teste', 'panfletagem', 'Só para testar o site.', id, 'Praça da Sé', 'Sé', 'São Paulo', -23.5505, -46.6333, 'Perto da catedral.', 'organizador_chama', 'publicada' from pessoa where email = 'guilhermepereirafranco@gmail.com';
insert into turno (acao, inicio, fim) select id, (hoje_brasilia() + 2)::timestamp + time '10:00', (hoje_brasilia() + 2)::timestamp + time '12:00' from acao where titulo = 'Ação de teste';
```

Sem dado real de terceiros: o organizador é o próprio dono do projeto.

## Importar ações de fontes públicas (agenda Bora Lula e redes)

Migrações `20261009000001_origem_importacao.sql` (pessoa de sistema, campos `fonte`/`fonte_id`/`lugar_aproximado`,
contato `divulgacao`, função `importar_acoes`) e `20261009000002_logo_organizacao.sql` (logo da organização:
`foto_url`/`foto_credito`/`foto_pagina` em `organizacao` e na view pública; `importar_acoes` aceita `organizacao_foto`
e nunca apaga um logo já gravado). Em produção elas ainda precisam ser aplicadas: `python scripts/ir_ao_ar.py migrar`
(pede `SUPABASE_ACCESS_TOKEN` e `SUPABASE_DB_PASSWORD`) ou colar o arquivo no SQL Editor e registrar em
`supabase_migrations.schema_migrations`. Se a senha do banco se perdeu, `python scripts/ir_ao_ar.py senha`
redefine pela Management API e guarda em `.env` na raiz (fora do git); os scripts leem o `.env`.

```bash
python scripts/publicar_acoes.py bora-lula             # baixa o feed e ensaia: resumo + levantamento/publicar-*.json e revisao-*.csv
python scripts/publicar_acoes.py bora-lula --aplicar   # grava (insere, atualiza, encerra o que sumiu do feed)
python scripts/publicar_acoes.py redes --de levantamento/acoes-consolidado-2026-10-08.csv --feed levantamento/bora-lula/<data>.json --aplicar
```

Destino pelas variáveis de ambiente: `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` (REST com a chave de serviço; é o
caminho da pilha local) ou, sem elas, `SUPABASE_ACCESS_TOKEN` + ref em `supabase/.temp/project-ref` (Management API,
produção). Rode o ensaio e leia o `revisao-*.csv` antes do `--aplicar`. Reimportar é seguro: a chave é
(`fonte`, `fonte_id`). Ação recusada por moderador não volta. Para o feed, o plano é rodar 2x por dia.

Tipos de ação: a migração `20261009000010_tipos_acao.sql` troca "roda de conversa" por "encontro" e cria "ato",
"caminhada" e "cultural". Depois de aplicá-la em produção, rode `python scripts/publicar_acoes.py bora-lula --aplicar`
de novo: o importador agora usa o título quando o feed diz "Outro" (no feed de 2026-10-09, "outro" cai de 241 para
11 das 427 ações). O app aceita "roda de conversa" enquanto a migração não chega.

Ponto exato e logo (2026-10-09): o endereço (ou o nome do local) do feed é geocodificado no Nominatim do
OpenStreetMap (1 consulta/s, `User-Agent` do projeto) e só vira ponto exato (`lugar_aproximado = false`) se o
resultado for prédio, número ou via dentro do município; senão fica o centro da cidade, marcado como aproximado.
O cache fica em `levantamento/geocache.json` (fora do git): a primeira rodada leva uns minutos, as seguintes só
consultam endereço novo. `--sem-geocodificar` pula tudo. Organização reconhecível (PT, PSOL, PCdoB, CUT, UNE, MST,
MTST, Levante) ganha o logo do Wikimedia Commons, com crédito, pelo mapa `LOGOS` em `scripts/bora_lula.py`; a
tela mostra o logo como avatar de quem divulga e como capa quando a ação não tem foto própria. Ação do feed sem
organização mostra a marca da Agenda Bora Lula (Comitê Popular) como avatar.
Aplicado em produção em 2026-10-09 (migração + reimportação do feed e das redes); capturas em
`docs/capturas/2026-10-09-acao-logo-ponto-exato.png` e `2026-10-09-vitrine-avatares.png`.

Conferido em 2026-10-09 na pilha local: 222 ações do feed e 57 das redes; capturas em
`docs/capturas/2026-10-09-acao-importada.png` e `2026-10-09-mapa-importadas.png`.

## Estado da produção (2026-10-09)

- Supabase: projeto `acoes-segundo-turno`, ref `ommitzndniqnmsjsjghb`, São Paulo, plano Free. As três
  migrações foram aplicadas pelo SQL Editor, com o histórico gravado em `supabase_migrations.schema_migrations`
  (um `db push` futuro só aplica as novas). A senha do banco foi gerada pelo painel e não foi guardada:
  redefina em Project Settings > Database se precisar do CLI.
- Login: só Google (e-mail desligado). Site URL e Redirect URLs como abaixo. Google Cloud: projeto
  `acoes-segundo-turno`, app "Ações do 2º turno" em Produção, cliente "Cliente Web 1" com origem
  `https://guipfranco.github.io` e callback `https://ommitzndniqnmsjsjghb.supabase.co/auth/v1/callback`.
  Domínios autorizados: `guipfranco.github.io` e `ommitzndniqnmsjsjghb.supabase.co` (o Google recusa `supabase.co`).
- `app/config.js` usa a chave `sb_publishable_...` (pública, equivalente à anon).
- Política de privacidade em `app/privacidade.html`, exigida pelo Google para publicar o login.
- Vaquinha: `configuracao.vaquinha` = `https://doelula.com.br/`.

## O que falta para ir ao ar

Roteiro original; os passos 1 a 3 já foram feitos pelo painel (veja acima). A parte do Supabase sai pelo
`scripts/ir_ao_ar.py` (Management API e CLI); só o Google Cloud é manual. No Git Bash, na raiz do repo:

1. Em https://supabase.com/dashboard, entrar (ou criar a conta) e gerar um token pessoal em
   https://supabase.com/dashboard/account/tokens. Escolher uma senha forte para o banco e guardar no
   gerenciador de senhas.

   ```bash
   export SUPABASE_ACCESS_TOKEN=<token> SUPABASE_DB_PASSWORD='<senha do banco>'
   python scripts/ir_ao_ar.py criar    # projeto acoes-segundo-turno em São Paulo (sa-east-1), org Free
   python scripts/ir_ao_ar.py migrar   # link, db push e confere que as views públicas são só leitura
   python scripts/ir_ao_ar.py auth     # desliga login por e-mail, Site URL e Redirect URLs; mostra a URI de callback
   ```

   Se a conta tiver mais de uma organização, `criar` lista as opções e pede `--org <id>` (use a do plano Free).
2. Google Cloud Console (https://console.cloud.google.com): criar projeto; Tela de permissão OAuth, tipo
   Externo, nome "Ações do 2º turno", e-mail de suporte, domínio autorizado `supabase.co`, escopos só
   `email`, `profile`, `openid`; publicar o app (modo Produção; escopos básicos não pedem verificação).
   Depois, Credenciais > ID do cliente OAuth, tipo Aplicativo da Web: origem JavaScript
   `https://guipfranco.github.io` e a URI de redirecionamento que o passo `auth` mostrou
   (`https://<ref>.supabase.co/auth/v1/callback`). Copiar ID e segredo.
3. Ligar o Google e preencher o app:

   ```bash
   export GOOGLE_CLIENT_ID=<id> GOOGLE_CLIENT_SECRET=<segredo>
   python scripts/ir_ao_ar.py auth     # agora com o Google ligado
   python scripts/ir_ao_ar.py config   # escreve URL e chave anon em app/config.js
   git add app/config.js && git commit -m "Ligar Supabase de produção" && git push
   ```

   O Pages publica sozinho em alguns minutos.
4. Entrar uma vez pelo site com o Google (isso cria a linha em `pessoa`) e semear a primeira ação:

   ```bash
   python scripts/ir_ao_ar.py semear --telefone "(11) 9xxxx-xxxx"
   ```

   Faz o mesmo que o SQL da seção acima, sem repetir a ação se rodar duas vezes.
5. Conferir no site publicado: a ação de teste aparece; Entrar leva ao Google e volta; Inscreva-se pede
   telefone e mostra "vai entrar em contato"; Minhas inscrições lista; desistir some; `?modo=exemplo` abre
   os dados fictícios.

Tudo pelo painel, sem o script, continua valendo: Authentication > Providers (Email desligado, Google com
ID e segredo), Authentication > URL Configuration (Site URL `https://guipfranco.github.io/acoes-segundo-turno/`,
Redirect URLs `https://guipfranco.github.io/acoes-segundo-turno/**` e `http://localhost:8000/**`) e
Settings > API (`Project URL` e `anon public` em `app/config.js`). O token pessoal pode ser revogado depois.
