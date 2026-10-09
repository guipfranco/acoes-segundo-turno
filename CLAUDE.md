# CLAUDE.md

Repo da plataforma de ações do 2º turno (voto do Lula). Nasceu do `mapa-segundo-turno` em 2026-10-08.

- Tudo em pt-BR, datas AAAA-MM-DD. Push logo depois de cada commit.
- `app/` (antes `mockup/`) é o app: estático, sem build. Publicado em https://guipfranco.github.io/acoes-segundo-turno/
  (GitHub Pages via `.github/workflows/pages.yml`, só a pasta `app/`; repo público desde 2026-10-08) e também
  como artifact do claude.ai https://claude.ai/artifact/5FLiCyZHCJD6ADZbofmrjL ; o mapa base no artifact é o
  Protomaps da RMSP copiado dos assets do artifact do mapa principal (ids em app/fundo.js); fora dele o
  app usa tiles do OpenStreetMap.
- Camada de dados em `app/api.js` (escolhe `api-exemplo.js`, dados fictícios em memória, ou `api-supabase.js`,
  Supabase com login Google, conforme `app/config.js`; `?modo=exemplo` força o exemplo). Regras sensíveis são
  funções SQL em `supabase/migrations/`. Nunca commitar service_role, senha do banco nem segredo do Google
  (a chave anon é pública). Operação e banco local em `docs/operacao.md`.
- Testes: `python -m pytest tests -q` (telas; `tests/test_supabase.py` só roda com `SUPABASE_URL`,
  `SUPABASE_ANON_KEY` e `SUPABASE_SERVICE_KEY` da pilha local) e `node --test "tests/js/*.test.js"`.
  Roteiro e2e do Inscreva-se em `tests/e2e/vou.spec.mjs` (precisa de `playwright`, fora do package.json).
- Sem dado pessoal real no repo (nome, telefone, e-mail, link de grupo de pessoa comum). Desde 2026-10-09 o Gui
  liberou dados reais de AÇÕES PÚBLICAS e de ORGANIZAÇÕES públicas (partidos, mandatos, movimentos, comitês) nos
  dados versionados e em produção, sempre com crédito à fonte (hoje: agenda Bora Lula do Comitê Popular). Pessoas
  de exemplo continuam inventadas; ação importada tem como organizador uma pessoa de sistema, nunca pessoa real.
  A pasta `levantamento/` segue fora do git deste repo porque guarda a varredura bruta com nomes e telefones.
  Desde 2026-10-09 ela é um repo próprio, PRIVADO: https://github.com/guipfranco/acoes-levantamento (clonar dentro
  de `levantamento/`; commit e push lá depois de cada rodada; nunca tornar público nem copiar para cá).
- Estado em 2026-10-08: app navegável (modo exemplo completo; Supabase + login Google na v1 etapas 1-2).
- Produção ligada em 2026-10-09: Supabase ref `ommitzndniqnmsjsjghb` e login Google; estado em `docs/operacao.md`.
- Telas: inicial sem mapa (estilo Meetup): busca por cidade que chuta a cidade pela geolocalização, filtro
  "Quando" (em breve, hoje, amanhã, esta semana, fim de semana, próxima semana, escolher datas), sem filtro de
  formato (só o link "Prefiro ajudar online"), vitrine por cidade (SP, Recife, BH, Porto Alegre, Salvador) com
  foto por ação e bloco "Online"; a cidade de "Perto de você" é um botão que abre a busca de cidade. Filtros da
  inicial e do mapa são separados e não passam de uma tela para a outra. Mapa com lista que acompanha o
  enquadramento em `#/mapa`; clicar no pino abre prévia da ação e marca o card na lista. Turno futuro tem
  "Adicionar à agenda" (Google Agenda e arquivo .ics). Tipos de ação (desde 2026-10-09): panfletagem, encontro, ato,
  caminhada, cultural, bandeiraço, adesivaço, porta a porta, ligatona, outro. Ação online: `lugar.online: true`, sem
  pino nem minimapa. Desktop (≥ 900 px) com cabeçalho no topo e página da ação em duas colunas. Fotos das ações
  vêm do Wikimedia Commons (campo `foto` com crédito).
- Conta e criação (branch `eu-vou-perfil`, 2026-10-09): logado, o botão da conta vira "Perfil" (`#/perfil`: WhatsApp,
  resumo do "Eu vou", ações que criei com situação e motivo da recusa, Sair no fim); deslogado, "Entrar" escuro e
  convite na inicial. "Eu vou!" em toda ação; na de divulgação (importada) só marca presença, sem telefone (migração
  20261009000020). Qualquer pessoa logada cria ação: nasce "em análise", exceto verificado (papel organizador ou
  moderador, ou membro de organização verificada), que publica direto; limite de 10 por dia e 10 em análise
  (migração 20261009000021: `criar_acao`, `minhas_acoes`, `encerrar_acao`, `fila_moderacao`, `aprovar_acao`,
  `recusar_acao`). Fila (`#/fila`) só para moderador. Editar ação, selo, bloquear seguem só no modo exemplo.
- Spec em `docs/superpowers/specs/`, desenho visual em `docs/2026-10-08-design-mockup.md`, capturas em
  `docs/capturas/`.
- Decisões do Gui: inscrição com nome e telefone desde a v1; moderação humana por voluntários no
  início, automação depois; uma vaquinha só, geral, apontando para arrecadação oficial; busca por
  lugar livre (Brasil inteiro), referência visual Airbnb/Meetup.
- Para republicar o artifact: publicar `app/index.html` com os arquivos `dados.js`, `lugares.js`,
  `fundo.js`, `config.js`, `api.js`, `api-exemplo.js`, `api-supabase.js` e `leaflet.css` ao lado (o artifact só carrega stylesheet próprio). Fora do artifact o
  mapa usa tiles do OpenStreetMap.
- Pages publica a cada push em `master` que toque `app/`.
- Fluxo de branches (desde 2026-10-09): ajuste pequeno e seguro vai direto na `master` com push; mudança maior ou
  arriscada vai numa branch, e o merge na `master` só acontece com OK do Gui. Sessões paralelas trabalham cada uma
  no seu worktree e na sua branch; a pasta principal fica na `master`, estável, para levantamento, publicação
  (`publicar_acoes.py --aplicar` grava em produção) e merges, um de cada vez (cada push na `master` republica o
  Pages). `levantamento/` só existe na pasta principal (não vai para worktree; noutra máquina, clonar o repo privado). A pilha local do Supabase é
  compartilhada: não rodar `test_supabase.py` nem migrações em duas sessões ao mesmo tempo. Remover o worktree
  (`git worktree remove`) depois do merge.
- Levantamento de ações reais (2026-10-08): pasta `levantamento/` (no .gitignore, nunca versionar: tem nomes e links)
  guarda a varredura de fontes e o balanço em `levantamento/RODADA-1.md`. Fonte principal: agenda "Bora Lula" do
  Comitê Popular (JSON público). `python scripts/bora_lula.py` baixa o feed, guarda cópia datada em
  `levantamento/bora-lula/` e gera `levantamento/dados-bora-lula.js` no formato de `app/dados.js` (modo exemplo).
  Para produção: `python scripts/publicar_acoes.py bora-lula [--aplicar]` (e `redes --de CSV --feed JSON`) chama a
  função SQL `importar_acoes` (migração 20261009000001: pessoa de sistema, `fonte`/`fonte_id`, `lugar_aproximado`,
  contato `divulgacao` sem inscrição; migração 20261009000002: logo da organização). O endereço vira ponto exato pelo
  Nominatim (cache em `levantamento/geocache.json`); organização reconhecível ganha logo do Commons (`LOGOS` em
  `scripts/bora_lula.py`). Imagem do post do Instagram como foto da ação: `python scripts/fotos_divulgacao.py coletar`
  (prévia de link, sem login; bucket `divulgacao`, migração 20261009000003); o `publicar_acoes.py --aplicar` já
  faz essa busca sozinho para os posts novos.
  Como rodar em `docs/operacao.md`; checklist resolvido em
  `docs/2026-10-08-plano-expansao-varredura.md`, seção "Publicar". Testes em `tests/test_bora_lula.py`,
  `tests/test_publicar_acoes.py` e `tests/test_supabase.py` (pilha local).
