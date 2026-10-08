# Desenho visual do mockup (2026-10-08)

Referências pedidas pelo Gui: Airbnb (busca por lugar, lista que acompanha o mapa, etiquetas nos pinos) e
Meetup (cards com cara de evento).

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
