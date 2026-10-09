# CLAUDE.md

Repo da plataforma de ações do 2º turno (voto do Lula). Nasceu do `mapa-segundo-turno` em 2026-10-08.

- Tudo em pt-BR, datas AAAA-MM-DD. Push logo depois de cada commit.
- `mockup/` é protótipo estático, sem build. Publicado em https://guipfranco.github.io/acoes-segundo-turno/
  (GitHub Pages via `.github/workflows/pages.yml`, só a pasta `mockup/`; repo público desde 2026-10-08) e também
  como artifact do claude.ai https://claude.ai/artifact/5FLiCyZHCJD6ADZbofmrjL ; o mapa base no artifact é o
  Protomaps da RMSP copiado dos assets do artifact do mapa principal (ids em mockup/fundo.js); fora dele o
  mockup usa tiles do OpenStreetMap.
- Sem dado pessoal real no repo. Como o repo é público, pessoas e organizações de exemplo são inventadas
  (nada de mandato, partido ou movimento real nos dados).
- Estado em 2026-10-08: mockup navegável. Inicial sem mapa (estilo Meetup): busca por cidade que chuta a
  cidade pela geolocalização, filtro "Quando" (em breve, hoje, amanhã, esta semana, fim de semana, próxima
  semana, escolher datas), formato presencial ou online, vitrine por cidade (SP, Recife, BH, Porto Alegre,
  Salvador) com foto placeholder por ação e bloco "Online". Mapa com lista que acompanha o enquadramento em
  `#/mapa`. Ação online: `lugar.online: true`, sem pino nem minimapa. Desktop (≥ 900 px) com cabeçalho no topo e
  página da ação em duas colunas. Fotos das ações vêm do Wikimedia Commons (campo `foto` com crédito). Spec em `docs/superpowers/specs/`, desenho visual em
  `docs/2026-10-08-design-mockup.md`, capturas em `docs/capturas/`. Testes: `python -m pytest tests`.
- Decisões do Gui: inscrição com nome e telefone desde a v1; moderação humana por voluntários no
  início, automação depois; uma vaquinha só, geral, apontando para arrecadação oficial; busca por
  lugar livre (Brasil inteiro), referência visual Airbnb/Meetup.
- Para republicar o artifact: publicar `mockup/index.html` com os arquivos `dados.js`, `lugares.js`,
  `fundo.js` e `leaflet.css` ao lado (o artifact só carrega stylesheet próprio). Fora do artifact o
  mapa usa tiles do OpenStreetMap.
- Pages publica a cada push em `master` que toque `mockup/`.
- Levantamento de ações reais (2026-10-08): pasta `levantamento/` (no .gitignore, nunca versionar: tem nomes e links)
  guarda a varredura de fontes e o balanço em `levantamento/RODADA-1.md`. Fonte principal: agenda "Bora Lula" do
  Comitê Popular (JSON público). `python scripts/bora_lula.py` baixa o feed, guarda cópia datada em
  `levantamento/bora-lula/` e gera `levantamento/dados-bora-lula.js` no formato do mockup (copiar sobre
  `mockup/dados.js` só localmente para ver; dados reais no site publicado é decisão do Gui). Testes em
  `tests/test_bora_lula.py`.
