#!/usr/bin/env bash
# Monta o site do GitHub Pages em _site/ (ou no diretório do 1º argumento):
#   raiz           -> app/ da master (produção)
#   previa/<nome>/ -> app/ de cada outra branch do origin, para o Gui conferir antes do merge
# A prévia abre com dados de exemplo (?modo=real liga o Supabase de produção), não conta visita
# no GoatCounter, não é indexada e mostra uma etiqueta com o nome da branch.
# Usado pelo .github/workflows/pages.yml; roda local também (precisa de git fetch antes).
set -euo pipefail

saida="${1:-_site}"
rm -rf "$saida"
mkdir -p "$saida/previa"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

extrair() { # extrair <ref> <destino>: copia a pasta app/ da ref; falha se a ref não tem app/
  rm -rf "$tmp/x" && mkdir -p "$tmp/x"
  git archive "$1" app | tar -x -C "$tmp/x" || return 1
  mkdir -p "$2" && cp -r "$tmp/x/app/." "$2/"
}

extrair origin/master "$saida"

itens=""
for ref in $(git for-each-ref --format='%(refname:short)' refs/remotes/origin); do
  branch="${ref#origin/}"
  case "$branch" in master|HEAD|origin) continue ;; esac
  nome="$(printf '%s' "$branch" | tr -c 'A-Za-z0-9._-' '-')"
  destino="$saida/previa/$nome"
  extrair "$ref" "$destino" 2>/dev/null || { echo "sem app/: $branch"; continue; }

  # index.html: não indexar e sem GoatCounter (sem o script, contar() não faz nada)
  sed -i -e 's|<meta charset="utf-8">|&\n<meta name="robots" content="noindex">|' \
         -e '/window\.goatcounter=/d' -e '/gc\.zgo\.at/d' "$destino/index.html"

  # config.js: exemplo por padrão e etiqueta da prévia
  cat >> "$destino/config.js" <<JS

// ---- prévia da branch $branch (acrescentado por scripts/montar_pages.sh, não existe no repo) ----
(function () {
  var real = new URLSearchParams(location.search).get('modo') === 'real';
  if (!real && window.CONFIG) delete window.CONFIG.supabase;
  document.addEventListener('DOMContentLoaded', function () {
    var e = document.createElement('div');
    e.textContent = 'Prévia: $nome · ' + (real ? 'dados reais' : 'dados de exemplo');
    e.style.cssText = 'position:fixed;top:0;left:50%;transform:translateX(-50%);z-index:99999;pointer-events:none;' +
      'background:#ffd400;color:#000;font:600 11px/1.6 system-ui,sans-serif;padding:0 8px;border-radius:0 0 6px 6px;opacity:.9';
    document.body.appendChild(e);
  });
})();
JS
  data="$(git log -1 --format=%cd --date=format:'%Y-%m-%d %H:%M' "$ref")"
  itens="$itens<li><a href=\"$nome/\">$nome</a> <small>(último commit $data, <a href=\"$nome/?modo=real\">dados reais</a>)</small></li>"
  echo "prévia: $branch -> previa/$nome/"
done

cat > "$saida/previa/index.html" <<HTML
<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="robots" content="noindex">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Prévias</title>
<style>body{font:16px/1.6 system-ui,sans-serif;margin:24px 16px;max-width:640px}small{color:#666}</style></head>
<body><h1>Prévias por branch</h1><p><a href="../">Produção (master)</a></p>
<ul>${itens:-<li>Nenhuma branch aberta.</li>}</ul></body></html>
HTML
