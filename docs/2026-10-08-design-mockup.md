# Desenho visual do mockup (2026-10-08)

Referências pedidas pelo Gui: Airbnb (busca por lugar, lista que acompanha o mapa, etiquetas nos pinos) e
Meetup (cards com cara de evento).

## Identidade do Comitê Popular do Lula (2026-10-10)

O site passou a ser uma iniciativa do Comitê Popular do Lula e, no mesmo dia, mudou de nome: de "Eleja o Lula"
para "Bora Lula" (pedido do Gui). Vale o "Guia de interface web e apps" do
Comitê (v1, 2026-10) e o `tokens.css` que o acompanha, copiado sem mudança para `app/tokens.css`. `app/marca.css`
foi reescrito sobre esses tokens e substitui a seção "Identidade da campanha" abaixo, que fica só como histórico.

- Decisões do Gui: logo do Comitê + nome do site no cabeçalho; só visual e acessibilidade (telas e fluxos
  iguais); rodapé e privacidade dizem só "Uma iniciativa do Comitê Popular do Lula" (o Gui tirou o nome dele, o
  "sem vínculo", o "Nenhuma divulgação paga" e o link do código no GitHub).
- Cards da inicial: a imagem preenche a área 4:5 (`object-fit: cover`), sem o fundo desfocado; corta a sobra dos
  stories 9:16 e das artes quadradas. A página da ação segue com a arte inteira.
- Cores `--cp-*`: vermelho 500 para botões e links, 600 no hover, 700 pressionado e erro; verde e azul de texto
  só na versão 700; amarelo só em sublinhado do item ativo, bordas de aviso e anel de foco sobre vermelho.
- Montserrat 500/700/800/900, escala fluida do guia; caixa-alta só na frase da inicial e nos rótulos (etiquetas).
- Botões em pílula de 44 px (52 px no "Eu vou!", 36 px só a partir de 1024 px); contorno vermelho no secundário.
- Campos com borda `--cp-border-strong`, foco com anel grafite; erro com ícone ⚠ e texto.
- Cards brancos com borda, raio 8 e padding 16; sem foto, faixas amarela, azul e verde do logo sobre a cor do tipo.
- Celular: barra de abas branca, aba ativa vermelha e sublinhada, respeita a área segura; logo no topo da inicial.
  Desktop: cabeçalho vermelho de 64 px só com "Bora Lula" (o Gui achou a barra com o logo alta demais; o logo
  fica no topo da inicial, 180 px), item ativo da altura da barra com sublinhado amarelo colado na borda de baixo,
  "Cadastrar ação" branco. Ícone do Perfil só no contorno, logado ou não. Respiro de 24 a 32 px entre as partes
  do topo da inicial.
- Favicon e ícone: a mão do "L" sobre o vermelho, tirada do PDF do guia. Sombra só em camadas (menus, gaveta).
- Fica para depois: `capa.png` (imagem de compartilhamento) ainda é a antiga.

## Identidade da campanha (2026-10-09)

Pedido do Gui: mais cor e mais perto da identidade da campanha do Lula. Fonte: manual "Guia simplificado
design" Lula 2026 (PDF no Drive da campanha, pasta Lula-Haddad-Tebet). Entre três rascunhos (só um toque de
cor, marca forte com leitura limpa, imersão total), o Gui escolheu **marca forte**. Mora em `app/marca.css`,
que vem depois do `<style>` do `index.html` e substitui os tokens e princípios abaixo onde eles conflitam:

- Paleta do manual: vermelho `#FD0000` (caixas grandes), vinho `#A20301` (links, degrau 3D dos botões),
  amarelo `#FFD400`, verde `#00B923`, verde-escuro `#006820` (selo, texto na caixa amarela), azul `#0034D2`.
  Onde há letra branca pequena (barra, botões) ou texto vermelho, o vermelho é `#E60000` (4,8:1 com o branco).
- Tipo: Archivo condensado black em caixa alta nos títulos (no lugar da Transducer Condensed Black) e
  Montserrat no texto (no lugar da Gotham); as do manual são do Adobe Fonts, pagas.
- Barra vermelha; "2º turno" num selo amarelo inclinado; Cadastrar ação em amarelo.
- Frase da inicial numa caixa amarela inclinada com letra verde-escura, como "O Brasil pronto pra mais".
- Título de cada bloco da inicial numa caixa inclinada com lateral 3D, alternando vermelho, verde, azul e
  amarelo; Online em azul. Hora da foto em selo amarelo; botões com degrau em vinho.
- Cards e listas seguem em fundo branco para ler bem. Nada do logo oficial: o site não é da campanha.

## Tokens

- Cores: papel `#FFFFFF`; asfalto (texto) `#17171A`; vermelho da campanha `#D6232E` (só em ações e no Doar);
  vinho `#8C1420` (destaque "área prioritária", pino selecionado); névoa `#EEF0F3` (bordas, fundo da gaveta);
  cinza `#6E6E76` (texto secundário); verde do selo `#1F7A3E`.
- Tipo: Public Sans (a mesma do mapa principal), uma família só. Título 26 px / 800 / -0.02 em;
  corpo 16 px / 400 / 1,45; secundário 13 px.
- Layout celular: mapa ocupa a tela; barra de busca flutuante no topo; linha rolável de tipos embaixo dela;
  gaveta arrastável sobe de baixo com "N ações nesta área" e os cards; barra de navegação fixa com Doar.
  Desktop (≥ 900 px): coluna de 440 px à esquerda (busca, tipos, lista) e mapa à direita.
- Pinos: etiqueta branca com o ícone do tipo e "sáb 10h"; a selecionada fica vinho com letra branca.
- Card: bloco quadrado com o ícone do tipo numa cor suave por tipo; título; organizador com selo; linha de
  dia e hora; linha de bairro e distância; "3 vão" e "Área prioritária".

## Princípios

- O elemento memorável é a gaveta sobre o mapa com as etiquetas de hora nos pinos. O resto fica quieto.
- Nada de texto em caixa alta, nada de pontos no meio das linhas de metadados, nada de rótulo numerado.
- Vermelho é ação: botões "Vou", "Publicar", "Doar". Não aparece em decoração.
- Texto na voz da interface: "Crie a primeira ação", "Marque o lugar no mapa", "Publicado".

## Revisão contra o padrão genérico

Primeira versão tinha chips iguais para tudo, cards idênticos com a mesma sombra e cinza no lugar de
hierarquia. Trocado por: um único elemento com sombra forte (a gaveta), cards sem sombra separados por
linha, tipos como linha rolável com ícone grande e rótulo pequeno, e o mapa como protagonista.

## Inicial sem mapa (segunda rodada, 2026-10-08)

Pedido do Gui: entrar como Airbnb e Meetup, sem mapa na primeira tela. A inicial passa a ser: frase da
campanha, busca grande "Em que cidade você está?", linha de filtros do Meetup (Quando, Formato, tipo de
ação) e vitrine de ações por cidade, cada uma com foto. A cidade de "Perto de você" é chutada pela
geolocalização (São Paulo se não der), com aviso "Chutamos a cidade". Depois vêm Recife, Belo Horizonte,
Porto Alegre, Salvador e o bloco "Online, de qualquer lugar". O mapa continua existindo em `#/mapa`.

- Filtro "Quando" explícito: Em breve (padrão, próximos turnos primeiro), Hoje, Amanhã, Esta semana,
  Fim de semana, Próxima semana, Escolher datas (campos "de" e "até"). Cada ação entra com o primeiro
  turno que cabe no intervalo.
- Formato: Presencial e online, Presencial, Online. Ação online não tem pino nem minimapa; na página
  diz "Você participa de casa. O link da chamada vai para quem se inscreve".
- Foto: placeholder em CSS (gradiente da cor do tipo e o ícone), com a hora no canto. A foto real
  entra no mesmo lugar depois. Sem imagem externa.
- Capturas: `r7-inicio-celular.png`, `r8-inicio-datas.png`, `r9-mapa-celular.png`, `r10-inicio-desktop.png`.

## Desktop de verdade e fotos reais (terceira rodada, 2026-10-08)

Pedido do Gui: a barra de baixo é coisa de celular; no PC a experiência tem que ser pensada para PC. E as
fotos dos cards devem ser imagens, não ícones.

- A partir de 900 px a navegação vira cabeçalho fixo no topo: marca "Eleja o Lula" à esquerda, itens
  em linha com ícone e texto, Doar como botão à direita. No celular continua a barra de baixo.
- Páginas internas mais largas (760 px; criar ação em 620 px). A página da ação fica em duas colunas:
  conteúdo à esquerda e um cartão fixo à direita com os turnos e o botão "Vou", que acompanha a rolagem.
- Inicial: filtros em linha, grade de quatro cards, hover sobe a foto e sublinha o título.
- Fotos: cada ação tem `foto {url, credito, pagina}`. O card mostra a imagem sobre o fundo da cor do tipo;
  se a imagem falhar, fica o fundo com o ícone. Na página da ação a foto vira capa 16:9 com crédito e link.
  As fotos de exemplo vêm do Wikimedia Commons (licenças CC e domínio público), inclusive do acervo
  CC BY-SA do Lula Oficial. Criar ação tem campo "Foto da ação (link, opcional)".
- Capturas: `r10-inicio-desktop.png`, `r11-acao-desktop.png`, `r4-desktop.png` (mapa), `r6-criar-lugar.png`.
