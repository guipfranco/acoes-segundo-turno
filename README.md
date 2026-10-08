# Ações do 2º turno

Plataforma onde quem organiza ações para eleger o Lula no 2º turno (panfletagem, adesivaço, roda de
conversa, ligatona...) cadastra a ação, e quem quer ajudar acha uma perto de si e se inscreve.
Desenho em `docs/superpowers/specs/2026-10-08-plataforma-acoes-design.md`.

Estado: **mockup navegável** em `mockup/index.html`, publicado em https://guipfranco.github.io/acoes-segundo-turno/ (GitHub Pages, workflow em `.github/workflows/pages.yml`) e como artifact do claude.ai em https://claude.ai/artifact/5FLiCyZHCJD6ADZbofmrjL. Dados de exemplo fictícios (pessoas e organizações inventadas). Capturas em `docs/capturas/`. Inicial sem mapa, estilo Meetup: busca por cidade, filtro de data com intervalo, formato presencial ou online, vitrine de ações por cidade com foto; o mapa fica em `#/mapa`. Desenho visual em `docs/2026-10-08-design-mockup.md`. A busca por lugar usa `mockup/lugares.js` (municípios do IBGE via kelvins/municipios-brasileiros, MIT, e os 96 distritos da capital). Dados de exemplo em
`mockup/dados.js`. Testes: `python -m pytest tests`.
