# Plano de expansão da varredura de ações (2026-10-08)

Contexto: a rodada 1 (ver `levantamento/RODADA-1.md`, fora do git) achou 464 ações únicas no Brasil até 2026-10-25.
A parte estruturada veio do feed Bora Lula do Comitê Popular (importador em `scripts/bora_lula.py`). A parte das
redes sociais foi feita só com a base de São Paulo (planilha de candidatos da coligação) e com contas nacionais.
Este plano diz como levar a mesma busca aos outros estados sem estourar uma sessão.

## O que aprendemos (vale para qualquer território)

| Fonte | Rendimento | Como usar |
|---|---|---|
| Feed Bora Lula | alto, 27 UFs, mas desigual | script 2x/dia; é a base. Onde o feed é ralo, as redes importam mais. |
| Instagram de **organizações de ponta** (PT municipal/estadual, PSOL, PCdoB local, UNE/UEE/DCEs, coletivos, agendas locais) | alto | ler legenda via og:description; card de agenda semanal está na imagem (2º slide). |
| Instagram de **candidato com mandato** | 1 em 5 rende, sempre os mesmos | varrer uma vez para descobrir quem publica agenda; depois só revisitar quem rendeu. |
| X | médio | buscar por data ("11/10") e convocação ("amanhã", "domingo") + capital. Não por tipo de ação. |
| Telegram | baixo, exceto agendas locais em imagem (ex.: Agenda Progressista DF) | procurar "agenda progressista <cidade>" e similares; não gastar com busca genérica. |
| Facebook | baixo | só aba Eventos de "PT <cidade>". |
| Sympla e afins | zero | não voltar. |
| WhatsApp | não testado; canal "Exército do Lula" (1,2 mi) apareceu em 3 frentes | rodada própria via WAHA. |

## Ordem dos estados

Critério: ações encontradas por milhão de eleitores (quanto menor, mais a varredura acrescenta) cruzado com peso
eleitoral. Números de 2026-10-08.

| Prioridade | UFs | Ações/milhão | Por quê |
|---|---|---|---|
| 1 | SC, PR, MG, GO, RS | 0,7 a 1,9 | Grandes e quase vazios no feed. |
| 2 | CE, MA, AM, BA, PI, PB, MS | 1,9 a 2,5 | Médios, cobertura fraca. |
| 3 | SP (interior), SE, PA, AL, PE, ES, RN | 2,3 a 4,2 | SP capital já foi varrida; o interior não. |
| 4 | RJ, MT, AC, AP, RR, DF | > 4,9 | Já razoáveis; DF tem agenda diária própria. |

## Unidade de trabalho: o kit do estado

Para cada UF, um arquivo `levantamento/territorios/<UF>.csv` com as contas a vigiar, uma por linha:
`uf,tipo,nome,instagram,outros,prioridade,observacao`, onde `tipo` é organização ou candidato.

Composição alvo por estado (20 a 30 linhas):
- Partidos: diretório estadual e das 3 a 5 maiores cidades (PT, PSOL, PCdoB, PSB, Rede, PDT quando aliado).
- Juventudes e estudantes: JPT, UJS, UEE, DCEs das federais da capital.
- Movimentos e centrais: CUT estadual, MST, MTST, Levante, CMP, comitês populares, Frente Brasil Popular.
- Agendas locais: qualquer "agenda progressista", "agenda da esquerda", "bora lula <UF>".
- Candidatos: deputados estaduais e federais com mandato dos partidos aliados que tenham base militante
  (listas públicas das assembleias e da Câmara; o handle vem de busca).

Fontes para montar o kit sem navegador: sites dos partidos, páginas das assembleias legislativas e da Câmara,
busca na web. Dá para fazer com subagentes baratos (Sonnet ou Haiku), um por estado, em paralelo, sem usar o Chrome.

## Fases e sessões

Cada fase cabe numa sessão. O quadro de progresso fica em `levantamento/territorios/ESTADO.md`
(uma linha por UF: kit pronto em, varrido em, ações achadas, perfis que renderam).

1. **Sessão de kits** (sem Chrome). Subagentes montam os kits das UFs de prioridade 1 e 2 (12 estados). Saída: 12 CSVs
   e o quadro de progresso. Custo baixo. Pode incluir a lista de candidatos do TSE para os partidos aliados, se existir
   em CSV aberto; senão, as assembleias.
2. **Sessões de varredura**, 3 a 4 UFs por sessão, um subagente Sonnet por UF, cada um na própria aba do Chrome.
   Mesmo protocolo da rodada 1 (`levantamento/PROTOCOLO.md`): Instagram do kit, X por data + capital, Facebook
   "PT <capital>", Telegram "agenda <cidade>". Limite de ritmo do Instagram: no máximo 2 subagentes nele ao
   mesmo tempo, um perfil por 40 s. Saída por UF: `acoes-<UF>.csv`, `frente-<UF>.md` e o quadro atualizado.
   Prioridade 1 e 2 = 3 a 4 sessões.
3. **Rotina diária até 25/10** (sessão curta ou agendada): `python scripts/bora_lula.py`; revisita dos perfis que
   renderam (marcados no quadro) 2x/dia; X por data 1x/dia; consolidação com dedup e um "delta do dia".
4. **WhatsApp via WAHA**: rodada própria quando o acesso existir. Primeiro o canal Exército do Lula e os links
   públicos por estado em `lula.com.br/mobilizacao/`; depois os grupos que o Gui indicar.
5. **Reconferir `pelobrasil.lula.com.br`** a cada sessão: se a plataforma oficial voltar, ela substitui boa parte
   das fases 2 e 3.

## Datas que mudam o volume
- 11/10 (dom): Dia Nacional de Mobilização. Programação local sai entre 9 e 10/10.
- 18/10 (sáb): Ato da Virada em centenas de cidades. Programação deve sair entre 14 e 16/10.
Varrer na véspera dessas datas rende mais que em qualquer outro dia.

## Regras que continuam valendo
- Só leitura nas redes: nada de seguir, curtir, entrar em grupo ou enviar mensagem.
- Nada de `levantamento/` vai para o git (nomes, telefones, links de grupo).
- Dados reais no site publicado só com decisão do Gui, e de preferência depois de um contato com o Comitê Popular.

## Publicar os dados reais (liberado pelo Gui em 2026-10-09)
Ações e organizações públicas podem ir para produção (Supabase) e para o modo exemplo (`app/dados.js`). O app agora lê
do Supabase em produção, então publicar = inserir no banco, não trocar o `dados.js`. Os sete itens abaixo foram
resolvidos em 2026-10-09 (migração `supabase/migrations/20261009000001_origem_importacao.sql`, script
`scripts/publicar_acoes.py`, tela); como rodar está em `docs/operacao.md`, seção "Importar ações de fontes públicas".
1. **Organizador de sistema.** Feito: a migração cria a pessoa "Agenda Bora Lula" (uuid fixo `...b07a`, usuário banido,
   sem senha nem provedor) e `importar_acoes` assina toda ação importada com ela. Nunca pessoa real.
2. **Coordenada obrigatória.** Feito: ação presencial recebe o centro do município (`app/lugares.js`) com
   `acao.lugar_aproximado = true`; região administrativa do DF vira Brasília com o bairro; sem cidade reconhecida vai
   para `levantamento/revisao-<fonte>-<data>.csv`. A tela avisa "ponto aproximado", o minimapa mostra um círculo e o
   mapa abre os pinos da mesma cidade em espiral.
3. **Link da divulgação original.** Feito: `contato_tipo = 'divulgacao'` com o link em `contato_link`, exposto na view
   como `link_divulgacao`; crédito da fonte na descrição. A tela troca "Inscreva-se" por "Ver a divulgação original" e
   a função `inscrever` recusa (`sem_inscricao`).
4. **Idempotência.** Feito: `acao.fonte` + `acao.fonte_id` (únicos) e `importada_em`; `importar_acoes(fonte, itens)`
   insere ou atualiza, encerra o que sumiu da fonte, republica o que voltou e respeita recusa de moderador.
5. **Consolidado das redes.** Feito: `publicar_acoes.py redes --de CSV --feed JSON` geocodifica por cidade, descarta o que
   já vem do feed (mesmo link, ou mesma data e cidade com título parecido), sem Lula explícito e confiança baixa.
6. **Miudezas.** Feito: bairro extraído do fim do endereço e `lugarCurto` sem vírgula sobrando; organizador de
   sistema chama "Agenda Bora Lula"; mesmo ato com títulos diferentes (mesma data, cidade, hora e local) fica só o
   primeiro id e o resto vai para a revisão.
7. `levantamento/` continua fora do git; `supabase/seed.sql` continua só com dados fictícios.
