# Plataforma de ações do 2º turno: desenho (2026-10-08)

Spec do produto. Vai virar um repo separado; fica aqui até ele existir.

## Problema

Muita gente da esquerda quer ajudar a eleger o Lula no 2º turno e não sabe como. Ao mesmo tempo,
mandatos, partidos, movimentos e pessoas comuns já fazem panfletagem, adesivaço, roda de conversa,
ligatona, sem visibilidade e com menos gente do que poderiam ter. A plataforma junta as duas pontas:
quem organiza cadastra a ação; quem quer ajudar acha uma perto de si e se inscreve.

## Decisões de base

- **Lista primeiro, mapa como segunda aba.** No celular e com poucas ações no início, "esta semana,
  perto de você" converte mais que um mapa.
- **Inscrição com nome e telefone desde a v1** (não só um link de WhatsApp). Permite contagem,
  lembrete e presença.
- **WhatsApp é a camada de execução.** A plataforma serve para descobrir e escolher a ação; o grupo
  de WhatsApp da ação serve para combinar o dia.
- **Moderação humana na v1**, por voluntários; automação entra depois sem mudar o modelo de dados.
- **Uma vaquinha só, geral**, num botão fixo que aponta para a arrecadação oficial da campanha
  (financiamento coletivo cadastrado no TSE). A plataforma não recebe dinheiro nem exibe valores. Link
  por ação fica fora, salvo orientação jurídica.
- **Dado mínimo.** Nome, telefone e inscrições. Endereço de casa nunca entra.
- Começa pela RMSP (onde o mapa de perda do Lula cobre), sem travar o resto do país.
- Construído e mantido pelo Gui com o Claude; hospedagem gratuita e sem servidor para operar.

## Referências

- Mobilize (EUA): feed compartilhado entre organizações, turnos, endereço só para inscritos, ação
  criada por voluntário com fila de aprovação. Modelo de dados em https://github.com/mobilizeamerica/api.
- "Agora é com a Gente" (Manuela d'Ávila, RS 2026): agentes criam atividades por bairro, agenda
  integrada a candidaturas aliadas.
- Momentum, My Campaign Map (UK 2019): mapa que direciona o voluntário para onde falta gente.
- Action Populaire (França Insoumise): grupos pequenos e certificados; vazamento de 2024 como alerta
  sobre quanto dado guardar.
- Bernie 2016, Rules for Revolutionaries: o centro define o plano, o voluntário executa.

## Papéis

- **Participante**: vê ações, se inscreve num turno.
- **Organizador**: cria e administra ações. Pode ser pessoa ou agir em nome de uma organização.
- **Moderador**: aprova, recusa, despublica, dá selo a organização, bloqueia organizador.

Organização com selo "verificada" publica sem passar pela fila.

## Modelo de dados

- **Organização**: nome, tipo (mandato, partido, movimento, coletivo), verificada (bool), contato.
- **Pessoa**: nome, telefone (verificado por código via WhatsApp ou SMS), papel, organização
  opcional, bloqueada (bool).
- **Ação**: título, tipo (panfletagem, adesivaço, roda de conversa, ligatona, porta a porta,
  bandeiraço, outro), descrição, organizador (pessoa) e organização opcional, ponto de encontro
  público (nome do lugar, bairro, cidade, coordenadas), detalhe do encontro (só inscritos), link do
  grupo de WhatsApp (só inscritos), status (rascunho, em análise, publicada, recusada, encerrada),
  motivo da recusa, área prioritária (bool, derivado do mapa de perda do Lula), criada em.
- **Turno**: ação, início, fim, lotação opcional.
- **Inscrição**: pessoa, turno, criada em, cancelada em, presença (marcada pelo organizador).
- **Configuração**: link da vaquinha, textos fixos, lista de áreas prioritárias.

Visibilidade: a página pública mostra só nome do lugar, bairro e cidade. Detalhe do encontro e link
do grupo só aparecem a inscritos. A lista de inscritos (nome e telefone) só o organizador da ação e
os moderadores veem. Telefone nunca aparece em página pública.

## Telas

### Início
- Cabeçalho: nome, frase ("O que você pode fazer hoje para eleger o Lula"), botão fixo **Doar**
  (vaquinha) e botão **Criar ação**.
- "Onde você está": CEP, bairro ou localização do celular; guardado no aparelho.
- Filtros: Quando (hoje, amanhã, fim de semana, qualquer dia) e Tipo (ícones dos sete tipos).
- Cards por data e distância: ícone do tipo, título, organizador com selo, dia e hora, bairro e
  distância, "N vão", destaque "área prioritária".
- Segunda aba: mapa com os mesmos cards como pinos.
- Vazio: "Ainda não tem ação perto de você. Crie a primeira."

### Ação
- Card completo, descrição, lugar do encontro com mini-mapa, turnos com botão **Vou**, quem organiza.
- **Vou**: nome e telefone, código pelo WhatsApp, confirma. Depois: detalhe do encontro, link do
  grupo, compartilhar. Inscrito pode desistir.

### Criar ação (3 passos)
1. Tipo; cada tipo pré-preenche título, descrição e dicas.
2. Onde e quando: busca de lugar público, confirma no mapa, turnos, detalhe só para inscritos, link
   do grupo.
3. Quem organiza: nome e telefone verificados; "em nome de uma organização?" com busca. Verificada
   publica na hora; demais veem "sua ação está em análise, avisamos pelo WhatsApp".

### Minhas ações (organizador)
- Suas ações, status, inscritos por turno. Dentro: nomes e telefones, copiar números, mandar aviso
  (texto pronto para o WhatsApp), marcar presença após o turno, editar, encerrar.

### Fila (moderador)
- Ações em análise, mais nova primeiro, com telefone do organizador e quantas ações já criou.
  **Aprovar**, **Recusar com motivo**, **Dar selo à organização**. Aba de publicadas para despublicar
  e bloquear organizador.

## Mensagens automáticas (WhatsApp; SMS ou link manual como reserva)
Código de verificação; confirmação de inscrição com detalhe e link do grupo; lembrete na véspera;
aviso ao organizador de aprovação ou recusa.

## Moderação e segurança

v1 (humano):
- Toda ação de organizador sem selo entra na fila. Meta de resposta: 2 h em horário comercial, com
  escala de moderadores.
- Regras de recusa: não é ação de campanha; lugar não é público; convoca para confronto; pede
  dinheiro; dado pessoal no texto.
- Despublicar e bloquear (pelo telefone) em um clique.
- Telefone verificado obrigatório para criar ou se inscrever.
- Aviso na inscrição: "Seu nome e telefone vão para quem organiza esta ação."
- Backup, acesso restrito, nada de telefone em página pública.

Depois (automação, mesmo modelo):
- Auto-aprovação para organizador com 2+ ações aprovadas e nenhuma recusa.
- Limite de ações por telefone por dia; lista de bloqueio.
- Detecção de texto fora da regra antes da fila.
- Botão de denúncia na tela da ação.

## Fora da v1
Comentários ou chat, vaquinha por ação, perfil público de organizador, gamificação e ranking,
integração com cadastro de porta-vozes, exportação para o mapa de perda do Lula (v1 só lê as áreas
prioritárias).

## Primeiro entregável: mockup
Protótipo navegável das cinco telas em HTML estático, dados de exemplo da RMSP, publicado como
artifact privado para a equipe clicar. Valida textos, ordem dos passos e o que aparece a quem não
está inscrito. Só depois dele vem a escolha de stack e o código.
