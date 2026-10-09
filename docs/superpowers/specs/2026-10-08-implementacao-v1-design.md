# Implementação real, v1: desenho (2026-10-08)

Complementa a spec do produto em `2026-10-08-plataforma-acoes-design.md`. O core daquela spec não
muda. Este documento define como sair do mockup estático para um produto no ar, com as decisões
tomadas com o Gui em 2026-10-08.

## Princípios

- Rápido e barato. O que puder ser feito à mão no começo, é feito à mão.
- De graça para começar. Nenhum serviço pago na v1.
- Sem servidor próprio para operar.
- Organizador é um status concedido por moderador, nunca automático. O risco de ataque por
  organizadores falsos é maior que o risco de participante falso.
- Dado mínimo. Telefone nunca é legível por quem não deve, e isso é garantido no banco, não no
  JavaScript.

## Arquitetura

- **Front**: o `mockup/` evolui para `app/`. HTML, CSS e JS puros, sem build, publicados no GitHub
  Pages como hoje. Mapa com Leaflet e tiles do OpenStreetMap. Busca de lugar com `lugares.js` local.
- **Banco e autenticação**: um projeto Supabase no plano grátis. Postgres com RLS (regras de acesso
  por linha). O front chama o Supabase direto pela `supabase-js` via CDN. Sem backend próprio.
- **Lógica sensível no banco**: inscrever, desistir, pedir para organizar, aprovar, recusar, dar selo,
  despublicar e bloquear são funções SQL (`security definer`) chamadas pelo front.
- **Segredos**: só a chave pública (anon) do Supabase fica no front. O RLS é o que protege os dados.
- **Ambientes**: um projeto Supabase de produção; para desenvolver, Supabase local via CLI (Docker)
  ou um segundo projeto grátis. Migrações SQL versionadas em `supabase/migrations/`.
- **Operação**: ping diário por GitHub Actions para o projeto grátis não pausar; backup semanal por
  `pg_dump` em Action, guardado fora do repo público (artefato privado da Action ou bucket).

## Login

- Só por conta social: **Google** na primeira entrega, **Facebook** assim que a Meta aprovar o app
  (exige app no painel da Meta, página de política de privacidade e endereço para pedido de exclusão
  de dados). Instagram não serve como login para contas pessoais desde 2024.
- Sem e-mail e senha, sem cadastro por fora, sem código por SMS ou WhatsApp.
- Primeiro login cria a pessoa com nome e e-mail e mostra aviso curto do que guardamos e para quê.
- Sem login dá para ver tudo que é público.

## Vocabulário na interface

Segue a Agenda do Google. **Ação** é o evento. Dentro dela, cada **horário** tem início, fim e
lotação opcional (na spec do produto chamava-se turno; o nome interno pode continuar `turno`).
Ao criar: "Dia e hora", depois "Repete?" com "Não se repete", "Todos os dias", "Toda semana",
"Escolher dias", até uma data final limitada ao dia do 2º turno. Botão "Adicionar outro horário"
para casos avulsos. Cada repetição vira um horário independente: cancela ou lota um sem mexer nos
outros; a inscrição é sempre num horário específico. Com um horário só, a tela mostra apenas dia e
hora.

O botão de inscrição é **Inscreva-se** (não "Vou"); depois de inscrito aparece **Inscrito ✓** e o botão de
desistir.

## Modelo de dados e visibilidade

**Pessoa** (criada no primeiro login): nome, e-mail, telefone (pedido no primeiro Vou ou ao pedir
para organizar), papel (participante, organizador, moderador), organização opcional, bloqueada.
A própria pessoa vê e edita só o seu. Organizador vê nome e telefone de quem se inscreveu nas ações
dele. Moderador vê tudo.

**Pedido para organizar**: pessoa, organização (existente ou proposta), telefone, texto "como a
equipe pode confirmar que você é você", estado (em análise, aprovado, recusado), motivo da recusa,
quem decidiu e quando. A pessoa vê o próprio pedido. Moderador vê e decide. Moderador também pode
marcar alguém como organizador direto, sem pedido (parceiros).

**Organização**: nome, tipo (mandato, partido, movimento, coletivo), verificada. Organizador escolhe
da lista ou propõe nova. Só moderador dá selo.

**Ação**: título, tipo, descrição, organizador, organização opcional, lugar público (nome, bairro,
cidade, coordenadas) ou online, detalhe do encontro (opcional), **forma de contato** (ver abaixo),
foto por URL, área prioritária (marcada à mão por moderador), estado (rascunho, em análise,
publicada, recusada, encerrada), motivo da recusa, criada em. Publicadas são públicas, menos detalhe
do encontro e dados de contato, que só inscritos em algum horário dela, o organizador e os
moderadores veem. Organizador de organização verificada publica direto; os demais vão para a fila.

**Forma de contato** da ação. O organizador escolhe como vai combinar com quem se inscrever:
- `organizador_chama` (padrão): a pessoa só deixa nome e telefone e não vê contato nenhum. O
  organizador chama no WhatsApp ou adiciona no grupo quem ele quiser, depois de ver quem é.
- `whatsapp`: a pessoa vê um número informado pelo organizador (o dele ou outro) e chama.
- `link_grupo`: a pessoa vê o link do grupo. Ao escolher, antes do campo do link, uma orientação
  curta com os passos no WhatsApp: configurar o grupo para **só administradores enviarem
  mensagens** e **aprovar quem entra**. Explica que sem isso qualquer inscrito pode falar com todo
  mundo e ver os números. Uma caixa "Já configurei o grupo assim" precisa ser marcada para o campo
  do link liberar. A mesma orientação aparece em Minhas ações.
Pode ser mudada depois editando a ação. Nunca é obrigatório informar link de grupo.

**Horário** (tabela `turno`): ação, início, fim, lotação opcional. Público junto com a ação.

**Inscrição**: pessoa, horário, criada em, cancelada em. Uma por pessoa por horário. A pessoa vê as
suas; organizador vê as da ação dele com nome e telefone; contagem "N vão" é pública.

**Configuração**: link da vaquinha, frase, textos fixos. Leitura pública, só moderador edita.

**Registro de moderação**: toda decisão (aprovar, recusar, selo, despublicar, bloquear, marcar
organizador) com quem, quando, alvo e motivo. Só moderador vê. Serve para auditoria.

Diferenças em relação à spec do produto: pedido para organizar é novo; papel organizador é status
concedido; registro de moderação é novo; verificação por código sai; telefone é informado, não
verificado.

## Fluxos

**Entrar.** "Entrar com Google". Primeira vez cria a pessoa e mostra o aviso de dados.

**Vou.** Toca em Vou num horário. Sem login, abre o Google e volta para onde estava. Sem telefone,
pede uma vez com o aviso "seu nome e telefone vão para quem organiza esta ação". Confirma. A tela
de confirmação diz o que acontece conforme a forma de contato: "Fulano vai entrar em contato pelo
seu telefone", ou mostra o número do WhatsApp, ou mostra o link do grupo. Mostra também o detalhe do
encontro, se houver, e o botão de compartilhar. A ação entra em "Minhas inscrições", de onde dá
para desistir. Lotação cheia bloqueia nova inscrição. Pessoa bloqueada não se inscreve.

**Quero organizar.** Botão na inicial e no rodapé. Pede telefone, organização e o texto de
confirmação. Fica em análise. Moderador confere fora da plataforma, aprova ou recusa com motivo. A
pessoa vê o resultado ao entrar e, se aprovada, ganha "Criar ação".

**Criar ação.** Os 3 passos do mockup com horários no vocabulário da Agenda e, no passo 2, a
pergunta "Como você vai combinar com quem se inscrever?" com as três formas de contato. Organização verificada
publica na hora; demais veem "sua ação está em análise". Editar e encerrar depois. Editar uma ação
publicada não a tira do ar.

**Minhas ações.** Ações do organizador com estado e inscritos por horário. Dentro: nomes e
telefones, copiar números, texto pronto de aviso para o WhatsApp, editar, encerrar.

**Fila (moderador).** Três abas: pedidos para organizar, ações em análise, publicadas. Aprovar,
recusar com motivo, dar selo, despublicar, bloquear pessoa, marcar organizador direto. Bloquear
cancela as inscrições da pessoa e tira do ar as ações dela. Toda decisão vai para o registro.

**Avisos.** Nenhum automático na v1. Resultados aparecem na plataforma ao entrar. Moderador e
organizador têm texto pronto para colar no WhatsApp.

**Doar.** Botão fixo para o link da configuração.

## Fora da v1

Código de verificação de telefone; marcar presença; lembrete na véspera e avisos automáticos; área
prioritária derivada do mapa; upload de foto; login por Instagram; denúncia pela tela da ação;
auto-aprovação de organizador por histórico. Tudo isso cabe no modelo sem migração destrutiva.

Risco: participante mal-intencionado se inscreve. Com a forma de contato padrão ele não vê nada e
o organizador filtra antes de chamar. Só na opção de link do grupo ele chega ao grupo, que
a orientação manda fechar para mensagens só de administradores; ali ele só lê os avisos. Bloqueio pelo moderador cobre o resto.

## Do mockup ao app

1. Criar uma camada de dados (`app/api.js`) com as operações: listar ações, pegar ação, inscrever,
   desistir, minhas inscrições, pedir para organizar, criar e editar ação, minhas ações, inscritos
   de uma ação, fila e decisões do moderador, configuração. Primeiro responde com os dados de
   exemplo; as telas passam a chamar só essa camada. Nada muda visualmente.
2. Trocar o miolo da camada pelo Supabase, tela por tela, com o site sempre funcionando.
3. Dados de exemplo passam a viver no Supabase de desenvolvimento. Produção começa vazia, com o Gui e
   os primeiros moderadores cadastrados à mão.

## Testes

- **Regras do banco** (o mais importante): scripts SQL ou Python que tentam ler telefone com conta
  comum, inscrever bloqueado, aprovar sem ser moderador, ver detalhe sem inscrição, e precisam
  falhar. Rodam contra o Supabase local.
- **Telas**: os testes atuais em `tests/` (pytest) continuam checando textos e templates.
- **Fluxo inteiro**: roteiro Playwright que entra, se inscreve, cria ação e modera, contra o
  Supabase de desenvolvimento.

## Ordem de entrega

1. Camada de dados sobre o mockup atual, sem mudança visível.
2. Supabase com tabelas e RLS, login Google, vitrine e Vou de verdade. Já usável com uma ação
   cadastrada à mão.
3. Quero organizar, Criar ação, Minhas ações.
4. Fila do moderador e registro.
5. Facebook, ping diário, backup.
