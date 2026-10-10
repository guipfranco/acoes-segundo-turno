---
name: importar-acoes
description: Use quando a tarefa da Agenda Bora Lula é trazer ações de fora para o site - rodar a importação da agenda Bora Lula do Comitê Popular ou do consolidado das redes, mexer em scripts/bora_lula.py, publicar_acoes.py ou fotos_divulgacao.py, pegar a arte de posts do Instagram, geocodificar endereços, ou quando o feed parece parado ou desatualizado.
---

# Importar ações

Ações de fontes públicas entram pelo `scripts/publicar_acoes.py`, que chama a função SQL `importar_acoes`. Rodar com
`--aplicar` grava em PRODUÇÃO e só o Gui faz. Qualquer pessoa pode mexer no código dos scripts (com testes) e rodar o
ensaio, que não grava nada.

## Fontes

| Fonte | Como chega |
| --- | --- |
| `bora-lula` | feed JSON público da agenda Bora Lula do Comitê Popular (`comitepopular.org.br/.../agenda-bora-lula/acoes.js`) |
| `redes` | CSV consolidado da varredura de Instagram/redes, guardado no repo PRIVADO `levantamento/` (só o Gui tem) |

Toda importada vai ao ar com a etiqueta "Divulgação pública" até a moderação verificar; mudança vinda da fonte tira a
verificação (`docs/funcionalidades.md`). Dúvida (confiança baixa nas redes, cidade não reconhecida) não é descartada:
entra "em análise", fora do ar, com `acao.motivo_duvida`, e a moderação decide na Fila. De fora ficam só repetições e
datas fora da janela; o `revisao-*.csv` marca com `aprovação:` o que foi para a Fila. Reimportar não desfaz decisão da
moderação.

## Rotina (pasta do projeto, na `master` atualizada, com `SUPABASE_ACCESS_TOKEN` no `.env`)

1. Ensaio: `python scripts/publicar_acoes.py bora-lula`. Guarda o feed datado em `levantamento/bora-lula/` e escreve
   `levantamento/publicar-*.json` e `revisao-*.csv`.
2. **Conferir que o feed mudou**: se o arquivo novo é idêntico ao anterior (mesmo md5) e já passou mais de meio dia,
   desconfie de cache antigo, não de feed parado (o servidor de lá guarda por um ano; o script pede com `?t=`).
3. Ler o `revisao-*.csv` (o que ficou de fora e por quê; avisos com prefixo `aviso:`).
4. `python scripts/publicar_acoes.py bora-lula --aplicar`. Se houver arte nova, ele grava em `fotos/divulgacao/` e PARA
   sem tocar no banco.
5. `git add fotos && git commit -m "Fotos: ..." && git push`, esperar o workflow do Pages terminar.
6. Rodar o mesmo `--aplicar` de novo: confere que o Pages já serve cada foto (HEAD 200) e grava. "O Pages ainda não
   serve N fotos" = esperar e repetir.

Redes: `python scripts/publicar_acoes.py redes --de levantamento/<consolidado>.csv --feed levantamento/bora-lula/<data>.json [--aplicar]`.
O `fonte_id` das redes sai da própria linha: corrigir título ou hora troca o id e encerra a ação antiga. Se isso
derrubaria alguém que marcou "Eu vou", o `--aplicar` para; `--forcar` encerra assim mesmo (só com decisão do Gui).

Opções úteis: `--sem-fotos` (não busca arte nova), `--sem-geocodificar`, `--sem-encerrar`. Veja `--help`.

## Fotos e Instagram (o que funciona)

- A arte do post sai sem login de `https://www.instagram.com/p/<código>/embed/captioned/` com o User-Agent de robô de
  prévia do projeto (`AGENTE_PREVIA` em `scripts/fotos_divulgacao.py`): arte inteira até 1080 px e um `display_url` por
  slide do carrossel. O `og:image` da página do post é só plano B (vem recortado em quadrado e corta o cartaz).
- Uma página a cada 3 s; no primeiro 429 o script para e guarda o que já fez. Nunca usar conta logada nem o Chrome do
  Gui para ler posts em série: dá 429 na conta.
- Fotos ficam em `fotos/divulgacao/<código>.jpg` + `<código>-mini.jpg` e são servidas pelo Pages. As URLs estão
  gravadas no banco: **não renomear nem apagar** arquivos dessa pasta.

## Lugar e organização

- Endereço vira ponto exato pelo Nominatim (1 consulta/s, cache em `levantamento/geocache.json`) só se cair em prédio,
  número ou via dentro do município; senão fica o centro da cidade marcado como aproximado.
- Organização reconhecível ganha logo do Wikimedia Commons pelo mapa `LOGOS` em `scripts/bora_lula.py`.
- Link que não é `http(s)://` é descartado (o contato vira `organizador_chama`).

## Dados pessoais

`levantamento/` tem nomes e telefones: nunca copiar nada de lá para o repo, para teste, issue ou PR. Commit da varredura
é no repo privado (`git -C levantamento ...`). Ação importada nunca tem pessoa real como organizador.

## Testes

`python -m pytest tests/test_bora_lula.py tests/test_publicar_acoes.py tests/test_fotos_divulgacao.py -q`; a função
`importar_acoes` é testada em `tests/test_supabase.py` (pilha local, skill `mudar-banco`).
