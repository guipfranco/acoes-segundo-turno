# O que o app faz (catálogo)

Referência do que está no ar, por área, com a migração SQL que sustenta cada regra. Para saber como mexer, veja as
skills em `.claude/skills/`; para operar a produção, `docs/operacao.md`. Atualize este arquivo junto com a mudança.

## Telas

- **Inicial** (`#/`), sem mapa, estilo Meetup: busca por cidade que chuta a cidade pela geolocalização; filtro
  "Quando" (em breve, hoje, amanhã, esta semana, fim de semana, próxima semana, escolher datas); sem filtro de formato,
  só o link "Prefiro ajudar online"; vitrine por cidade (SP, Recife, BH, Porto Alegre, Salvador) com foto por ação; bloco
  "Online" em lista compacta por horário. A cidade de "Perto de você" é um botão que abre a busca de cidade. Deslogado,
  convite para entrar.
- **Mapa** (`#/mapa`): lista que acompanha o enquadramento; clicar no pino abre prévia da ação e marca o card na lista.
  Tiles do OpenStreetMap. Filtros da inicial e do mapa são separados e não passam de uma tela para a outra.
- **Página da ação** (`#/acao/<id>`): turnos, local, quem organiza, "Eu vou!", "Adicionar à agenda" (Google Agenda e
  arquivo .ics) para turno futuro. Ação online (`lugar.online: true`) não tem pino nem minimapa. O formulário do
  "Eu vou!" abre onde a pessoa tocou (topo no celular, coluna "Quando" no computador).
- **Desktop** (≥ 900 px): cabeçalho no topo e página da ação em duas colunas. Celular vem primeiro.
- **Tipos de ação**: panfletagem, encontro, ato, caminhada, cultural, bandeiraço, adesivaço, porta a porta, ligatona,
  outro (migração 20261009000010).
- **Fotos**: das ações importadas, a arte do post (em `fotos/divulgacao/`, arte + `-mini.jpg`); das de exemplo, Wikimedia
  Commons com crédito (campo `foto`).
- **Sem foto** (desde 2026-10-10): o app desenha um cartaz na área da imagem (card, lista online e página da ação):
  cor da marca alternada pelo id, tarja amarela "Bora Lula", o tipo em letra grande e a cidade. Com logo da
  organização, o logo vai no alto do cartaz. Ele fica por baixo da foto e aparece também quando ela não carrega.
- **Turno que já terminou** some das listas, do mapa e do "Eu vou!" (`config.agora`, em Brasília; no exemplo,
  `dados.config.agora`). `turno.hora_aproximada`: divulgação que só diz "à noite" aparece como "sex 09/10, à noite",
  com aviso (migração 20261009000050).

## Conta e perfil

- Login só com Google (botão do Google sobre o site, `googleClientId` em `app/config.js`; sem ele, redirecionamento).
- Logado, o botão da conta vira "Perfil" (`#/perfil`): WhatsApp, resumo do "Eu vou", ações que criei com situação e
  motivo da recusa, organização, Sair no fim. Deslogado: "Entrar" escuro.
- "Eu vou!" em toda ação; na de divulgação (importada) só marca presença, sem telefone (migração 20261009000020).
  Desistência fica no histórico do Perfil ("você desistiu"); quem organiza vê quem desistiu, só pelo nome. Telefones dos
  inscritos ficam visíveis a quem organiza (decisão do Gui).

## Cadastro de ação

- Qualquer pessoa logada cadastra ("Cadastrar ação", botão vermelho da barra e da inicial), em 4 passos; a imagem é
  obrigatória (passo 3): enviada do celular, reduzida no navegador e guardada no bucket `fotos-acoes`
  (migração 20261009000022), ou puxada do link do post pela função `supabase/functions/previa-instagram` (máximo de 10
  chamadas por pessoa por hora).
- Nasce "em análise", exceto quem é verificado (papel `organizador` ou `moderador`, ou membro de organização
  verificada), que publica direto. Limite de 10 por dia e 10 em análise (migração 20261009000021: `criar_acao`,
  `minhas_acoes`, `encerrar_acao`, `fila_moderacao`, `aprovar_acao`, `recusar_acao`).
- "Quem organiza?": eu mesmo(a), minha organização ou outra escrita à mão (criada sem selo). Ação em nome de organização
  pede o link do POST oficial da organização anunciando aquela ação (`acao.organizacao_link`, erro `link_post`).
- O cadastro não recarrega a tela ao mudar horário ou "Vagas limitadas" (no iPhone fechava o seletor e rolava ao topo);
  `rerender()` mantém a rolagem.
- Editar ação, selo e bloquear pelo próprio organizador seguem só no modo exemplo.

## Organizações e verificação

- No Perfil a pessoa cadastra a sua (nome, tipo, logo, link do perfil oficial `link_oficial`). Nome novo cria sem selo
  e liga na hora; nome que já existe vira pedido para a moderação. Selo dado na Fila (migração 20261009000023).
- A moderação confere pelo link oficial (Perfil) e pelo link do post (ação).

## Moderação (`#/fila`, só moderador)

- Abas: Em análise, Publicadas, Divulgação, Organizações, Mensagens.
- Suspender, reativar e excluir ação (migração 20261009000030); bloquear e desbloquear pessoa (migração
  20261009000051, `bloquear_pessoa`/`desbloquear_pessoa`).
- **Divulgação pública** (migração 20261010000010): toda ação importada vai ao ar com a etiqueta "Divulgação pública"
  (cards e aviso na página) até um moderador verificar na aba Divulgação (`verificar_acao`/`desverificar_acao`,
  `acao.verificada_em`). Reimportar com qualquer mudança vinda da fonte (só foto e logo não contam) tira a verificação.
- **Canceladas** (migração 20261009000040): "Cancelar ação" (status segue `encerrada`); `acao.publicada_em` (gatilho)
  marca a primeira ida ao ar, e só a cancelada que já esteve publicada abre pelo link para todos, sem contato. Importada
  encerrada mostra "Saiu da agenda" ou "Já aconteceu".

## Fale com a gente

`#/contato` (e `#/contato/<acao>` na página da ação), logado ou não: texto + contato opcional + tela + navegador
resumido. Tabela `feedback` sem acesso direto (`enviar_feedback`, freio de 10/h por pessoa e 100/h anônimas;
`feedbacks` e `tratar_feedback` só moderador). Chega na aba Mensagens da Fila (migração 20261009000050).

## Ações importadas (divulgação)

- Fonte principal: agenda Bora Lula do Comitê Popular (JSON público); secundária: varredura das redes (CSV consolidado
  no repo privado do levantamento). Importadas por `scripts/publicar_acoes.py` via função SQL `importar_acoes`
  (migrações 20261009000001 a 03): organizador é uma pessoa de sistema, `fonte`/`fonte_id`, `lugar_aproximado`, contato
  `divulgacao` sem inscrição, logo da organização (Commons, mapa `LOGOS` em `scripts/bora_lula.py`).
- Endereço vira ponto exato pelo Nominatim (cache em `levantamento/geocache.json`).
- **Dúvida vai para aprovação** (migração 20261010000020): a importação não descarta ação por dúvida. Confiança baixa
  na varredura ou cidade não reconhecida entra "em análise" (fora do ar, `acao.motivo_duvida`, aba Em análise da Fila);
  aprovar põe no ar já verificada. O resto vai ao ar com a etiqueta; sem Lula explícito deixou de ser corte. Fora só
  repetição e datas fora da janela.
- Sempre com crédito e link para a divulgação original.

## Escala e segurança

- A vitrine e a página da ação, para quem só olha, leem `publico.json` (gerado de hora em hora pelo workflow do Pages,
  `scripts/snapshot_publico.py`); plano B direto no Supabase se o arquivo faltar ou tiver mais de 3 h. Logado ou depois
  de gravar algo, tudo vai direto ao Supabase. Leituras ao vivo pedem as views de 1000 em 1000 (`tudo()` em
  `app/api-supabase.js`), porque a API corta em `max_rows` sem avisar.
- Imagem de ação e logo só do próprio Storage; importação descarta link que não é http(s); máximo de 40 fotos por
  pessoa no bucket (migração 20261009000051); `acao.foto_mini_url` (migração 20261009000060).
- Scripts de CDN com `integrity`; GoatCounter fixado em `count.v5.js`.
- Cópia diária do banco cifrada (`.github/workflows/backup.yml`).

## Marca

- Iniciativa do Comitê Popular do Lula (não é a campanha), segue o "Guia de interface web e apps" do Comitê: tokens em
  `app/tokens.css` (arquivo do guia, não editar), aplicação em `app/marca.css` (Montserrat, botões em pílula de 44 px,
  foco visível, cards com borda).
- Logo do Comitê no topo da inicial; na barra do computador, "BORA" sobre "LULA" na letra Transducer Extended, em
  `app/marca-barra.svg`. Capa do link (`app/capa.png`) e esse SVG saem de `scripts/gerar_capa.py`, que baixa a fonte do
  site do Comitê (fonte comercial: nunca versionar o arquivo).
- Rodapé (inicial e privacidade), texto fixo: "Uma iniciativa do Comitê Popular do Lula. Não é site oficial da
  campanha. Nenhuma divulgação paga." Sem nome de pessoa e sem link do código.
- Detalhes em `docs/2026-10-08-design-mockup.md`.

## Linha do tempo curta

- 2026-10-08: nasce do `mapa-segundo-turno`; app navegável no modo exemplo; levantamento de fontes.
- 2026-10-09: produção ligada (Supabase `ommitzndniqnmsjsjghb`, login Google); cadastro, moderação, organizações,
  canceladas, feedback, segurança, fotos e lista pelo Pages, cópia do banco.
- 2026-10-10: nome "Agenda Bora Lula" (antes "Eleja o Lula" e "Ações do 2º turno"), marca do Comitê, divulgação pública.
