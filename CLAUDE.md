# CLAUDE.md

Repo da plataforma "Eleja o Lula" (nome visível desde 2026-10-09; antes "Ações do 2º turno"), de ações do 2º turno pelo voto do Lula.
Nasceu do `mapa-segundo-turno` em 2026-10-08. URL, repo e projeto Supabase seguem `acoes-segundo-turno` por decisão do Gui.

- Tudo em pt-BR, datas AAAA-MM-DD. Push logo depois de cada commit.
- `app/` (antes `mockup/`) é o app: estático, sem build. Publicado em https://guipfranco.github.io/acoes-segundo-turno/
  (GitHub Pages via `.github/workflows/pages.yml`, só a pasta `app/`; repo público desde 2026-10-08). O artifact
  do claude.ai foi aposentado e apagado em 2026-10-09: o único endereço é o Pages, com tiles do OpenStreetMap
  (o ramo Protomaps de `app/fundo.js` só valia dentro do artifact).
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
- Conta e cadastro de ação (em produção desde 2026-10-09: migrações 20261009000020 a 22 aplicadas, função
  previa-instagram publicada, Gui com papel moderador): logado, o botão da conta vira "Perfil" (`#/perfil`: WhatsApp,
  resumo do "Eu vou", ações que criei com situação e motivo da recusa, Sair no fim); deslogado, "Entrar" escuro e
  convite na inicial. "Eu vou!" em toda ação; na de divulgação (importada) só marca presença, sem telefone (migração
  20261009000020). Qualquer pessoa logada cadastra ação ("Cadastrar ação", botão vermelho da barra e da inicial): nasce "em análise", exceto verificado (papel organizador ou
  moderador, ou membro de organização verificada), que publica direto; limite de 10 por dia e 10 em análise
  (migração 20261009000021: `criar_acao`, `minhas_acoes`, `encerrar_acao`, `fila_moderacao`, `aprovar_acao`,
  `recusar_acao`). Fila (`#/fila`) só para moderador (abas Em análise, Publicadas e Organizações).
  Organização (migração 20261009000023, em produção desde 2026-10-09): no Perfil a pessoa cadastra a sua (nome, tipo, logo);
  nome novo cria sem selo e liga na hora, nome que já existe vira pedido para a moderação; selo dado na Fila. No
  cadastro, "Quem organiza?": eu mesmo(a), minha organização ou outra escrita à mão (criada sem selo).
  Verificação: no Perfil, link do perfil oficial da organização (`link_oficial`); em toda ação em nome de organização
  (a minha, com ou sem selo, ou outra), link do POST oficial da organização anunciando aquela ação
  (`acao.organizacao_link`, erro `link_post`). A moderação confere pelos dois na Fila. Imagem obrigatória no cadastro (passo 3 de 4): enviada do celular,
  reduzida no navegador e guardada no bucket `fotos-acoes` (migração 20261009000022), ou puxada do link do post pela
  função `supabase/functions/previa-instagram` (precisa de `supabase functions deploy previa-instagram` em produção). Editar ação, selo, bloquear seguem só no modo exemplo.
  Canceladas não somem (migração 20261009000040, em produção desde 2026-10-09): "Encerrar" virou "Cancelar ação" (status segue `encerrada`); `acao.publicada_em`
  (gatilho) marca a primeira ida ao ar, e só a cancelada que já esteve publicada abre pelo link para todos (sem dados
  de contato); importada encerrada mostra "Saiu da agenda" ou "Já aconteceu"; desistência fica no histórico do Perfil
  ("você desistiu") e quem organiza vê quem desistiu, só pelo nome. O formulário do "Eu vou!" abre onde a pessoa tocou
  (topo no celular, coluna "Quando" no computador).
  Correções do primeiro uso real e "Fale com a gente" (branch `feedback-1009`, migração 20261009000050): turno que já
  terminou some das listas, do mapa e do "Eu vou!" (`config.agora`, em Brasília; no exemplo, `dados.config.agora`);
  `turno.hora_aproximada` (divulgação que só diz "à noite": o app mostra "sex 09/10, à noite" e avisa; a importação das
  redes marca pelo texto, `bl.faixa_aproximada`); bloco Online da inicial é lista compacta por horário; o cadastro não
  recarrega a tela ao mudar horário ou "Vagas limitadas" (no iPhone fechava o seletor e rolava ao topo) e `rerender()`
  mantém a rolagem nos filtros. Feedback: `#/contato` (e `#/contato/<acao>` na página da ação), logado ou não, texto +
  contato opcional + tela + navegador resumido, tabela `feedback` sem acesso direto (`enviar_feedback`, freio de 10/h por
  pessoa e 100/h anônimas; `feedbacks` e `tratar_feedback` só moderador), aba Mensagens na Fila.
- Spec em `docs/superpowers/specs/`, desenho visual em `docs/2026-10-08-design-mockup.md`, capturas em
  `docs/capturas/`.
- Decisões do Gui: inscrição com nome e telefone desde a v1; moderação humana por voluntários no
  início, automação depois; uma vaquinha só, geral, apontando para arrecadação oficial; busca por
  lugar livre (Brasil inteiro), referência visual Airbnb/Meetup.
- Pages publica a cada push que toque `app/` (qualquer branch; desde 2026-10-09): a raiz é sempre a `master` e cada outra
  branch do origin vira prévia em https://guipfranco.github.io/acoes-segundo-turno/previa/<branch>/ (lista em `/previa/`),
  montada por `scripts/montar_pages.sh`: dados de exemplo por padrão (`?modo=real` usa o Supabase de produção, cuidado
  com branch de migração não aplicada), sem GoatCounter, `noindex`, etiqueta amarela com o nome da branch. Ao terminar
  um trabalho num worktree: push da branch e mandar ao Gui o link da prévia (não subir servidor local). Apagar a branch
  no origin depois do merge tira a prévia.
- Fluxo de branches (desde 2026-10-09, endurecido no mesmo dia): TODA mudança de código (app, scripts, testes,
  migrações), por menor que seja, é feita num worktree com branch própria, nunca direto na `master`. O merge na
  `master` só acontece com OK do Gui. Direto na `master` só o que não é código: documentação, CLAUDE.md e o merge
  em si. Sessões paralelas trabalham cada uma no seu worktree e na sua branch; a pasta principal fica na `master`, estável, para levantamento, publicação
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
