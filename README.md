# Bora Lula

Site onde quem organiza ações pelo voto do Lula no 2º turno (panfletagem, bandeiraço, adesivaço, porta a
porta, ligatona, ato, encontro...) cadastra a ação, e quem quer ajudar acha uma perto de si e diz "Eu vou!".

**No ar:** https://guipfranco.github.io/acoes-segundo-turno/

Código aberto sob a licença MIT. Contribuições são bem-vindas: leia o [CONTRIBUTING.md](CONTRIBUTING.md).

## Como funciona

- **Inicial** sem mapa, estilo Meetup: busca por cidade (chuta a sua pela geolocalização), filtro "Quando",
  vitrine por cidade com foto por ação e bloco "Online". O mapa fica em `#/mapa`.
- **Página da ação** com turnos, local, quem organiza, "Eu vou!" e "Adicionar à agenda".
- **Conta** com login Google: perfil, minhas ações, cadastro de ação (nasce "em análise" e passa por
  moderação humana; organizações verificadas publicam direto).
- **Ações de divulgação** importadas da agenda Bora Lula do Comitê Popular, com crédito à fonte.
- **Fale com a gente** em `#/contato` para mandar sugestão ou avisar de erro.

## Como rodar no seu computador

O app é estático, sem build: a pasta `app/` é o site inteiro. Basta servir a pasta:

```sh
python -m http.server 8000 -d app
```

e abrir http://localhost:8000/?modo=exemplo. O `?modo=exemplo` usa dados fictícios em memória
(`app/dados.js`, pessoas e organizações inventadas), então tudo funciona sem banco nem login: cadastrar
ação, moderar, inscrever-se. É assim que a maior parte das mudanças de interface é feita e testada.

Sem `?modo=exemplo` o app lê o Supabase configurado em `app/config.js` (a produção). Para mexer em banco,
regras de acesso e funções SQL (pasta `supabase/`), rode a pilha local do Supabase: veja `docs/operacao.md`.

## Testes

```sh
python -m pytest tests -q          # telas e scripts (test_supabase.py só roda com a pilha local)
node --test "tests/js/*.test.js"   # camada de dados
```

## Mapa do repositório

| Pasta | O que é |
| --- | --- |
| `app/` | o site: HTML, CSS e JS sem framework. Camada de dados em `api.js` (`api-exemplo.js` ou `api-supabase.js`) |
| `supabase/migrations/` | esquema, RLS e funções SQL; `supabase/functions/` tem a função de prévia de link |
| `scripts/` | importação de ações (Bora Lula), fotos, snapshot público, cópia do banco |
| `tests/` | pytest e `node --test` |
| `docs/` | spec (`docs/superpowers/specs/`), desenho visual, operação (`docs/operacao.md`), capturas |
| `fotos/divulgacao/` | fotos das ações importadas, servidas pelo Pages |
| `.github/workflows/` | publicação no Pages (com prévia por branch em `/previa/<branch>/`), cópia diária do banco |

## Dados e privacidade

Não há dado pessoal real no repositório: pessoas de exemplo são inventadas. Ações e organizações públicas
(partidos, mandatos, movimentos, comitês) aparecem com crédito à fonte. Política de privacidade e responsável
pelo site estão no próprio app.
