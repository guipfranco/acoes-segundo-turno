#!/usr/bin/env bash
# Cópia do banco: esquema (public) e dados de public, auth e storage, num .tar.gz cifrado com senha.
# O plano Free do Supabase não faz backup; sem isto, um comando errado no SQL Editor apaga inscrições e
# cadastros sem volta. Roda todo dia no workflow .github/workflows/backup.yml e grava o arquivo cifrado como
# artefato (o repo é público e qualquer pessoa logada no GitHub baixa artefato: por isso a cifra).
#
#   bash scripts/backup_banco.sh local     [pasta]   # pilha local (npx supabase start)
#   bash scripts/backup_banco.sh producao  [pasta]   # projeto ligado; precisa de SUPABASE_ACCESS_TOKEN e SUPABASE_DB_PASSWORD
#
# Sempre precisa de BACKUP_SENHA (a senha da cifra; guarde no gerenciador de senhas, sem ela o arquivo é lixo).
# Sai em <pasta>/banco-<data>.tar.gz.enc (pasta padrão: backups/, fora do git). Para abrir e restaurar, veja
# docs/operacao.md, seção "Cópia do banco".
set -euo pipefail

alvo="${1:?uso: backup_banco.sh local|producao [pasta]}"
saida="${2:-backups}"
: "${BACKUP_SENHA:?defina BACKUP_SENHA (senha da cifra)}"
# CLI 2.x: escolhe o pg_dump da versão do servidor. O 1.200.3 do package.json traz pg_dump 15 e a produção
# roda Postgres 17 ("aborting because of server version mismatch", visto em 2026-10-10).
CLI="npx --yes supabase@${SUPABASE_CLI:-2.120.0}"

case "$alvo" in
  local) flags=(--local) ;;
  producao)
    : "${SUPABASE_DB_PASSWORD:?defina SUPABASE_DB_PASSWORD}"
    flags=(--linked -p "$SUPABASE_DB_PASSWORD") ;;
  *) echo "alvo deve ser local ou producao" >&2; exit 2 ;;
esac

data="$(date -u +%Y-%m-%dT%H%MZ)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

$CLI db dump "${flags[@]}" -f "$tmp/esquema.sql"
$CLI db dump "${flags[@]}" --data-only --use-copy -s public,auth,storage -f "$tmp/dados.sql"
echo "linhas: esquema $(wc -l < "$tmp/esquema.sql"), dados $(wc -l < "$tmp/dados.sql") (tabelas: $(grep -c '^COPY' "$tmp/dados.sql"))"

tar -czf "$tmp/banco.tar.gz" -C "$tmp" esquema.sql dados.sql
mkdir -p "$saida"
arquivo="$saida/banco-$data.tar.gz.enc"
openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -in "$tmp/banco.tar.gz" -out "$arquivo" -pass env:BACKUP_SENHA
echo "gravado: $arquivo ($(du -k "$arquivo" | cut -f1) KB)"
