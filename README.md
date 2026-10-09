# Ações do 2º turno

Plataforma onde quem organiza ações para eleger o Lula no 2º turno (panfletagem, adesivaço, roda de
conversa, ligatona...) cadastra a ação, e quem quer ajudar acha uma perto de si e se inscreve.
Desenho em `docs/superpowers/specs/2026-10-08-plataforma-acoes-design.md`.

Estado: **app em `app/`**, publicado em https://guipfranco.github.io/acoes-segundo-turno/ (GitHub Pages, workflow em `.github/workflows/pages.yml`, só a pasta `app/`). O site publicado ainda roda com dados de exemplo até `app/config.js` ser preenchido (ainda não ligado em produção; ver `docs/operacao.md`). Lê do Supabase (esquema, RLS e funções em `supabase/migrations/`) com login Google: Inscreva-se e Minhas inscrições funcionam de verdade; Criar ação, Minhas ações e Fila de moderação só existem no modo exemplo até a próxima etapa. Abra com `?modo=exemplo` para navegar com dados fictícios (pessoas e organizações inventadas, em `app/dados.js`); sem Supabase configurado em `app/config.js` o app já abre assim, e também existe como artifact do claude.ai em https://claude.ai/artifact/5FLiCyZHCJD6ADZbofmrjL. Camada de dados em `app/api.js` (escolhe `api-exemplo.js` ou `api-supabase.js`). Inicial sem mapa, estilo Meetup: busca por cidade, filtro de data com intervalo, formato presencial ou online, vitrine de ações por cidade com foto; o mapa fica em `#/mapa`. A busca por lugar usa `app/lugares.js` (municípios do IBGE via kelvins/municipios-brasileiros, MIT, e os 96 distritos da capital). Capturas em `docs/capturas/`; desenho visual em `docs/2026-10-08-design-mockup.md`.

Operação (banco local, migrações, papéis, o que falta para ir ao ar): `docs/operacao.md`.
Testes: `python -m pytest tests -q` e `node --test "tests/js/*.test.js"`.
