# Fusão da Agenda Bora Lula com o boralula.org (2026-10-10)

Documento de entrega para quem vai executar a fusão no repo `comite-popular-tech/agregador-de-agendas` (a equipe do
boralula e o Claude dela). Combinado entre o Gui (Agenda Bora Lula) e a equipe do boralula em 2026-10-10.

## Em uma frase

A Agenda Bora Lula deixa de existir como site: tudo o que ela faz passa a existir no boralula.org, com as regras do Gui
(telefone no "Eu vou!" e moderação antes de publicar) valendo para o site inteiro, e o endereço antigo passa a levar
ao boralula.org.

## Situação (2026-10-10, fim do dia)

- Item A entrou no `main` do agregador (PR #36, juntado pelo Carlos). Ainda não está em produção: falta o núcleo
  seguir os passos de produção do PR (migração, ligar a fonte `bora-lula`).
- A equipe do boralula escreveu outro caminho para a mudança: `docs/superpowers/specs/2026-10-10-agenda-gui-no-supabase-design.md`
  no agregador. O banco da Agenda entra como está no Supabase do boralula, o app da Agenda passa a morar em
  `boralula.org/agenda/` e o Supabase do Gui é pausado; a convergência dos esquemas fica para uma etapa 2.
- **O Gui aceitou esse caminho**: por um tempo são dois sites em paralelo dentro do boralula, com a mesma ação do
  Comitê aparecendo nos dois quando a fonte `bora-lula` for ligada. Contas, a 1 inscrição futura e o papel de
  moderador não vão junto (o Gui avisa e é refeito à mão).
- Condição: alguém precisa manter a importação do feed rodando contra o banco do boralula depois da troca, senão
  `boralula.org/agenda/` fica com ações velhas (sem as novas e com as mudadas ou canceladas erradas). **Decisão do
  Gui: o Carlos roda à mão** (`scripts/publicar_acoes.py bora-lula --ref <ref do boralula>`, com o
  `SUPABASE_ACCESS_TOKEN` dele), pelo menos 2 vezes por dia.
- Os itens B a E abaixo continuam valendo como destino da etapa 2.

## Onde está cada coisa

- Código da Agenda Bora Lula no agregador: pasta `acoes-segundo-turno/` (trazida por `git subtree`, com histórico;
  atualizar com o comando do README da raiz antes de começar, para pegar o que entrou depois de 663b779: endereço
  público da ação, cartaz para ação sem foto, arte das redes nas ações do feed, migração 20261010000030).
- Leia primeiro, dentro dela: `CLAUDE.md` (regras e mapa), `docs/funcionalidades.md` (o que o app faz, tela a tela, com
  a migração de cada regra) e `docs/operacao.md` (rotinas e o que já deu errado). As skills em
  `acoes-segundo-turno/.claude/skills/` explicam importação (`importar-acoes`) e banco (`mudar-banco`) da Agenda.
- Site da Agenda: https://guipfranco.github.io/acoes-segundo-turno/ (GitHub Pages do repo público
  `guipfranco/acoes-segundo-turno`). Banco: Supabase ref `ommitzndniqnmsjsjghb`. O Gui tem as chaves.
- Dados brutos da varredura das redes (nomes e telefones): repo privado `guipfranco/acoes-levantamento`. Nunca vão
  para o agregador; o importador recebe só o CSV consolidado.

## Decisões (não reabrir sem o Gui)

1. **"Eu vou!" pede nome e telefone, no site inteiro** (eventos públicos e atividades). Quem organiza vê nome e
   telefone de quem confirmou. Na Agenda é assim desde a v1 (`inscrever`, erro `sem_telefone`, telefone guardado no
   perfil e reaproveitado).
2. **Toda publicação nova passa pela moderação antes de ir ao ar**, no site inteiro, inclusive o envio sem login. Quem
   é verificado publica direto: na Agenda, papel organizador ou moderador, ou membro de organização com selo; no
   boralula, o equivalente é representante de organização com selo e moderação.
3. **Exceção à regra 2: importação da agenda do Comitê vai ao ar com a etiqueta "Divulgação pública"** até alguém da moderação conferir
   no post original (decisão da Agenda: não confiamos na revisão de quem publica a agenda de origem, que tem formulário
   aberto). Mudança vinda da fonte tira a verificação. Dúvida (cidade não reconhecida, confiança baixa) entra na fila,
   fora do ar. A bandeira vermelha do boralula pode ser essa etiqueta, se o sentido for o mesmo.
4. **Endereço da ação é público** (Agenda, migração 20261010000030), com aviso de que deve ser lugar público.
5. **Marca, rodapé e nome do site ficam como os do boralula.** O código pode seguir fechado (o repo público da Agenda
   é MIT; o que for portado para o boralula segue a regra do boralula).
6. **Continua valendo o que o boralula já tem:** trava eleitoral das 22h da véspera, "não é rede social", aceite LGPD,
   login por Google e por código.

## Consentimento e quem já usa (obrigatório antes de ligar as decisões 1 e 2)

- Política de privacidade nova no boralula dizendo que o telefone de quem confirma vai para quem organiza, e aceite
  novo no próximo acesso de quem já tem conta.
- Quem confirmou presença antes da mudança confirmou sob a promessa "ninguém vê": essas presenças continuam sem
  mostrar nome nem telefone. Só confirmações feitas depois do aceite novo aparecem para quem organiza.
- Eventos que já estão no ar continuam no ar; a moderação prévia vale para os novos e para mudança de data, hora ou
  lugar feita por quem não é verificado.

## O que portar (checklist)

Antes de cada item, confira se o boralula já tem algo equivalente (ele importou a agenda do Comitê à mão em 6/10, por
exemplo) e reaproveite em vez de duplicar.

### A. Agenda do Comitê e redes (o que mais ajuda a campanha; fazer primeiro)

- Importar o feed da agenda Bora Lula do Comitê (`comitepopular.org.br/wp-content/uploads/agenda-bora-lula/acoes.js`,
  626 ações em 2026-10-10), que é outra fonte que não a planilha da Lulaço que o boralula sincroniza (6 linhas hoje).
  Referência: `acoes-segundo-turno/scripts/bora_lula.py` e `publicar_acoes.py`.
- Pelo menos 2 vezes por dia; idempotente pela chave da fonte (no boralula, `eventos_publicos.importado_de`); o que
  some do feed vira "saiu da agenda"; recusa da moderação não volta na reimportação.
- Sem duplicar: casar com eventos que o boralula já tem pelo código do post do Instagram e, sem post, por cidade + data +
  hora.
- Armadilhas conhecidas: o feed vem com cache de um ano (pedir com `?t=<agora>` e `Cache-Control: no-cache`; se o
  arquivo novo é idêntico ao anterior, desconfie); endereço vira ponto exato pelo Nominatim (1 consulta/s, cache, só
  aceita prédio, número ou via dentro do município, senão centro da cidade marcado como aproximado); logo de
  organização conhecida pelo mapa `LOGOS`; link que não é `http(s)` é descartado.
- Arte de cada ação: a imagem do post vem sem login de `https://www.instagram.com/p/<código>/embed/captioned/` com
  User-Agent de robô de prévia (`AGENTE_PREVIA` em `fotos_divulgacao.py`), arte inteira até 1080 px; uma página a cada
  3 s e parar no primeiro 429; nunca usar conta logada. Guardar no R2 do boralula (arte + miniatura de 480 px).
- Ações da varredura das redes: importar do CSV consolidado (rota `redes` de `publicar_acoes.py`), com as mesmas regras.
  Ação do feed sem post ganha a arte do post das redes que divulga a mesma ação.

### B. Regras do Gui (decisões 1 e 2, depois do consentimento)

- Telefone no "Eu vou!" (pedido uma vez, guardado no perfil), lista de quem vai com nome e telefone para quem organiza.
- Fila antes de publicar para todo envio novo; verificados publicam direto; limite por pessoa (na Agenda, 10 por dia e
  10 em análise).

### C. Ação com vários horários

O boralula tem um horário por evento (até 24 h); a Agenda tem ação com turnos e "Eu vou!" por turno. Sugestão de menor
impacto: cada turno vira um evento, ligados por um identificador de série; a página mostra "outros horários" e o
cadastro deixa adicionar vários. Turno que já terminou some das listas.

### D. O resto da Agenda

- Inicial com vitrine por cidade e foto por ação; cartaz desenhado para ação sem foto.
- Tipos que faltam: porta a porta, ligatona, bandeiraço, adesivaço, encontro.
- Hora aproximada ("sex 09/10, à noite") para divulgação que não diz a hora (o `fim_informado` do boralula é parecido).
- "Adicionar ao Google Agenda" além do .ics.
- "Fale com a gente" (`#/contato`, logado ou não, com freio) e aba Mensagens na moderação.
- Organização cadastrada pela própria pessoa, com link do perfil oficial e, em ação em nome dela, link do post oficial
  anunciando aquela ação.
- Botão de bloquear pessoa na moderação; ação cancelada que já esteve no ar continua abrindo pelo link, sem contato.
- Link da vaquinha (`https://doelula.com.br/`).
- Cópia diária cifrada do banco (`acoes-segundo-turno/.github/workflows/backup.yml` e `scripts/backup_banco.sh`).

### E. Mudança e desligamento (por último)

- Trazer do banco da Agenda: ações cadastradas pelo app, organizações (com selo, logo e link oficial), quem é membro de
  cada uma, moderadores, e as inscrições de turnos futuros ligadas ao e-mail da pessoa (quando ela entrar no boralula
  com o mesmo e-mail, encontra o "Eu vou" dela e dá o aceite). As importadas não migram: a importação do item A refaz.
- Redirecionar o endereço antigo: o `index.html` do repo público passa a mandar para o boralula.org, e
  `#/acao/<id>` vai para `#/e/<id novo>` por uma tabela de correspondência gerada na migração. Links que já circulam
  no WhatsApp não podem cair em página vazia.
- Desligar na Agenda: importação, snapshot de hora em hora, prévias; última cópia do banco guardada; projeto Supabase
  pausado depois de 30 dias sem uso.

## Como entregar

- PRs no agregador; o Carlos traz para a cópia dele antes do próximo envio, para o envio não apagar o que foi juntado.
- Itens A a E podem ir num PR ou em vários; o site do boralula não pode quebrar no meio. A Agenda continua no ar até o
  item E.
- Migração de banco do boralula segue as regras de lá (bloco de permissões, `ANON_ESPERADO`, `supabase/rascunho/`).
- Cada item atualiza o `docs/funcionalidades.md` do boralula.

## Como saber que acabou

- As ações da agenda do Comitê aparecem no boralula.org, com arte, sem duplicata, e se atualizam sozinhas.
- "Eu vou!" pede telefone e quem organiza vê a lista; publicação nova espera a moderação; o aceite novo foi pedido.
- Ação com vários horários funciona; os itens de D estão no ar ou recusados por escrito pela equipe.
- O endereço antigo e os links de ação levam ao boralula.org; a Agenda não importa nem publica mais nada.
