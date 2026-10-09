// Escolhe o miolo da camada de dados: Supabase quando configurado, senão o exemplo em memória.
// Forçar o exemplo mesmo com Supabase configurado: abrir com ?modo=exemplo
(function () {
  const forcaExemplo = new URLSearchParams(location.search).get('modo') === 'exemplo';
  const cfg = window.CONFIG && window.CONFIG.supabase;
  const temLib = !!(window.supabase && window.ApiSupabase);
  if (cfg && !forcaExemplo && !temLib) console.warn('Supabase indisponível; usando dados de exemplo');
  if (cfg && !forcaExemplo && temLib) window.API = window.ApiSupabase.criar(cfg);
  else window.API = window.ApiExemplo.criar(window.DADOS);
})();
