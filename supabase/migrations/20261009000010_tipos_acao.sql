-- Tipos de ação revistos em 2026-10-09 a partir das ações reais da agenda Bora Lula:
-- "Encontro" (plenária, assembleia, roda de conversa), "Ato", "Caminhada" (e carreata) e "Cultural" somam a maior
-- parte do feed e antes caíam em "roda de conversa" ou "outro".
-- "roda de conversa" vira "encontro" (as linhas existentes mudam junto, porque é o mesmo valor do enum).
-- Depois de aplicar, rode de novo a importação (scripts/publicar_acoes.py bora-lula --aplicar) para reclassificar
-- o que hoje está em "outro". O app aceita os dois nomes enquanto a migração não chega a produção.
alter type tipo_acao rename value 'roda de conversa' to 'encontro';
alter type tipo_acao add value if not exists 'ato';
alter type tipo_acao add value if not exists 'caminhada';
alter type tipo_acao add value if not exists 'cultural';
