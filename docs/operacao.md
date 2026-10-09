# Operação (v1)

- Produção: Supabase projeto `acoes-segundo-turno` (região São Paulo, plano grátis). Front no GitHub Pages
  (`https://guipfranco.github.io/acoes-segundo-turno/`: a pasta `app/` da master na raiz, mais `publico.json` e
  `fotos/`; cada outra branch em `/previa/<branch>/`, montado por `scripts/montar_pages.sh`). Veja "Lista e fotos
  pelo GitHub Pages".
- Migrações: `supabase/migrations/`. Aplicar com `npx supabase db push` depois de `npx supabase link`.
- Moderador: por enquanto, `update pessoa set papel='moderador' where email='...'` no SQL Editor. Bloquear e
  desbloquear pessoa já é botão na Fila ("Bloquear organizador", migração 20261009000051); veja "Incidentes e abuso".
- Organizador parceiro: `update pessoa set papel='organizador' where email='...'`.
- Plano grátis pausa após 7 dias sem uso: o ping diário entra na etapa 5.
- Capa de compartilhamento (WhatsApp, redes): `app/capa.png` (1200x630) e `app/favicon.png`, geradas por `scripts/gerar_capa.py`; as metatags ficam no `<head>` de `app/index.html`.
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
Nas redes, o `fonte_id` vem só da própria linha (link, início, cidade e título; desde 2026-10-09): corrigir título
ou hora no consolidado troca o id, e a ação antiga é encerrada. Por isso o `--aplicar` consulta antes as ações com
"Eu vou" em turno de hoje em diante e para sem gravar nada se fosse encerrar alguma; `--forcar` encerra assim mesmo
(quem marcou perde a presença). Card com várias ações no mesmo post vira uma ação por linha.

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
Imagem da divulgação (2026-10-09): `scripts/fotos_divulgacao.py` põe a imagem do post do Instagram como foto da
ação. A imagem vem da prévia de link do post (og:image e og:url), que o Instagram entrega sem login a robôs de
prévia, como a do WhatsApp: nada de conta logada. `pendentes` lista os códigos sem foto; `coletar` lê a prévia de
cada um (uma a cada 3 s, para no primeiro 429), baixa, reduz para 720 px e sobe no bucket público `divulgacao` (2026-10-09 em produção: 194 imagens, 264 das 406 ações publicadas com foto; captura em
`docs/capturas/2026-10-09-vitrine-fotos-divulgacao.png`) (migração `20261009000003_foto_divulgacao.sql`), anotando em
`levantamento/fotos-divulgacao.json`; o `publicar_acoes.py --aplicar` já chama essa busca para os posts sem foto
antes de gravar (desde 2026-10-09; `--sem-fotos` pula), então não há passo separado na rotina. O crédito
leva o @ do perfil só quando a ação tem organização pública; senão fica "Divulgação original no Instagram".
Aplicado em produção em 2026-10-09 (migração + reimportação do feed e das redes); capturas em
`docs/capturas/2026-10-09-acao-logo-ponto-exato.png` e `2026-10-09-vitrine-avatares.png`.
Arte inteira (2026-10-09, branch cards-verticais): o og:image vem recortado em quadrado de 640 px com zoom e corta o
texto dos cartazes. Agora a imagem sai da página de embed do post (`/p/<código>/embed/captioned/`, mesmo robô de
prévia): a maior versão sem recorte (`stp` sem `c...`) de até 1080 px, quase sempre 4:5 (vídeo dá a capa 9:16). O
og:image só fica como plano B. O mapa anota `"inteira": true`. Para trocar as já publicadas: `python
scripts/fotos_divulgacao.py refazer [--max N]` (pasta principal, com `SUPABASE_ACCESS_TOKEN`): sobe como
`<código>-inteira.jpg` (nome novo, para escapar do cache de uma semana) e aponta as ações (`acao.foto_url`) para a
nova. A função `previa-instagram` faz o mesmo caminho para o cadastro pelo app (precisa de `supabase functions deploy
previa-instagram`). O card da vitrine passou a 4:5 com a arte inteira e a sobra preenchida pela própria imagem
desfocada; a capa da página da ação mostra a imagem na proporção dela.

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
- Em 2026-10-09 (tarde): migrações 20261009000020 (Eu vou na divulgação), 21 (cadastro de ação e moderação) e 22
  (bucket `fotos-acoes`, imagem obrigatória) aplicadas com `python scripts/ir_ao_ar.py migrar`; função
  `previa-instagram` publicada com `npx supabase functions deploy previa-instagram --project-ref ommitzndniqnmsjsjghb`
  (token do `.env`); o dono passou a `moderador`.
- Em 2026-10-09 (fim da tarde): migrações 20261009000023 (organização própria, link do perfil oficial e do post da
  organização anunciando a ação) e 20261009000030 (suspender, reativar e excluir ação) aplicadas com `ir_ao_ar.py migrar`.
- Em 2026-10-09 (noite): merge da branch `ajustes-feedback-1009` e migração 20261009000040 (canceladas visíveis,
  `acao.publicada_em`, desistências no histórico) aplicada com `ir_ao_ar.py migrar` (conferida com
  `npx supabase migration list --linked`).
- Em 2026-10-09 (noite): merge da branch `cards-verticais` (card 4:5 com a arte inteira); `refazer` trocou 224
  imagens recortadas pela arte inteira do embed (343 das 356 ações com foto de divulgação; ficaram 3 vídeos que não
  deixam incorporar: DeMS8kWi0jE, DePGosYRM0X, DePeocbkbRR); `previa-instagram` republicada com o embed.
- Pendente (branch `feedback-1009`, depois do merge): aplicar a migração 20261009000050 (`turno.hora_aproximada`,
  `turno_publico` com a coluna nova, `importar_acoes` que a grava; tabela `feedback` e funções `enviar_feedback`,
  `feedbacks`, `tratar_feedback`) com `python scripts/ir_ao_ar.py migrar`, e em seguida reimportar as redes
  (`python scripts/publicar_acoes.py redes --de levantamento/acoes-consolidado-2026-10-08.csv --feed levantamento/bora-lula/<data>.json --aplicar`)
  para que as linhas sem hora (ex.: "Noite - Giro nos Bares", que estava como 9h às 11h) passem a "à noite" com
  `hora_aproximada`. A hora muda o `fonte_id` dessas linhas: a ação antiga é encerrada e nasce outra, pela regra de sempre.
  As mensagens do "Fale com a gente" chegam na aba Mensagens da Fila (`#/fila`, só moderador).

## Lista e fotos pelo GitHub Pages

Quem só olha o site não bate no Supabase: a vitrine (inicial e mapa) lê `publico.json`, que o workflow
"Publicar app no GitHub Pages" (`.github/workflows/pages.yml`) gera com `scripts/snapshot_publico.py` de hora em
hora (cron `7 * * * *`) e a cada push que toque `app/` ou `fotos/`. O script baixa as views públicas
(`configuracao_publica`, `organizacao_publica`, `acao_publica`, `turno_publico` com `inicio >= hoje` em Brasília)
pela REST com a chave anon, paginando de 1000 em 1000, e grava as linhas cruas com `geradoEm`. Plano B em
`app/api-supabase.js` (`publico()`): se o arquivo não existir (prévia por branch), falhar ou tiver mais de 3 h,
lê direto do Supabase como antes; `window.API.origemPublico` diz qual dos dois valeu (`snapshot` ou `supabase`).
Página da ação, login, "Eu vou!", Perfil, cadastro e Fila continuam ao vivo. Consequência: uma ação aprovada na
Fila (ou importada) aparece na vitrine em até 1 h; para adiantar, Actions > "Publicar app no GitHub Pages" >
Run workflow. Se o snapshot falhar, o deploy segue sem o arquivo (`continue-on-error`) e o app cai no plano B.
As fotos das ações importadas moram em `fotos/divulgacao/` na raiz do repo e `montar_pages.sh` copia a pasta da
master para a raiz do site (as prévias não a recebem).

Rotina de importação com fotos (pasta principal, na `master`, com `SUPABASE_ACCESS_TOKEN`):

1. `python scripts/publicar_acoes.py bora-lula --aplicar`: busca a arte dos posts novos, grava
   `fotos/divulgacao/<código>.jpg` e `<código>-mini.jpg`, escreve o ensaio e, se houver foto nova, PARA sem gravar no
   banco ("fotos novas em fotos/divulgacao ainda não foram commitadas e enviadas para a master").
2. `git add fotos && git commit -m "Fotos: ..." && git push` e esperar o workflow do Pages terminar.
3. Rodar o mesmo comando de novo: sem pendência, grava no banco com as URLs do Pages (`--sem-fotos` pula a busca e a trava).

Acervo antigo (uma vez, depois da migração 20261009000060 em produção): `python scripts/fotos_divulgacao.py migrar-pages`
(ensaio: baixa cada foto do bucket `divulgacao`, gera os dois arquivos, não mexe no banco) -> commit + push de `fotos/` ->
esperar o Pages -> `python scripts/fotos_divulgacao.py migrar-pages --aplicar` (troca `foto_url` e grava `foto_mini_url`).
Depois disso o bucket `divulgacao` pode ser esvaziado.

## Incidentes e abuso

Curto e prático. Tudo pela Fila (`#/fila`, só moderador) quando dá; SQL Editor e painel do Supabase como reserva.

- **Bloquear pessoa** (spam, dado falso, ataque): na Fila, abra a ação e use "Bloquear organizador" (migração
  20261009000050, funções `bloquear_pessoa` / `desbloquear_pessoa`): a pessoa não cria ação nem marca "Eu vou", e as
  ações dela saem do ar. Reserva no SQL Editor:
  ```sql
  select id, nome, email from pessoa where email = 'fulano@exemplo.com';   -- acha o uuid pelo e-mail
  select bloquear_pessoa('<uuid>', 'motivo curto');
  select desbloquear_pessoa('<uuid>');
  ```
- **Tirar ação do ar**: na Fila, "Suspender" (volta com "Reativar") ou "Excluir" (migração 20261009000030). A imagem
  continua no bucket público `fotos-acoes` até alguém apagar: pelo painel (Storage > fotos-acoes > pasta `<uuid da
  pessoa>` > arquivo > Delete) ou, para tudo o que ficou sem dono há mais de 24 h (cadastro abandonado, ação recusada
  ou excluída), `python scripts/limpar_fotos.py` (ensaio, só lista) e `python scripts/limpar_fotos.py --aplicar`
  (pasta principal, com `SUPABASE_ACCESS_TOKEN`; `--horas N` muda a margem). Rodar uma vez por dia enquanto o site
  estiver no ar.
- **Pedido de remoção de arte de terceiros** (dono da foto ou do cartaz pede para tirar): excluir a ação na Fila e
  apagar a imagem do bucket no mesmo dia; responder a quem pediu dizendo que saiu.
- **Segundo moderador**: o comando é o do topo deste arquivo (`update pessoa set papel='moderador' where email='...'`);
  a pessoa precisa ter entrado uma vez pelo site antes. Para tirar: `papel='apoiador'`.
- **Links e fotos vindos de fora**: a importação (`bora_lula.py`, `publicar_acoes.py`, inclusive a rota `redes`) descarta
  link que não comece com `http://` ou `https://` (o contato vira `organizador_chama`) e url de imagem que não seja
  `https://`; o aviso sai no resumo e na `revisao-*.csv` com o prefixo `aviso:`. O banco também recusa.
- **Uso do plano Free**: painel em
  https://supabase.com/dashboard/project/ommitzndniqnmsjsjghb/settings/billing/usage. Olhar egress (saída de dados:
  fotos do bucket e respostas da API, é o que mais cresce com visita), storage e MAU. Limites do Free consultados em
  2026-10-09 em https://supabase.com/pricing e nos guias de uso (docs/guides/platform/manage-your-usage/egress e
  database-size): 5 GB de egress por mês (+ 5 GB de egress em cache), 1 GB de arquivos no Storage, 500 MB de banco,
  50.000 MAU, 500.000 invocações de edge function, 2 projetos ativos, pausa após 7 dias sem uso. Ao estourar: egress e
  storage acima da cota geram aviso por e-mail e um período de carência; se continuar, a organização entra em
  restrição (Fair Use) que só sai no ciclo seguinte ou ao subir de plano; banco acima de 500 MB entra em modo só
  leitura na hora. Saída: Pro por US$ 25/mês (spend cap ligado por padrão). Aliviar antes: fotos já saem reduzidas
  (720 px na importação, até 1600 px no cadastro) com `Cache-Control` de uma semana; `limpar_fotos.py` segura o storage.
- **Lei eleitoral** (Lei 9.504/97, art. 57-B e 57-D): propaganda na internet feita por pessoa natural é permitida,
  sem impulsionamento pago e sem anonimato. Por isso o rodapé do site leva o nome de quem responde pela página, e
  nunca se paga impulsionamento (anúncio, post patrocinado, "turbinar") para o site nem para ação cadastrada nele.
  Ação importada mostra sempre a fonte e o link da divulgação original.

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
